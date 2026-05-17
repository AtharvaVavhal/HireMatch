# ─────────────────────────────────────────────────────────────────────────────
# chart_routes.py
# Add this Blueprint to your existing Flask app.
#
# In your main app.py:
#   from chart_routes import charts_bp
#   app.register_blueprint(charts_bp)
# ─────────────────────────────────────────────────────────────────────────────

from flask import Blueprint, request, jsonify, send_file, abort
import io
from core.visualizations import (
    score_comparison_chart,
    candidate_ranking_chart,
    skill_radar_chart,
    score_distribution_chart,
    export_chart_png,
)

charts_bp = Blueprint("charts", __name__, url_prefix="/charts")


# ── helper ────────────────────────────────────────────────────────────────────
def _get_candidates():
    """Pull candidates list from JSON body; abort 400 if missing."""
    data = request.get_json(force=True, silent=True) or {}
    candidates = data.get("candidates")
    if not candidates or not isinstance(candidates, list):
        abort(400, "Body must contain a 'candidates' list.")
    return data, candidates


# ── 1. Score comparison chart ─────────────────────────────────────────────────
@charts_bp.route("/comparison", methods=["POST"])
def comparison():
    """
    POST /charts/comparison
    Body: { "candidates": [{"name":"Alice","score":87},...], "job_title":"SWE" }
    Returns: { "image": "<base64 PNG>" }
    """
    data, candidates = _get_candidates()
    job_title = data.get("job_title", "Job")
    img = score_comparison_chart(candidates, job_title)
    return jsonify({"image": img})


# ── 2. Candidate ranking chart ────────────────────────────────────────────────
@charts_bp.route("/ranking", methods=["POST"])
def ranking():
    """
    POST /charts/ranking
    Body: { "candidates": [...], "top_n": 10 }
    Returns: { "image": "<base64 PNG>" }
    """
    data, candidates = _get_candidates()
    top_n = int(data.get("top_n", 10))
    img = candidate_ranking_chart(candidates, top_n)
    return jsonify({"image": img})


# ── 3. Skill radar chart ──────────────────────────────────────────────────────
@charts_bp.route("/radar", methods=["POST"])
def radar():
    """
    POST /charts/radar
    Body: {
        "candidate_name": "Alice",
        "skill_scores": {"Python": 90, "SQL": 75, "ML": 60}
    }
    Returns: { "image": "<base64 PNG>" }
    """
    data = request.get_json(force=True, silent=True) or {}
    name   = data.get("candidate_name", "Candidate")
    skills = data.get("skill_scores")
    if not skills:
        abort(400, "Body must contain 'skill_scores' dict.")
    img = skill_radar_chart(name, skills)
    return jsonify({"image": img})


# ── 4. Score distribution histogram ──────────────────────────────────────────
@charts_bp.route("/distribution", methods=["POST"])
def distribution():
    """
    POST /charts/distribution
    Body: { "candidates": [...] }
    Returns: { "image": "<base64 PNG>" }
    """
    _, candidates = _get_candidates()
    img = score_distribution_chart(candidates)
    return jsonify({"image": img})


# ── 5. Export any chart as a downloadable PNG ─────────────────────────────────
@charts_bp.route("/export/<chart_type>", methods=["POST"])
def export(chart_type: str):
    """
    POST /charts/export/<comparison|ranking|distribution|radar>
    Body: same as the corresponding chart endpoint above.
    Returns: PNG file download.
    """
    data = request.get_json(force=True, silent=True) or {}
    candidates     = data.get("candidates", [])
    job_title      = data.get("job_title", "Job")
    candidate_name = data.get("candidate_name", "Candidate")
    skill_scores   = data.get("skill_scores")

    try:
        png_bytes = export_chart_png(
            chart_type    = chart_type,
            candidates    = candidates,
            job_title     = job_title,
            candidate_name= candidate_name,
            skill_scores  = skill_scores,
        )
    except ValueError as e:
        abort(400, str(e))

    return send_file(
        io.BytesIO(png_bytes),
        mimetype="image/png",
        as_attachment=True,
        download_name=f"{chart_type}_chart.png",
    )
