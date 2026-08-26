"""logging_config.py

Provides structured JSON logging configuration and a basic health‑check endpoint for the Flask
application. The module is deliberately lightweight and uses only the Python standard library.

Usage in ``app.py``::

    from movie_booking_website.logging_config import init_app
    app = Flask(__name__)
    init_app(app)

The ``init_app`` helper configures the root logger to emit JSON lines to ``stdout`` and registers a
``/healthz`` endpoint that returns a minimal JSON payload suitable for container orchestration
probes (Kubernetes, Docker, etc.).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Mapping

from flask import Flask, jsonify

class JSONFormatter(logging.Formatter):
    """Format log records as a single‑line JSON string.

    The output includes a timestamp (ISO‑8601 UTC), the log level, logger name, the log
    message and any extra mapping passed via the ``extra`` argument of ``logger.xxx``.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base payload
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include any user‑supplied attributes that are not part of LogRecord's standard set
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord.__dict__ and not key.startswith("_")
        }
        if extra:
            payload["extra"] = extra
        return json.dumps(payload, ensure_ascii=False)


def configure_structured_logging() -> None:
    """Configure the root logger to emit JSON formatted logs to ``stdout``.

    The function is idempotent – calling it multiple times will not add duplicate handlers.
    """
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) and isinstance(getattr(h, "formatter", None), JSONFormatter) for h in root.handlers):
        # Already configured
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Silence overly verbose third‑party loggers (e.g., SQLAlchemy) unless explicitly overridden
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def register_health_check(app: Flask) -> None:
    """Add a simple health‑check endpoint to the Flask app.

    The endpoint follows the conventional ``/healthz`` path used by many orchestration platforms.
    It returns a JSON payload with ``status`` set to ``"ok"`` and a ``timestamp``.
    """

    @app.route("/healthz", methods=["GET"])
    def healthz():  # pragma: no cover – trivial endpoint
        return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


def init_app(app: Flask) -> None:
    """Public helper to initialise logging and register health checks.

    This function should be called once during the Flask application bootstrap.
    """
    configure_structured_logging()
    register_health_check(app)

# If the module is executed directly, run a tiny demo server to verify the health endpoint.
if __name__ == "__main__":  # pragma: no cover
    demo_app = Flask(__name__)
    init_app(demo_app)
    demo_app.run(host="0.0.0.0", port=5001)
