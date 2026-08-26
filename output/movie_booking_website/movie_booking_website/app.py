"""Flask application factory for the Movie Booking Website.

This module creates the Flask app, loads configuration, initialises extensions
and registers blueprints for the various functional areas of the system.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

db = SQLAlchemy()


class Config:
    """Base configuration class.

    Environment variables can override defaults, which is useful for Docker or
    other deployment scenarios.
    """

    # Secret key for session management / JWT signing
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # SQLAlchemy settings – default to a local SQLite DB for development
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///movie_booking.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings – algorithm used by PyJWT
    JWT_ALGORITHM = "HS256"


def create_app(config_class: type = Config) -> Flask:
    """Application factory.

    Args:
        config_class: The configuration class to use. Defaults to ``Config``.

    Returns:
        A fully configured :class:`flask.Flask` instance.
    """

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.config.from_object(config_class)

    # Initialise extensions
    db.init_app(app)

    # Register blueprints – each sub‑module defines a ``Blueprint`` object.
    # Importing inside the function avoids circular import issues.
    from .auth import auth_bp
    from .movie import movie_bp
    from .showtime import showtime_bp
    from .booking import booking_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(movie_bp, url_prefix="/api")
    app.register_blueprint(showtime_bp, url_prefix="/api")
    app.register_blueprint(booking_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return {"message": "Movie Booking API is running"}

    return app
