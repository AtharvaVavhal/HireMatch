import pytest

from core.scorer import ScoreResult, compute_score, get_missing_skills, rank_resumes


def test_compute_score_returns_score_result():
	result = compute_score("python fastapi", "python fastapi")
	assert isinstance(result, ScoreResult)


def test_identical_text_gets_perfect_score():
	text = "python fastapi postgresql docker"
	result = compute_score(text, text)
	assert result.score == pytest.approx(100.0)
	assert result.cosine_raw == pytest.approx(1.0)
	assert result.label == "Excellent Match"


def test_empty_resume_returns_zero_poor_match():
	result = compute_score("", "python fastapi")
	assert result.score == 0.0
	assert result.cosine_raw == 0.0
	assert result.label == "Poor Match"
	assert result.resume_word_count == 0


def test_empty_jd_returns_zero_poor_match():
	result = compute_score("python fastapi", "")
	assert result.score == 0.0
	assert result.cosine_raw == 0.0
	assert result.label == "Poor Match"
	assert result.jd_word_count == 0


def test_score_always_between_zero_and_hundred():
	result = compute_score("python", "java")
	assert 0.0 <= result.score <= 100.0
	assert 0.0 <= result.cosine_raw <= 1.0


def test_unrelated_texts_score_lower_than_related_texts():
	related = compute_score("python fastapi docker", "python fastapi")
	unrelated = compute_score("graphic design photoshop", "python fastapi")
	assert related.score > unrelated.score


def test_get_missing_skills_returns_set_difference():
	resume_skills = {"python", "fastapi", "git"}
	jd_skills = {"python", "fastapi", "docker", "postgresql"}
	assert get_missing_skills(resume_skills, jd_skills) == {"docker", "postgresql"}


def test_rank_resumes_orders_by_score_descending():
	resumes = [
		("strong", "python fastapi docker postgresql git"),
		("medium", "python django sql"),
		("weak", "illustrator figma branding"),
	]
	jd = "python fastapi docker postgresql"

	ranked = rank_resumes(resumes, jd)

	assert len(ranked) == 3
	assert ranked[0]["score"] >= ranked[1]["score"] >= ranked[2]["score"]
	assert {r["candidate"] for r in ranked} == {"strong", "medium", "weak"}


def test_rank_resumes_empty_input_returns_empty_list():
	assert rank_resumes([], "python fastapi") == []
