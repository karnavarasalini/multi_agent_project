import os
import stripe
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from movie_booking_website.models import db, Booking, Payment

# Blueprint for payment‑related routes
payment_bp = Blueprint('payment', __name__)

# Initialise Stripe with secret key from environment
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@payment_bp.route('/api/checkout', methods=['POST'])
def create_checkout():
    """Create a Stripe Checkout Session for a given booking.

    Expected JSON payload:
        {"booking_id": <int>}
    Returns the Checkout Session ID on success.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    booking_id = data.get('booking_id')
    if not booking_id:
        return jsonify({"error": "'booking_id' is required"}), 400

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404

    # Prevent duplicate payments
    if getattr(booking, 'status', None) == 'paid':
        return jsonify({"error": "Booking already paid"}), 400

    # Create a pending payment record linked to the booking
    payment = Payment(
        booking_id=booking.id,
        payment_gateway='stripe',
        amount=booking.total_price,
        status='pending',
        processed_at=None
    )
    db.session.add(payment)
    db.session.commit()

    # Stripe line item – amount is expressed in cents
    line_items = [{
        'price_data': {
            'currency': 'usd',
            'unit_amount': int(booking.total_price * 100),
            'product_data': {
                'name': f'Booking #{booking.id}',
                'description': f'Movie ticket purchase',
            },
        },
        'quantity': 1,
    }]

    # URLs for success / cancellation – configurable via app config
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
    success_url = f"{frontend_url}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{frontend_url}/checkout/cancel"

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'payment_id': payment.id,
                'booking_id': booking.id,
            },
        )
        return jsonify({'sessionId': session.id})
    except Exception as e:
        current_app.logger.error(f'Stripe checkout creation failed: {e}')
        return jsonify({'error': 'Stripe checkout creation failed'}), 500

@payment_bp.route('/api/webhook', methods=['POST'])
def stripe_webhook():
    """Handle incoming Stripe webhook events.

    Only the `checkout.session.completed` event is processed to mark a payment
    as succeeded and update the related booking status.
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return 'Invalid signature', 400

    # Process the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_id = session['metadata'].get('payment_id')
        if payment_id:
            payment = Payment.query.get(payment_id)
            if payment:
                payment.status = 'succeeded'
                payment.processed_at = datetime.utcnow()
                # Update associated booking status
                booking = Booking.query.get(payment.booking_id)
                if booking:
                    booking.status = 'paid'
                db.session.commit()
    # Acknowledge receipt of the event
    return '', 200
