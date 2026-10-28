from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.auction import AuctionRoom
from app.models.team import Team, TeamSquad
from app.services.auction_service import get_available_teams_for_room, select_franchise

team_bp = Blueprint("team", __name__)

@team_bp.route("/auction/<int:auction_id>/team-selection")
@login_required
def team_selection(auction_id):
    room = AuctionRoom.query.get_or_404(auction_id)
    available_franchises = get_available_teams_for_room(auction_id)
    user_team = Team.query.filter_by(auction_id=auction_id, owner_id=current_user.id).first()

    return render_template(
        "team_selection.html",
        room=room,
        available_franchises=available_franchises,
        user_team=user_team
    )


@team_bp.route("/auction/<int:auction_id>/my-team")
@login_required
def my_team(auction_id):
    room = AuctionRoom.query.get_or_404(auction_id)
    team = Team.query.filter_by(auction_id=auction_id, owner_id=current_user.id).first()
    if not team:
        flash("You haven't selected a team in this auction yet.", "warning")
        return redirect(url_for("team.team_selection", auction_id=auction_id))

    return render_template("team_squad.html", room=room, team=team)


# REST APIs
@team_bp.route("/api/teams", methods=["GET"])
def api_get_teams():
    auction_id = request.args.get("auction_id")
    if auction_id:
        teams = Team.query.filter_by(auction_id=auction_id).all()
    else:
        teams = Team.query.limit(50).all()
    return jsonify({"success": True, "teams": [t.to_dict(include_squad=True) for t in teams]})


@team_bp.route("/api/teams/select", methods=["POST"])
@login_required
def api_select_team():
    data = request.get_json() or {}
    auction_id = data.get("auction_id")
    team_code = data.get("team_code")

    if not auction_id or not team_code:
        return jsonify({"success": False, "message": "auction_id and team_code are required"}), 400

    success, result = select_franchise(auction_id, current_user.id, team_code)
    if not success:
        return jsonify({"success": False, "message": result}), 400

    return jsonify({"success": True, "team": result.to_dict()})


@team_bp.route("/api/teams/<int:team_id>", methods=["GET"])
def api_get_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({"success": False, "message": "Team not found"}), 404
    return jsonify({"success": True, "team": team.to_dict(include_squad=True)})


@team_bp.route("/api/teams/<int:team_id>/squad", methods=["GET"])
def api_get_team_squad(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({"success": False, "message": "Team not found"}), 404

    squad = [entry.to_dict() for entry in team.squad_entries]
    return jsonify({
        "success": True,
        "team_name": team.team_name,
        "team_code": team.team_code,
        "total_players": len(squad),
        "squad": squad
    })
