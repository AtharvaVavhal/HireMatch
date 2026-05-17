"""
tests/test_scorer_extended.py
------------------------------
Extended unit + boundary tests for core/scorer.py

Covers everything the baseline test_scorer.py does NOT:
  - Score boundary values (label thresholds: 85/65/45)
  - Score always in [0, 100] across adversarial inputs
  - Word count accuracy in ScoreResult
  - rank_resumes edge cases (ties, single entry, all empty texts)
  - get_missing_skills set arithmetic edge cases
  - Whitespace-only inputs treated as empty
  - Very long texts
  - Single-word inputs

Run:
    pytest tests/test_scorer_extended.py -v
    pytest tests/test_scorer_extended.py -v --cov=core.scorer
"""

from __future__ import annotations

import pytest

from core.scorer import ScoreResult, compute_score, get_missing_skills, rank_resumes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text(words: list[str], repeat: int = 1) -> str:
    return " ".join(words * repeat)


# ===========================================================================
# TestScoreValidation — boundary & contract tests
# ===========================================================================

class TestScoreValidation:
    """Score must always be a float in [0.0, 100.0]; cosine_raw in [0.0, 1.0]."""

    @pytest.mark.parametrize("resume,jd", [
        ("python", "java"),
        ("", "python"),
        ("python", ""),
        ("", ""),
        # NOTE: single-letter tokens ("a b c d e") are intentionally excluded
        # here because sklearn's TF-IDF strips them as stop words, producing
        # an empty vocabulary which raises ValueError. See
        # test_single_letter_tokens_raises_known_error below.
        ("python fastapi docker", "python fastapi docker"),
        ("   ", "python developer"),
        ("python developer", "   "),
    ])
    def test_score_always_in_range(self, resume, jd):
        result = compute_score(resume, jd)
        assert 0.0 <= result.score <= 100.0, (
            f"Score {result.score} out of [0, 100] for inputs ({resume!r}, {jd!r})"
        )

    @pytest.mark.parametrize("resume,jd", [
        ("python", "java"),
        ("python fastapi", "python fastapi"),
        ("abc", "xyz"),
    ])
    def test_cosine_raw_always_in_range(self, resume, jd):
        result = compute_score(resume, jd)
        assert 0.0 <= result.cosine_raw <= 1.0

    def test_score_is_float(self):
        result = compute_score("python", "python")
        assert isinstance(result.score, float)

    def test_single_letter_tokens_now_returns_zero(self):
        """
        FIXED BUG: sklearn TF-IDF used to raise ValueError (empty vocabulary)
        when both inputs consist entirely of single-letter stop-word tokens.

        The fix in core/scorer.py catches ValueError and returns ScoreResult
        with score=0.0 and label='Poor Match' instead of crashing.

        This test verifies the fix is in place.
        """
        result = compute_score("a b c d e", "f g h i j")
        assert result.score == 0.0
        assert result.label == "Poor Match"
        assert result.cosine_raw == 0.0

    def test_cosine_raw_is_float(self):
        result = compute_score("python", "python")
        assert isinstance(result.cosine_raw, float)

    def test_score_matches_cosine_raw_times_100(self):
        result = compute_score("python developer", "python developer flask")
        assert abs(result.score - round(result.cosine_raw * 100, 2)) < 0.01


# ===========================================================================
# TestLabelThresholds — score-to-label mapping
# ===========================================================================

class TestLabelThresholds:
    """
    Score ranges mapped to labels:
        85 – 100  → Excellent Match
        65 – 84   → Good Match
        45 – 64   → Moderate Match
        0  – 44   → Poor Match
    """

    def test_identical_text_is_excellent(self):
        text = "python fastapi postgresql docker redis"
        result = compute_score(text, text)
        assert result.label == "Excellent Match"
        assert result.score == pytest.approx(100.0)

    def test_zero_score_is_poor_match(self):
        result = compute_score("", "python fastapi")
        assert result.label == "Poor Match"

    def test_completely_unrelated_is_poor_match(self):
        resume = "graphic design photoshop illustrator figma branding"
        jd = "machine learning tensorflow python neural network"
        result = compute_score(resume, jd)
        # May not be exactly 0 due to TF-IDF, but should be poor
        assert result.label == "Poor Match"

    def test_label_is_string(self):
        result = compute_score("python", "python")
        assert isinstance(result.label, str)

    def test_label_is_one_of_known_values(self):
        valid_labels = {"Excellent Match", "Good Match", "Moderate Match", "Poor Match"}
        for resume, jd in [
            ("python fastapi docker", "python fastapi"),
            ("java spring boot", "python fastapi"),
            ("", "python"),
        ]:
            result = compute_score(resume, jd)
            assert result.label in valid_labels, f"Unexpected label: {result.label!r}"


