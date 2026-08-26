'''Report generation endpoints for attendance data.'''

from flask import Blueprint, request, Response, send_file
from io import StringIO, BytesIO
import csv
from datetime import datetime

from .models import AttendanceRecord, Student, db
from sqlalchemy import and_

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Blueprint for report routes
reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _parse_date(date_str: str) -> datetime.date:
    """Parse a YYYY-MM-DD string into a date object."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def generate_attendance_csv(records):
    """Return a CSV string for the supplied attendance records.

    Columns: Student ID, Student Name, Date, Status, Marked By, Timestamp
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Student Name', 'Date', 'Status', 'Marked By', 'Timestamp'])
    for rec in records:
        student = Student.query.get(rec.student_id)
        name = f"{student.first_name} {student.last_name}" if student else ''
        writer.writerow([
            rec.student_id,
            name,
            rec.date.isoformat(),
            rec.status,
            rec.marked_by,
            rec.timestamp.isoformat() if rec.timestamp else ''
        ])
    return output.getvalue()


def generate_attendance_pdf(records, start_date, end_date):
    """Return a PDF (as bytes) for the supplied attendance records.

    The PDF contains a title and a table with the same columns as the CSV.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title = Paragraph(f"Attendance Report: {start_date} to {end_date}", styles['Title'])
    elements.append(title)

    data = [['Student ID', 'Student Name', 'Date', 'Status', 'Marked By', 'Timestamp']]
    for rec in records:
        student = Student.query.get(rec.student_id)
        name = f"{student.first_name} {student.last_name}" if student else ''
        data.append([
            rec.student_id,
            name,
            rec.date.isoformat(),
            rec.status,
            rec.marked_by,
            rec.timestamp.isoformat() if rec.timestamp else ''
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER')
    ]))
    elements.append(table)
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


@reports_bp.route('/attendance', methods=['GET'])
def attendance_report():
    """Endpoint to download attendance data as CSV or PDF.

    Query parameters:
        start (YYYY-MM-DD) – required
        end   (YYYY-MM-DD) – required
        format (csv|pdf)   – optional, defaults to csv
        student_id (int)   – optional filter by student
    """
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    fmt = request.args.get('format', 'csv').lower()
    student_id = request.args.get('student_id', type=int)

    if not start_str or not end_str:
        return Response('Missing required start or end parameters', status=400)

    try:
        start_date = _parse_date(start_str)
        end_date = _parse_date(end_str)
    except ValueError:
        return Response('Invalid date format; expected YYYY-MM-DD', status=400)

    query = AttendanceRecord.query.filter(
        and_(AttendanceRecord.date >= start_date,
             AttendanceRecord.date <= end_date)
    )
    if student_id:
        query = query.filter_by(student_id=student_id)

    records = query.order_by(AttendanceRecord.date).all()

    if fmt == 'pdf':
        pdf_bytes = generate_attendance_pdf(records, start_date, end_date)
        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='attendance_report.pdf'
        )
    else:
        csv_data = generate_attendance_csv(records)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=attendance_report.csv'}
        )
