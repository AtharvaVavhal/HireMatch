"""
app/config.py
-------------
Flask application configuration.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False

    # File uploads
    UPLOAD_FOLDER = str(BASE_DIR / "data" / "resumes")
    OUTPUT_FOLDER = str(BASE_DIR / "data" / "outputs")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {"pdf"}


class DevelopmentConfig(Config):
    DEBUG = True


config = DevelopmentConfig()