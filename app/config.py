"""
app/config.py
-------------
Centralised Flask configuration with environment-variable support.

Environment variables (all optional — sane defaults provided):
    SECRET_KEY          Flask session secret (REQUIRED in production)
    FLASK_ENV           'development' or 'production'
    UPLOAD_FOLDER       Absolute path for uploaded PDFs
    OUTPUT_FOLDER       Absolute path for generated CSVs
    MAX_UPLOAD_MB       Maximum upload size in MB (default: 16)
    LOG_LEVEL           Python logging level name (default: INFO)
    LOG_TO_FILE         '1' to enable rotating file logs (default: 0)

Usage:
    from app.config import get_config
    app.config.from_object(get_config())
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root = parent of this file's parent
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _env_bool(key: str, default: bool = False) -> bool:
    """Read an environment variable as a boolean ('1', 'true', 'yes' → True)."""
    return os.environ.get(key, str(int(default))).strip().lower() in ("1", "true", "yes")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Base config (shared by all environments)
# ---------------------------------------------------------------------------

class Config:
    # ── Security ──────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "dev-insecure-key-change-before-production"
    )

    # ── File handling ──────────────────────────────────────────────────────
    UPLOAD_FOLDER: str = os.environ.get(
        "UPLOAD_FOLDER", str(BASE_DIR / "uploads")
    )
    OUTPUT_FOLDER: str = os.environ.get(
        "OUTPUT_FOLDER", str(BASE_DIR / "outputs")
    )
    MAX_CONTENT_LENGTH: int = _env_int("MAX_UPLOAD_MB", 16) * 1024 * 1024
    ALLOWED_EXTENSIONS: set[str] = {"pdf"}

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_TO_FILE: bool = _env_bool("LOG_TO_FILE", False)
    LOG_DIR: str = str(BASE_DIR / "logs")

    # ── Flask ──────────────────────────────────────────────────────────────
    DEBUG: bool = False
    TESTING: bool = False

    # ── Limits ─────────────────────────────────────────────────────────────
    MAX_BATCH_RESUMES: int = _env_int("MAX_BATCH_RESUMES", 20)


# ---------------------------------------------------------------------------
# Environment-specific subclasses
# ---------------------------------------------------------------------------

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
    LOG_TO_FILE = True

    # Enforce a real secret key in production
    @classmethod
    def validate(cls) -> None:
        if cls.SECRET_KEY == "dev-insecure-key-change-before-production":
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    LOG_LEVEL = "WARNING"
    LOG_TO_FILE = False
    # Tests use tmp_path — these are overridden per-fixture
    UPLOAD_FOLDER = "/tmp/hirematch_test_uploads"
    OUTPUT_FOLDER = "/tmp/hirematch_test_outputs"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_CONFIG_MAP: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}


def get_config() -> Config:
    """
    Return the correct Config instance based on FLASK_ENV.
    Defaults to DevelopmentConfig if FLASK_ENV is unset or unrecognised.
    """
    env = os.environ.get("FLASK_ENV", "development").lower()
    cfg_class = _CONFIG_MAP.get(env, DevelopmentConfig)
    return cfg_class()