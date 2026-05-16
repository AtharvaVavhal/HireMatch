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

import os
from pathlib import Path

from flask import (
    Blueprint, current_app, jsonify,
    redirect, render_template, request,
    send_file, url_for, flash
)
from werkzeug.utils import secure_filename

from core.parser import parse_pdf
from core.preprocessor import preprocess
from core.scorer import compute_score, get_missing_skills
from core.skill_extractor import extract_skills
from core.visualizer import (
    build_dataframe, export_csv, rank_resumes_from_texts
)

main = Blueprint("main", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


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
    return render_template("index.html")


@main.route("/analyze", methods=["POST"])
def analyze():
    """
    Single resume analysis.

    Form fields:
        resume  : PDF file upload
        jd_text : Job description textarea
    """
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
        flash("Only PDF files are allowed.", "error")
        return redirect(url_for("main.index"))

    if not jd_text:
        flash("Job description cannot be empty.", "error")
        return redirect(url_for("main.index"))

    # Save and parse
    path = save_upload(file)
    parse_result = parse_pdf(path)

    if not parse_result.success:
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

    if not files or all(f.filename == "" for f in files):
        flash("No resume files uploaded.", "error")
        return redirect(url_for("main.index"))

    if not jd_text:
        flash("Job description cannot be empty.", "error")
        return redirect(url_for("main.index"))

    # Parse all PDFs
    resumes = []
    for file in files:
        if file and allowed_file(file.filename):
            path = save_upload(file)
            pr = parse_pdf(path)
            name = Path(path).stem
            resumes.append((name, pr.text if pr.success else ""))

    if not resumes:
        flash("No valid PDF files found.", "error")
        return redirect(url_for("main.index"))

    # Rank
    ranked = rank_resumes_from_texts(resumes, jd_text)
    df = build_dataframe(ranked)
    csv_path = export_csv(df, current_app.config["OUTPUT_FOLDER"])

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