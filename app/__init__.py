import os
from flask import Flask, jsonify, render_template, request
from app.config import config_by_name
from app.extensions import db, migrate, login_manager, socketio, cors
from app.models.player import format_inr
from app.services.player_service import seed_players_if_empty, seed_or_sync_players
from app.services.timer_service import start_timer_service

# Pre-register SocketIO event decorators while socketio.server is None
# so that all events are preserved in socketio.handlers for every app instance
import app.sockets  # noqa: F401

def create_app(config_name=None):
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    login_manager.init_app(flask_app)
    cors.init_app(flask_app)

    # Trust X-Forwarded-* headers when behind reverse proxies (Vercel, Render, Cloudflare)
    from werkzeug.middleware.proxy_fix import ProxyFix
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Initialize SocketIO with cross-origin support and threading/simple_websocket
    socketio.init_app(flask_app, cors_allowed_origins="*", async_mode="threading")

    # Register custom Jinja filters
    @flask_app.template_filter("inr")
    def inr_filter(amount):
        return format_inr(amount)

    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.auction_routes import auction_bp
    from app.routes.team_routes import team_bp
    from app.routes.player_routes import player_bp
    from app.routes.ai_routes import ai_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(auction_bp)
    flask_app.register_blueprint(team_bp)
    flask_app.register_blueprint(player_bp)
    flask_app.register_blueprint(ai_bp)

    # Global HTTP error handlers
    @flask_app.errorhandler(404)
    def handle_404(err):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Endpoint not found"}), 404
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(500)
    def handle_500(err):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @flask_app.errorhandler(403)
    def handle_403(err):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Forbidden"}), 403
        return render_template("errors/404.html"), 403

    # Database initialization and background timer
    with flask_app.app_context():
        try:
            db.create_all()
            seed_or_sync_players(force=False)
        except Exception as e:
            print(f"Database init warning: {e}")

        # Start authoritative background auction timer (non-testing and non-serverless)
        if not flask_app.config.get("TESTING") and not os.getenv("VERCEL"):
            start_timer_service(flask_app)

    return flask_app
