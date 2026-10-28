from flask import request
from flask_login import current_user
from flask_socketio import emit
from app.extensions import socketio, db
from app.models.auction import AuctionRoom, AuctionPlayer
from app.models.team import Team
from app.services.auction_service import (
    select_franchise,
    toggle_team_ready,
    start_auction_service,
    pause_auction_service,
    resume_auction_service,
    advance_to_next_player,
    get_available_teams_for_room
)
from app.services.bidding_service import validate_and_place_bid, finalize_current_player

@socketio.on("select_team")
def handle_select_team(data):
    """User selects an IPL franchise in the lobby."""
    if not current_user.is_authenticated:
        emit("error_message", {"message": "You must be logged in to select a team."})
        return

    room_id = data.get("room_id")
    team_code = data.get("team_code")
    
    success, result = select_franchise(room_id, current_user.id, team_code)
    if not success:
        emit("error_message", {"message": result})
        return

    channel = f"auction_{room_id}"
    available_franchises = get_available_teams_for_room(room_id)
    room = db.session.get(AuctionRoom, room_id)
    
    # Broadcast updated team list and franchise availability
    emit("team_selected", {
        "user_id": current_user.id,
        "username": current_user.username,
        "team": result.to_dict(),
        "teams": [t.to_dict() for t in room.teams],
        "available_franchises": available_franchises
    }, room=channel)


@socketio.on("toggle_ready")
def handle_toggle_ready(data):
    """Participant marks team as ready/unready."""
    if not current_user.is_authenticated:
        return
    room_id = data.get("room_id")
    success, is_ready = toggle_team_ready(room_id, current_user.id)
    if success:
        channel = f"auction_{room_id}"
        team = Team.query.filter_by(auction_id=room_id, owner_id=current_user.id).first()
        emit("team_ready_updated", {
            "team_id": team.id,
            "team_code": team.team_code,
            "is_ready": is_ready
        }, room=channel)


@socketio.on("start_auction")
def handle_start_auction(data):
    """Host starts the live auction."""
    if not current_user.is_authenticated:
        emit("error_message", {"message": "Authentication required."})
        return

    room_id = data.get("room_id")
    success, room_or_msg = start_auction_service(room_id, current_user.id)
    if not success:
        emit("error_message", {"message": room_or_msg})
        return

    channel = f"auction_{room_id}"
    room = room_or_msg
    emit("auction_started", {
        "room_id": room.id,
        "current_player": room.current_player.to_dict() if room.current_player else None,
        "timer_duration": room.get_rules().get("timer_duration", 30),
        "bid_deadline": room.bid_deadline.isoformat() if room.bid_deadline else None
    }, room=channel)


@socketio.on("place_bid")
def handle_place_bid(data):
    """Participant submits a bid on the current player."""
    if not current_user.is_authenticated:
        emit("error_message", {"message": "You must be logged in to place a bid."})
        return

    room_id = data.get("room_id")
    custom_amount = data.get("amount")

    success, message, bid_data = validate_and_place_bid(room_id, current_user.id, custom_amount)
    if not success:
        emit("error_message", {"message": message})
        return

    channel = f"auction_{room_id}"
    # Broadcast accepted bid to everyone in the room!
    emit("bid_updated", bid_data, room=channel)


@socketio.on("host_hammer")
def handle_host_hammer(data):
    """Host strikes the gavel/hammer to finalize and sell current player to the highest bidder."""
    if not current_user.is_authenticated:
        emit("error_message", {"message": "You must be logged in."})
        return
    room_id = data.get("room_id")
    room = db.session.get(AuctionRoom, room_id)
    if not room or room.host_id != current_user.id:
        emit("error_message", {"message": "Only the auction host can strike the hammer."})
        return
    if room.status != "active" or not room.current_player_id:
        emit("error_message", {"message": "No active player currently on the hammer."})
        return

    channel = f"auction_{room.id}"
    is_sold, result_data = finalize_current_player(room.id)
    if is_sold:
        emit("player_sold", result_data, room=channel)
    else:
        emit("player_unsold", result_data, room=channel)

    from app.services.timer_service import queue_next_player_cooldown
    queue_next_player_cooldown(room.id, delay_seconds=3.5)


@socketio.on("host_unsold")
def handle_host_unsold(data):
    """Host passes current player as unsold."""
    if not current_user.is_authenticated:
        emit("error_message", {"message": "You must be logged in."})
        return
    room_id = data.get("room_id")
    room = db.session.get(AuctionRoom, room_id)
    if not room or room.host_id != current_user.id:
        emit("error_message", {"message": "Only the auction host can pass players."})
        return
    if room.status != "active" or not room.current_player_id:
        emit("error_message", {"message": "No active player currently on the hammer."})
        return

    # Clear bids so player is recorded as unsold
    room.current_highest_bid = 0
    room.current_highest_team_id = None
    db.session.commit()

    channel = f"auction_{room.id}"
    is_sold, result_data = finalize_current_player(room.id)
    emit("player_unsold", result_data, room=channel)

    from app.services.timer_service import queue_next_player_cooldown
    queue_next_player_cooldown(room.id, delay_seconds=3.5)


@socketio.on("pause_auction")
def handle_pause_auction(data):
    """Host pauses live bidding."""
    if not current_user.is_authenticated:
        return
    room_id = data.get("room_id")
    success, room_or_msg = pause_auction_service(room_id, current_user.id)
    if not success:
        emit("error_message", {"message": room_or_msg})
        return

    channel = f"auction_{room_id}"
    emit("auction_paused", {
        "room_id": room_id,
        "remaining_seconds": room_or_msg.timer_paused_remaining
    }, room=channel)


@socketio.on("resume_auction")
def handle_resume_auction(data):
    """Host resumes live bidding."""
    if not current_user.is_authenticated:
        return
    room_id = data.get("room_id")
    success, room_or_msg = resume_auction_service(room_id, current_user.id)
    if not success:
        emit("error_message", {"message": room_or_msg})
        return

    channel = f"auction_{room_id}"
    emit("auction_resumed", {
        "room_id": room_id,
        "bid_deadline": room_or_msg.bid_deadline.isoformat() if room_or_msg.bid_deadline else None
    }, room=channel)


@socketio.on("skip_player")
def handle_skip_player(data):
    """Host skips the current player without a sale."""
    if not current_user.is_authenticated:
        return
    room_id = data.get("room_id")
    room = db.session.get(AuctionRoom, room_id)
    if not room or room.host_id != current_user.id:
        emit("error_message", {"message": "Only the host can skip players."})
        return

    is_sold, result_data = finalize_current_player(room.id)
    channel = f"auction_{room.id}"
    if is_sold:
        emit("player_sold", result_data, room=channel)
    else:
        emit("player_unsold", result_data, room=channel)
        
    from app.services.timer_service import queue_next_player_cooldown
    queue_next_player_cooldown(room.id, delay_seconds=2.0)

