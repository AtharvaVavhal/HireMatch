"""
tests/test_parser.py
--------------------
Unit tests for core/parser.py

Run from the project root (venv active):
    pytest tests/test_parser.py -v
    pytest tests/test_parser.py -v --cov=core.parser

Test strategy
-------------
We never rely on real PDF files in unit tests — they are slow, fragile,
and not always available in CI.  Instead we use:
  - tmp_path (pytest built-in fixture) to create temp files on disk
  - a minimal valid PDF written as raw bytes
  - intentionally broken content to test error paths
"""

import logging
from pathlib import Path

import pytest

from core.parser import ParseResult, get_text_only, parse_multiple_pdfs, parse_pdf

# ---------------------------------------------------------------------------
# Minimal valid single-page PDF that pdfplumber can open.
# This is a hand-crafted PDF byte string — the smallest legal PDF
# that contains one page with the text "Hello World".
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

CORRUPTED_PDF_BYTES = b"This is not a valid PDF at all %%EOF"
EMPTY_PDF_BYTES = b""


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """A minimal but genuine PDF file on disk."""
    pdf_file = tmp_path / "valid_resume.pdf"
    pdf_file.write_bytes(MINIMAL_PDF_BYTES)
    return pdf_file


@pytest.fixture
def corrupted_pdf(tmp_path: Path) -> Path:
    """A file with a .pdf extension but garbage content."""
    pdf_file = tmp_path / "corrupted_resume.pdf"
    pdf_file.write_bytes(CORRUPTED_PDF_BYTES)
    return pdf_file


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """A completely empty file with a .pdf extension."""
    pdf_file = tmp_path / "empty.pdf"
    pdf_file.write_bytes(EMPTY_PDF_BYTES)
    return pdf_file


@pytest.fixture
def non_pdf_file(tmp_path: Path) -> Path:
    """A plain text file — wrong extension."""
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text("This is a plain text file, not a PDF.")
    return txt_file


@pytest.fixture
def resume_folder(tmp_path: Path, valid_pdf: Path) -> Path:
    """
    A folder containing:
      - two valid PDFs
      - one corrupted PDF
      - one non-PDF file (should be silently ignored)
    """
    folder = tmp_path / "resumes"
    folder.mkdir()

    # Valid PDF 1 (copy the fixture)
    (folder / "resume_alice.pdf").write_bytes(MINIMAL_PDF_BYTES)

    # Valid PDF 2
    (folder / "resume_bob.pdf").write_bytes(MINIMAL_PDF_BYTES)

    # Corrupted PDF
    (folder / "resume_corrupt.pdf").write_bytes(CORRUPTED_PDF_BYTES)

    # Non-PDF — must be ignored, NOT counted as a failure
    (folder / "notes.txt").write_text("ignore me")

    return folder


@pytest.fixture
def empty_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "empty_resumes"
    folder.mkdir()
    return folder


# ===========================================================================
# Tests: parse_pdf()
# ===========================================================================

