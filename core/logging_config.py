"""
core/logging_config.py
-----------------------
Centralised logging setup for HireMatch.

Call setup_logging() exactly once at application startup (in run.py or
the app factory). All modules use the standard pattern:

    import logging
    logger = logging.getLogger(__name__)

and get the correct handlers / level automatically.

Features:
  - Console handler (always on)
  - Rotating file handler (optional, enabled by LOG_TO_FILE=1)
  - Log level controlled by LOG_LEVEL env var or config
  - Structured format: timestamp | level | logger | message
  - Flask/werkzeug noise suppressed in production
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_CONSOLE_FMT = logging.Formatter(_FMT, datefmt=_DATE_FMT)
_FILE_FMT    = logging.Formatter(_FMT, datefmt=_DATE_FMT)


# ---------------------------------------------------------------------------
# Public setup function
# ---------------------------------------------------------------------------

def setup_logging(
    level: str = "INFO",
    log_to_file: bool = False,
    log_dir: str = "logs",
) -> None:
    """
    Configure the root logger and HireMatch-specific loggers.

    Args:
        level      : Logging level string ('DEBUG', 'INFO', 'WARNING', …).
        log_to_file: If True, add a rotating file handler.
        log_dir    : Directory for log files (created if absent).

    Call once at startup:
        from core.logging_config import setup_logging
        setup_logging(level="INFO", log_to_file=True)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── Root logger ────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Avoid adding duplicate handlers on repeated calls (e.g. during tests)
    if root.handlers:
        return

    # ── Console handler ────────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(_CONSOLE_FMT)
    root.addHandler(console)

    # ── Rotating file handler (optional) ───────────────────────────────────
    if log_to_file:
        log_path = Path(log_dir).resolve()
        log_path.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "hirematch.log",
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=3,              # keep 3 rotated backups
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(_FILE_FMT)
        root.addHandler(file_handler)

        # Separate error log — WARNING and above only
        error_handler = logging.handlers.RotatingFileHandler(
            filename=log_path / "errors.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(_FILE_FMT)
        root.addHandler(error_handler)

    # ── Silence chatty third-party loggers in production ──────────────────
    if level.upper() not in ("DEBUG",):
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("pdfminer").setLevel(logging.ERROR)

    logging.getLogger(__name__).info(
        "Logging initialised — level=%s, file=%s", level.upper(), log_to_file
    )
