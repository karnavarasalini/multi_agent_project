"""Public view routes for the food menu website.

Provides the homepage, category listings, item detail page and search
functionality. All routes are registered on a Flask Blueprint named
``public_bp`` which is expected to be imported and registered in the
application factory (``food_menu_website.app.__init__``).
"""

from flask import Blueprint, render_template, request, abort
from sqlalchemy import or_

# Local imports – models are defined in ``food_menu_website.models``
from food_menu_website.models import Category, MenuItem

public_bp = Blueprint("public", __name__)


@public_bp.route("/", methods=["GET"])
def home():
    """Render the home page showing all categories as tiles.

    Returns
    -------
    Response
        Rendered ``home.html`` template with a ``categories`` context
        variable containing a list of :class:`Category` objects.
    """
    categories = Category.query.all()
    return render_template("home.html", categories=categories)


@public_bp.route("/menu/<string:category_slug>", methods=["GET"])
def category_items(category_slug: str):
    """List menu items belonging to a specific category.

    Parameters
    ----------
    category_slug: str
        URL‑friendly slug identifying the category.
    """
    category = Category.query.filter_by(slug=category_slug).first()
    if not category:
        abort(404, description="Category not found")
    items = MenuItem.query.filter_by(category_id=category.id).all()
    return render_template("category.html", category=category, items=items)


@public_bp.route("/item/<string:item_slug>", methods=["GET"])
def item_detail(item_slug: str):
    """Display detailed information for a single menu item.

    Parameters
    ----------
    item_slug: str
        URL‑friendly slug identifying the menu item.
    """
    item = MenuItem.query.filter_by(slug=item_slug).first()
    if not item:
        abort(404, description="Menu item not found")
    return render_template("item_detail.html", item=item)


@public_bp.route("/search", methods=["GET"])
def search():
    """Search menu items by a free‑text query.

    The query string is read from the ``q`` URL parameter.  Matching is
    performed case‑insensitively against the ``name`` and ``description``
    fields of :class:`MenuItem`.
    """
    query = request.args.get("q", "").strip()
    results = []
    if query:
        like_pattern = f"%{query}%"
        results = (
            MenuItem.query.filter(
                or_(
                    MenuItem.name.ilike(like_pattern),
                    MenuItem.description.ilike(like_pattern),
                )
            )
            .all()
        )
    return render_template("search.html", query=query, results=results)
