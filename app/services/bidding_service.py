from datetime import timedelta
from app.extensions import db, utc_now
from app.models.player import Player, format_inr
from app.models.team import Team, TeamSquad
from app.models.bid import Bid, AuctionEvent
from app.models.auction import AuctionRoom, AuctionPlayer

def get_next_bid_amount(current_bid, base_price):
    """
    Computes the standard next legal bid based on IPL auction increment slabs.
    - If no bid yet: base_price
    - Up to 1 Crore: +10 Lakh
    - 1 Crore to 2 Crore: +20 Lakh
    - 2 Crore to 5 Crore: +25 Lakh
    - 5 Crore to 10 Crore: +50 Lakh
    - Above 10 Crore: +1 Crore
    """
    if current_bid <= 0:
        return base_price
    
    if current_bid < 10000000:       # < 1 Cr
        return current_bid + 1000000  # +10 L
    elif current_bid < 20000000:     # 1 Cr - 2 Cr
        return current_bid + 2000000  # +20 L
    elif current_bid < 50000000:     # 2 Cr - 5 Cr
        return current_bid + 2500000  # +25 L
    elif current_bid < 100000000:    # 5 Cr - 10 Cr
        return current_bid + 5000000  # +50 L
    else:                            # > 10 Cr
        return current_bid + 10000000 # +1 Cr


def validate_and_place_bid(auction_id, user_id, custom_amount=None):
    """
    Validates and places a bid with authoritative server checks and DB transaction.
    """
    # 1. Fetch Auction Room
    room = db.session.get(AuctionRoom, auction_id)
    if not room:
        return False, "Auction room not found.", None

    # 2. Check auction active state
    if room.status != "active":
        return False, f"Auction is currently {room.status}. Bidding is disabled.", None

    # 3. Check authoritative server deadline
    now = utc_now()
    if room.bid_deadline and now > room.bid_deadline:
        return False, "Bidding time has expired for this player.", None

    # 4. Check current player
    if not room.current_player_id:
        return False, "No active player on the auction table.", None
    
    player = db.session.get(Player, room.current_player_id)
    if not player:
        return False, "Player not found.", None

    ap = AuctionPlayer.query.filter_by(auction_id=auction_id, player_id=player.id, status="current").first()
    if not ap:
        return False, "This player is not currently available for bidding.", None

    # 5. Check user team ownership
    team = Team.query.filter_by(auction_id=auction_id, owner_id=user_id).first()
    if not team:
        return False, "You do not control any team in this auction room.", None

    # 6. Prevent self outbidding
    if room.current_highest_team_id == team.id:
        return False, "Your team already holds the highest bid!", None

    # 7. Calculate bid amount
    if custom_amount is not None and custom_amount > 0:
        bid_amount = int(custom_amount)
    else:
        bid_amount = get_next_bid_amount(room.current_highest_bid, player.base_price)

    # Validate amount is higher than current
    if room.current_highest_bid > 0 and bid_amount <= room.current_highest_bid:
        return False, f"Bid amount ({format_inr(bid_amount)}) must exceed current bid ({format_inr(room.current_highest_bid)}).", None
    elif room.current_highest_bid == 0 and bid_amount < player.base_price:
        return False, f"Bid must be at least the base price of {format_inr(player.base_price)}.", None

    # 8. Check team budget
    if team.remaining_budget < bid_amount:
        return False, f"Insufficient purse! Remaining budget is {format_inr(team.remaining_budget)}, needed {format_inr(bid_amount)}.", None

    # 9. Squad Rules & Minimum Reserve Purse Check
    rules = room.get_rules()
    max_squad_size = rules.get("max_squad_size", 25)
    min_squad_size = rules.get("min_squad_size", 18)
    max_overseas = rules.get("max_overseas", 8)
    reserve_per_slot = 2000000  # Default 20 Lakhs per unfilled minimum squad slot

    current_squad_count = team.squad_count
    if current_squad_count >= max_squad_size:
        return False, f"Maximum squad size of {max_squad_size} reached.", None

    # Overseas limit check
    if player.is_overseas:
        if team.overseas_count >= max_overseas:
            return False, f"Overseas player limit ({max_overseas}) reached for your squad.", None

    # Budget reserve check: can team still afford to fill remaining minimum squad slots?
    remaining_slots_needed = max(0, min_squad_size - (current_squad_count + 1))
    required_reserve = remaining_slots_needed * reserve_per_slot
    if (team.remaining_budget - bid_amount) < required_reserve:
        return False, f"Reserve rule: Must retain at least {format_inr(required_reserve)} to satisfy minimum squad size of {min_squad_size}.", None

    # 10. Update room state
    room.current_highest_bid = bid_amount
    room.current_highest_team_id = team.id

    # 11. Create Bid record
    bid_record = Bid(
        auction_id=auction_id,
        player_id=player.id,
        team_id=team.id,
        user_id=user_id,
        amount=bid_amount,
        timestamp=now
    )
    db.session.add(bid_record)

    # 12. Create Event record
    event = AuctionEvent(auction_id=auction_id, event_type="BID_PLACED")
    event.set_data({
        "player_id": player.id,
        "player_name": player.name,
        "team_id": team.id,
        "team_name": team.team_name,
        "team_code": team.team_code,
        "amount": bid_amount,
        "amount_formatted": format_inr(bid_amount),
        "username": team.owner.username if team.owner else "User"
    })
    db.session.add(event)

    db.session.commit()

    bid_data = {
        "bid_id": bid_record.id,
        "auction_id": auction_id,
        "player_id": player.id,
        "player_name": player.name,
        "team_id": team.id,
        "team_name": team.team_name,
        "team_code": team.team_code,
        "primary_color": team.primary_color,
        "amount": bid_amount,
        "amount_formatted": format_inr(bid_amount),
        "next_bid": get_next_bid_amount(bid_amount, player.base_price),
        "next_bid_formatted": format_inr(get_next_bid_amount(bid_amount, player.base_price)),
        "bid_deadline": room.bid_deadline.isoformat(),
        "timestamp": now.strftime("%H:%M:%S")
    }

    return True, "Bid placed successfully!", bid_data


