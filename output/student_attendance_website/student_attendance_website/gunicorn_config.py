import os, multiprocessing

# Bind address and port for Gunicorn. Override with GUNICORN_BIND env var.
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')

# Number of worker processes. Defaults to (CPU cores * 2) + 1.
workers = int(os.getenv('GUNICORN_WORKERS', str(multiprocessing.cpu_count() * 2 + 1)))

# Log level (debug, info, warning, error, critical).
loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info')

# Access and error log destinations. '-' means stdout/stderr.
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')

# Preload the application for copy‑on‑write memory savings.
preload_app = os.getenv('GUNICORN_PRELOAD', 'true').lower() == 'true'

def when_ready(server):
    """Hook called just after the master process is ready.
    Useful for logging or initializing resources.
    """
    server.log.info('Gunicorn server ready – listening on %s with %s workers', bind, workers)

def on_exit(server):
    """Hook called just before the master process exits."""
    server.log.info('Gunicorn server shutting down')