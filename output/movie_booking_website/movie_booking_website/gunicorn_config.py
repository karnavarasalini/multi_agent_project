import os

# Number of worker processes. Adjust based on CPU cores.
workers = int(os.getenv("GUNICORN_WORKERS", "3"))

# Number of threads per worker. Useful for handling concurrent requests.
threads = int(os.getenv("GUNICORN_THREADS", "2"))

# Bind address and port.
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Timeout for worker processes.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))

# Logging configuration.
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # '-' means stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")

# Preload the application for faster worker spawn and memory savings.
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() == "true"

def when_ready(server):
    """Hook executed when the server is ready.
    Useful for logging or initializing resources.
    """
    server.log.info("Gunicorn server is ready. Workers have been spawned.")

def worker_int(worker):
    """Hook executed when a worker receives a SIGINT (Ctrl+C).
    Allows graceful shutdown handling.
    """
    worker.log.info("Worker received INT signal, shutting down gracefully.")
