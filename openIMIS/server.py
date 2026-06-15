import os
import socket
import sys


def get_proxy_ip():
    try:
        return socket.gethostbyname('frontend')
    except socket.gaierror:
        return ""


# Server configuration from environment
BIND = os.environ.get("SERVER_BIND", "0.0.0.0:8000")
WORKERS = int(os.environ.get("SERVER_WORKERS", "8"))
THREADS = int(os.environ.get("SERVER_THREADS", "4"))
SERVER_ENGINE = os.environ.get("SERVER_ENGINE", "gunicorn")
# Recycle each gunicorn worker after ~N requests so the RSS that CPython never
# returns to the OS gets reclaimed. Measured: a fresh worker is ~260 MB; after
# ~3.5 days without recycling they drift to ~1.9 GB. Jitter staggers the
# restarts so all workers don't recycle at once.
MAX_REQUESTS = int(os.environ.get("SERVER_MAX_REQUESTS", "1000"))
MAX_REQUESTS_JITTER = int(os.environ.get("SERVER_MAX_REQUESTS_JITTER", "100"))
# Load the WSGI app before forking so workers share its baseline via
# copy-on-write (preload is OFF today -> each worker holds its own ~260 MB).
# Off by default; opt in per deployment via SERVER_PRELOAD_APP=true once it's
# confirmed nothing fork-unsafe is opened at import time.
PRELOAD_APP = os.environ.get("SERVER_PRELOAD_APP", "false").lower() in ("1", "true", "yes")

trusted_proxy = get_proxy_ip()
trusted_proxy_headers = (
    "x-forwarded-host",
    "x-forwarded-for",
    "x-forwarded-proto",
    "x-forwarded-port",
    "x-forwarded-by"
)


def run_gunicorn():
    """Multi-process server — better for CPU-bound Django + sync DB queries."""
    import gunicorn.app.base

    class OpenIMISApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    from openIMIS.wsgi import application

    options = {
        "bind": BIND,
        "workers": WORKERS,
        "threads": THREADS,
        "timeout": 300,
        "graceful_timeout": 30,
        "forwarded_allow_ips": trusted_proxy or "*",
        "max_requests": MAX_REQUESTS,
        "max_requests_jitter": MAX_REQUESTS_JITTER,
        "preload_app": PRELOAD_APP,
    }
    OpenIMISApplication(application, options).run()


def run_waitress():
    """Thread-based server — simpler, Windows-compatible."""
    from waitress import serve
    from openIMIS.wsgi import application

    serve_kwargs = {
        "listen": BIND,
        "threads": THREADS,
    }
    if trusted_proxy:
        serve_kwargs["trusted_proxy"] = trusted_proxy
        serve_kwargs["trusted_proxy_headers"] = trusted_proxy_headers

    serve(application, **serve_kwargs)


if __name__ == '__main__':
    if SERVER_ENGINE == "gunicorn":
        run_gunicorn()
    else:
        run_waitress()
