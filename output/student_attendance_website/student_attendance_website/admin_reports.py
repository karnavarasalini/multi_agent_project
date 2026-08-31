from flask import Blueprint, jsonify, Response, current_app
from flask_login import login_required, current_user
import sqlite3
import csv
import io
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def _admin_required():
    """Abort request if the current user is not an admin."""
    if not current_user.is_authenticated or getattr(current_user, 'role', None) != 'admin':
        from flask import abort
        abort(403)

def get_db():
    """Return a SQLite connection using the path defined in app config.

    The app is expected to set ``app.config['DATABASE']`` to the SQLite file.
    """
    db_path = current_app.config.get('DATABASE', 'attendance.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@admin_bp.route('/reports', methods=['GET'])
@login_required
def reports():
    """Return a JSON list with all attendance records.

    Each record contains:
        - id
        - student_name
        - class_name
        - date (ISO string)
        - status
    """
    _admin_required()
    conn = get_db()
    cur = conn.cursor()
    query = '''
        SELECT ar.id,
               s.first_name || ' ' || s.last_name AS student_name,
               c.name AS class_name,
               ar.date,
               ar.status
        FROM AttendanceRecord ar
        JOIN Student s ON ar.student_id = s.id
        JOIN Class c ON ar.class_id = c.id
        ORDER BY ar.date DESC
    '''
    cur.execute(query)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@admin_bp.route('/export', methods=['GET'])
@login_required
def export():
    """Export the same attendance data as a CSV file.

    The response includes a ``Content‑Disposition`` header so browsers prompt a download.
    """
    _admin_required()
    conn = get_db()
    cur = conn.cursor()
    query = '''
        SELECT s.first_name || ' ' || s.last_name AS student_name,
               c.name AS class_name,
               ar.date,
               ar.status
        FROM AttendanceRecord ar
        JOIN Student s ON ar.student_id = s.id
        JOIN Class c ON ar.class_id = c.id
        ORDER BY ar.date DESC
    '''
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Class Name', 'Date', 'Status'])
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3]])
    csv_data = output.getvalue()
    output.close()
    filename = f"attendance_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment;filename={filename}'
        }
    )
