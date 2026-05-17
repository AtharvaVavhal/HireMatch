"""
app/routes.py
-------------
Flask routes for Resume Parser & Job Match Scorer.

Routes:
    GET  /          → index page (upload form)
    POST /analyze   → single resume analysis
    POST /rank      → multi-resume ranking
    GET  /download  → download CSV
"""

import logging
import os
from pathlib import Path

from flask import (
    Blueprint, current_app,
    redirect, render_template, request,
    send_file, url_for, flash
)
from werkzeug.utils import secure_filename
try:
    import magic
except ImportError:
    magic = None

from core.parser import parse_pdf
from core.preprocessor import preprocess
from core.scorer import compute_score, get_missing_skills
from core.skill_extractor import extract_skills
from core.visualizer import (
    build_dataframe, export_csv, rank_resumes_from_texts
)
from core.cleanup import cleanup_old_files

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def is_pdf(file_path: str) -> bool:
    """Check if the file at file_path is a real PDF using MIME magic."""
    if magic is None:
        logger.warning("magic library or libmagic missing. Falling back to extension check.")
        return file_path.lower().endswith('.pdf')
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        return file_type == 'application/pdf'
    except Exception as e:
        logger.warning(f"MIME check failed: {e}. Falling back to extension check.")
        return file_path.lower().endswith('.pdf')


def save_upload(file) -> str:
    """Save uploaded file and return its path."""
    filename = secure_filename(file.filename)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    path = os.path.join(upload_dir, filename)
    file.save(path)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/")
def index():
    """Home page — upload form."""
    # Trigger cleanup of old files (older than 1 hour)
    cleanup_old_files(current_app.config["UPLOAD_FOLDER"])
    cleanup_old_files(current_app.config["OUTPUT_FOLDER"])
    return render_template("index.html")


@main.route("/analyze", methods=["POST"])
def analyze():
    """
    Single resume analysis.

    Form fields:
        resume  : PDF file upload
        jd_text : Job description textarea
    """
    logger.info("POST /analyze — file=%s", request.files.get("resume", {}).filename if "resume" in request.files else "<none>")

    # Validate inputs
    if "resume" not in request.files:
        flash("No resume file uploaded.", "error")
        return redirect(url_for("main.index"))

    file = request.files["resume"]
    jd_text = request.form.get("jd_text", "").strip()

    if not file.filename:
        flash("No file selected.", "error")
        return redirect(url_for("main.index"))

    if not allowed_file(file.filename):
        logger.warning("Rejected non-PDF upload: %s", file.filename)
        flash("Only PDF files are allowed.", "error")
        return redirect(url_for("main.index"))

    # Save and parse
    path = save_upload(file)

    # Secondary MIME check for security
    if not is_pdf(path):
        logger.warning("MIME mismatch: %s is not a real PDF.", path)
        os.remove(path)
        flash("The uploaded file is not a valid PDF content.", "error")
        return redirect(url_for("main.index"))

    if not jd_text:
        flash("Job description cannot be empty.", "error")
        return redirect(url_for("main.index"))

    parse_result = parse_pdf(path)

    if not parse_result.success:
        logger.error("PDF parse failed for '%s': %s", Path(path).name, parse_result.error)
        flash(f"Could not read PDF: {parse_result.error}", "error")
        return redirect(url_for("main.index"))

    # Pipeline
    raw_resume = parse_result.text
    clean_resume = preprocess(raw_resume)
    clean_jd = preprocess(jd_text)

    score_result = compute_score(clean_resume, clean_jd)

    resume_skills = set(extract_skills(raw_resume)["all_skills"])
    jd_skills = set(extract_skills(jd_text)["all_skills"])
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(get_missing_skills(resume_skills, jd_skills))

    logger.info(
        "Analysis complete — file=%s score=%.1f label=%s matched=%d missing=%d",
        Path(path).name, score_result.score, score_result.label,
        len(matched), len(missing),
    )

    return render_template(
        "results.html",
        mode="single",
        filename=Path(path).name,
        score=score_result.score,
        label=score_result.label,
        matched_skills=matched,
        missing_skills=missing,
        page_count=parse_result.page_count,
    )


@main.route("/rank", methods=["POST"])
def rank():
    """
    Multi-resume ranking.

    Form fields:
        resumes[]  : Multiple PDF file uploads
        jd_text    : Job description textarea
    """
    files = request.files.getlist("resumes[]")
    jd_text = request.form.get("jd_text", "").strip()
    logger.info("POST /rank — %d file(s) received", len(files))

    if not files or all(f.filename == "" for f in files):
        flash("No resume files uploaded.", "error")
        return redirect(url_for("main.index"))

    if not jd_text:
        flash("Job description cannot be empty.", "error")
        return redirect(url_for("main.index"))

    max_batch = current_app.config.get("MAX_BATCH_RESUMES", 20)
    if len(files) > max_batch:
        flash(f"Too many files. Maximum batch size is {max_batch}.", "error")
        return redirect(url_for("main.index"))

    # Parse all PDFs
    resumes = []
    failed = 0
    for file in files:
        if file and allowed_file(file.filename):
            path = save_upload(file)
            # Secondary MIME check
            if not is_pdf(path):
                logger.warning("Batch: MIME mismatch for '%s'", file.filename)
                os.remove(path)
                failed += 1
                continue

            pr = parse_pdf(path)
            name = Path(path).stem
            if not pr.success:
                logger.warning("Batch: failed to parse '%s': %s", name, pr.error)
                failed += 1
            resumes.append((name, pr.text if pr.success else ""))

    if not resumes:
        flash("No valid PDF files found.", "error")
        return redirect(url_for("main.index"))

    if failed:
        flash(f"{failed} file(s) could not be parsed and were scored as 0.", "warning")

    # Rank
    ranked = rank_resumes_from_texts(resumes, jd_text)
    df = build_dataframe(ranked)
    csv_path = export_csv(df, current_app.config["OUTPUT_FOLDER"])

    logger.info("Ranking complete — %d candidates, CSV=%s", len(ranked), csv_path)

    return render_template(
        "results.html",
        mode="rank",
        ranked=ranked,
        csv_filename=Path(csv_path).name if csv_path else None,
    )


@main.route("/download/<filename>")
def download(filename):
    """Download a generated CSV file."""
    output_dir = current_app.config["OUTPUT_FOLDER"]
    file_path = os.path.join(output_dir, secure_filename(filename))

    if not os.path.exists(file_path):
        flash("File not found.", "error")
        return redirect(url_for("main.index"))

    return send_file(file_path, as_attachment=True)