def finalize_current_player(auction_id):
    """
    Server-authoritative finalization when the auction countdown timer expires:
    - If bids were placed: Marks player SOLD to highest bidder, deducts funds, adds to squad.
    - If no bids were placed: Marks player UNSOLD.
    Returns: (is_sold, result_data)
    """
    room = db.session.get(AuctionRoom, auction_id)
    if not room or not room.current_player_id:
        return False, None

    player = db.session.get(Player, room.current_player_id)
    ap = AuctionPlayer.query.filter_by(auction_id=auction_id, player_id=room.current_player_id, status="current").first()
    if not ap or not player:
        return False, None

    highest_team = db.session.get(Team, room.current_highest_team_id) if room.current_highest_team_id else None
    
    if highest_team and room.current_highest_bid > 0:
        # Mark as SOLD
        sold_price = room.current_highest_bid
        ap.status = "sold"
        ap.sold_price = sold_price
        ap.winning_team_id = highest_team.id

        # Deduct budget
        highest_team.remaining_budget = max(0, highest_team.remaining_budget - sold_price)

        # Add to TeamSquad
        squad_entry = TeamSquad(
            auction_id=auction_id,
            team_id=highest_team.id,
            player_id=player.id,
            purchase_price=sold_price
        )
        db.session.add(squad_entry)

        event = AuctionEvent(auction_id=auction_id, event_type="PLAYER_SOLD")
        event.set_data({
            "player_id": player.id,
            "player_name": player.name,
            "team_id": highest_team.id,
            "team_name": highest_team.team_name,
            "team_code": highest_team.team_code,
            "price": sold_price,
            "price_formatted": format_inr(sold_price)
        })
        db.session.add(event)
        db.session.commit()

        result_data = {
            "status": "sold",
            "player_id": player.id,
            "player_name": player.name,
            "role": player.role,
            "team_id": highest_team.id,
            "team_name": highest_team.team_name,
            "team_code": highest_team.team_code,
            "primary_color": highest_team.primary_color,
            "price": sold_price,
            "price_formatted": format_inr(sold_price),
            "team_remaining_budget": highest_team.remaining_budget,
            "team_remaining_budget_formatted": format_inr(highest_team.remaining_budget),
            "team_squad_count": highest_team.squad_count,
            "team_overseas_count": highest_team.overseas_count
        }
        return True, result_data
    else:
        # Mark as UNSOLD
        ap.status = "unsold"
        ap.sold_price = 0
        ap.winning_team_id = None

        event = AuctionEvent(auction_id=auction_id, event_type="PLAYER_UNSOLD")
        event.set_data({
            "player_id": player.id,
            "player_name": player.name,
            "base_price": player.base_price,
            "base_price_formatted": format_inr(player.base_price)
        })
        db.session.add(event)
        db.session.commit()

        result_data = {
            "status": "unsold",
            "player_id": player.id,
            "player_name": player.name,
            "role": player.role,
            "base_price": player.base_price,
            "base_price_formatted": format_inr(player.base_price)
        }
        return False, result_data
