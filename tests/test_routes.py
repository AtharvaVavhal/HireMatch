from io import BytesIO

from core.parser import ParseResult
from core.scorer import ScoreResult


def test_index_route_renders(client):
	response = client.get("/")
	assert response.status_code == 200
	assert b"Resume Intelligence Engine" in response.data


def test_analyze_rejects_missing_resume(client):
	response = client.post("/analyze", data={"jd_text": "python role"}, follow_redirects=True)
	assert response.status_code == 200
	assert b"No resume file uploaded" in response.data


def test_analyze_rejects_non_pdf_file(client):
	data = {
		"resume": (BytesIO(b"not-a-pdf"), "resume.txt"),
		"jd_text": "python role",
	}
	response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
	assert response.status_code == 200
	assert b"Only PDF files are allowed" in response.data


def test_analyze_handles_corrupted_pdf(client, monkeypatch):
	def fake_parse_pdf(_):
		return ParseResult(
			file_path="/tmp/broken.pdf",
			text="",
			page_count=0,
			success=False,
			error="corrupted pdf",
		)

	monkeypatch.setattr("app.routes.parse_pdf", fake_parse_pdf)

	data = {
		"resume": (BytesIO(b"%PDF-1.4 broken"), "broken.pdf"),
		"jd_text": "python role",
	}
	response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
	assert response.status_code == 200
	assert b"Could not read PDF" in response.data


def test_analyze_success_renders_results(client, monkeypatch):
	monkeypatch.setattr(
		"app.routes.parse_pdf",
		lambda _: ParseResult(file_path="/tmp/resume.pdf", text="python fastapi", page_count=1, success=True),
	)
	monkeypatch.setattr("app.routes.preprocess", lambda text: text)
	monkeypatch.setattr(
		"app.routes.compute_score",
		lambda _resume, _jd: ScoreResult(
			score=88.0,
			label="Excellent Match",
			cosine_raw=0.88,
			resume_word_count=2,
			jd_word_count=2,
		),
	)
	monkeypatch.setattr("app.routes.extract_skills", lambda _text: {"all_skills": ["python", "fastapi"]})

	data = {
		"resume": (BytesIO(b"%PDF-1.4"), "resume.pdf"),
		"jd_text": "python fastapi",
	}
	response = client.post("/analyze", data=data, content_type="multipart/form-data", follow_redirects=True)
	assert response.status_code == 200
	assert b"Match" in response.data
	assert b"Excellent Match" in response.data


def test_rank_rejects_empty_input(client):
	response = client.post("/rank", data={"jd_text": "python role"}, follow_redirects=True)
	assert response.status_code == 200
	assert b"No resume files uploaded" in response.data


def test_rank_success_renders_table(client, monkeypatch, tmp_path):
	monkeypatch.setattr(
		"app.routes.parse_pdf",
		lambda _: ParseResult(file_path="/tmp/resume.pdf", text="python fastapi", page_count=1, success=True),
	)
	monkeypatch.setattr(
		"app.routes.rank_resumes_from_texts",
		lambda _resumes, _jd: [
			{
				"rank": 1,
				"candidate": "alice",
				"score": 91.2,
				"label": "Excellent Match",
				"matched_skills": ["python"],
				"missing_skills": ["docker"],
			}
		],
	)
	monkeypatch.setattr("app.routes.build_dataframe", lambda _ranked: object())
	monkeypatch.setattr("app.routes.export_csv", lambda _df, _out: str(tmp_path / "ranked.csv"))

	data = {
		"resumes[]": [(BytesIO(b"%PDF-1.4"), "resume1.pdf")],
		"jd_text": "python fastapi",
	}
	response = client.post("/rank", data=data, content_type="multipart/form-data", follow_redirects=True)
	assert response.status_code == 200
	assert b"Candidate" in response.data
	assert b"alice" in response.data
