import pytest
from app import create_app
from app.extensions import db
from app.models.player import Player
from app.services.player_service import search_players, get_player_by_id, seed_or_sync_players

@pytest.fixture
def player_ctx():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed players if testing DB empty
        if Player.query.count() < 300:
            seed_or_sync_players(force=True)
        yield app
        db.session.remove()
        db.drop_all()

def test_total_player_count_is_300(player_ctx):
    assert Player.query.count() == 300

def test_role_distribution(player_ctx):
    batsmen = Player.query.filter_by(role="Batsman").count()
    wicketkeepers = Player.query.filter_by(role="Wicketkeeper").count()
    allrounders = Player.query.filter_by(role="All-rounder").count()
    bowlers = Player.query.filter_by(role="Bowler").count()

    assert batsmen == 85
    assert wicketkeepers == 40
    assert allrounders == 85
    assert bowlers == 90
    assert (batsmen + wicketkeepers + allrounders + bowlers) == 300

def test_breakout_stars_included(player_ctx):
    # Verify key 2026 stars are present
    vaibhav = Player.query.filter_by(name="Vaibhav Suryavanshi").first()
    assert vaibhav is not None
    assert vaibhav.role == "Batsman"
    assert vaibhav.is_uncapped is True

    digvesh = Player.query.filter_by(name="Digvesh Rathi").first()
    assert digvesh is not None
    assert digvesh.role == "Bowler"
    assert digvesh.is_uncapped is True

    mayank = Player.query.filter_by(name="Mayank Yadav").first()
    assert mayank is not None
    assert mayank.rating >= 90

    andre = Player.query.filter_by(name="C Andre Siddarth").first()
    assert andre is not None

def test_retired_players_excluded(player_ctx):
    # Retired players should not be in the active 300 pool
    assert Player.query.filter_by(name="Dinesh Karthik").first() is None
    assert Player.query.filter_by(name="Wriddhiman Saha").first() is None
    assert Player.query.filter_by(name="Shikhar Dhawan").first() is None

def test_search_and_pagination(player_ctx):
    # Search by name
    res = search_players(query="Kohli", page=1, per_page=10)
    assert len(res["players"]) >= 1
    assert res["players"][0]["name"] == "Virat Kohli"

    # Filter by role
    res_bowlers = search_players(role="Bowler", page=1, per_page=20)
    assert res_bowlers["total"] == 90
    assert len(res_bowlers["players"]) == 20
    assert all(p["role"] == "Bowler" for p in res_bowlers["players"])

    # Filter by overseas
    res_overseas = search_players(is_overseas=True, page=1, per_page=10)
    assert all(p["is_overseas"] is True for p in res_overseas["players"])

def test_player_api_endpoints(player_ctx):
    with player_ctx.test_client() as client:
        # API list
        res = client.get("/api/players?per_page=10")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["total"] == 300
        assert len(data["players"]) == 10

        # API single player
        res_p = client.get("/api/players/1")
        assert res_p.status_code == 200
        p_data = res_p.get_json()
        assert p_data["success"] is True
        assert p_data["player"]["name"] == "Virat Kohli"
        assert p_data["player"]["pool"] == "Marquee"
        assert p_data["player"]["is_marquee"] is True


def test_pool_distribution(player_ctx):
    marquee = Player.query.filter((Player.pool == "Marquee") | (Player.is_marquee == True)).count()
    uncapped = Player.query.filter((Player.pool == "Uncapped") | (Player.is_uncapped == True)).count()
    capped = Player.query.filter((Player.pool == "Capped") & (Player.is_uncapped == False) & (Player.is_marquee == False)).count()

    assert marquee == 37
    assert uncapped == 75
    assert capped == 188
    assert (marquee + capped + uncapped) == 300


def test_search_players_by_pool(player_ctx):
    # Test pool=Marquee filter
    res_m = search_players(pool="Marquee", per_page=50)
    assert res_m["total"] == 37
    assert all(p["pool"] == "Marquee" or p["is_marquee"] for p in res_m["players"])

    # Test pool=Uncapped filter
    res_u = search_players(pool="Uncapped", per_page=100)
    assert res_u["total"] == 75
    assert all(p["pool"] == "Uncapped" or p["is_uncapped"] for p in res_u["players"])

    # Test pool=Capped filter
    res_c = search_players(pool="Capped", per_page=100)
    assert res_c["total"] == 188
    assert all(p["pool"] == "Capped" for p in res_c["players"])


def test_set_names_assigned_to_all_players(player_ctx):
    all_p = Player.query.all()
    assert len(all_p) == 300
    for p in all_p:
        assert p.set_name is not None and len(p.set_name) > 0
        assert p.pool in ["Marquee", "Capped", "Uncapped"]

