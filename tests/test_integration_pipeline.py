"""
tests/test_integration_pipeline.py
-----------------------------------
Full end-to-end integration tests for the HireMatch pipeline.

Pipeline under test:
    PDF file → parse_pdf() → preprocess() → extract_skills() → compute_score()
                                                              → rank_resumes()

Test strategy:
  - Use in-memory PDF bytes (no real files required)
  - Test the happy path with a real-looking resume
  - Test each failure mode (corrupted PDF, empty PDF, wrong extension)
  - Test graceful degradation: failures must not crash the pipeline
  - Verify data contracts between stages (types, ranges, structure)

Run:
    pytest tests/test_integration_pipeline.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.parser import parse_pdf
from core.preprocessor import preprocess
from core.scorer import ScoreResult, compute_score, rank_resumes
from core.skill_extractor import extract_skills

# ---------------------------------------------------------------------------
# Shared PDF bytes
# ---------------------------------------------------------------------------

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

CORRUPTED_PDF_BYTES = b"This is definitely not a valid PDF %%EOF garbage"
EMPTY_FILE_BYTES = b""
NON_PDF_BYTES = b"This is a plain text file, not a PDF."


# ===========================================================================
# Happy Path — parse → preprocess → score
# ===========================================================================

class TestHappyPathPipeline:
    """Full pipeline works end-to-end on valid PDF input."""

    def test_parse_succeeds(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        result = parse_pdf(str(pdf))
        assert result.success is True

    def test_preprocess_returns_string(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean = preprocess(parsed.text)
        assert isinstance(clean, str)

    def test_score_returns_score_result(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean_resume = preprocess(parsed.text)
        clean_jd = preprocess("hello world")
        score = compute_score(clean_resume, clean_jd)
        assert isinstance(score, ScoreResult)

    def test_score_in_valid_range(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean_resume = preprocess(parsed.text)
        clean_jd = preprocess("hello world")
        score = compute_score(clean_resume, clean_jd)
        assert 0.0 <= score.score <= 100.0

    def test_same_content_jd_gives_high_score(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        # JD text identical to resume content → should score ≥ 90
        clean = preprocess(parsed.text)
        score = compute_score(clean, clean)
        assert score.score >= 90.0

    def test_page_count_is_positive(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        assert parsed.page_count >= 1

    def test_extract_skills_does_not_crash_on_parsed_text(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        try:
            result = extract_skills(parsed.text)
            assert isinstance(result["all_skills"], list)
        except Exception as exc:
            pytest.fail(f"extract_skills raised: {exc}")


# ===========================================================================
# Corrupted PDF Handling
# ===========================================================================

class TestCorruptedPDFHandling:
    """Corrupted PDF must fail gracefully without crashing the pipeline."""

    def test_parse_returns_failure(self, make_pdf):
        pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
        result = parse_pdf(str(pdf))
        assert result.success is False

    def test_parse_error_message_is_set(self, make_pdf):
        pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
        result = parse_pdf(str(pdf))
        assert result.error is not None
        assert isinstance(result.error, str)
        assert len(result.error) > 0

    def test_parse_text_is_empty_string(self, make_pdf):
        pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
        result = parse_pdf(str(pdf))
        assert result.text == ""

    def test_parse_page_count_is_zero(self, make_pdf):
        pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
        result = parse_pdf(str(pdf))
        assert result.page_count == 0

    def test_scoring_empty_text_gives_zero(self, make_pdf):
        pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
        parsed = parse_pdf(str(pdf))
        jd = preprocess("python backend developer")
        score = compute_score(parsed.text, jd)
        assert score.score == 0.0
        assert score.label == "Poor Match"

    def test_pipeline_does_not_raise(self, make_pdf):
        """The full pipeline must not raise any exception on corrupted input."""
        try:
            pdf = make_pdf("broken.pdf", CORRUPTED_PDF_BYTES)
            parsed = parse_pdf(str(pdf))
            clean = preprocess(parsed.text)
            jd = preprocess("python backend developer")
            score = compute_score(clean, jd)
            skills = extract_skills(parsed.text)
            assert isinstance(skills, dict)
        except Exception as exc:
            pytest.fail(f"Pipeline raised on corrupted PDF: {exc}")

    def test_one_corrupted_does_not_block_others(self, tmp_path, make_pdf):
        """Parsing multiple resumes — corruption in one must not affect others."""
        good_pdf = tmp_path / "good.pdf"
        good_pdf.write_bytes(MINIMAL_PDF_BYTES)

        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(CORRUPTED_PDF_BYTES)

        good_result = parse_pdf(str(good_pdf))
        bad_result = parse_pdf(str(bad_pdf))

        # Good file unaffected
        assert good_result.success is True
        # Bad file fails gracefully
        assert bad_result.success is False


# ===========================================================================
# Empty Resume Handling
# ===========================================================================

class TestEmptyResumeHandling:
    """Zero-byte and whitespace-only resumes must degrade gracefully."""

    def test_empty_file_parse_returns_failure(self, make_pdf):
        pdf = make_pdf("empty.pdf", EMPTY_FILE_BYTES)
        result = parse_pdf(str(pdf))
        assert result.success is False

    def test_empty_file_text_is_empty_string(self, make_pdf):
        pdf = make_pdf("empty.pdf", EMPTY_FILE_BYTES)
        result = parse_pdf(str(pdf))
        assert result.text == ""

    def test_empty_resume_score_is_zero(self, make_pdf):
        pdf = make_pdf("empty.pdf", EMPTY_FILE_BYTES)
        parsed = parse_pdf(str(pdf))
        jd = preprocess("python backend developer")
        score = compute_score(parsed.text, jd)
        assert score.score == 0.0

    def test_empty_resume_label_is_poor_match(self, make_pdf):
        pdf = make_pdf("empty.pdf", EMPTY_FILE_BYTES)
        parsed = parse_pdf(str(pdf))
        jd = preprocess("python backend developer")
        score = compute_score(parsed.text, jd)
        assert score.label == "Poor Match"

    def test_preprocess_on_empty_returns_empty_string(self):
        assert preprocess("") == ""

    def test_extract_skills_on_empty_returns_no_skills(self):
        result = extract_skills("")
        assert result["all_skills"] == []

    def test_full_pipeline_on_empty_file_does_not_raise(self, make_pdf):
        try:
            pdf = make_pdf("empty.pdf", EMPTY_FILE_BYTES)
            parsed = parse_pdf(str(pdf))
            clean = preprocess(parsed.text)
            jd = preprocess("python developer backend")
            score = compute_score(clean, jd)
            skills = extract_skills(parsed.text)
            assert score.score == 0.0
        except Exception as exc:
            pytest.fail(f"Pipeline raised on empty PDF: {exc}")


# ===========================================================================
# Wrong Extension Handling
# ===========================================================================

class TestWrongExtensionHandling:
    """Non-PDF files must be rejected early by the parser."""

    def test_txt_file_parse_returns_failure(self, tmp_path):
        txt = tmp_path / "resume.txt"
        txt.write_bytes(NON_PDF_BYTES)
        result = parse_pdf(str(txt))
        assert result.success is False

    def test_txt_file_error_message_present(self, tmp_path):
        txt = tmp_path / "resume.txt"
        txt.write_bytes(NON_PDF_BYTES)
        result = parse_pdf(str(txt))
        assert result.error is not None

    def test_docx_extension_rejected(self, tmp_path):
        docx = tmp_path / "resume.docx"
        docx.write_bytes(b"PK fake docx content")
        result = parse_pdf(str(docx))
        assert result.success is False

    def test_pipeline_graceful_on_wrong_extension(self, tmp_path):
        txt = tmp_path / "resume.txt"
        txt.write_bytes(NON_PDF_BYTES)
        try:
            parsed = parse_pdf(str(txt))
            score = compute_score(parsed.text, "python developer")
            assert score.score == 0.0
        except Exception as exc:
            pytest.fail(f"Pipeline raised on wrong extension: {exc}")


# ===========================================================================
# Missing File Handling
# ===========================================================================

class TestMissingFileHandling:
    """Passing a nonexistent path must return a failure, not raise."""

    def test_missing_file_parse_returns_failure(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.success is False

    def test_missing_file_error_message_mentions_not_found(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.error is not None
        assert "not found" in result.error.lower() or "ghost.pdf" in result.error

    def test_pipeline_graceful_on_missing_file(self, tmp_path):
        try:
            parsed = parse_pdf(str(tmp_path / "nonexistent.pdf"))
            score = compute_score(parsed.text, "python developer")
            assert score.score == 0.0
        except Exception as exc:
            pytest.fail(f"Pipeline raised on missing file: {exc}")


# ===========================================================================
# Multi-Resume Ranking Integration
# ===========================================================================

class TestMultiResumeRankingIntegration:
    """rank_resumes() integrates correctly across the full pipeline."""

    def test_ranked_output_is_sorted(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean = preprocess(parsed.text)
        jd = preprocess("python developer")

        resumes = [
            ("Alice", clean),
            ("Bob",   ""),
            ("Carol", "totally unrelated design arts"),
        ]
        ranked = rank_resumes(resumes, jd)
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_ranked_all_candidates_present(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean = preprocess(parsed.text)
        jd = preprocess("python developer")

        resumes = [("Alice", clean), ("Bob", ""), ("Carol", "design")]
        ranked = rank_resumes(resumes, jd)
        names = {r["candidate"] for r in ranked}
        assert names == {"Alice", "Bob", "Carol"}

    def test_empty_and_corrupted_still_ranked(self, make_pdf, tmp_path):
        good_pdf = make_pdf("good.pdf")
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(CORRUPTED_PDF_BYTES)

        good_parsed = parse_pdf(str(good_pdf))
        bad_parsed = parse_pdf(str(bad_pdf))

        resumes = [
            ("Good", preprocess(good_parsed.text)),
            ("Bad",  preprocess(bad_parsed.text)),
        ]
        jd = preprocess("hello world python developer")
        ranked = rank_resumes(resumes, jd)
        assert len(ranked) == 2


# ===========================================================================
# Score Validation Integration
# ===========================================================================

class TestScoreValidationIntegration:
    """Cross-stage score validation across the whole pipeline."""

    def test_score_always_valid_after_full_pipeline(self, make_pdf):
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        clean = preprocess(parsed.text)
        jd = preprocess("python backend developer docker postgresql")
        score = compute_score(clean, jd)

        assert 0.0 <= score.score <= 100.0
        assert 0.0 <= score.cosine_raw <= 1.0
        assert isinstance(score.label, str)
        assert score.label in {
            "Excellent Match", "Good Match", "Moderate Match", "Poor Match"
        }

    def test_skills_union_subset_of_all_supported(self, make_pdf):
        """Skills returned by extract_skills must all be canonical known skills."""
        from core.skill_extractor import list_all_supported_skills
        pdf = make_pdf("resume.pdf")
        parsed = parse_pdf(str(pdf))
        result = extract_skills(parsed.text)
        all_supported = {
            s
            for skills in list_all_supported_skills().values()
            for s in skills
        }
        for skill in result["all_skills"]:
            assert skill in all_supported, (
                f"Skill '{skill}' not found in supported skills dictionary"
            )
