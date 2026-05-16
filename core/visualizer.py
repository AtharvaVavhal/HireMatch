"""
core/visualizer.py
------------------
Multi-Resume Ranking, DataFrame Generation, and CSV Export.

Pipeline:
    resumes (list of PDFs)
        → parse       (core.parser)
        → preprocess  (core.preprocessor)
        → score       (core.scorer)
        → rank        (this module)
        → DataFrame   (pandas)
        → CSV export  (pandas)

Public API:
    rank_resumes_from_texts()  → ranked list of dicts
    build_dataframe()          → pandas DataFrame
    export_csv()               → saves CSV, returns path
    full_pipeline()            → end-to-end: PDFs + JD → CSV
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.parser import parse_multiple_pdfs, parse_pdf
from core.preprocessor import preprocess
from core.scorer import compute_score, get_missing_skills
from core.skill_extractor import extract_skills

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core ranking logic
# ─────────────────────────────────────────────────────────────────────────────

def rank_resumes_from_texts(
    resumes: list[tuple[str, str]],  # [(candidate_name, raw_text), ...]
    jd_text: str,
) -> list[dict]:
    """
    Rank multiple resumes against a single job description.

    Args:
        resumes : List of (name, raw_resume_text) tuples.
        jd_text : Raw job description text.

    Returns:
        List of result dicts sorted by score descending. Each dict has:
            - rank          : int
            - candidate     : str
            - score         : float (0-100)
            - label         : str (Excellent/Good/Moderate/Poor)
            - matched_skills: list[str]
            - missing_skills: list[str]
            - resume_words  : int
            - jd_words      : int
    """
    if not resumes:
        logger.warning("rank_resumes_from_texts() called with empty resume list.")
        return []

    # Preprocess JD once
    clean_jd = preprocess(jd_text)
    jd_skills = extract_skills(jd_text)["all_skills"]

    results = []

    for name, raw_text in resumes:
        if not raw_text or not raw_text.strip():
            logger.warning("Skipping '%s' — empty resume text.", name)
            results.append({
                "candidate": name,
                "score": 0.0,
                "label": "Poor Match",
                "matched_skills": [],
                "missing_skills": jd_skills,
                "resume_words": 0,
                "jd_words": len(clean_jd.split()),
            })
            continue

        clean_resume = preprocess(raw_text)
        score_result = compute_score(clean_resume, clean_jd)

        resume_skills = extract_skills(raw_text)["all_skills"]
        matched = sorted(set(resume_skills) & set(jd_skills))
        missing = sorted(get_missing_skills(set(resume_skills), set(jd_skills)))

        results.append({
            "candidate":      name,
            "score":          score_result.score,
            "label":          score_result.label,
            "matched_skills": matched,
            "missing_skills": missing,
            "resume_words":   score_result.resume_word_count,
            "jd_words":       score_result.jd_word_count,
        })

    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Add rank
    for i, r in enumerate(results, 1):
        r["rank"] = i

    return results


# ─────────────────────────────────────────────────────────────────────────────
# DataFrame builder
# ─────────────────────────────────────────────────────────────────────────────

def build_dataframe(ranked_results: list[dict]) -> pd.DataFrame:
    """
    Convert ranked results list into a clean pandas DataFrame.

    Args:
        ranked_results: Output from rank_resumes_from_texts().

    Returns:
        DataFrame with columns:
            Rank, Candidate, Score (%), Match Level,
            Matched Skills, Missing Skills, Resume Words, JD Words
    """
    if not ranked_results:
        return pd.DataFrame()

    rows = []
    for r in ranked_results:
        rows.append({
            "Rank":           r["rank"],
            "Candidate":      r["candidate"],
            "Score (%)":      r["score"],
            "Match Level":    r["label"],
            "Matched Skills": ", ".join(r["matched_skills"]) or "—",
            "Missing Skills": ", ".join(r["missing_skills"]) or "—",
            "Resume Words":   r["resume_words"],
            "JD Words":       r["jd_words"],
        })

    df = pd.DataFrame(rows)
    df = df.set_index("Rank")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# CSV export
# ─────────────────────────────────────────────────────────────────────────────

def export_csv(
    df: pd.DataFrame,
    output_dir: str = "data/outputs",
    filename: str | None = None,
) -> str:
    """
    Export the ranked DataFrame to a CSV file.

    Args:
        df         : DataFrame from build_dataframe().
        output_dir : Directory to save the CSV (created if missing).
        filename   : Optional filename. Defaults to timestamped name.

    Returns:
        Absolute path to the saved CSV file.
    """
    if df.empty:
        logger.warning("export_csv() called with empty DataFrame — nothing saved.")
        return ""

    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ranked_results_{timestamp}.csv"

    csv_path = out_path / filename
    df.to_csv(csv_path)

    logger.info("Ranked results saved to: %s", csv_path)
    return str(csv_path)


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end pipeline
# ─────────────────────────────────────────────────────────────────────────────

def full_pipeline(
    resume_folder: str,
    jd_text: str,
    output_dir: str = "data/outputs",
) -> tuple[pd.DataFrame, str]:
    """
    End-to-end: parse folder of PDFs → rank → export CSV.

    Args:
        resume_folder: Path to folder containing PDF resumes.
        jd_text      : Raw job description text.
        output_dir   : Where to save the CSV output.

    Returns:
        (DataFrame, csv_path) tuple.
    """
    parse_results = parse_multiple_pdfs(resume_folder)

    if not parse_results:
        logger.warning("No PDFs found in '%s'.", resume_folder)
        return pd.DataFrame(), ""

    resumes = []
    for pr in parse_results:
        name = Path(pr.file_path).stem  # filename without .pdf
        text = pr.text if pr.success else ""
        resumes.append((name, text))

    ranked = rank_resumes_from_texts(resumes, jd_text)
    df = build_dataframe(ranked)
    csv_path = export_csv(df, output_dir)

    return df, csv_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    JD = """
    We are looking for a Python Backend Developer with experience in FastAPI,
    PostgreSQL, Docker, Redis, and JWT authentication. Knowledge of AWS and
    Kubernetes is a plus. Strong Git skills required.
    """

    RESUMES = [
        ("Alice",
         "Python developer with 2 years experience. Built REST APIs using FastAPI "
         "and Flask. Used PostgreSQL and Redis for data storage. Docker deployment. "
         "JWT auth. Git and GitHub daily. Familiar with AWS EC2."),

        ("Bob",
         "Java Spring Boot developer. MySQL database. Hibernate ORM. REST API design. "
         "Maven build tool. Jenkins CI/CD. Some Python scripting experience."),

        ("Carol",
         "Full stack developer. Python Django backend, React frontend. PostgreSQL. "
         "Docker Compose. Redis caching. Celery task queue. GitHub Actions CI/CD. "
         "JWT tokens. Some Kubernetes experience."),

        ("Dave",
         "Data scientist. Python pandas numpy scikit-learn tensorflow. "
         "Jupyter notebooks. Machine learning model deployment. SQL queries."),
    ]

    print("=" * 65)
    print("  MULTI-RESUME RANKING DEMO")
    print("=" * 65)

    ranked = rank_resumes_from_texts(RESUMES, JD)

    for r in ranked:
        print(f"\n  #{r['rank']} {r['candidate']}")
        print(f"     Score   : {r['score']}%  [{r['label']}]")
        print(f"     Matched : {', '.join(r['matched_skills']) or '—'}")
        print(f"     Missing : {', '.join(r['missing_skills']) or '—'}")

    df = build_dataframe(ranked)
    print("\n" + "=" * 65)
    print("  DATAFRAME")
    print("=" * 65)
    print(df.to_string())

    csv_path = export_csv(df)
    print(f"\n✅ CSV saved → {csv_path}")