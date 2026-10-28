import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.auction import AuctionRoom
from app.models.team import Team, TeamSquad
from app.services.auction_service import create_auction_room, select_franchise, start_auction_service
from app.services.bidding_service import validate_and_place_bid, finalize_current_player, get_next_bid_amount

@pytest.fixture
def bidding_setup():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Create users
        u1 = User(username="csk_boss", email="csk@ipl.com")
        u1.set_password("pass123")
        u2 = User(username="mi_boss", email="mi@ipl.com")
        u2.set_password("pass123")
        db.session.add_all([u1, u2])
        db.session.commit()

        # Create room and teams
        room = create_auction_room(user_id=u1.id, room_name="War Room 2026", starting_budget=1200000000)
        select_franchise(room.id, u1.id, "CSK")
        select_franchise(room.id, u2.id, "MI")
        start_auction_service(room.id, u1.id)

        yield app, room, u1, u2
        db.session.remove()
        db.drop_all()

def test_bid_increment_slabs():
    assert get_next_bid_amount(0, 20000000) == 20000000
    assert get_next_bid_amount(5000000, 2000000) == 6000000       # < 1 Cr -> +10L
    assert get_next_bid_amount(15000000, 2000000) == 17000000     # 1-2 Cr -> +20L
    assert get_next_bid_amount(30000000, 2000000) == 32500000     # 2-5 Cr -> +25L
    assert get_next_bid_amount(70000000, 2000000) == 75000000     # 5-10 Cr -> +50L
    assert get_next_bid_amount(120000000, 2000000) == 130000000   # > 10 Cr -> +1 Cr

def test_valid_bids_flow(bidding_setup):
    app, room, u1, u2 = bidding_setup
    
    # 1. Opening bid by CSK
    ok, msg, data = validate_and_place_bid(room.id, u1.id)
    assert ok is True
    assert data["team_code"] == "CSK"
    assert data["amount"] == room.current_player.base_price

    # 2. CSK cannot outbid itself
    ok_self, msg_self, _ = validate_and_place_bid(room.id, u1.id)
    assert ok_self is False
    assert "already holds the highest bid" in msg_self

    # 3. MI counter-bids
    ok_mi, msg_mi, data_mi = validate_and_place_bid(room.id, u2.id)
    assert ok_mi is True
    assert data_mi["team_code"] == "MI"
    assert data_mi["amount"] > data["amount"]

def test_player_sold_finalization(bidding_setup):
    app, room, u1, u2 = bidding_setup
    
    # Place a bid
    validate_and_place_bid(room.id, u1.id)
    winning_amount = room.current_highest_bid

    # Finalize sold
    is_sold, res = finalize_current_player(room.id)
    assert is_sold is True
    assert res["status"] == "sold"
    assert res["team_code"] == "CSK"
    assert res["price"] == winning_amount

    # Verify team remaining budget deducted
    csk_team = Team.query.filter_by(auction_id=room.id, team_code="CSK").first()
    assert csk_team.remaining_budget == (1200000000 - winning_amount)
    assert csk_team.squad_count == 1

def test_player_unsold_finalization(bidding_setup):
    app, room, u1, u2 = bidding_setup
    
    # No bids placed
    is_sold, res = finalize_current_player(room.id)
    assert is_sold is False
    assert res["status"] == "unsold"
    assert res["base_price_formatted"] is not None
