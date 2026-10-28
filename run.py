import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import socketio

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"[IPL Auction Simulator] Starting on http://localhost:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
