"""SQLAlchemy ORM models for the Movie Booking website.

This module defines the database schema for all core entities:
- User
- Movie
- Theater
- Seat
- Showtime
- Booking
- Payment

It uses Flask‑SQLAlchemy. The `db` instance is created here and can be
imported by the Flask application (see `app.py`).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# The SQLAlchemy instance used throughout the package.
# The Flask app will import this and call `init_app(app)` during startup.

db = SQLAlchemy()

# Association table for the many‑to‑many relationship between Booking and Seat.
booking_seats = db.Table(
    "booking_seats",
    db.Column("booking_id", db.Integer, db.ForeignKey("booking.id"), primary_key=True),
    db.Column("seat_id", db.Integer, db.ForeignKey("seat.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="customer", nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    bookings = db.relationship("Booking", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"


class Movie(db.Model):
    __tablename__ = "movie"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    synopsis = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    trailer_url = db.Column(db.String(500), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False)

    showtimes = db.relationship("Showtime", back_populates="movie", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Movie {self.id} {self.title}>"


class Theater(db.Model):
    __tablename__ = "theater"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    seats = db.relationship("Seat", back_populates="theater", cascade="all, delete-orphan")
    showtimes = db.relationship("Showtime", back_populates="theater", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Theater {self.id} {self.name}>"


class Seat(db.Model):
    __tablename__ = "seat"

    id = db.Column(db.Integer, primary_key=True)
    theater_id = db.Column(db.Integer, db.ForeignKey("theater.id"), nullable=False)
    row = db.Column(db.String(5), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    is_vip = db.Column(db.Boolean, default=False, nullable=False)

    theater = db.relationship("Theater", back_populates="seats")
    bookings = db.relationship(
        "Booking",
        secondary=booking_seats,
        back_populates="seats",
    )

    __table_args__ = (
        db.UniqueConstraint("theater_id", "row", "number", name="uq_seat_position"),
    )

    def __repr__(self) -> str:
        return f"<Seat {self.id} {self.row}{self.number} VIP={self.is_vip}>"


class Showtime(db.Model):
    __tablename__ = "showtime"

    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=False)
    theater_id = db.Column(db.Integer, db.ForeignKey("theater.id"), nullable=False)
    show_date = db.Column(db.Date, nullable=False)
    show_time = db.Column(db.Time, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)

    movie = db.relationship("Movie", back_populates="showtimes")
    theater = db.relationship("Theater", back_populates="showtimes")
    bookings = db.relationship("Booking", back_populates="showtime", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return (
            f"<Showtime {self.id} movie={self.movie_id} theater={self.theater_id} "
            f"date={self.show_date} time={self.show_time}>"
        )


class Booking(db.Model):
    __tablename__ = "booking"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    showtime_id = db.Column(db.Integer, db.ForeignKey("showtime.id"), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    user = db.relationship("User", back_populates="bookings")
    showtime = db.relationship("Showtime", back_populates="bookings")
    seats = db.relationship(
        "Seat",
        secondary=booking_seats,
        back_populates="bookings",
    )

    payments = db.relationship("Payment", back_populates="booking", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Booking {self.id} user={self.user_id} status={self.status}>"


class Payment(db.Model):
    __tablename__ = "payment"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)
    payment_gateway = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    processed_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    booking = db.relationship("Booking", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment {self.id} booking={self.booking_id} status={self.status}>"
