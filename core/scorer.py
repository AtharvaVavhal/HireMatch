"""
core/scorer.py
--------------
Resume vs Job Description Match Scorer.

Algorithm:
    1. TF-IDF Vectorization  — converts text to numerical vectors
    2. Cosine Similarity     — measures angle between vectors (0.0 to 1.0)
    3. Score = similarity * 100  (percentage)

Mathematics:
    TF(t, d)  = count(t in d) / total_terms(d)
    IDF(t, D) = log( N / (1 + df(t)) )   where N = total docs, df = docs containing t
    TF-IDF    = TF * IDF

    Cosine Similarity = (A · B) / (||A|| * ||B||)
        - 1.0 = identical content direction
        - 0.0 = completely unrelated

Score Interpretation:
    85-100  → Excellent Match
    65-84   → Good Match
    45-64   → Moderate Match
    0-44    → Poor Match
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoreResult:
    score: float          # 0.0 to 100.0
    label: str            # Excellent / Good / Moderate / Poor
    cosine_raw: float     # raw cosine similarity (0.0 to 1.0)
    resume_word_count: int
    jd_word_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _label(score: float) -> str:
    if score >= 85:
        return "Excellent Match"
    elif score >= 65:
        return "Good Match"
    elif score >= 45:
        return "Moderate Match"
    return "Poor Match"


# ─────────────────────────────────────────────────────────────────────────────
# Core functions
# ─────────────────────────────────────────────────────────────────────────────

def compute_score(resume_text: str, jd_text: str) -> ScoreResult:
    """
    Compute match score between a resume and a job description.

    Args:
        resume_text: Preprocessed resume text (lowercase, no stopwords).
        jd_text:     Preprocessed job description text.

    Returns:
        ScoreResult with score (0-100), label, and diagnostics.
    """
    if not resume_text or not resume_text.strip():
        logger.warning("Empty resume text received.")
        return ScoreResult(0.0, "Poor Match", 0.0, 0, len(jd_text.split()))

    if not jd_text or not jd_text.strip():
        logger.warning("Empty JD text received.")
        return ScoreResult(0.0, "Poor Match", 0.0, len(resume_text.split()), 0)

    # Step 1: TF-IDF vectorization
    # fit_transform on both docs together so vocab is shared
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])

    # Step 2: Cosine similarity between resume (row 0) and JD (row 1)
    raw = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    raw = float(round(raw, 4))

    score = round(raw * 100, 2)

    return ScoreResult(
        score=score,
        label=_label(score),
        cosine_raw=raw,
        resume_word_count=len(resume_text.split()),
        jd_word_count=len(jd_text.split()),
    )


def get_missing_skills(resume_skills: set[str], jd_skills: set[str]) -> set[str]:
    """
    Return skills present in JD but missing from resume.

    Args:
        resume_skills: Skills extracted from resume.
        jd_skills:     Skills extracted from job description.

    Returns:
        Set of missing skill strings.
    """
    return jd_skills - resume_skills


def rank_resumes(
    resumes: list[tuple[str, str]],  # [(filename, preprocessed_text), ...]
    jd_text: str,
) -> list[dict]:
    """
    Rank multiple resumes against one job description.

    Args:
        resumes: List of (name, preprocessed_text) tuples.
        jd_text: Preprocessed job description text.

    Returns:
        List of dicts sorted by score descending.
    """
    results = []
    for name, text in resumes:
        result = compute_score(text, jd_text)
        results.append({
            "candidate": name,
            "score": result.score,
            "label": result.label,
            "cosine_raw": result.cosine_raw,
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test case 1: Good match
    resume1 = "python developer fastapi postgresql docker redis jwt git github"
    jd1 = "python backend developer fastapi postgresql docker kubernetes aws jwt"

    # Test case 2: Poor match
    resume2 = "graphic designer photoshop illustrator figma adobe indesign"
    jd2 = "python developer machine learning tensorflow pandas scikit-learn"

    # Test case 3: Perfect match
    resume3 = "python fastapi postgresql"
    jd3 = "python fastapi postgresql"

    print("=" * 55)
    print("  SCORER TEST CASES")
    print("=" * 55)

    for i, (r, j, label) in enumerate([
        (resume1, jd1, "Good Match Test"),
        (resume2, jd2, "Poor Match Test"),
        (resume3, jd3, "Perfect Match Test"),
    ], 1):
        result = compute_score(r, j)
        print(f"\nTC-{i}: {label}")
        print(f"  Score      : {result.score}%")
        print(f"  Label      : {result.label}")
        print(f"  Cosine Raw : {result.cosine_raw}")

    # Multi-resume ranking
    print("\n" + "=" * 55)
    print("  MULTI-RESUME RANKING")
    print("=" * 55)

    resumes = [
        ("Alice", "python fastapi docker postgresql jwt github"),
        ("Bob",   "java spring boot mysql hibernate rest api"),
        ("Carol", "python django redis celery postgresql aws"),
    ]
    jd = "python backend fastapi postgresql docker jwt"

    ranked = rank_resumes(resumes, jd)
    for rank, r in enumerate(ranked, 1):
        print(f"  #{rank} {r['candidate']:8} → {r['score']:5.1f}%  [{r['label']}]")

    # Missing skills
    print("\n" + "=" * 55)
    print("  MISSING SKILLS")
    print("=" * 55)
    resume_skills = {"python", "fastapi", "postgresql", "git"}
    jd_skills     = {"python", "fastapi", "postgresql", "docker", "aws", "kubernetes"}
    missing = get_missing_skills(resume_skills, jd_skills)
    print(f"  Missing: {sorted(missing)}")