import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"

def create_app(config_object="student_attendance_website.config.Config"):
    """Factory pattern for creating Flask application instances.

    Args:
        config_object (str): Fully qualified config class name.
    Returns:
        Flask: Configured Flask application.
    """
    app = Flask(__name__, instance_relative_config=False)
    # Load configuration
    app.config.from_object(config_object)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints (placeholders – actual blueprints live in their modules)
    from .auth import auth_bp
    from .attendance import attendance_bp
    from .reports import reports_bp
    from .qr import qr_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(qr_bp, url_prefix="/qr")

    # Simple health check route
    @app.route("/ping")
    def ping():
        return {"status": "ok"}

    return app
