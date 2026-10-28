from flask import Blueprint, render_template, request, jsonify
from app.models.player import Player
from app.services.player_service import search_players, get_player_by_id

player_bp = Blueprint("player", __name__)

@player_bp.route("/players")
def players_page():
    role = request.args.get("role", "All")
    pool = request.args.get("pool", "All")
    country = request.args.get("country", "All")
    q = request.args.get("q", "")
    page = int(request.args.get("page", 1))

    is_overseas = None
    if request.args.get("overseas") == "true":
        is_overseas = True
    elif request.args.get("overseas") == "false":
        is_overseas = False

    is_uncapped = None
    if request.args.get("uncapped") == "true":
        is_uncapped = True

    data = search_players(
        query=q,
        role=role,
        pool=pool,
        country=country,
        is_overseas=is_overseas,
        is_uncapped=is_uncapped,
        page=page,
        per_page=16
    )

    all_countries = [c[0] for c in Player.query.with_entities(Player.country).distinct().order_by(Player.country).all()]

    # Aggregate pool and role counts for quick-filter tabs
    total_all = Player.query.count()
    marquee_count = Player.query.filter((Player.pool == "Marquee") | (Player.is_marquee == True)).count()
    uncapped_count = Player.query.filter((Player.pool == "Uncapped") | (Player.is_uncapped == True)).count()
    capped_count = total_all - marquee_count - uncapped_count

    batsmen_count = Player.query.filter_by(role="Batsman").count()
    bowlers_count = Player.query.filter_by(role="Bowler").count()
    allrounders_count = Player.query.filter_by(role="All-rounder").count()
    keepers_count = Player.query.filter_by(role="Wicketkeeper").count()

    return render_template(
        "players.html",
        players=data["players"],
        total=data["total"],
        pages=data["pages"],
        current_page=data["current_page"],
        has_next=data["has_next"],
        has_prev=data["has_prev"],
        selected_role=role,
        selected_pool=pool,
        selected_country=country,
        search_query=q,
        countries=all_countries,
        counts={
            "total": total_all,
            "marquee": marquee_count,
            "capped": capped_count,
            "uncapped": uncapped_count,
            "batsman": batsmen_count,
            "bowler": bowlers_count,
            "allrounder": allrounders_count,
            "wicketkeeper": keepers_count
        }
    )


# REST APIs
@player_bp.route("/api/players", methods=["GET"])
def api_get_players():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    role = request.args.get("role")
    pool = request.args.get("pool")
    country = request.args.get("country")
    q = request.args.get("q")
    
    data = search_players(query=q, role=role, pool=pool, country=country, page=page, per_page=per_page)
    return jsonify({"success": True, **data})



@player_bp.route("/api/players/<int:player_id>", methods=["GET"])
def api_get_player(player_id):
    player = get_player_by_id(player_id)
    if not player:
        return jsonify({"success": False, "message": "Player not found"}), 404
    return jsonify({"success": True, "player": player.to_dict()})


@player_bp.route("/api/players/search", methods=["GET"])
def api_search_players():
    q = request.args.get("q", "").strip()
    role = request.args.get("role")
    data = search_players(query=q, role=role, per_page=10)
    return jsonify({"success": True, "results": data["players"]})
