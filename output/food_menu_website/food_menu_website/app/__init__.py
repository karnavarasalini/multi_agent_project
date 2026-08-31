'''Flask application factory for the food_menu_website project.

This module creates and configures the Flask app, registers blueprints,
and initialises extensions such as Flask‑Login and Flask‑Babel.
''' 

from flask import Flask
from flask_login import LoginManager
from flask_babel import Babel

from ..config import Config

# Initialise extensions (instances are shared across the app)
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.session_protection = "strong"

babel = Babel()


def create_app(config_class: type[Config] = Config) -> Flask:
    """Application factory.

    Args:
        config_class: The configuration class to use. Defaults to ``Config``
            from :pymod:`food_menu_website.config`.

    Returns:
        A fully configured :class:`flask.Flask` instance.
    """
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(config_class)

    # Initialise extensions with the app instance
    login_manager.init_app(app)
    babel.init_app(app)

    # Register blueprints – import inside the function to avoid circular imports
    from ..views import main as main_bp
    from ..admin import admin as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Example: make ``gettext`` available in templates
    @app.context_processor
    def inject_globals():
        return {"_": babel.gettext}

    return app
