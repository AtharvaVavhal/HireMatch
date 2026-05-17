"""
tests/test_api.py
------------------
Unit tests for the new REST API endpoints (/api/*).

Tests:
    GET  /api/health
    POST /api/analyze
    POST /api/rank
"""

import pytest
from flask import Flask

from app.api import api
from core.preprocessor import preprocess


@pytest.fixture
def api_client(tmp_path):
    """Specific test client for the API blueprint."""
    app = Flask(__name__)
    app.config.update(TESTING=True)
    app.register_blueprint(api)
    return app.test_client()


# ─────────────────────────────────────────────────────────────────────────────
# /api/health
# ─────────────────────────────────────────────────────────────────────────────

def test_api_health(api_client):
    """GET /api/health should return 200 and OK status."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "version" in data


# ─────────────────────────────────────────────────────────────────────────────
# /api/analyze
# ─────────────────────────────────────────────────────────────────────────────

def test_api_analyze_success(api_client):
    """POST /api/analyze with valid JSON should return score and skills."""
    payload = {
        "resume_text": "python developer with fastapi and docker skills",
        "jd_text": "we need a python backend dev with fastapi"
    }
    response = api_client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "score" in data
    assert "label" in data
    assert "matched_skills" in data
    assert "python" in data["matched_skills"]
    assert "fastapi" in data["matched_skills"]
    assert "processing_ms" in data


def test_api_analyze_missing_fields(api_client):
    """POST /api/analyze with missing fields should return 400."""
    # Missing jd_text
    response = api_client.post("/api/analyze", json={"resume_text": "..."})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_analyze_empty_text(api_client):
    """POST /api/analyze with blank text should return 400."""
    payload = {"resume_text": "  ", "jd_text": "valid jd"}
    response = api_client.post("/api/analyze", json=payload)
    assert response.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# /api/rank
# ─────────────────────────────────────────────────────────────────────────────

def test_api_rank_success(api_client):
    """POST /api/rank with multiple resumes should return a sorted list."""
    payload = {
        "jd_text": "python developer",
        "resumes": [
            {"name": "Alice", "text": "I am a python developer"},
            {"name": "Bob", "text": "I write java code"}
        ]
    }
    response = api_client.post("/api/rank", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert "ranked" in data
    assert len(data["ranked"]) == 2
    assert data["ranked"][0]["candidate"] == "Alice"  # Alice should score higher
    assert data["ranked"][0]["score"] > data["ranked"][1]["score"]
    assert "total" in data


def test_api_rank_invalid_structure(api_client):
    """POST /api/rank with non-list resumes should return 400."""
    payload = {"jd_text": "...", "resumes": "not a list"}
    response = api_client.post("/api/rank", json=payload)
    assert response.status_code == 400


def test_api_rank_batch_limit(api_client):
    """POST /api/rank with >50 resumes should return 400."""
    resumes = [{"name": str(i), "text": "..."} for i in range(51)]
    payload = {"jd_text": "...", "resumes": resumes}
    response = api_client.post("/api/rank", json=payload)
    assert response.status_code == 400
    assert "Maximum 50 resumes" in response.get_json()["error"]
