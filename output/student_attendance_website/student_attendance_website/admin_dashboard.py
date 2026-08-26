"""Admin dashboard routes for the Student Attendance Website.

Provides a view for administrators to manage users and view system settings.
The routes are registered on a Flask Blueprint so they can be imported and
registered in the main application factory.
"""

from flask import Blueprint, render_template, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from student_attendance_website.models import User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _admin_required(func):
    """Decorator that restricts access to users with role 'admin'."""
    @login_required
    def wrapper(*args, **kwargs):
        if getattr(current_user, 'role', None) != 'admin':
            abort(403)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@admin_bp.route('/dashboard')
@_admin_required
def dashboard():
    """Render the admin dashboard.

    The template receives a list of all users and the current application
    configuration (excluding any secret values).  This information can be used
    to display user management tables and system‑wide settings.
    """
    # Load users with their related role‑specific tables for convenience.
    users = (
        User.query.options(
            joinedload('student'),
            joinedload('teacher'),
            joinedload('staff')
        )
        .order_by(User.email)
        .all()
    )

    # Prepare a safe copy of configuration values for display.
    safe_config = {
        key: value
        for key, value in current_app.config.items()
        if key.isupper() and key not in {'SECRET_KEY', 'SQLALCHEMY_DATABASE_URI'}
    }

    return render_template(
        'dashboard.html',
        users=users,
        config=safe_config,
        current_user=current_user,
    )
