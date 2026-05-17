"""
run.py
------
HireMatch application entry point.

Responsibilities:
  - Create and configure the Flask app
  - Initialise logging
  - Register blueprints
  - Ensure required directories exist
  - Start the dev server (or expose `app` for a WSGI server)

Production (gunicorn):
    gunicorn "run:app" --workers 2 --bind 0.0.0.0:8000

Development:
    python run.py          (or: make run)
    flask run --debug
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from app.config import get_config
from app.routes import main
from app.api import api
from app.chart_routes import charts_bp
from core.logging_config import setup_logging

import logging


def create_app() -> Flask:
    """Application factory — returns a fully configured Flask instance."""
    cfg = get_config()

    # ── Logging (must be first so all modules see correct handlers) ────────
    setup_logging(
        level=cfg.LOG_LEVEL,
        log_to_file=cfg.LOG_TO_FILE,
        log_dir=cfg.LOG_DIR,
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting HireMatch [env=%s]", os.environ.get("FLASK_ENV", "development"))

    # ── Flask app ──────────────────────────────────────────────────────────
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(cfg)

    # ── Ensure upload / output directories exist ───────────────────────────
    for folder_key in ("UPLOAD_FOLDER", "OUTPUT_FOLDER"):
        folder = app.config.get(folder_key, "")
        if folder:
            Path(folder).mkdir(parents=True, exist_ok=True)
            logger.debug("Directory ready: %s", folder)

    # ── Blueprints ──────────────────────────────────────────────────────────
    app.register_blueprint(main)        # HTML routes: /, /analyze, /rank, /download
    app.register_blueprint(api)         # JSON REST API: /api/analyze, /api/rank, /api/health
    app.register_blueprint(charts_bp)   # Chart routes: /charts/*

    # ── Visualize route (kept in run.py; can be moved to a blueprint) ──────
    _register_visualize_route(app)

    logger.info("HireMatch app created — blueprints registered.")
    return app


def _register_visualize_route(app: Flask) -> None:
    """Register the /visualize route directly on the app (not a blueprint)."""
    from flask import flash, redirect, render_template, request, url_for
    from pathlib import Path
    from werkzeug.utils import secure_filename

    from core.parser import parse_pdf
    from core.visualizer import rank_resumes_from_texts

    @app.route("/visualize", methods=["GET", "POST"])
    def visualize():
        logger = logging.getLogger("hirematch.visualize")

        if request.method == "POST":
            files = request.files.getlist("resumes[]")
            jd_text = request.form.get("jd_text", "").strip()

            if not files or not jd_text:
                flash("Please upload resumes and enter a job description.", "error")
                return redirect(url_for("visualize"))

            resumes = []
            for file in files:
                if file and file.filename.endswith(".pdf"):
                    filename = secure_filename(file.filename)
                    path = Path(app.config["UPLOAD_FOLDER"]) / filename
                    file.save(path)
                    pr = parse_pdf(str(path))
                    name = path.stem
                    resumes.append((name, pr.text if pr.success else ""))
                    if not pr.success:
                        logger.warning("Visualize: failed to parse '%s'", filename)

            if not resumes:
                flash("No valid PDFs found.", "error")
                return redirect(url_for("visualize"))

            ranked = rank_resumes_from_texts(resumes, jd_text)
            candidates = [
                {"name": r["candidate"], "score": round(r["score"], 1)}
                for r in ranked
            ]
            logger.info("Visualize: ranked %d resumes.", len(candidates))
            return render_template("charts.html", job_title="Job Match", candidates=candidates)

        return render_template("visualize_upload.html")


# ── Entry point ────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV", "development") == "development"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, port=port, host="0.0.0.0")
