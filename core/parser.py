"""
core/parser.py
--------------
PDF Resume Parser using pdfplumber.

Responsibilities:
  - Extract raw text from a single PDF file
  - Batch-extract text from multiple PDFs in a folder
  - Handle corrupted, empty, or unreadable PDFs without crashing
  - Return structured results the rest of the pipeline can consume

This module has ZERO knowledge of Flask, scoring, or NLP.
It only reads PDFs and hands back text.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pdfplumber

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Using a module-level logger (not root logger) so callers can control
# verbosity independently.  Name matches the dotted import path.
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParseResult:
    """
    Holds the outcome of parsing one PDF.

    Attributes:
        file_path : Absolute path to the source PDF.
        text      : Extracted raw text (empty string on failure).
        page_count: Number of pages successfully read (0 on failure).
        success   : True if extraction succeeded, False otherwise.
        error     : Human-readable error message when success=False.
    """
    file_path: str
    text: str = ""
    page_count: int = 0
    success: bool = True
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Single-file parser
# ---------------------------------------------------------------------------

def parse_pdf(file_path: str) -> ParseResult:
    """
    Extract all text from a single PDF file.

    The function reads the PDF page by page, concatenates the text,
    and returns a ParseResult.  Any exception (corrupt file, password-
    protected PDF, IO error) is caught and stored in the result instead
    of propagating — the caller decides what to do with failures.

    Args:
        file_path: Path to the PDF file (str or Path-like).

    Returns:
        ParseResult with .text populated on success,
        or .success=False and .error set on failure.

    Example:
        result = parse_pdf("resumes/john_doe.pdf")
        if result.success:
            print(result.text[:200])
    """
    # Normalise to an absolute string path so error messages are unambiguous
    path = Path(file_path).resolve()
    path_str = str(path)

    logger.info("Parsing PDF: %s", path_str)

    # --- Guard: file must exist -----------------------------------------------
    if not path.exists():
        msg = f"File not found: {path_str}"
        logger.warning(msg)
        return ParseResult(file_path=path_str, success=False, error=msg)

    # --- Guard: must be a .pdf ------------------------------------------------
    if path.suffix.lower() != ".pdf":
        msg = f"Not a PDF file (got '{path.suffix}'): {path_str}"
        logger.warning(msg)
        return ParseResult(file_path=path_str, success=False, error=msg)

    # --- Extraction -----------------------------------------------------------
    try:
        pages_text = []  # Collect text from each page separately

        with pdfplumber.open(path_str) as pdf:
            total_pages = len(pdf.pages)

            for page_number, page in enumerate(pdf.pages, start=1):
                try:
                    # extract_text() returns None when a page has no text layer
                    # (e.g. scanned image PDF).  We default to "" in that case.
                    raw = page.extract_text() or ""
                    pages_text.append(raw)

                except Exception as page_err:
                    # A single bad page should not abort the whole document.
                    # Log it and move on.
                    logger.warning(
                        "Could not extract page %d of '%s': %s",
                        page_number, path_str, page_err
                    )
                    pages_text.append("")   # keep page count consistent

        # Join pages with a double newline so section boundaries are preserved
        full_text = "\n\n".join(pages_text)

        # Strip leading/trailing whitespace from the whole document
        full_text = full_text.strip()

        # Warn if the document produced no text at all (likely a scanned PDF)
        if not full_text:
            logger.warning(
                "No text extracted from '%s'. "
                "The PDF may be image-based (scanned). "
                "Consider running OCR first.",
                path_str
            )

        logger.info(
            "Successfully parsed '%s' — %d pages, %d characters",
            path.name, total_pages, len(full_text)
        )

        return ParseResult(
            file_path=path_str,
            text=full_text,
            page_count=total_pages,
            success=True,
        )

    # pdfplumber raises generic Exception for corrupt/encrypted PDFs;
    # catch broadly so no crash leaks to the caller.
    except Exception as err:
        msg = f"Failed to parse '{path_str}': {err}"
        logger.error(msg)
        return ParseResult(file_path=path_str, success=False, error=msg)


# ---------------------------------------------------------------------------
# Batch parser
# ---------------------------------------------------------------------------

def parse_multiple_pdfs(folder_path: str) -> list[ParseResult]:
    """
    Parse every PDF found (non-recursively) in a folder.

    Skips non-PDF files silently.  Each PDF is parsed independently,
    so one corrupted file does not block the rest.

    Args:
        folder_path: Path to a directory containing PDF files.

    Returns:
        List of ParseResult objects, one per PDF found.
        Returns an empty list if the folder is empty or contains no PDFs.

    Raises:
        NotADirectoryError: if folder_path does not point to a directory.

    Example:
        results = parse_multiple_pdfs("data/resumes/")
        for r in results:
            print(r.file_path, "→", "OK" if r.success else r.error)
    """
    folder = Path(folder_path).resolve()

    if not folder.is_dir():
        raise NotADirectoryError(f"Expected a directory, got: {folder}")

    # Collect all .pdf files (case-insensitive suffix check)
    pdf_files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        logger.warning("No PDF files found in '%s'", folder)
        return []

    logger.info("Found %d PDF(s) in '%s'. Starting batch parse…", len(pdf_files), folder)

    results = [parse_pdf(str(pdf)) for pdf in pdf_files]

    # Summary log
    succeeded = sum(1 for r in results if r.success)
    logger.info(
        "Batch complete: %d/%d PDFs parsed successfully.",
        succeeded, len(results)
    )

    return results


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------

def get_text_only(file_path: str) -> str:
    """
    Thin wrapper around parse_pdf() for callers that just want the text
    string and are happy to receive an empty string on failure.

    Useful for quick scripts or notebooks where you don't need the full
    ParseResult metadata.

    Args:
        file_path: Path to a single PDF file.

    Returns:
        Extracted text as a string, or "" if extraction failed.
    """
    result = parse_pdf(file_path)
    return result.text