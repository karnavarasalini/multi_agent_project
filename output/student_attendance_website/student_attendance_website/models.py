"""SQLAlchemy ORM models for the Student Attendance website.

This module defines the data structures used throughout the application:
- User
- Student
- Teacher
- Staff
- AttendanceRecord
- QRToken

It relies on the Flask‑SQLAlchemy instance `db` created in `app.py`.
"""

from datetime import datetime, timedelta
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Import the SQLAlchemy instance from the application package.
# The app module must expose a variable `db = SQLAlchemy(app)`.
from .app import db


class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STAFF = "staff"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.TEACHER)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships to concrete profiles
    student = db.relationship("Student", uselist=False, back_populates="user")
    teacher = db.relationship("Teacher", uselist=False, back_populates="user")
    staff = db.relationship("Staff", uselist=False, back_populates="user")
    attendance_marked = db.relationship(
        "AttendanceRecord",
        back_populates="marked_by_user",
        foreign_keys="AttendanceRecord.marked_by",
    )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email} ({self.role.value})>"

    # Password helpers
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(20), nullable=False)
    parent_email = db.Column(db.String(255), nullable=False)

    user = db.relationship("User", back_populates="student")
    attendance_records = db.relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    qr_tokens = db.relationship("QRToken", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Student {self.id} {self.first_name} {self.last_name}>"


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)

    user = db.relationship("User", back_populates="teacher")
    # Teachers can also be the `marked_by` user on attendance records via the User relationship.

    def __repr__(self) -> str:
        return f"<Teacher {self.id} {self.first_name} {self.last_name}>"


class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(100), nullable=False)

    user = db.relationship("User", back_populates="staff")

    def __repr__(self) -> str:
        return f"<Staff {self.id} {self.name} ({self.position})>"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(AttendanceStatus), nullable=False)
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("Student", back_populates="attendance_records")
    marked_by_user = db.relationship("User", back_populates="attendance_marked", foreign_keys=[marked_by])

    __table_args__ = (
        db.UniqueConstraint("student_id", "date", name="uq_student_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceRecord {self.id} student={self.student_id} date={self.date} "
            f"status={self.status.value}>"
        )


class QRToken(db.Model):
    __tablename__ = "qr_tokens"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(hours=1))

    student = db.relationship("Student", back_populates="qr_tokens")

    def __repr__(self) -> str:
        return f"<QRToken {self.id} student={self.student_id} expires={self.expires_at}>"
