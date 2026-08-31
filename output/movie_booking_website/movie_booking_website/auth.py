import datetime
import functools
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

# Local imports – assume `db` and model definitions live in models.py
from .models import db, User

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# ---------------------------------------------------------------------------
# JWT helper functions
# ---------------------------------------------------------------------------

def _get_secret_key():
    """Return the secret key used for JWT encoding/decoding.
    The secret key is expected to be set in the Flask app config under
    ``SECRET_KEY``. If it is missing, a RuntimeError is raised.
    """
    secret = current_app.config.get('SECRET_KEY')
    if not secret:
        raise RuntimeError('SECRET_KEY not configured for Flask app')
    return secret


def create_access_token(user_id: int, role: str, expires_delta: datetime.timedelta = None) -> str:
    """Create a signed JWT for the given user.

    Args:
        user_id: Primary key of the user.
        role: User role (e.g., ``admin`` or ``user``).
        expires_delta: Optional ``timedelta`` for token expiry. If omitted,
            defaults to 1 hour.
    Returns:
        A JWT as a string.
    """
    if expires_delta is None:
        expires_delta = datetime.timedelta(hours=1)
    payload = {
        'sub': user_id,
        'role': role,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + expires_delta,
    }
    token = jwt.encode(payload, _get_secret_key(), algorithm='HS256')
    # PyJWT returns ``bytes`` in older versions, ``str`` in newer – normalize.
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def decode_access_token(token: str) -> dict:
    """Validate a JWT and return its payload.

    Raises ``jwt.ExpiredSignatureError`` if the token is expired and
    ``jwt.InvalidTokenError`` for any other validation problem.
    """
    return jwt.decode(token, _get_secret_key(), algorithms=['HS256'])


def token_required(fn):
    """Flask view decorator that enforces JWT authentication.

    The decoded token payload is stored on ``flask.g`` as ``g.current_user``
    (the ``User`` model instance). If authentication fails, a 401 response
    is returned.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Authorization header must be Bearer token'}), 401
        token = parts[1]
        try:
            payload = decode_access_token(token)
            user = User.query.get(payload['sub'])
            if not user:
                raise jwt.InvalidTokenError('User not found')
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'message': f'Invalid token: {str(e)}'}), 401
        return fn(*args, **kwargs)
    return wrapper

# ---------------------------------------------------------------------------
# Registration endpoint
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    role = data.get('role', 'user')

    if not email or not password or not name:
        return jsonify({'message': 'Missing required fields'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 409

    password_hash = generate_password_hash(password)
    user = User(email=email, password_hash=password_hash, name=name, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'created_at': user.created_at.isoformat()
    }), 201

# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = create_access_token(user_id=user.id, role=user.role)
    return jsonify({
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role
        }
    })

# ---------------------------------------------------------------------------
# Helper endpoint (optional) – retrieve current user info
# ---------------------------------------------------------------------------

@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    user = g.current_user
    return jsonify({
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role,
        'created_at': user.created_at.isoformat()
    })
