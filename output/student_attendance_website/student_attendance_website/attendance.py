from datetime import datetime

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from student_attendance_website.models import db, AttendanceRecord, Student

attendance_bp = Blueprint('attendance', __name__)


def _parse_date(date_str: str) -> datetime:
    """Parse a YYYY-MM-DD string into a datetime object.
    Raises a 400 Bad Request if the format is invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (TypeError, ValueError):
        abort(400, description=f"Invalid date format for '{date_str}'. Expected YYYY-MM-DD.")


@attendance_bp.route('/attendance', methods=['GET'])
@login_required
def view_attendance():
    """Return attendance records for a given student within an optional date range.

    Query Parameters
    ----------------
    student_id: int (required) – ID of the student whose records are requested.
    start: str (optional) – Start date in YYYY-MM-DD format. Inclusive.
    end:   str (optional) – End date in YYYY-MM-DD format. Inclusive.

    Permissions
    -----------
    * Teachers and staff can view any student's attendance.
    * Students/parents can only view their own child's records – this is simplified
      to a check that the current user is linked to the requested student via the
      `Student.user_id` foreign key.
    """
    # ---------------------------------------------------------------------
    # Validate and fetch query parameters
    # ---------------------------------------------------------------------
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        abort(400, description="Missing required query parameter 'student_id'.")

    start_str = request.args.get('start')
    end_str = request.args.get('end')

    start_date = _parse_date(start_str) if start_str else None
    end_date = _parse_date(end_str) if end_str else None

    # ---------------------------------------------------------------------
    # Authorization check
    # ---------------------------------------------------------------------
    student = Student.query.get_or_404(student_id)
    # Assume role attribute on User model: 'admin', 'teacher', 'staff', 'student', 'parent'
    allowed = False
    if hasattr(current_user, 'role'):
        if current_user.role in {'admin', 'teacher', 'staff'}:
            allowed = True
        elif current_user.role in {'student', 'parent'}:
            # For simplicity, allow if the logged‑in user owns the student record
            allowed = student.user_id == current_user.id
    if not allowed:
        abort(403, description="You do not have permission to view this student's attendance.")

    # ---------------------------------------------------------------------
    # Build the query
    # ---------------------------------------------------------------------
    query = AttendanceRecord.query.filter_by(student_id=student_id)
    if start_date:
        query = query.filter(AttendanceRecord.date >= start_date.date())
    if end_date:
        query = query.filter(AttendanceRecord.date <= end_date.date())

    records = query.order_by(AttendanceRecord.date.desc()).all()

    # ---------------------------------------------------------------------
    # Serialize response
    # ---------------------------------------------------------------------
    result = []
    for rec in records:
        result.append({
            "id": rec.id,
            "student_id": rec.student_id,
            "date": rec.date.isoformat(),
            "status": rec.status,
            "marked_by": rec.marked_by,
            "timestamp": rec.timestamp.isoformat() if rec.timestamp else None,
        })

    return jsonify({"attendance": result})
