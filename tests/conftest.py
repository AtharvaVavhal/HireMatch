"""
tests/conftest.py
-----------------
Shared pytest fixtures for the HireMatch test suite.

Fixtures defined here are automatically available to every test file
in the tests/ directory — no imports required.

Fixture inventory:
  minimal_pdf_bytes   → bytes of a valid 1-page PDF (text "Hello World")
  corrupted_pdf_bytes → bytes of a garbage file with .pdf extension
  empty_pdf_bytes     → zero-byte content
  make_pdf            → factory: creates a PDF on disk with custom content
  upload_pdf          → factory: returns (BytesIO, filename) for route tests
  flask_app           → configured Flask test application instance
  client              → Flask test client (uses flask_app)
  sample_jd           → a short, reusable job description string
  sample_resume_text  → a realistic, multi-skill resume body text
  tech_jd_text        → a full-stack engineering job description
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask

from app.routes import main


# ---------------------------------------------------------------------------
# Raw PDF byte fixtures
# ---------------------------------------------------------------------------

# Minimal valid single-page PDF that pdfplumber can open.
# Hand-crafted: smallest legal PDF with one page containing "Hello World".
MINIMAL_PDF_BYTES = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
  /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000360 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
441
%%EOF"""

CORRUPTED_PDF_BYTES = b"This is not a valid PDF at all %%EOF"
EMPTY_PDF_BYTES = b""


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """Valid minimal PDF bytes (1 page, text: 'Hello World')."""
    return MINIMAL_PDF_BYTES


@pytest.fixture
def corrupted_pdf_bytes() -> bytes:
    """Garbage bytes with no valid PDF structure."""
    return CORRUPTED_PDF_BYTES


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """Zero-byte content — simulates a completely empty upload."""
    return EMPTY_PDF_BYTES


# ---------------------------------------------------------------------------
# File-on-disk factories
# ---------------------------------------------------------------------------

@pytest.fixture
def make_pdf(tmp_path: Path, minimal_pdf_bytes: bytes):
    """
    Factory fixture: creates a PDF file on disk and returns its Path.

    Usage:
        def test_something(make_pdf):
            pdf = make_pdf("resume.pdf")                    # valid PDF
            bad = make_pdf("broken.pdf", b"garbage bytes")  # corrupted
    """
    def _make_pdf(filename: str = "resume.pdf", content: bytes | None = None) -> Path:
        path = tmp_path / filename
        path.write_bytes(content if content is not None else minimal_pdf_bytes)
        return path

    return _make_pdf


@pytest.fixture
def upload_pdf(minimal_pdf_bytes: bytes):
    """
    Factory fixture: returns a (BytesIO, filename) tuple for Flask route tests.

    Usage:
        def test_route(client, upload_pdf):
            stream, name = upload_pdf("resume.pdf")
            client.post("/analyze", data={"resume": (stream, name), ...})
    """
    def _upload_pdf(filename: str = "resume.pdf", content: bytes | None = None):
        data = content if content is not None else minimal_pdf_bytes
        return BytesIO(data), filename

    return _upload_pdf


# ---------------------------------------------------------------------------
# Flask application + test client
# ---------------------------------------------------------------------------

@pytest.fixture
def flask_app(tmp_path: Path) -> Flask:
    """
    A fully configured Flask application instance for testing.

    - UPLOAD_FOLDER and OUTPUT_FOLDER point to isolated tmp_path directories
    - TESTING=True disables error propagation
    - All blueprints registered
    """
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parents[1] / "templates"),
        static_folder=str(Path(__file__).resolve().parents[1] / "static"),
    )
    app.secret_key = "hirematch-test-secret-key"
    app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        OUTPUT_FOLDER=str(tmp_path / "outputs"),
        ALLOWED_EXTENSIONS={"pdf"},
        WTF_CSRF_ENABLED=False,
    )
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["OUTPUT_FOLDER"]).mkdir(parents=True, exist_ok=True)
    app.register_blueprint(main)
    return app


@pytest.fixture
def client(flask_app: Flask):
    """Flask test client backed by the isolated flask_app fixture."""
    return flask_app.test_client()


# ---------------------------------------------------------------------------
# Text data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_jd() -> str:
    """A short job description used across multiple test modules."""
    return "python fastapi postgresql docker git"


@pytest.fixture
def tech_jd_text() -> str:
    """A realistic full-stack engineering job description."""
    return """
    We are looking for a Senior Backend Engineer to join our platform team.

    Requirements:
    - 4+ years of Python development experience
    - Strong proficiency with FastAPI or Flask for REST API development
    - Experience with PostgreSQL, Redis, and MongoDB
    - Familiarity with Docker, Kubernetes, and GitHub Actions (CI/CD)
    - Knowledge of JWT authentication, OAuth2, and secure API design
    - Experience with cloud platforms (AWS, GCP, or Azure)
    - Bonus: scikit-learn or TensorFlow experience for ML integration

    Nice to have:
    - React or Next.js for frontend collaboration
    - Familiarity with Celery for distributed task queues
    """


@pytest.fixture
def sample_resume_text() -> str:
    """A realistic software engineer resume body (plain text, no PDF)."""
    return """
    John Doe | Software Engineer | john.doe@example.com
    GitHub: github.com/johndoe | Pune, India

    SKILLS
    ------
    Languages  : Python, JavaScript, TypeScript, SQL
    Backend    : FastAPI, Flask, Node.js, REST API, GraphQL
    Databases  : PostgreSQL, MongoDB, Redis
    DevOps     : Docker, GitHub Actions, Nginx, Vercel
    ML / AI    : scikit-learn, Pandas, NumPy, XGBoost
    Tools      : Git, Postman, Figma, VS Code

    EXPERIENCE
    ----------
    Backend Engineer — TechCorp (2022–2024)
    - Built REST APIs with FastAPI and PostgreSQL serving 10K+ daily users
    - Containerised services with Docker; deployed via GitHub Actions CI/CD
    - Implemented JWT authentication and OAuth2 flows

    Junior Developer — StartupXYZ (2021–2022)
    - Developed Flask microservices integrated with Redis for caching
    - Wrote ETL pipelines with Pandas and NumPy

    EDUCATION
    ---------
    B.E. Computer Engineering — University of Pune, 2021

    PROJECTS
    --------
    ResumeMatch  — FastAPI + scikit-learn resume-JD scorer
    StockAlert   — Real-time WebSocket dashboard with Redis pub/sub
    """
