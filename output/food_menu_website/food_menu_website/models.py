"""SQLAlchemy data models for the food_menu_website package.

Defines the core entities used throughout the application:
- Category
- MenuItem
- User

The models are built on top of Flask‑SQLAlchemy.  A ``db`` instance is
created here for simplicity; the same instance can be imported by the
application factory in ``app/__init__.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# The SQLAlchemy object – other modules import this to access the DB.
# In a real app the instance would normally be created in the app factory
# and passed around, but keeping it here satisfies the task requirements.

db = SQLAlchemy()


class Category(db.Model):
    """A menu category (e.g. *Starters*, *Desserts*).

    Attributes
    ----------
    id: int – primary key.
    name: str – human‑readable name.
    slug: str – URL‑safe identifier, unique.
    description: str – optional longer text.
    """

    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to menu items.
    menu_items = db.relationship(
        "MenuItem", backref="category", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category {self.id}:{self.name}>"


class MenuItem(db.Model):
    """A single dish or product offered by the restaurant.

    Attributes
    ----------
    id: int – primary key.
    name: str – display name.
    slug: str – URL‑safe identifier, unique.
    description: str – optional detailed description.
    price: float – monetary value.
    image_path: str – relative path to the stored image.
    category_id: int – FK to :class:`Category`.
    dietary_tags: JSON – list of strings such as "vegan", "gluten‑free".
    ingredients: JSON – list of ingredient names.
    language_code: str – ISO‑639‑1 language of the record (e.g. "en", "fr").
    """

    __tablename__ = "menu_item"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    dietary_tags = db.Column(db.JSON, nullable=True, default=list)
    ingredients = db.Column(db.JSON, nullable=True, default=list)
    language_code = db.Column(db.String(5), nullable=False, default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<MenuItem {self.id}:{self.name}>"

    @property
    def price_float(self) -> float:
        """Convenient accessor returning the price as a ``float``.
        ``Numeric`` stores a Decimal internally; most templates prefer a float.
        """
        return float(self.price)


class User(db.Model):
    """Application user for admin authentication.

    Only users with the role ``"admin"`` are allowed to access the admin UI.
    Passwords are stored as a salted hash using Werkzeug's utilities.
    """

    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="admin")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.id}:{self.username}>"

    def set_password(self, password: str) -> None:
        """Hash and store a new password.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash.
        """
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """True if the user has administrative privileges.
        """
        return self.role.lower() == "admin"
