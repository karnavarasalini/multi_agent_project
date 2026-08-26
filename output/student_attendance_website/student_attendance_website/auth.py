from flask import Blueprint, request, jsonify, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import check_password_hash
from .models import User, db

# Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def init_auth(app):
    """Register the auth blueprint and initialise Flask-Login with the app.

    This function should be called from the central application factory or
    ``app.py`` after the Flask app instance has been created.
    """
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Extend the User model to satisfy Flask-Login's requirements if not already done
# (UserMixin provides is_authenticated, is_active, is_anonymous, get_id)
if not issubclass(User, UserMixin):
    User.__bases__ = (UserMixin,) + User.__bases__

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user (teacher or admin) via email/password.

    Expected JSON payload:
    {
        "email": "user@example.com",
        "password": "plain-text-password"
    }
    """
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Email and password required'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if user is None:
        return jsonify({'error': 'Invalid credentials'}), 401

    if not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Optional: restrict login to certain roles (e.g., teacher, admin)
    if getattr(user, 'role', None) not in ('teacher', 'admin'):
        return jsonify({'error': 'Insufficient permissions'}), 403

    login_user(user)
    return jsonify({'message': 'Logged in successfully'}), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Terminate the current user session."""
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200
