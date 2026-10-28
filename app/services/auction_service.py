import random
import string
import json
import os
from datetime import timedelta
from app.extensions import db, utc_now
from app.models.user import User
from app.models.player import Player, format_inr
from app.models.team import Team, TeamSquad
from app.models.bid import Bid, AuctionEvent
from app.models.auction import AuctionRoom, AuctionPlayer

TEAMS_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "teams.json")
RULES_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "auction_rules.json")

def load_franchise_data():
    """Loads default IPL franchise profiles."""
    if os.path.exists(TEAMS_JSON_PATH):
        with open(TEAMS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_default_rules(auction_type="mega"):
    """Loads default rules for auction type."""
    if os.path.exists(RULES_JSON_PATH):
        with open(RULES_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("auction_types", {}).get(auction_type, {
                "name": "IPL Mega Auction",
                "starting_budget": 1200000000,
                "max_teams": 10,
                "min_squad_size": 18,
                "max_squad_size": 25,
                "max_overseas": 8,
                "timer_duration": 30,
                "timer_extend_seconds": 15
            })
    return {
        "min_squad_size": 18,
        "max_squad_size": 25,
        "max_overseas": 8,
        "timer_duration": 30,
        "timer_extend_seconds": 15
    }

def generate_unique_room_code():
    """Generates a 6-character uppercase alphanumeric room code."""
    chars = string.ascii_uppercase + "23456789"  # omit 0, 1 to prevent ambiguity
    while True:
        code = "".join(random.choices(chars, k=6))
        if not AuctionRoom.query.filter_by(room_code=code).first():
            return code


def create_auction_room(user_id, room_name, auction_type="mega", starting_budget=None, max_teams=10, custom_rules=None):
    """Creates a new auction room and queues players."""
    defaults = load_default_rules(auction_type)
    if not starting_budget:
        starting_budget = defaults.get("starting_budget", 1200000000)
        
    rules = defaults.copy()
    if custom_rules:
        rules.update(custom_rules)

    room_code = generate_unique_room_code()
    room = AuctionRoom(
        room_code=room_code,
        room_name=room_name.strip(),
        host_id=user_id,
        status="lobby",
        auction_type=auction_type,
        starting_budget=starting_budget,
        max_teams=min(10, max(2, max_teams)),
        timer_paused_remaining=rules.get("timer_duration", 30)
    )
    room.set_rules(rules)
    db.session.add(room)
    db.session.flush()

    # Queue all 300 available players into this auction organized by authentic Pools & Sets
    all_players = Player.query.all()
    
    # 12 IPL Mega Auction Sets across 3 Pools:
    # 1. Marquee Batsmen, 2. Marquee All-rounders, 3. Marquee Wicketkeepers, 4. Marquee Bowlers
    # 5. Capped Batsmen, 6. Capped All-rounders, 7. Capped Wicketkeepers, 8. Capped Bowlers
    # 9. Uncapped Batsmen, 10. Uncapped All-rounders, 11. Uncapped Wicketkeepers, 12. Uncapped Bowlers
    set_definitions = [
        ("Marquee", "Batsman", "Marquee Batsmen"),
        ("Marquee", "All-rounder", "Marquee All-rounders"),
        ("Marquee", "Wicketkeeper", "Marquee Wicketkeepers"),
        ("Marquee", "Bowler", "Marquee Bowlers"),
        ("Capped", "Batsman", "Capped Batsmen"),
        ("Capped", "All-rounder", "Capped All-rounders"),
        ("Capped", "Wicketkeeper", "Capped Wicketkeepers"),
        ("Capped", "Bowler", "Capped Bowlers"),
        ("Uncapped", "Batsman", "Uncapped Batsmen"),
        ("Uncapped", "All-rounder", "Uncapped All-rounders"),
        ("Uncapped", "Wicketkeeper", "Uncapped Wicketkeepers"),
        ("Uncapped", "Bowler", "Uncapped Bowlers"),
    ]

    ordered_players = []
    for pool_name, role_name, set_title in set_definitions:
        matching = [
            p for p in all_players 
            if (p.pool == pool_name or (pool_name == "Marquee" and p.is_marquee)) and p.role == role_name
        ]
        # Order by rating descending, base price descending within the set
        matching.sort(key=lambda p: (p.rating or 0, p.base_price or 0), reverse=True)
        for p in matching:
            ordered_players.append((p, pool_name, set_title))

    # Catch any remaining players that might have had unexpected tags
    queued_ids = {p[0].id for p in ordered_players}
    remaining = [p for p in all_players if p.id not in queued_ids]
    if remaining:
        remaining.sort(key=lambda p: (p.rating or 0, p.base_price or 0), reverse=True)
        for p in remaining:
            pool_val = p.pool or ("Marquee" if p.is_marquee else ("Uncapped" if p.is_uncapped else "Capped"))
            set_val = p.set_name or f"{pool_val} {p.role}s"
            ordered_players.append((p, pool_val, set_val))

    for idx, (player, pool_val, set_val) in enumerate(ordered_players):
        ap = AuctionPlayer(
            auction_id=room.id,
            player_id=player.id,
            status="pending",
            order_index=idx + 1,
            pool=pool_val,
            set_name=set_val
        )
        db.session.add(ap)

    # Log event
    event = AuctionEvent(auction_id=room.id, event_type="ROOM_CREATED")
    event.set_data({"host_id": user_id, "room_name": room_name, "room_code": room_code})
    db.session.add(event)

    db.session.commit()
    return room


def get_available_teams_for_room(auction_id):
    """Returns all 10 franchises with taken/available status."""
    franchises = load_franchise_data()
    existing_teams = Team.query.filter_by(auction_id=auction_id).all()
    taken_codes = {t.team_code: t for t in existing_teams}

    result = []
    for f in franchises:
        f_copy = f.copy()
        if f["team_code"] in taken_codes:
            team_obj = taken_codes[f["team_code"]]
            f_copy["is_taken"] = True
            f_copy["taken_by"] = team_obj.owner.username if team_obj.owner else "Unknown"
            f_copy["team_id"] = team_obj.id
            f_copy["owner_id"] = team_obj.owner_id
            f_copy["is_ready"] = team_obj.is_ready
        else:
            f_copy["is_taken"] = False
            f_copy["taken_by"] = None
            f_copy["team_id"] = None
            f_copy["owner_id"] = None
            f_copy["is_ready"] = False
        result.append(f_copy)
    return result


def select_franchise(auction_id, user_id, team_code):
    """Assigns an IPL franchise to a user in the auction room."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return False, "Auction room not found."
    if room.status != "lobby":
        return False, "Team selection is only allowed in the lobby."

    # Check if this team code is already chosen by someone else
    existing_team = Team.query.filter_by(auction_id=auction_id, team_code=team_code).first()
    if existing_team and existing_team.owner_id != user_id:
        return False, f"{team_code} is already claimed by another participant."

    # Check if user already owns a different team in this room
    user_team = Team.query.filter_by(auction_id=auction_id, owner_id=user_id).first()
    
    # Load franchise metadata
    franchises = {f["team_code"]: f for f in load_franchise_data()}
    f_info = franchises.get(team_code)
    if not f_info:
        return False, f"Invalid team code: {team_code}"

    if user_team:
        # Update existing team
        user_team.team_code = team_code
        user_team.team_name = f_info["team_name"]
        user_team.short_name = f_info["short_name"]
        user_team.primary_color = f_info["primary_color"]
        user_team.secondary_color = f_info["secondary_color"]
        user_team.text_color = f_info["text_color"]
        user_team.logo_icon = f_info["logo_icon"]
        team_obj = user_team
    else:
        # Check team limit
        current_count = Team.query.filter_by(auction_id=auction_id).count()
        if current_count >= room.max_teams:
            return False, f"Maximum team limit ({room.max_teams}) reached for this auction."

        team_obj = Team(
            auction_id=auction_id,
            owner_id=user_id,
            team_name=f_info["team_name"],
            team_code=team_code,
            short_name=f_info["short_name"],
            primary_color=f_info["primary_color"],
            secondary_color=f_info["secondary_color"],
            text_color=f_info["text_color"],
            logo_icon=f_info["logo_icon"],
            starting_budget=room.starting_budget,
            remaining_budget=room.starting_budget,
            is_ready=False
        )
        db.session.add(team_obj)

    event = AuctionEvent(auction_id=auction_id, event_type="TEAM_SELECTED")
    event.set_data({"user_id": user_id, "team_code": team_code, "team_name": f_info["team_name"]})
    db.session.add(event)

    db.session.commit()
    return True, team_obj


def toggle_team_ready(auction_id, user_id):
    """Toggles ready status for user's team."""
    team = Team.query.filter_by(auction_id=auction_id, owner_id=user_id).first()
    if not team:
        return False, "You have not selected a team yet."
    team.is_ready = not team.is_ready
    db.session.commit()
    return True, team.is_ready


def start_auction_service(auction_id, user_id):
    """Starts the live auction by queueing the first player."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return False, "Auction room not found."
    if room.host_id != user_id:
        return False, "Only the auction host can start the auction."
    if room.status != "lobby":
        return False, "Auction is already in progress or completed."
    
    teams = Team.query.filter_by(auction_id=auction_id).all()
    if len(teams) < 1:
        return False, "At least one team must join before starting the auction."

    # Find the first pending player
    first_ap = AuctionPlayer.query.filter_by(auction_id=auction_id, status="pending").order_by(AuctionPlayer.order_index).first()
    if not first_ap:
        return False, "No players available in queue."

    rules = room.get_rules()
    timer_duration = rules.get("timer_duration", 30)

    room.status = "active"
    room.current_player_id = first_ap.player_id
    room.current_highest_bid = 0
    room.current_highest_team_id = None
    if timer_duration and timer_duration > 0:
        room.bid_deadline = utc_now() + timedelta(seconds=timer_duration)
        room.timer_paused_remaining = timer_duration
    else:
        room.bid_deadline = None
        room.timer_paused_remaining = None

    first_ap.status = "current"

    event = AuctionEvent(auction_id=auction_id, event_type="AUCTION_STARTED")
    event.set_data({
        "first_player_id": first_ap.player_id,
        "first_player_name": first_ap.player.name,
        "timer_duration": timer_duration
    })
    db.session.add(event)
    db.session.commit()

    return True, room


def pause_auction_service(auction_id, user_id):
    """Pauses the live auction countdown."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return False, "Room not found"
    if room.host_id != user_id:
        return False, "Only the host can pause the auction."
    if room.status != "active":
        return False, "Auction is not actively in progress."

    # Calculate remaining time
    now = utc_now()
    if room.bid_deadline and room.bid_deadline > now:
        remaining = int((room.bid_deadline - now).total_seconds())
    else:
        remaining = 0
    room.timer_paused_remaining = max(1, remaining)
    room.status = "paused"

    event = AuctionEvent(auction_id=auction_id, event_type="AUCTION_PAUSED")
    event.set_data({"remaining_seconds": room.timer_paused_remaining})
    db.session.add(event)

    db.session.commit()
    return True, room


def resume_auction_service(auction_id, user_id):
    """Resumes the live auction countdown."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return False, "Room not found"
    if room.host_id != user_id:
        return False, "Only the host can resume the auction."
    if room.status != "paused":
        return False, "Auction is not paused."

    duration = room.timer_paused_remaining if room.timer_paused_remaining > 0 else 15
    room.bid_deadline = utc_now() + timedelta(seconds=duration)
    room.status = "active"

    event = AuctionEvent(auction_id=auction_id, event_type="AUCTION_RESUMED")
    event.set_data({"resumed_duration": duration})
    db.session.add(event)

    db.session.commit()
    return True, room


def advance_to_next_player(auction_id):
    """Advances the auction to the next pending player, or completes auction."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return None

    # Next pending player
    next_ap = AuctionPlayer.query.filter_by(auction_id=auction_id, status="pending").order_by(AuctionPlayer.order_index).first()
    if not next_ap:
        # All players completed!
        room.status = "completed"
        room.current_player_id = None
        room.current_highest_bid = 0
        room.current_highest_team_id = None
        room.bid_deadline = None

        event = AuctionEvent(auction_id=auction_id, event_type="AUCTION_ENDED")
        event.set_data({"completed_at": utc_now().isoformat()})
        db.session.add(event)
        db.session.commit()
        return None

    rules = room.get_rules()
    timer_duration = rules.get("timer_duration", 30)

    room.current_player_id = next_ap.player_id
    room.current_highest_bid = 0
    room.current_highest_team_id = None
    if timer_duration and timer_duration > 0:
        room.bid_deadline = utc_now() + timedelta(seconds=timer_duration)
        room.timer_paused_remaining = timer_duration
    else:
        room.bid_deadline = None
        room.timer_paused_remaining = None
    room.status = "active"

    next_ap.status = "current"

    event = AuctionEvent(auction_id=auction_id, event_type="PLAYER_ANNOUNCED")
    event.set_data({
        "player_id": next_ap.player_id,
        "player_name": next_ap.player.name,
        "base_price": next_ap.player.base_price,
        "base_price_formatted": format_inr(next_ap.player.base_price)
    })
    db.session.add(event)
    db.session.commit()

    return next_ap


def get_auction_results_summary(auction_id):
    """Returns detailed statistics and team squad comparisons for completed or active auction."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return None

    teams = Team.query.filter_by(auction_id=auction_id).all()
    auction_players = AuctionPlayer.query.filter_by(auction_id=auction_id).all()
    
    sold_players = [ap for ap in auction_players if ap.status == "sold"]
    unsold_players = [ap for ap in auction_players if ap.status == "unsold"]
    
    total_spent = sum(t.spent_budget for t in teams)
    highest_sale = max(sold_players, key=lambda ap: ap.sold_price) if sold_players else None

    team_summaries = []
    for t in teams:
        team_summaries.append({
            "team_id": t.id,
            "team_name": t.team_name,
            "team_code": t.team_code,
            "owner_name": t.owner.username if t.owner else "Unknown",
            "primary_color": t.primary_color,
            "secondary_color": t.secondary_color,
            "starting_budget": t.starting_budget,
            "remaining_budget": t.remaining_budget,
            "remaining_budget_formatted": format_inr(t.remaining_budget),
            "spent_budget": t.spent_budget,
            "spent_budget_formatted": format_inr(t.spent_budget),
            "squad_count": t.squad_count,
            "overseas_count": t.overseas_count,
            "roles": t.get_role_distribution(),
            "squad": [entry.to_dict() for entry in t.squad_entries]
        })

    return {
        "room_id": room.id,
        "room_name": room.room_name,
        "room_code": room.room_code,
        "status": room.status,
        "created_at": room.created_at.strftime("%b %d, %Y %H:%M") if room.created_at else "",
        "total_teams": len(teams),
        "total_players_sold": len(sold_players),
        "total_unsold_players": len(unsold_players),
        "total_spent": total_spent,
        "total_spent_formatted": format_inr(total_spent),
        "highest_purchase": {
            "player_name": highest_sale.player.name if highest_sale else "N/A",
            "amount": highest_sale.sold_price if highest_sale else 0,
            "amount_formatted": format_inr(highest_sale.sold_price) if highest_sale else "₹0",
            "team_name": highest_sale.winning_team.team_name if (highest_sale and highest_sale.winning_team) else "N/A"
        } if highest_sale else None,
        "teams": team_summaries,
        "sold_players": [ap.to_dict() for ap in sold_players],
        "unsold_players": [ap.to_dict() for ap in unsold_players]
    }


def get_auction_pools_summary(auction_id):
    """
    Returns summary statistics and set progression for an auction room:
    Pools (Marquee, Capped, Uncapped) and Categories (Batsman, Bowler, All-rounder, Wicketkeeper).
    """
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return None

    auction_players = AuctionPlayer.query.filter_by(auction_id=auction_id).order_by(AuctionPlayer.order_index).all()
    
    pools = {
        "Marquee": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0},
        "Capped": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0},
        "Uncapped": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}
    }
    
    categories = {
        "Batsman": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0},
        "Bowler": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0},
        "All-rounder": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0},
        "Wicketkeeper": {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}
    }

    sets_order = [
        "Marquee Batsmen", "Marquee All-rounders", "Marquee Wicketkeepers", "Marquee Bowlers",
        "Capped Batsmen", "Capped All-rounders", "Capped Wicketkeepers", "Capped Bowlers",
        "Uncapped Batsmen", "Uncapped All-rounders", "Uncapped Wicketkeepers", "Uncapped Bowlers"
    ]
    sets_data = {
        s: {"set_name": s, "total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}
        for s in sets_order
    }

    current_set = None
    current_pool = None

    for ap in auction_players:
        pool_name = ap.pool or (ap.player.pool if ap.player else "Capped")
        if pool_name not in pools:
            pools[pool_name] = {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}
        role_name = ap.player.role if ap.player else "Batsman"
        if role_name not in categories:
            categories[role_name] = {"total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}
        set_name = ap.set_name or (ap.player.set_name if ap.player else f"{pool_name} {role_name}s")
        if set_name not in sets_data:
            sets_data[set_name] = {"set_name": set_name, "total": 0, "sold": 0, "unsold": 0, "pending": 0, "current": 0, "spent": 0}

        status = ap.status
        sold_price = ap.sold_price or 0

        # Update pool
        pools[pool_name]["total"] += 1
        pools[pool_name][status] = pools[pool_name].get(status, 0) + 1
        if status == "sold":
            pools[pool_name]["spent"] += sold_price

        # Update category
        categories[role_name]["total"] += 1
        categories[role_name][status] = categories[role_name].get(status, 0) + 1
        if status == "sold":
            categories[role_name]["spent"] += sold_price

        # Update set
        sets_data[set_name]["total"] += 1
        sets_data[set_name][status] = sets_data[set_name].get(status, 0) + 1
        if status == "sold":
            sets_data[set_name]["spent"] += sold_price

        if status == "current":
            current_set = set_name
            current_pool = pool_name

    # If no current player, determine active set by first pending player
    if not current_set:
        first_pending = next((ap for ap in auction_players if ap.status == "pending"), None)
        if first_pending:
            current_set = first_pending.set_name or (first_pending.player.set_name if first_pending.player else "Marquee Batsmen")
            current_pool = first_pending.pool or (first_pending.player.pool if first_pending.player else "Marquee")

    return {
        "room_id": room.id,
        "current_pool": current_pool or "Marquee",
        "current_set": current_set or "Marquee Batsmen",
        "pools": pools,
        "categories": categories,
        "sets": [sets_data[s] for s in sets_order if s in sets_data]
    }


def jump_to_set_service(auction_id, set_name, user_id):
    """Allows host to rearrange pending players so that the specified set comes next."""
    room = db.session.get(AuctionRoom, auction_id)
    if not room or room.host_id != user_id:
        return False, "Unauthorized: only the host can jump sets."

    pending_players = AuctionPlayer.query.filter_by(auction_id=auction_id, status="pending").order_by(AuctionPlayer.order_index).all()
    if not pending_players:
        return False, "No pending players available to reorder."

    target_set_players = [ap for ap in pending_players if ap.set_name == set_name]
    other_pending = [ap for ap in pending_players if ap.set_name != set_name]

    if not target_set_players:
        return False, f"No pending players found in set '{set_name}'."

    base_order = pending_players[0].order_index
    new_pending_order = target_set_players + other_pending
    for i, ap in enumerate(new_pending_order):
        ap.order_index = base_order + i

    db.session.commit()
    return True, f"Successfully advanced queue to {set_name}."

