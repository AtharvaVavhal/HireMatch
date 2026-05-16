"""
skill_extractor.py
------------------
Rule-based skill extraction from cleaned resume text.

Matching pipeline (no ML):
    1. Normalise  – lowercase + collapse whitespace.
    2. Alias pass – replace known alternate spellings with canonical names.
    3. Multi-word match – longest-match-first scan using a sorted phrase list
                          so "machine learning" is caught before "machine".
    4. Word-boundary check – uses regex \\b anchors to avoid partial matches
                             (e.g. "rust" inside "frustration" won't fire).
    5. Deduplication – set-based; preserves one canonical form per skill.
    6. Categorisation – maps each detected skill back to its category bucket.

Usage:
    from skill_extractor import extract_skills

    result = extract_skills(resume_text)
    # result["by_category"]  → dict[str, list[str]]
    # result["all_skills"]   → list[str]  (flat, sorted)
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TypedDict

from data.skills_dict import ALIASES, EXCLUDED_CATEGORIES, SKILLS_DICT

# ─────────────────────────────────────────────────────────────────────────────
# Pre-computation (runs once at import time)
# ─────────────────────────────────────────────────────────────────────────────

# Flat map: canonical_skill → category  (for quick reverse lookup)
_SKILL_TO_CATEGORY: dict[str, str] = {}
for _cat, _skills in SKILLS_DICT.items():
    if _cat in EXCLUDED_CATEGORIES:
        continue
    for _s in _skills:
        _SKILL_TO_CATEGORY[_s.lower()] = _cat

# Sorted skill list – longest phrases first prevents short substrings from
# shadowing multi-word skills during the scan.
_ALL_CANONICAL: list[str] = sorted(
    _SKILL_TO_CATEGORY.keys(), key=len, reverse=True
)

# Pre-compile one regex per skill using word-boundary anchors.
# Escape special regex chars (c++, c#, .net, etc.)
_SKILL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (skill, re.compile(r"(?<![a-z0-9\-\+\#])" + re.escape(skill) + r"(?![a-z0-9\-\+\#])", re.IGNORECASE))
    for skill in _ALL_CANONICAL
]

# Alias patterns – sorted longest first for the same reason
_ALIAS_PAIRS: list[tuple[str, str]] = sorted(
    ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True
)


# ─────────────────────────────────────────────────────────────────────────────
# Public Types
# ─────────────────────────────────────────────────────────────────────────────

class ExtractionResult(TypedDict):
    all_skills: list[str]
    by_category: dict[str, list[str]]
    unmatched_aliases: list[str]
    stats: dict[str, int]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lowercase + collapse runs of whitespace/newlines to single space."""
    text = text.lower()
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _apply_aliases(text: str) -> tuple[str, list[str]]:
    """
    Replace alias surface forms with their canonical equivalents.
    Returns (modified_text, list_of_applied_aliases).

    Only whole-word replacements are made (word-boundary aware).
    """
    applied: list[str] = []
    for alias, canonical in _ALIAS_PAIRS:
        pattern = re.compile(
            r"(?<![a-z0-9\-])" + re.escape(alias) + r"(?![a-z0-9\-])",
            re.IGNORECASE,
        )
        if pattern.search(text):
            text = pattern.sub(canonical, text)
            applied.append(f"{alias} → {canonical}")
    return text, applied


def _match_skills(text: str) -> set[str]:
    """
    Scan normalised text for all canonical skill names.
    Returns a set of matched canonical skill strings.

    Longest-match-first ordering (established at import time) ensures
    multi-word skills like 'machine learning' are matched whole rather
    than their subwords individually.
    """
    found: set[str] = set()
    for skill, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            found.add(skill)
    return found


