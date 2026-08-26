"""QR code generation endpoint for student check‑in.

Provides a Flask Blueprint with a single route:
    GET /qr/<student_id>
which creates a secure token, stores it in the QRToken table, and returns a PNG
image of the generated QR code containing that token.
"""

from datetime import datetime, timedelta
import secrets
from io import BytesIO

import qrcode
from flask import Blueprint, abort, current_app, send_file

# Import the SQLAlchemy instance and models from the package.
from .models import db, QRToken, Student

# Blueprint registration name matches the module purpose.
qr_bp = Blueprint('qr', __name__)

@qr_bp.route('/qr/<int:student_id>', methods=['GET'])
def generate_qr(student_id: int):
    """Generate a QR code for the given ``student_id``.

    * Validates that the student exists.
    * Creates a cryptographically‑secure random token.
    * Stores the token with an expiration timestamp (default 2 hours).
    * Returns the QR code image (PNG) directly as the HTTP response.
    """
    # Ensure the student exists; 404 otherwise.
    student = Student.query.get(student_id)
    if student is None:
        abort(404, description="Student not found")

    # Generate a secure token and set an expiration.
    token = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(hours=2)

    # Persist the token.
    qr_token = QRToken(student_id=student.id, token=token, expires_at=expires_at)
    db.session.add(qr_token)
    db.session.commit()

    # Build the QR code. For simplicity we encode only the token string.
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    # Write PNG image to an in‑memory buffer.
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Return the image with appropriate MIME type.
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=False,
        download_name=f'qr_{student_id}.png'
    )