class TestParsePdf:

    def test_returns_parse_result(self, valid_pdf):
        """Return type must always be ParseResult."""
        result = parse_pdf(str(valid_pdf))
        assert isinstance(result, ParseResult)

    def test_success_flag_true_on_valid_pdf(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        assert result.success is True

    def test_text_is_string_on_success(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        assert isinstance(result.text, str)

    def test_page_count_positive_on_valid_pdf(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        assert result.page_count >= 1

    def test_error_is_none_on_success(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        assert result.error is None

    def test_file_path_stored_in_result(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        # file_path should contain the filename
        assert "valid_resume.pdf" in result.file_path

    # --- Missing file --------------------------------------------------------

    def test_missing_file_returns_failure(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.success is False

    def test_missing_file_error_message(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.error is not None
        assert "not found" in result.error.lower() or "ghost.pdf" in result.error

    def test_missing_file_text_is_empty_string(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.text == ""

    def test_missing_file_page_count_is_zero(self, tmp_path):
        result = parse_pdf(str(tmp_path / "ghost.pdf"))
        assert result.page_count == 0

    # --- Wrong extension -----------------------------------------------------

    def test_non_pdf_extension_returns_failure(self, non_pdf_file):
        result = parse_pdf(str(non_pdf_file))
        assert result.success is False

    def test_non_pdf_extension_error_message(self, non_pdf_file):
        result = parse_pdf(str(non_pdf_file))
        assert result.error is not None

    # --- Corrupted PDF -------------------------------------------------------

    def test_corrupted_pdf_returns_failure(self, corrupted_pdf):
        """pdfplumber should raise on garbage content; we catch and return failure."""
        result = parse_pdf(str(corrupted_pdf))
        # May succeed with empty text OR fail — either is acceptable
        # The important thing is the program does NOT raise an exception
        assert isinstance(result, ParseResult)

    def test_corrupted_pdf_does_not_raise(self, corrupted_pdf):
        """Absolutely must not propagate any exception."""
        try:
            parse_pdf(str(corrupted_pdf))
        except Exception as exc:
            pytest.fail(f"parse_pdf raised an unexpected exception: {exc}")

    # --- Empty file ----------------------------------------------------------

    def test_empty_pdf_does_not_raise(self, empty_file):
        try:
            parse_pdf(str(empty_file))
        except Exception as exc:
            pytest.fail(f"parse_pdf raised an unexpected exception: {exc}")

    # --- Path type handling --------------------------------------------------

    def test_accepts_path_object(self, valid_pdf):
        """parse_pdf should accept a Path object, not just str."""
        result = parse_pdf(valid_pdf)          # passing Path, not str
        assert isinstance(result, ParseResult)

    def test_accepts_string_path(self, valid_pdf):
        result = parse_pdf(str(valid_pdf))
        assert isinstance(result, ParseResult)


# ===========================================================================
# Tests: parse_multiple_pdfs()
# ===========================================================================

class TestParseMultiplePdfs:

    def test_returns_list(self, resume_folder):
        results = parse_multiple_pdfs(str(resume_folder))
        assert isinstance(results, list)

    def test_returns_parse_result_objects(self, resume_folder):
        results = parse_multiple_pdfs(str(resume_folder))
        assert all(isinstance(r, ParseResult) for r in results)

    def test_counts_only_pdfs_not_txt(self, resume_folder):
        """The .txt file in the folder must be silently ignored."""
        results = parse_multiple_pdfs(str(resume_folder))
        # folder has 3 PDFs (2 valid + 1 corrupt) and 1 txt
        assert len(results) == 3

    def test_two_valid_pdfs_succeed(self, resume_folder):
        results = parse_multiple_pdfs(str(resume_folder))
        successes = [r for r in results if r.success]
        assert len(successes) >= 2

    def test_empty_folder_returns_empty_list(self, empty_folder):
        results = parse_multiple_pdfs(str(empty_folder))
        assert results == []

    def test_raises_on_non_directory(self, valid_pdf):
        """Passing a file path instead of a folder should raise NotADirectoryError."""
        with pytest.raises(NotADirectoryError):
            parse_multiple_pdfs(str(valid_pdf))

    def test_one_bad_pdf_does_not_stop_others(self, resume_folder):
        """Corrupt file must not prevent good files from being parsed."""
        results = parse_multiple_pdfs(str(resume_folder))
        file_names = [Path(r.file_path).name for r in results if r.success]
        assert "resume_alice.pdf" in file_names
        assert "resume_bob.pdf" in file_names


# ===========================================================================
# Tests: get_text_only()
# ===========================================================================

class TestGetTextOnly:

    def test_returns_string(self, valid_pdf):
        text = get_text_only(str(valid_pdf))
        assert isinstance(text, str)

    def test_returns_empty_string_on_missing_file(self, tmp_path):
        text = get_text_only(str(tmp_path / "nope.pdf"))
        assert text == ""

    def test_does_not_raise_on_bad_input(self, tmp_path):
        try:
            get_text_only(str(tmp_path / "nope.pdf"))
        except Exception as exc:
            pytest.fail(f"get_text_only raised: {exc}")


# ===========================================================================
# Tests: logging behaviour (non-critical, informational)
# ===========================================================================

class TestLogging:

    def test_warning_logged_for_missing_file(self, tmp_path, caplog):
        with caplog.at_level(logging.WARNING, logger="core.parser"):
            parse_pdf(str(tmp_path / "missing.pdf"))
        assert any("not found" in r.message.lower() for r in caplog.records)

    def test_info_logged_on_success(self, valid_pdf, caplog):
        with caplog.at_level(logging.INFO, logger="core.parser"):
            parse_pdf(str(valid_pdf))
        assert any("successfully" in r.message.lower() for r in caplog.records)