def _categorise(skills: set[str]) -> dict[str, list[str]]:
    """Group skills by their category, sorted alphabetically within each."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        cat = _SKILL_TO_CATEGORY.get(skill, "uncategorised")
        buckets[cat].append(skill)
    return {cat: sorted(lst) for cat, lst in sorted(buckets.items())}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_skills(
    raw_text: str,
    exclude_categories: set[str] | None = None,
) -> ExtractionResult:
    """
    Extract technical skills from resume text.

    Args:
        raw_text: Raw or lightly cleaned resume text (any casing/whitespace).
        exclude_categories: Optional override for categories to skip.
                            Falls back to EXCLUDED_CATEGORIES from skills_dict.

    Returns:
        ExtractionResult with:
            all_skills      – deduplicated, sorted flat list
            by_category     – skills grouped by category
            unmatched_aliases – aliases that fired (diagnostic)
            stats           – summary counts
    """
    if not raw_text or not raw_text.strip():
        return ExtractionResult(
            all_skills=[],
            by_category={},
            unmatched_aliases=[],
            stats={"total": 0, "categories": 0},
        )

    # Step 1: Normalise
    normalised = _normalise(raw_text)

    # Step 2: Alias substitution
    normalised, alias_log = _apply_aliases(normalised)

    # Step 3 & 4: Match with word-boundary-aware regex (longest-first)
    matched = _match_skills(normalised)

    # Step 5: Apply category exclusions
    _excluded = exclude_categories if exclude_categories is not None else EXCLUDED_CATEGORIES
    if _excluded:
        matched = {s for s in matched if _SKILL_TO_CATEGORY.get(s) not in _excluded}

    # Step 6: Categorise + deduplicate (set already deduplicates)
    by_category = _categorise(matched)
    all_skills = sorted(matched)

    return ExtractionResult(
        all_skills=all_skills,
        by_category=by_category,
        unmatched_aliases=alias_log,
        stats={
            "total": len(all_skills),
            "categories": len(by_category),
        },
    )


def get_skills_by_category(raw_text: str, category: str) -> list[str]:
    """Convenience: extract and return skills for a single category only."""
    result = extract_skills(raw_text)
    return result["by_category"].get(category, [])


def list_all_supported_skills() -> dict[str, list[str]]:
    """Return the full skill dictionary (useful for debugging/UI)."""
    return {
        cat: sorted(skills)
        for cat, skills in SKILLS_DICT.items()
        if cat not in EXCLUDED_CATEGORIES
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI demo (python skill_extractor.py)
# ─────────────────────────────────────────────────────────────────────────────

_SAMPLE_RESUME = """
Atharva Vavhal | Software Engineer
GitHub: AtharvaVavhal | Pune, India

SKILLS
------
Languages : Python, JavaScript (ES6+), TypeScript, C++, SQL
Frontend  : React.js, Next.js, Tailwind CSS, Redux, Three.js, PWA
Backend   : Node.js, FastAPI, Express.js, Flask, REST API, Socket.IO
Databases : PostgreSQL, MongoDB, Redis, Firebase Firestore
Cloud/Ops : Docker, GitHub Actions, Vercel, Render, Cloudflare, Nginx
ML/AI     : XGBoost, scikit-learn, Pandas, NumPy, Groq API, OpenAI
Tools     : Git, GitHub, Postman, Figma, VS Code

PROJECTS
--------
Intervenix – Loan Default Prediction (XGBoost, FastAPI, React, PostgreSQL)
CampusCopy – Print automation with Razorpay, Twilio, WebSocket, Redis
FoodSafe   – AI-powered food diary; Groq Vision, PWA, VAPID push notifications
PRGuard    – GitHub PR review bot using FastAPI, Webhooks, LLM scoring

DSA prep in C/C++ targeting FAANG placements.
Experience with OAuth2, JWT, CORS, and secure API design.
"""

if __name__ == "__main__":
    result = extract_skills(_SAMPLE_RESUME)

    print("=" * 60)
    print("  SKILL EXTRACTION DEMO")
    print("=" * 60)

    print(f"\n📊 Stats: {result['stats']['total']} skills across "
          f"{result['stats']['categories']} categories\n")

    for category, skills in result["by_category"].items():
        label = category.replace("_", " ").title()
        print(f"  [{label}]")
        for skill in skills:
            print(f"    • {skill}")
        print()

    if result["unmatched_aliases"]:
        print("🔁 Alias substitutions applied:")
        for a in result["unmatched_aliases"]:
            print(f"    {a}")

    print("\n✅ Flat list (all_skills):")
    print("  ", ", ".join(result["all_skills"]))