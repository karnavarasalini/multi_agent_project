from flask import Blueprint, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from movie_booking_website.models import db, Showtime, Seat, Booking
from movie_booking_website.auth import jwt_required, get_current_user

showtime_bp = Blueprint('showtime', __name__, url_prefix='/api')

@showtime_bp.route('/showtimes/<int:showtime_id>/seats', methods=['GET'])
@jwt_required
def get_seat_map(showtime_id):
    """Return seat map for a showtime with real‑time availability."""
    # Verify showtime exists
    showtime = Showtime.query.get_or_404(showtime_id)

    # All seats for the theater hosting the showtime
    seats = Seat.query.filter_by(theater_id=showtime.theater_id).all()

    # Seats already reserved (pending or confirmed) for this showtime
    booked_seat_ids = set()
    bookings = Booking.query.filter_by(showtime_id=showtime_id).filter(
        Booking.status.in_(['pending', 'confirmed'])
    ).all()
    for b in bookings:
        booked_seat_ids.update(b.seat_ids or [])

    seat_map = []
    for seat in seats:
        seat_map.append({
            'id': seat.id,
            'row': seat.row,
            'number': seat.number,
            'is_vip': seat.is_vip,
            'available': seat.id not in booked_seat_ids,
        })
    return jsonify({'showtime_id': showtime_id, 'seats': seat_map})

@showtime_bp.route('/cart', methods=['POST'])
@jwt_required
def add_to_cart():
    """Add selected seats to the user's cart (a pending booking)."""
    data = request.get_json()
    if not data or 'showtime_id' not in data or 'seat_ids' not in data:
        return jsonify({'error': 'showtime_id and seat_ids are required'}), 400

    user = get_current_user()
    showtime_id = data['showtime_id']
    seat_ids = data['seat_ids']

    if not isinstance(seat_ids, list) or not all(isinstance(s, int) for s in seat_ids):
        return jsonify({'error': 'seat_ids must be a list of integers'}), 400

    try:
        with db.session.begin():
            # Lock the showtime row to avoid race conditions on seat count updates
            showtime = Showtime.query.filter_by(id=showtime_id).with_for_update().first()
            if not showtime:
                return jsonify({'error': 'Showtime not found'}), 404

            # Validate seats belong to the same theater and lock them
            seats = Seat.query.filter(
                Seat.id.in_(seat_ids),
                Seat.theater_id == showtime.theater_id
            ).with_for_update().all()
            if len(seats) != len(seat_ids):
                return jsonify({'error': 'One or more seats are invalid for this showtime'}), 400

            # Check for existing reservations on these seats
            existing_bookings = Booking.query.filter_by(showtime_id=showtime_id).filter(
                Booking.status.in_(['pending', 'confirmed'])
            ).with_for_update().all()
            for eb in existing_bookings:
                if set(seat_ids) & set(eb.seat_ids or []):
                    return jsonify({'error': 'One or more seats are already reserved'}), 409

            # Compute total price (simple example, could be more complex)
            total_price = calculate_price(seat_ids)

            # Create a pending booking representing the cart
            new_booking = Booking(
                user_id=user.id,
                showtime_id=showtime_id,
                seat_ids=seat_ids,
                total_price=total_price,
                status='pending'
            )
            db.session.add(new_booking)
        db.session.commit()
        return jsonify({'message': 'Seats added to cart', 'booking_id': new_booking.id}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Error while adding seats to cart')
        return jsonify({'error': 'Internal server error'}), 500

def calculate_price(seat_ids):
    """Calculate total price for a list of seat IDs.
    Base price is $10; VIP seats add $5.
    """
    base_price = 10.0
    vip_surcharge = 5.0
    seats = Seat.query.filter(Seat.id.in_(seat_ids)).all()
    total = 0.0
    for seat in seats:
        price = base_price + (vip_surcharge if seat.is_vip else 0.0)
        total += price
    return total
