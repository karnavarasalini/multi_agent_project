from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from sqlalchemy import func
import jwt

from movie_booking_website.models import db, Movie, Theater, Showtime, Booking, Payment, User

admin_bp = Blueprint('admin', __name__)


def _get_jwt_payload():
    auth_header = request.headers.get('Authorization', '')
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    token = parts[1]
    try:
        payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
        return payload
    except jwt.PyJWTError:
        return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        payload = _get_jwt_payload()
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        # attach user info to request context if needed
        request.admin_user_id = payload.get('sub')
        return f(*args, **kwargs)
    return decorated_function

# ---------- Movie CRUD ----------
@admin_bp.route('/api/admin/movies', methods=['POST'])
@admin_required
def create_movie():
    data = request.get_json() or {}
    required = ['title', 'genre', 'synopsis', 'rating', 'trailer_url', 'duration_minutes']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required movie fields'}), 400
    movie = Movie(
        title=data['title'],
        genre=data['genre'],
        synopsis=data['synopsis'],
        rating=data['rating'],
        trailer_url=data['trailer_url'],
        duration_minutes=data['duration_minutes']
    )
    db.session.add(movie)
    db.session.commit()
    return jsonify({'id': movie.id, 'message': 'Movie created'}), 201

@admin_bp.route('/api/admin/movies/<int:movie_id>', methods=['PUT'])
@admin_required
def update_movie(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    data = request.get_json() or {}
    for attr in ['title', 'genre', 'synopsis', 'rating', 'trailer_url', 'duration_minutes']:
        if attr in data:
            setattr(movie, attr, data[attr])
    db.session.commit()
    return jsonify({'id': movie.id, 'message': 'Movie updated'}), 200

# ---------- Theater CRUD ----------
@admin_bp.route('/api/admin/theaters', methods=['POST'])
@admin_required
def create_theater():
    data = request.get_json() or {}
    required = ['name', 'location', 'capacity']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required theater fields'}), 400
    theater = Theater(
        name=data['name'],
        location=data['location'],
        capacity=data['capacity']
    )
    db.session.add(theater)
    db.session.commit()
    return jsonify({'id': theater.id, 'message': 'Theater created'}), 201

@admin_bp.route('/api/admin/theaters/<int:theater_id>', methods=['PUT'])
@admin_required
def update_theater(theater_id):
    theater = Theater.query.get_or_404(theater_id)
    data = request.get_json() or {}
    for attr in ['name', 'location', 'capacity']:
        if attr in data:
            setattr(theater, attr, data[attr])
    db.session.commit()
    return jsonify({'id': theater.id, 'message': 'Theater updated'}), 200

# ---------- Showtime CRUD ----------
@admin_bp.route('/api/admin/showtimes', methods=['POST'])
@admin_required
def create_showtime():
    data = request.get_json() or {}
    required = ['movie_id', 'theater_id', 'show_date', 'show_time', 'available_seats']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required showtime fields'}), 400
    # Validate foreign keys existence
    if not Movie.query.get(data['movie_id']):
        return jsonify({'error': 'Movie not found'}), 404
    if not Theater.query.get(data['theater_id']):
        return jsonify({'error': 'Theater not found'}), 404
    showtime = Showtime(
        movie_id=data['movie_id'],
        theater_id=data['theater_id'],
        show_date=data['show_date'],
        show_time=data['show_time'],
        available_seats=data['available_seats']
    )
    db.session.add(showtime)
    db.session.commit()
    return jsonify({'id': showtime.id, 'message': 'Showtime created'}), 201

@admin_bp.route('/api/admin/showtimes/<int:showtime_id>', methods=['PUT'])
@admin_required
def update_showtime(showtime_id):
    showtime = Showtime.query.get_or_404(showtime_id)
    data = request.get_json() or {}
    for attr in ['movie_id', 'theater_id', 'show_date', 'show_time', 'available_seats']:
        if attr in data:
            if attr == 'movie_id' and not Movie.query.get(data[attr]):
                return jsonify({'error': 'Movie not found'}), 404
            if attr == 'theater_id' and not Theater.query.get(data[attr]):
                return jsonify({'error': 'Theater not found'}), 404
            setattr(showtime, attr, data[attr])
    db.session.commit()
    return jsonify({'id': showtime.id, 'message': 'Showtime updated'}), 200

# ---------- Sales Report ----------
@admin_bp.route('/api/admin/reports/sales', methods=['GET'])
@admin_required
def sales_report():
    # Total revenue from successful payments
    total_revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(Payment.status == 'succeeded').scalar()
    # Number of bookings per day (last 30 days)
    recent = db.session.query(
        func.date(Booking.created_at).label('date'),
        func.count(Booking.id).label('bookings')
    ).filter(Booking.created_at >= func.now() - func.interval('30 day')).group_by('date').order_by('date').all()
    daily = [{ 'date': str(row.date), 'bookings': row.bookings } for row in recent]
    return jsonify({
        'total_revenue': float(total_revenue),
        'bookings_last_30_days': daily
    }), 200
