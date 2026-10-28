import json
import os
from app.extensions import db
from app.models.player import Player

def ensure_schema_columns():
    """Ensure pool, is_marquee, and set_name columns exist in SQLite or Postgres."""
    try:
        engine = db.engine
        with engine.connect() as conn:
            # Check players table
            try:
                conn.execute(db.text("SELECT pool, is_marquee, set_name FROM players LIMIT 1"))
            except Exception:
                try:
                    conn.execute(db.text("ALTER TABLE players ADD COLUMN pool VARCHAR(32) DEFAULT 'Capped'"))
                except Exception:
                    pass
                try:
                    conn.execute(db.text("ALTER TABLE players ADD COLUMN is_marquee BOOLEAN DEFAULT 0"))
                except Exception:
                    pass
                try:
                    conn.execute(db.text("ALTER TABLE players ADD COLUMN set_name VARCHAR(64) DEFAULT ''"))
                except Exception:
                    pass
                try:
                    conn.commit()
                except Exception:
                    pass

            # Check auction_players table
            try:
                conn.execute(db.text("SELECT pool, set_name FROM auction_players LIMIT 1"))
            except Exception:
                try:
                    conn.execute(db.text("ALTER TABLE auction_players ADD COLUMN pool VARCHAR(32) DEFAULT ''"))
                except Exception:
                    pass
                try:
                    conn.execute(db.text("ALTER TABLE auction_players ADD COLUMN set_name VARCHAR(64) DEFAULT ''"))
                except Exception:
                    pass
                try:
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        print(f"Schema check error: {e}")


def _build_player_obj(item):
    is_uncapped = item.get("is_uncapped", False)
    rating = item.get("rating", 80)
    role = item.get("role", "Batsman")
    pool = item.get("pool")
    is_marquee = item.get("is_marquee")
    if not pool:
        if not is_uncapped and rating >= 93:
            pool = "Marquee"
            is_marquee = True
        elif is_uncapped:
            pool = "Uncapped"
            is_marquee = False
        else:
            pool = "Capped"
            is_marquee = False

    plural = "Batsmen" if role == "Batsman" else ("Bowlers" if role == "Bowler" else ("All-rounders" if role == "All-rounder" else "Wicketkeepers"))
    set_name = item.get("set_name") or f"{pool} {plural}"

    return Player(
        id=item.get("id"),
        name=item["name"],
        country=item.get("country", "India"),
        role=role,
        batting_style=item.get("batting_style", "Right Handed"),
        bowling_style=item.get("bowling_style", "None"),
        base_price=item.get("base_price", 20000000),
        is_overseas=item.get("is_overseas", False),
        is_uncapped=is_uncapped,
        pool=pool,
        is_marquee=bool(is_marquee or pool == "Marquee"),
        set_name=set_name,
        image_url=item.get("image_url", ""),
        rating=rating
    )


def seed_or_sync_players(force=False):
    """
    Seeds or synchronizes the database from data/players.json.
    If force=True, cleans and reloads the full 300-player roster with correct IDs 1..300.
    If force=False, seeds if empty, adds missing players, and updates pool/category metadata.
    """
    ensure_schema_columns()

    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "players.json")
    if not os.path.exists(json_path):
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        players_data = json.load(f)

    existing_count = Player.query.count()

    if force:
        from app.models.bid import Bid, AuctionEvent
        from app.models.auction import AuctionPlayer, AuctionRoom
        from app.models.team import TeamSquad, Team

        # Clean test auction records that reference obsolete player IDs
        Bid.query.delete()
        AuctionEvent.query.delete()
        TeamSquad.query.delete()
        AuctionPlayer.query.delete()
        AuctionRoom.query.delete()
        Team.query.delete()
        Player.query.delete()
        db.session.commit()

        for item in players_data:
            p = _build_player_obj(item)
            db.session.add(p)
        db.session.commit()
        print(f"Force seeded all {len(players_data)} players into the database with pools & categories.")
        return len(players_data)

    if existing_count == 0:
        for item in players_data:
            p = _build_player_obj(item)
            db.session.add(p)
        db.session.commit()
        print(f"Seeded {len(players_data)} players into empty database.")
        return len(players_data)

    # Sync missing or update pool info on existing players
    existing_ids = {p.id for p in Player.query.with_entities(Player.id).all()}
    added = 0
    for item in players_data:
        if item.get("id") not in existing_ids:
            p = _build_player_obj(item)
            db.session.add(p)
            added += 1

    # Update existing player pool and set_name if missing
    players_by_id = {item.get("id"): item for item in players_data}
    db_players = Player.query.all()
    for p in db_players:
        item = players_by_id.get(p.id)
        if item:
            item_pool = item.get("pool") or ("Marquee" if (not item.get("is_uncapped") and item.get("rating", 0) >= 93) else ("Uncapped" if item.get("is_uncapped") else "Capped"))
            item_marquee = bool(item.get("is_marquee") or item_pool == "Marquee")
            plural = "Batsmen" if p.role == "Batsman" else ("Bowlers" if p.role == "Bowler" else ("All-rounders" if p.role == "All-rounder" else "Wicketkeepers"))
            item_set = item.get("set_name") or f"{item_pool} {plural}"

            if not p.pool or p.pool != item_pool or p.is_marquee != item_marquee or not p.set_name:
                p.pool = item_pool
                p.is_marquee = item_marquee
                p.set_name = item_set

    db.session.commit()
    if added > 0:
        print(f"Synchronized database with {added} new players (Total: {Player.query.count()}).")

    return Player.query.count()


def seed_players_if_empty():
    """Backwards-compatible alias for seed_or_sync_players."""
    return seed_or_sync_players(force=False)


def search_players(query=None, role=None, pool=None, country=None, is_overseas=None, is_uncapped=None, min_price=None, max_price=None, page=1, per_page=20):
    """Filters and searches players with pagination, supporting pools & roles."""
    q = Player.query
    if query:
        q = q.filter(Player.name.ilike(f"%{query}%"))
    if role and role != "All":
        q = q.filter(Player.role == role)
    if pool and pool != "All":
        if pool == "Marquee":
            q = q.filter((Player.pool == "Marquee") | (Player.is_marquee == True))
        elif pool == "Uncapped":
            q = q.filter((Player.pool == "Uncapped") | (Player.is_uncapped == True))
        elif pool == "Capped":
            q = q.filter((Player.pool == "Capped") & (Player.is_uncapped == False) & (Player.is_marquee == False))
        else:
            q = q.filter(Player.pool == pool)
    if country and country != "All":
        q = q.filter(Player.country == country)
    if is_overseas is not None:
        q = q.filter(Player.is_overseas == is_overseas)
    if is_uncapped is not None:
        q = q.filter(Player.is_uncapped == is_uncapped)
    if min_price is not None:
        q = q.filter(Player.base_price >= min_price)
    if max_price is not None:
        q = q.filter(Player.base_price <= max_price)

    # Order by marquee first, rating descending, then base price descending
    q = q.order_by(Player.rating.desc(), Player.base_price.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        "players": [p.to_dict() for p in pagination.items],
        "total": pagination.total,
        "pages": pagination.pages,
        "current_page": page,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev
    }


def get_player_by_id(player_id):
    """Fetches a single player by ID."""
    return db.session.get(Player, player_id)

