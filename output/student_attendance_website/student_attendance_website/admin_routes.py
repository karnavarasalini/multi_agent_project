import sqlite3
from flask import Blueprint, request, jsonify, abort, current_app, g
from flask_login import login_required, current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def _admin_required():
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(403)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config.get('DATABASE', 'attendance.db'))
        g.db.row_factory = sqlite3.Row
    return g.db

# ---------- Class CRUD ----------
@admin_bp.route('/classes', methods=['GET'])
@login_required
def list_classes():
    _admin_required()
    db = get_db()
    rows = db.execute('SELECT id, name, teacher_id FROM Class').fetchall()
    classes = [dict(row) for row in rows]
    return jsonify(classes), 200

@admin_bp.route('/classes', methods=['POST'])
@login_required
def create_class():
    _admin_required()
    data = request.get_json() or {}
    name = data.get('name')
    teacher_id = data.get('teacher_id')
    if not name or teacher_id is None:
        return jsonify({'error': 'Missing name or teacher_id'}), 400
    db = get_db()
    cur = db.execute('INSERT INTO Class (name, teacher_id) VALUES (?, ?)', (name, teacher_id))
    db.commit()
    new_id = cur.lastrowid
    return jsonify({'id': new_id, 'name': name, 'teacher_id': teacher_id}), 201

@admin_bp.route('/classes/<int:class_id>', methods=['PUT'])
@login_required
def update_class(class_id):
    _admin_required()
    data = request.get_json() or {}
    name = data.get('name')
    teacher_id = data.get('teacher_id')
    if name is None and teacher_id is None:
        return jsonify({'error': 'No fields to update'}), 400
    db = get_db()
    if name is not None:
        db.execute('UPDATE Class SET name = ? WHERE id = ?', (name, class_id))
    if teacher_id is not None:
        db.execute('UPDATE Class SET teacher_id = ? WHERE id = ?', (teacher_id, class_id))
    db.commit()
    return jsonify({'id': class_id, 'name': name, 'teacher_id': teacher_id}), 200

@admin_bp.route('/classes/<int:class_id>', methods=['DELETE'])
@login_required
def delete_class(class_id):
    _admin_required()
    db = get_db()
    db.execute('DELETE FROM Class WHERE id = ?', (class_id,))
    db.commit()
    return jsonify({'result': 'deleted', 'id': class_id}), 200

# ---------- Student CRUD ----------
@admin_bp.route('/students', methods=['GET'])
@login_required
def list_students():
    _admin_required()
    db = get_db()
    rows = db.execute('SELECT id, user_id, class_id, first_name, last_name FROM Student').fetchall()
    students = [dict(row) for row in rows]
    return jsonify(students), 200

@admin_bp.route('/students', methods=['POST'])
@login_required
def create_student():
    _admin_required()
    data = request.get_json() or {}
    user_id = data.get('user_id')
    class_id = data.get('class_id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    if None in (user_id, class_id, first_name, last_name):
        return jsonify({'error': 'Missing required student fields'}), 400
    db = get_db()
    cur = db.execute(
        'INSERT INTO Student (user_id, class_id, first_name, last_name) VALUES (?, ?, ?, ?)',
        (user_id, class_id, first_name, last_name)
    )
    db.commit()
    new_id = cur.lastrowid
    return jsonify({'id': new_id, 'user_id': user_id, 'class_id': class_id,
                    'first_name': first_name, 'last_name': last_name}), 201

@admin_bp.route('/students/<int:student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    _admin_required()
    data = request.get_json() or {}
    fields = []
    values = []
    for col in ('user_id', 'class_id', 'first_name', 'last_name'):
        if col in data:
            fields.append(f"{col} = ?")
            values.append(data[col])
    if not fields:
        return jsonify({'error': 'No fields to update'}), 400
    values.append(student_id)
    db = get_db()
    db.execute(f"UPDATE Student SET {', '.join(fields)} WHERE id = ?", values)
    db.commit()
    return jsonify({'id': student_id, **data}), 200

@admin_bp.route('/students/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    _admin_required()
    db = get_db()
    db.execute('DELETE FROM Student WHERE id = ?', (student_id,))
    db.commit()
    return jsonify({'result': 'deleted', 'id': student_id}), 200
