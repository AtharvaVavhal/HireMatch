# ──────────────────────────────────────────────────────────────
# gunicorn.conf.py  —  Production WSGI server configuration
# ──────────────────────────────────────────────────────────────
# Usage:
#   gunicorn -c gunicorn.conf.py "run:app"
#
# Environment variables can override any setting:
#   WEB_CONCURRENCY=4 gunicorn -c gunicorn.conf.py "run:app"
# ──────────────────────────────────────────────────────────────

import multiprocessing
import os

# ── Binding ───────────────────────────────────────────────────
host = os.environ.get("HOST", "0.0.0.0")
port = os.environ.get("PORT", "8000")
bind = f"{host}:{port}"

# ── Workers ───────────────────────────────────────────────────
# Rule of thumb: (2 × CPU cores) + 1
# Override with WEB_CONCURRENCY env var (Render / Railway set this)
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"        # sync is fine for CPU-bound PDF tasks
threads = 1
worker_connections = 1000

# ── Timeouts ─────────────────────────────────────────────────
# PDF parsing + TF-IDF can be slow on large batches
timeout = 120                # worker killed after 120s of silence
graceful_timeout = 30
keepalive = 5

# ── Logging ──────────────────────────────────────────────────
accesslog = "-"              # stdout (captured by hosting platform)
errorlog  = "-"              # stderr
loglevel  = os.environ.get("LOG_LEVEL", "warning").lower()
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sμs'

# ── Process naming ────────────────────────────────────────────
proc_name = "hirematch"

# ── Security ─────────────────────────────────────────────────
limit_request_line   = 8190
limit_request_fields = 100
forwarded_allow_ips  = "*"   # Render / Railway sit behind a proxy
