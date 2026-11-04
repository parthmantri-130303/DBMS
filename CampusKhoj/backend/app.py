import datetime
import time
from collections import defaultdict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .config import config
from .errors import RateLimitedError, register_error_handlers
from .routes.admin import admin_bp
from .routes.auth import auth_bp
from .routes.claims import claims_bp
from .routes.items import items_bp
from .routes.messages import messages_bp
from .routes.notifications import notif_bp
from .routes.profile import profile_bp
from .routes.reference import ref_bp
from .routes.timeline import timeline_bp

_rate_limits = defaultdict(list)

def setup_rate_limiting(app):
    @app.before_request
    def check_rate_limits():
        if app.testing or app.config.get("TESTING"):
            return
        
        path = request.path
        if not path.startswith("/api/"):
            return

        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
        now = time.time()

        # Stricter limit on auth login (20 per min) vs general API (180 per min)
        if path.startswith("/api/v1/auth/login"):
            key = f"auth:{ip}"
            limit = 20
            window = 60
        else:
            key = f"api:{ip}"
            limit = 180
            window = 60

        timestamps = [t for t in _rate_limits[key] if t > now - window]
        if len(timestamps) >= limit:
            raise RateLimitedError("Rate limit exceeded. Please slow down and try again shortly.")
        timestamps.append(now)
        _rate_limits[key] = timestamps
        return

def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = config.JWT_SECRET

    # Configure CORS for both portals
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"]
    )

    # Register error handlers
    register_error_handlers(app)

    # Setup sliding window rate limiting
    setup_rate_limiting(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(ref_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(notif_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(admin_bp)

    # Media folder file server
    @app.route("/media/<path:filename>")
    def serve_media(filename):
        return send_from_directory(config.MEDIA_ROOT, filename)

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        db_status = "disconnected"
        try:
            from .db import query_one
            row = query_one("SELECT 1 AS alive")
            if row and row.get("alive") == 1:
                db_status = "connected"
        except Exception as e:
            db_status = f"error: {e!s}"

        return jsonify({
            "status": "healthy",
            "service": "campuskhoj-api",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "database": db_status
        }), 200

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
