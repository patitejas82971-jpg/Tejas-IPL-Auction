from flask import request
from flask_login import current_user
from flask_socketio import join_room as sock_join_room, leave_room as sock_leave_room, emit
from app.extensions import socketio, db
from app.models.auction import AuctionRoom, AuctionPlayer
from app.models.team import Team
from app.services.auction_service import get_available_teams_for_room, get_auction_results_summary

@socketio.on("join_room")
def handle_join_room(data):
    """Client joins an auction room channel."""
    room_id = data.get("room_id")
    if not room_id:
        emit("error_message", {"message": "Invalid room specified."})
        return

    room = db.session.get(AuctionRoom, room_id)
    if not room:
        emit("error_message", {"message": "Auction room not found."})
        return

    channel = f"auction_{room.id}"
    sock_join_room(channel)

    user_info = {
        "user_id": current_user.id if current_user.is_authenticated else "guest",
        "username": current_user.username if current_user.is_authenticated else data.get("username", "Guest")
    }

    # Notify room
    emit("user_joined", user_info, room=channel)

    # Send full synchronized state to this client
    state = room.to_dict(full=True)
    state["available_franchises"] = get_available_teams_for_room(room.id)
    emit("auction_state", state)


@socketio.on("leave_room")
def handle_leave_room(data):
    """Client leaves an auction room channel."""
    room_id = data.get("room_id")
    if not room_id:
        return
    channel = f"auction_{room_id}"
    sock_leave_room(channel)
    username = current_user.username if current_user.is_authenticated else data.get("username", "Guest")
    emit("user_left", {"username": username}, room=channel)


@socketio.on("request_auction_state")
def handle_request_auction_state(data):
    """Sends current state on demand (e.g., after reconnect)."""
    try:
        room_id = data.get("room_id")
        if not room_id:
            return
        room = db.session.get(AuctionRoom, room_id)
        if room:
            state = room.to_dict(full=True)
            state["available_franchises"] = get_available_teams_for_room(room.id)
            emit("auction_state", state)
    except Exception as e:
        print(f"ERROR in handle_request_auction_state: {e}")
