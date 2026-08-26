from flask import Blueprint, request, jsonify, current_app
from movie_booking_website.models import Movie

movie_bp = Blueprint('movie', __name__)


def _movie_to_dict(movie):
    """Serialize a Movie model instance to a plain dict suitable for JSON response."""
    return {
        "id": movie.id,
        "title": movie.title,
        "genre": movie.genre,
        "synopsis": movie.synopsis,
        "rating": movie.rating,
        "trailer_url": movie.trailer_url,
        "duration_minutes": movie.duration_minutes,
        # Optional field – include if present
        "created_at": movie.created_at.isoformat() if hasattr(movie, "created_at") and movie.created_at else None,
    }


@movie_bp.route("/api/movies", methods=["GET"])
def list_movies():
    """Return a list of movies, optionally filtered by query parameters.

    Supported query parameters:
        - title: partial match on movie title (case‑insensitive)
        - genre: partial match on genre (case‑insensitive)
        - min_rating: float, inclusive lower bound on rating
        - max_rating: float, inclusive upper bound on rating
    """
    query = Movie.query

    title = request.args.get("title")
    if title:
        query = query.filter(Movie.title.ilike(f"%{title}%"))

    genre = request.args.get("genre")
    if genre:
        query = query.filter(Movie.genre.ilike(f"%{genre}%"))

    min_rating = request.args.get("min_rating", type=float)
    if min_rating is not None:
        query = query.filter(Movie.rating >= min_rating)

    max_rating = request.args.get("max_rating", type=float)
    if max_rating is not None:
        query = query.filter(Movie.rating <= max_rating)

    movies = query.all()
    return jsonify([_movie_to_dict(m) for m in movies]), 200


@movie_bp.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_movie(movie_id):
    """Return detailed information for a single movie identified by *movie_id*."""
    movie = Movie.query.get_or_404(movie_id)
    return jsonify(_movie_to_dict(movie)), 200
