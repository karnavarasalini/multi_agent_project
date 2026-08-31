from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import sqlite3
from datetime import datetime

from student_attendance_website.auth import role_required
from student_attendance_website import config

# Blueprint for all view routes
views_bp = Blueprint('views', __name__)

DB_PATH = config.DATABASE_URI  # e.g., 'attendance.db'

def _get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _fetch_student(user_id):
    conn = _get_db_connection()
    student = conn.execute(
        "SELECT * FROM Student WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return student

def _fetch_parent(user_id):
    conn = _get_db_connection()
    parent = conn.execute(
        "SELECT * FROM Parent WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return parent

def _fetch_attendance_by_student(student_id):
    conn = _get_db_connection()
    rows = conn.execute(
        """
        SELECT ar.id, ar.date, ar.status, c.name AS class_name
        FROM AttendanceRecord ar
        JOIN Class c ON ar.class_id = c.id
        WHERE ar.student_id = ?
        ORDER BY ar.date DESC
        """,
        (student_id,)
    ).fetchall()
    conn.close()
    return rows

@views_bp.route('/student/attendance')
@login_required
@role_required('student')
def student_attendance():
    student = _fetch_student(current_user.id)
    if not student:
        abort(404, description='Student record not found')
    attendance = _fetch_attendance_by_student(student['id'])
    # Convert dates to ISO strings for template rendering
    records = [
        {
            'id': row['id'],
            'date': datetime.strptime(row['date'], '%Y-%m-%d').date(),
            'status': row['status'],
            'class_name': row['class_name']
        }
        for row in attendance
    ]
    return render_template('student_attendance.html', student=student, records=records)

@views_bp.route('/parent/attendance')
@login_required
@role_required('parent')
def parent_attendance():
    parent = _fetch_parent(current_user.id)
    if not parent:
        abort(404, description='Parent record not found')
    # A parent may be linked to multiple students; fetch all
    conn = _get_db_connection()
    students = conn.execute(
        "SELECT * FROM Student WHERE id = ?", (parent['student_id'],)
    ).fetchall()
    conn.close()
    # Gather attendance per student
    all_records = []
    for stu in students:
        attendance = _fetch_attendance_by_student(stu['id'])
        for row in attendance:
            all_records.append({
                'student_id': stu['id'],
                'student_name': f"{stu['first_name']} {stu['last_name']}",
                'date': datetime.strptime(row['date'], '%Y-%m-%d').date(),
                'status': row['status'],
                'class_name': row['class_name']
            })
    # Sort by date descending
    all_records.sort(key=lambda r: r['date'], reverse=True)
    return render_template('parent_attendance.html', parent=parent, records=all_records)