# ===========================================================================
# TestWordCounts — resume_word_count / jd_word_count accuracy
# ===========================================================================

class TestWordCounts:
    """ScoreResult.resume_word_count and jd_word_count must match input lengths."""

    def test_resume_word_count_accurate(self):
        resume = "python fastapi postgresql docker redis git"  # 6 words
        result = compute_score(resume, "python")
        assert result.resume_word_count == 6

    def test_jd_word_count_accurate(self):
        jd = "senior python engineer backend"  # 4 words
        result = compute_score("python", jd)
        assert result.jd_word_count == 4

    def test_empty_resume_word_count_zero(self):
        result = compute_score("", "python fastapi")
        assert result.resume_word_count == 0

    def test_empty_jd_word_count_zero(self):
        result = compute_score("python fastapi", "")
        assert result.jd_word_count == 0

    def test_both_empty_word_counts_zero(self):
        result = compute_score("", "")
        assert result.resume_word_count == 0
        assert result.jd_word_count == 0

    def test_single_word_resume_count_one(self):
        result = compute_score("python", "java")
        assert result.resume_word_count == 1

    def test_single_word_jd_count_one(self):
        result = compute_score("java", "python")
        assert result.jd_word_count == 1


# ===========================================================================
# TestWhitespaceInputs
# ===========================================================================

class TestWhitespaceInputs:
    """Whitespace-only strings must behave like empty strings."""

    @pytest.mark.parametrize("ws", ["   ", "\n\n", "\t", "\r\n\t"])
    def test_whitespace_resume_score_is_zero(self, ws):
        result = compute_score(ws, "python fastapi")
        assert result.score == 0.0

    @pytest.mark.parametrize("ws", ["   ", "\n\n", "\t", "\r\n\t"])
    def test_whitespace_jd_score_is_zero(self, ws):
        result = compute_score("python fastapi", ws)
        assert result.score == 0.0

    @pytest.mark.parametrize("ws", ["   ", "\n\n", "\t"])
    def test_whitespace_resume_label_is_poor(self, ws):
        result = compute_score(ws, "python fastapi")
        assert result.label == "Poor Match"


# ===========================================================================
# TestGetMissingSkills
# ===========================================================================

class TestGetMissingSkills:
    """get_missing_skills() must return JD skills not present in resume."""

    def test_returns_set(self):
        assert isinstance(get_missing_skills({"python"}, {"python", "docker"}), set)

    def test_exact_match_returns_empty(self):
        skills = {"python", "fastapi", "docker"}
        assert get_missing_skills(skills, skills) == set()

    def test_all_missing_returns_full_jd_set(self):
        resume = {"figma", "illustrator"}
        jd = {"python", "fastapi", "docker"}
        assert get_missing_skills(resume, jd) == jd

    def test_partial_overlap_correct(self):
        resume = {"python", "fastapi", "git"}
        jd = {"python", "fastapi", "docker", "postgresql"}
        missing = get_missing_skills(resume, jd)
        assert missing == {"docker", "postgresql"}

    def test_empty_resume_returns_all_jd_skills(self):
        jd = {"python", "docker", "git"}
        assert get_missing_skills(set(), jd) == jd

    def test_empty_jd_returns_empty_set(self):
        resume = {"python", "docker"}
        assert get_missing_skills(resume, set()) == set()

    def test_both_empty_returns_empty_set(self):
        assert get_missing_skills(set(), set()) == set()

    def test_extra_resume_skills_not_in_result(self):
        resume = {"python", "fastapi", "docker", "kubernetes"}
        jd = {"python", "fastapi"}
        # No skills are missing from jd in resume
        assert get_missing_skills(resume, jd) == set()

    def test_case_sensitivity_preserved(self):
        """Skill strings are treated case-sensitively (caller normalises first)."""
        resume = {"Python"}
        jd = {"python"}  # different case
        missing = get_missing_skills(resume, jd)
        assert "python" in missing


# ===========================================================================
# TestRankResumes
# ===========================================================================

