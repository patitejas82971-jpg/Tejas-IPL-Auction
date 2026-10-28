import pytest
from app import create_app
from app.services.gemini_service import get_player_analysis, get_auction_strategy, get_team_squad_analysis

@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        yield client

def test_player_analysis_fallback_mode():
    player_data = {
        "id": 101,
        "name": "Virat Kohli",
        "role": "Batsman",
        "country": "India",
        "is_overseas": False,
        "base_price": 20000000,
        "rating": 97,
        "batting_style": "Right Handed",
        "bowling_style": "Right-arm medium"
    }

    # Should gracefully return structured advice even without API key
    res = get_player_analysis(player_data)
    assert res is not None
    assert "recommended_bid_range" in res
    assert "strengths" in res
    assert len(res["strengths"]) > 0
    assert "verdict" in res
    if res.get("status") == "fallback":
        assert "AI insights are temporarily unavailable. You can continue your auction normally." in res["notice"]

def test_team_squad_analysis_fallback_mode():
    team_data = {
        "team_name": "Chennai Super Kings",
        "remaining_budget": 500000000,
        "spent_budget": 700000000,
        "overseas_count": 3
    }
    squad_list = [
        {"player": {"name": "MS Dhoni", "role": "Wicketkeeper"}},
        {"player": {"name": "Ravindra Jadeja", "role": "All-rounder"}},
        {"player": {"name": "Ruturaj Gaikwad", "role": "Batsman"}}
    ]

    res = get_team_squad_analysis(team_data, squad_list)
    assert res is not None
    assert "squad_rating" in res
    assert "strengths" in res
    assert "suggested_xi" in res

def test_ai_api_endpoint(client):
    res = client.post("/api/ai/player-analysis", json={
        "player": {
            "name": "Jasprit Bumrah",
            "role": "Bowler",
            "country": "India",
            "base_price": 20000000,
            "rating": 98,
            "batting_style": "Right Handed",
            "bowling_style": "Right-arm fast"
        }
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "analysis" in data
