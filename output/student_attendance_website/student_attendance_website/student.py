"""Student profile CRUD endpoints for the Student Attendance Website.

This module defines a Flask Blueprint that provides the REST API for creating,
reading, updating, and deleting student records. It relies on the existing
SQLAlchemy ``db`` instance and model classes defined in ``models.py``.
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user

from student_attendance_website.models import db, Student, User

# Blueprint registration name
student_bp = Blueprint('student', __name__, url_prefix='/students')


def _has_access() -> bool:
    """Return True if the current user is allowed to manage student data.

    Only users with role ``admin`` or ``teacher`` are permitted.
    """
    return getattr(current_user, 'role', None) in {'admin', 'teacher'}


def _student_to_dict(student: Student) -> dict:
    """Serialize a ``Student`` instance to a plain dict suitable for JSON response."""
    return {
        'id': student.id,
        'user_id': student.user_id,
        'first_name': student.first_name,
        'last_name': student.last_name,
        'grade': student.grade,
        'parent_email': student.parent_email,
        'created_at': student.created_at.isoformat() if hasattr(student, 'created_at') else None,
    }


@student_bp.route('', methods=['GET'])
@login_required
def list_students():
    """List all students.

    Accessible by admins and teachers. Returns a JSON array of student objects.
    """
    if not _has_access():
        abort(403, description='Insufficient permissions')
    students = Student.query.all()
    return jsonify([_student_to_dict(s) for s in students]), 200


@student_bp.route('', methods=['POST'])
@login_required
def create_student():
    """Create a new student record.

    Expected JSON payload:
    {
        "user_id": int,
        "first_name": str,
        "last_name": str,
        "grade": str,
        "parent_email": str
    }
    """
    if not _has_access():
        abort(403, description='Insufficient permissions')
    data = request.get_json() or {}
    required_fields = {'user_id', 'first_name', 'last_name', 'grade', 'parent_email'}
    if not required_fields.issubset(data):
        missing = required_fields - data.keys()
        abort(400, description=f'Missing fields: {", ".join(missing)}')

    # Verify the associated User exists
    user = User.query.get(data['user_id'])
    if not user:
        abort(400, description='User with given user_id does not exist')

    student = Student(
        user_id=data['user_id'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        grade=data['grade'],
        parent_email=data['parent_email'],
        created_at=datetime.utcnow()
    )
    db.session.add(student)
    db.session.commit()
    return jsonify(_student_to_dict(student)), 201


@student_bp.route('/<int:student_id>', methods=['GET'])
@login_required
def get_student(student_id: int):
    """Retrieve details of a single student by ``student_id``."""
    if not _has_access():
        abort(403, description='Insufficient permissions')
    student = Student.query.get_or_404(student_id)
    return jsonify(_student_to_dict(student)), 200


@student_bp.route('/<int:student_id>', methods=['PUT'])
@login_required
def update_student(student_id: int):
    """Update an existing student record.

    Accepts partial JSON payload; only provided fields are updated.
    """
    if not _has_access():
        abort(403, description='Insufficient permissions')
    student = Student.query.get_or_404(student_id)
    data = request.get_json() or {}
    allowed_fields = {'user_id', 'first_name', 'last_name', 'grade', 'parent_email'}
    for key, value in data.items():
        if key not in allowed_fields:
            continue
        if key == 'user_id':
            # Validate new user reference
            if not User.query.get(value):
                abort(400, description='User with given user_id does not exist')
        setattr(student, key, value)
    db.session.commit()
    return jsonify(_student_to_dict(student)), 200


@student_bp.route('/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id: int):
    """Delete a student record permanently."""
    if not _has_access():
        abort(403, description='Insufficient permissions')
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({'message': f'Student {student_id} deleted'}), 200
