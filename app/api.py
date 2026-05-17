"""
app/api.py
----------
REST API Blueprint — JSON endpoints for programmatic access.

Endpoints:
    POST /api/analyze   → analyse single resume text against a JD
    POST /api/rank      → rank multiple resume texts against a JD
    GET  /api/health    → service health check

All endpoints accept and return JSON.
PDF parsing is the caller's responsibility — send extracted text directly.
For PDF-upload API, use the multipart form routes in routes.py.

Example (curl):
    curl -X POST http://localhost:5000/api/analyze \\
      -H "Content-Type: application/json" \\
      -d '{"resume_text": "python fastapi docker", "jd_text": "python backend"}'
"""

from __future__ import annotations

import logging
import time

from flask import Blueprint, jsonify, request

from core.preprocessor import preprocess
from core.scorer import ScoreResult, compute_score, get_missing_skills
from core.skill_extractor import extract_skills
from core.visualizer import rank_resumes_from_texts

logger = logging.getLogger(__name__)
api = Blueprint("api", __name__, url_prefix="/api")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def _validate_text(value, field_name: str):
    """Return (text, error_response) — error_response is None on success."""
    if not value or not isinstance(value, str):
        return None, _error(f"'{field_name}' must be a non-empty string.")
    if not value.strip():
        return None, _error(f"'{field_name}' must not be blank.")
    return value.strip(), None


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/health
# ─────────────────────────────────────────────────────────────────────────────

@api.route("/health", methods=["GET"])
def health():
    """
    Health check — confirms the service is running.

    Response 200:
        { "status": "ok", "version": "1.0.0" }
    """
    from app import __version__
    return jsonify({"status": "ok", "version": __version__}), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/analyze
# ─────────────────────────────────────────────────────────────────────────────

@api.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyse a single resume against a job description.

    Request body (JSON):
        {
            "resume_text": "<raw or pre-extracted resume text>",
            "jd_text":     "<job description text>"
        }

    Response 200:
        {
            "score":          87.34,
            "label":          "Excellent Match",
            "cosine_raw":     0.8734,
            "matched_skills": ["python", "fastapi", "docker"],
            "missing_skills": ["kubernetes", "aws"],
            "resume_word_count": 312,
            "jd_word_count":     98,
            "processing_ms":     42
        }

    Response 400:
        { "error": "<reason>" }
    """
    t0 = time.perf_counter()
    body = request.get_json(force=True, silent=True) or {}

    resume_text, err = _validate_text(body.get("resume_text"), "resume_text")
    if err:
        return err

    jd_text, err = _validate_text(body.get("jd_text"), "jd_text")
    if err:
        return err

    # Pipeline
    clean_resume = preprocess(resume_text)
    clean_jd     = preprocess(jd_text)
    score_result: ScoreResult = compute_score(clean_resume, clean_jd)

    resume_skills = set(extract_skills(resume_text)["all_skills"])
    jd_skills     = set(extract_skills(jd_text)["all_skills"])
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(get_missing_skills(resume_skills, jd_skills))

    elapsed_ms = round((time.perf_counter() - t0) * 1000)
    logger.info(
        "API /analyze — score=%.1f label=%s matched=%d missing=%d (%dms)",
        score_result.score, score_result.label,
        len(matched), len(missing), elapsed_ms,
    )

    return jsonify({
        "score":             score_result.score,
        "label":             score_result.label,
        "cosine_raw":        score_result.cosine_raw,
        "matched_skills":    matched,
        "missing_skills":    missing,
        "resume_word_count": score_result.resume_word_count,
        "jd_word_count":     score_result.jd_word_count,
        "processing_ms":     elapsed_ms,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/rank
# ─────────────────────────────────────────────────────────────────────────────

@api.route("/rank", methods=["POST"])
def rank():
    """
    Rank multiple resumes against one job description.

    Request body (JSON):
        {
            "resumes": [
                {"name": "Alice", "text": "<resume text>"},
                {"name": "Bob",   "text": "<resume text>"}
            ],
            "jd_text": "<job description text>"
        }

    Response 200:
        {
            "ranked": [
                {
                    "rank": 1,
                    "candidate": "Alice",
                    "score": 91.2,
                    "label": "Excellent Match",
                    "matched_skills": ["python", "docker"],
                    "missing_skills": ["kubernetes"]
                },
                ...
            ],
            "total": 2,
            "processing_ms": 87
        }

    Response 400:
        { "error": "<reason>" }
    """
    t0 = time.perf_counter()
    body = request.get_json(force=True, silent=True) or {}

    jd_text, err = _validate_text(body.get("jd_text"), "jd_text")
    if err:
        return err

    resumes_raw = body.get("resumes")
    if not resumes_raw or not isinstance(resumes_raw, list):
        return _error("'resumes' must be a non-empty list of {name, text} objects.")

    if len(resumes_raw) > 50:
        return _error("Maximum 50 resumes per /api/rank request.")

    # Validate and collect (name, text) pairs
    resumes: list[tuple[str, str]] = []
    for i, item in enumerate(resumes_raw):
        if not isinstance(item, dict):
            return _error(f"resumes[{i}] must be an object with 'name' and 'text' keys.")
        name = item.get("name", f"candidate_{i + 1}")
        text = item.get("text", "")
        if not isinstance(text, str):
            return _error(f"resumes[{i}].text must be a string.")
        resumes.append((str(name), text))

    ranked = rank_resumes_from_texts(resumes, jd_text)
    elapsed_ms = round((time.perf_counter() - t0) * 1000)

    logger.info(
        "API /rank — %d candidates ranked in %dms", len(ranked), elapsed_ms
    )

    return jsonify({
        "ranked":        ranked,
        "total":         len(ranked),
        "processing_ms": elapsed_ms,
    }), 200