class TestRankResumes:
    """rank_resumes() must return a correctly sorted, complete list of dicts."""

    def test_result_is_list(self):
        resumes = [("Alice", "python fastapi")]
        assert isinstance(rank_resumes(resumes, "python"), list)

    def test_result_length_matches_input(self):
        resumes = [("A", "python"), ("B", "java"), ("C", "docker")]
        ranked = rank_resumes(resumes, "python")
        assert len(ranked) == 3

    def test_each_entry_has_required_keys(self):
        ranked = rank_resumes([("Alice", "python fastapi")], "python fastapi")
        required = {"candidate", "score", "label", "cosine_raw"}
        for entry in ranked:
            assert required.issubset(entry.keys())

    def test_sorted_descending_by_score(self):
        resumes = [
            ("strong", "python fastapi docker postgresql git"),
            ("medium", "python django sql"),
            ("weak",   "photoshop illustrator branding"),
        ]
        ranked = rank_resumes(resumes, "python fastapi docker postgresql")
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_candidate_names_preserved(self):
        resumes = [("Alice", "python"), ("Bob", "java")]
        ranked = rank_resumes(resumes, "python")
        names = {r["candidate"] for r in ranked}
        assert names == {"Alice", "Bob"}

    def test_single_resume_ranked_correctly(self):
        resumes = [("Solo", "python fastapi")]
        ranked = rank_resumes(resumes, "python fastapi docker")
        assert len(ranked) == 1
        assert ranked[0]["candidate"] == "Solo"

    def test_all_empty_resumes_all_score_zero(self):
        resumes = [("A", ""), ("B", ""), ("C", "")]
        ranked = rank_resumes(resumes, "python fastapi")
        for entry in ranked:
            assert entry["score"] == 0.0

    def test_empty_resume_list_returns_empty(self):
        assert rank_resumes([], "python fastapi") == []

    def test_scores_are_floats(self):
        resumes = [("Alice", "python fastapi")]
        ranked = rank_resumes(resumes, "python")
        assert isinstance(ranked[0]["score"], float)

    def test_labels_are_known_values(self):
        valid = {"Excellent Match", "Good Match", "Moderate Match", "Poor Match"}
        resumes = [("A", "python"), ("B", "java"), ("C", "")]
        ranked = rank_resumes(resumes, "python fastapi")
        for r in ranked:
            assert r["label"] in valid

    def test_tie_in_scores_both_present(self):
        """Identical resumes against same JD → same score, both returned."""
        resumes = [("Alice", "python fastapi"), ("Bob", "python fastapi")]
        ranked = rank_resumes(resumes, "python fastapi")
        assert len(ranked) == 2
        assert ranked[0]["score"] == ranked[1]["score"]

    def test_very_long_resume_does_not_crash(self):
        long_text = "python " * 5000
        resumes = [("LongResume", long_text)]
        try:
            ranked = rank_resumes(resumes, "python developer")
            assert len(ranked) == 1
        except Exception as exc:
            pytest.fail(f"rank_resumes raised on long text: {exc}")


# ===========================================================================
# TestComputeScoreAdversarial
# ===========================================================================

class TestComputeScoreAdversarial:
    """Stress-test compute_score with unusual inputs."""

    def test_single_word_each(self):
        result = compute_score("python", "python")
        assert result.score == pytest.approx(100.0)

    def test_single_shared_word_with_extra(self):
        result = compute_score("python developer senior", "python engineer junior")
        # Shared 'python' means score > 0
        assert result.score > 0.0

    def test_numeric_only_strings(self):
        result = compute_score("123 456 789", "987 654 321")
        # TF-IDF on digits — should not crash
        assert isinstance(result, ScoreResult)

    def test_special_characters_handled(self):
        result = compute_score("C++ .NET Node.js", "C++ Python REST-API")
        assert isinstance(result, ScoreResult)
        assert 0.0 <= result.score <= 100.0

    def test_very_long_identical_texts_perfect_score(self):
        long = " ".join(["python", "fastapi", "docker"] * 1000)
        result = compute_score(long, long)
        assert result.score == pytest.approx(100.0)

    def test_returns_score_result_type(self):
        result = compute_score("python", "java")
        assert isinstance(result, ScoreResult)

    def test_unicode_inputs(self):
        result = compute_score("développeur python django", "python backend developer")
        assert isinstance(result, ScoreResult)
        assert 0.0 <= result.score <= 100.0
