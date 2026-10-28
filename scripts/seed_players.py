import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse
from app import create_app
from app.extensions import db
from app.services.player_service import seed_or_sync_players
from app.models.player import Player

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed IPL 2026 300 player pool into database")
    parser.add_argument("--force", action="store_true", help="Force clean reload of all 300 players")
    args = parser.parse_args()

    flask_app = create_app()
    with flask_app.app_context():
        db.create_all()
        count = seed_or_sync_players(force=args.force)
        total_in_db = Player.query.count()
        print(f"Database successfully loaded with {total_in_db} players! (Target: 300)")
