from flask import Blueprint, request, jsonify
from app.extensions import db
from app.services.gemini_service import get_player_analysis, get_auction_strategy, get_team_squad_analysis
from app.models.player import Player
from app.models.team import Team

ai_bp = Blueprint("ai", __name__)

@ai_bp.route("/api/ai/player-analysis", methods=["POST"])
def api_player_analysis():
    data = request.get_json() or {}
    player_id = data.get("player_id")
    player_dict = data.get("player")

    if not player_dict and player_id:
        p = db.session.get(Player, player_id)
        if p:
            player_dict = p.to_dict()

    if not player_dict:
        return jsonify({"success": False, "message": "Player data is required"}), 400

    team_squad = data.get("team_squad", [])
    remaining_budget = data.get("remaining_budget")

    analysis = get_player_analysis(player_dict, team_squad, remaining_budget)
    return jsonify({"success": True, "analysis": analysis})


@ai_bp.route("/api/ai/auction-strategy", methods=["POST"])
def api_auction_strategy():
    data = request.get_json() or {}
    team_id = data.get("team_id")
    team_dict = data.get("team")

    if not team_dict and team_id:
        t = db.session.get(Team, team_id)
        if t:
            team_dict = t.to_dict(include_squad=True)

    if not team_dict:
        return jsonify({"success": False, "message": "Team data is required"}), 400

    strategy = get_auction_strategy(team_dict)
    return jsonify({"success": True, "strategy": strategy})


@ai_bp.route("/api/ai/team-analysis", methods=["POST"])
def api_team_analysis():
    data = request.get_json() or {}
    team_id = data.get("team_id")
    team_dict = data.get("team")
    squad_list = data.get("squad", [])

    if not team_dict and team_id:
        t = db.session.get(Team, team_id)
        if t:
            team_dict = t.to_dict(include_squad=True)
            squad_list = team_dict.get("squad", [])

    if not team_dict:
        return jsonify({"success": False, "message": "Team data is required"}), 400

    analysis = get_team_squad_analysis(team_dict, squad_list)
    return jsonify({"success": True, "analysis": analysis})
