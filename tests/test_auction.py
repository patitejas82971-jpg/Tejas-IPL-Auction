import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.auction import AuctionRoom
from app.models.team import Team
from app.services.auction_service import (
    create_auction_room,
    select_franchise,
    start_auction_service,
    pause_auction_service,
    resume_auction_service
)

@pytest.fixture
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Create users
        host = User(username="auction_host", email="host@ipl.com")
        host.set_password("hostpass123")
        user2 = User(username="player_two", email="p2@ipl.com")
        user2.set_password("userpass123")
        db.session.add_all([host, user2])
        db.session.commit()
        yield app, host, user2
        db.session.remove()
        db.drop_all()

def test_create_auction_room(app_ctx):
    app, host, user2 = app_ctx
    room = create_auction_room(
        user_id=host.id,
        room_name="Grand Auction 2026",
        auction_type="mega",
        starting_budget=1200000000,
        max_teams=10
    )
    assert room.id is not None
    assert len(room.room_code) == 6
    assert room.host_id == host.id
    assert room.status == "lobby"
    assert room.starting_budget == 1200000000

def test_select_franchise(app_ctx):
    app, host, user2 = app_ctx
    room = create_auction_room(user_id=host.id, room_name="Test Room")
    
    # Host claims CSK
    ok, team_csk = select_franchise(room.id, host.id, "CSK")
    assert ok is True
    assert team_csk.team_code == "CSK"
    assert team_csk.remaining_budget == 1200000000

    # User 2 tries to claim CSK (should fail: duplicate team claim)
    ok_dup, msg = select_franchise(room.id, user2.id, "CSK")
    assert ok_dup is False
    assert "already claimed" in msg

    # User 2 claims MI (should succeed)
    ok_mi, team_mi = select_franchise(room.id, user2.id, "MI")
    assert ok_mi is True
    assert team_mi.team_code == "MI"

def test_start_and_pause_auction(app_ctx):
    app, host, user2 = app_ctx
    room = create_auction_room(user_id=host.id, room_name="Auction Start Test")
    select_franchise(room.id, host.id, "RCB")

    # Start auction
    ok, started_room = start_auction_service(room.id, host.id)
    assert ok is True
    assert started_room.status == "active"
    assert started_room.current_player_id is not None
    assert started_room.bid_deadline is not None

    # Pause auction
    ok_pause, paused_room = pause_auction_service(room.id, host.id)
    assert ok_pause is True
    assert paused_room.status == "paused"

    # Resume auction
    ok_resume, resumed_room = resume_auction_service(room.id, host.id)
    assert ok_resume is True
    assert resumed_room.status == "active"


def test_auction_queue_pool_and_set_ordering(app_ctx):
    from app.models.auction import AuctionPlayer
    app, host, user2 = app_ctx
    room = create_auction_room(user_id=host.id, room_name="Pool Separation Room")
    queue = AuctionPlayer.query.filter_by(auction_id=room.id).order_by(AuctionPlayer.order_index).all()
    
    assert len(queue) == 300
    
    # Marquee Batsmen first 8
    for ap in queue[0:8]:
        assert ap.pool == "Marquee"
        assert ap.set_name == "Marquee Batsmen"
        assert ap.player.role == "Batsman"

    # Marquee All-rounders next 6
    for ap in queue[8:14]:
        assert ap.pool == "Marquee"
        assert ap.set_name == "Marquee All-rounders"
        assert ap.player.role == "All-rounder"

    # Marquee Wicketkeepers next 7
    for ap in queue[14:21]:
        assert ap.pool == "Marquee"
        assert ap.set_name == "Marquee Wicketkeepers"
        assert ap.player.role == "Wicketkeeper"

    # Marquee Bowlers next 16
    for ap in queue[21:37]:
        assert ap.pool == "Marquee"
        assert ap.set_name == "Marquee Bowlers"
        assert ap.player.role == "Bowler"

    # Followed by Capped sets (38 to 225)
    for ap in queue[37:225]:
        assert ap.pool == "Capped"
        assert "Capped" in ap.set_name

    # Followed by Uncapped sets (226 to 300)
    for ap in queue[225:300]:
        assert ap.pool == "Uncapped"
        assert "Uncapped" in ap.set_name


def test_auction_pools_summary_api(app_ctx):
    from app.services.auction_service import get_auction_pools_summary
    app, host, user2 = app_ctx
    room = create_auction_room(user_id=host.id, room_name="Summary Test Room")
    summary = get_auction_pools_summary(room.id)
    
    assert summary is not None
    assert summary["pools"]["Marquee"]["total"] == 37
    assert summary["pools"]["Capped"]["total"] == 188
    assert summary["pools"]["Uncapped"]["total"] == 75
    assert len(summary["sets"]) == 12

