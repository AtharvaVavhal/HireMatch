"""
tests/test_preprocessor.py
---------------------------
Unit tests for core/preprocessor.py

Run from project root (venv active):
    pytest tests/test_preprocessor.py -v
    pytest tests/test_preprocessor.py -v --cov=core.preprocessor

Test strategy:
  - One test class per public function
  - Cover happy path, edge cases, and empty/None input
  - No mocking needed — all functions are pure transformations
"""

import pytest

from core.preprocessor import (
    collapse_whitespace,
    lemmatize,
    preprocess,
    preprocess_batch,
    rejoin,
    remove_emails,
    remove_punctuation,
    remove_stopwords,
    remove_urls,
    to_lowercase,
    tokenize,
)


# ===========================================================================
# TestToLowercase
# ===========================================================================

class TestToLowercase:

    def test_converts_uppercase(self):
        assert to_lowercase("PYTHON DEVELOPER") == "python developer"

    def test_converts_mixed_case(self):
        assert to_lowercase("Flask REST API") == "flask rest api"

    def test_already_lowercase_unchanged(self):
        assert to_lowercase("python") == "python"

    def test_empty_string(self):
        assert to_lowercase("") == ""

    def test_digits_unchanged(self):
        assert to_lowercase("Python3 v2.0") == "python3 v2.0"


# ===========================================================================
# TestRemoveUrls
# ===========================================================================

class TestRemoveUrls:

    def test_removes_https_url(self):
        result = remove_urls("See https://github.com/user/repo for code")
        assert "https" not in result
        assert "github" not in result

    def test_removes_http_url(self):
        result = remove_urls("Visit http://portfolio.com today")
        assert "http" not in result

    def test_removes_www_url(self):
        result = remove_urls("Check www.linkedin.com/in/john")
        assert "www" not in result

    def test_preserves_non_url_text(self):
        result = remove_urls("Python developer with Flask experience")
        assert "Python developer with Flask experience" == result

    def test_empty_string(self):
        assert remove_urls("") == ""

    def test_multiple_urls_removed(self):
        result = remove_urls("http://a.com and https://b.com")
        assert "http" not in result
        assert "https" not in result


# ===========================================================================
# TestRemoveEmails
# ===========================================================================

class TestRemoveEmails:

    def test_removes_standard_email(self):
        result = remove_emails("Contact john.doe@gmail.com for details")
        assert "@" not in result
        assert "gmail" not in result

    def test_preserves_surrounding_text(self):
        result = remove_emails("Email me@test.com please")
        assert "Email" in result
        assert "please" in result

    def test_no_email_unchanged(self):
        text = "Python developer with five years experience"
        assert remove_emails(text) == text

    def test_empty_string(self):
        assert remove_emails("") == ""


# ===========================================================================
# TestRemovePunctuation
# ===========================================================================

class TestRemovePunctuation:

    def test_removes_comma(self):
        assert "," not in remove_punctuation("Python, Flask, Django")

    def test_removes_period(self):
        assert "." not in remove_punctuation("B.Sc. in Computer Science.")

    def test_removes_special_chars(self):
        result = remove_punctuation("C++ / REST-API & Node.js!")
        for char in ["+", "/", "-", "&", ".", "!"]:
            assert char not in result

    def test_keeps_letters(self):
        result = remove_punctuation("Hello, World!")
        assert "Hello" in result
        assert "World" in result

    def test_keeps_digits(self):
        result = remove_punctuation("5 years experience")
        assert "5" in result

    def test_empty_string(self):
        assert remove_punctuation("") == ""


# ===========================================================================
# TestCollapseWhitespace
# ===========================================================================

class TestCollapseWhitespace:

    def test_collapses_double_spaces(self):
        assert collapse_whitespace("python  developer") == "python developer"

    def test_collapses_newlines(self):
        assert collapse_whitespace("python\n\ndeveloper") == "python developer"

    def test_collapses_tabs(self):
        assert collapse_whitespace("python\tdeveloper") == "python developer"

    def test_strips_leading_trailing(self):
        assert collapse_whitespace("  python  ") == "python"

    def test_empty_string(self):
        assert collapse_whitespace("") == ""

    def test_already_clean(self):
        assert collapse_whitespace("python developer") == "python developer"


# ===========================================================================
# TestTokenize
# ===========================================================================

class TestTokenize:

    def test_returns_list(self):
        assert isinstance(tokenize("python developer"), list)

    def test_splits_words(self):
        result = tokenize("python developer flask")
        assert "python" in result
        assert "developer" in result
        assert "flask" in result

    def test_empty_string_returns_empty_list(self):
        assert tokenize("") == []

    def test_single_word(self):
        assert tokenize("python") == ["python"]

    def test_token_count(self):
        result = tokenize("one two three four five")
        assert len(result) == 5


# ===========================================================================
# TestRemoveStopwords
# ===========================================================================

class TestRemoveStopwords:

    def test_removes_common_stopwords(self):
        tokens = ["i", "am", "a", "python", "developer"]
        result = remove_stopwords(tokens)
        assert "i" not in result
        assert "am" not in result
        assert "a" not in result

    def test_keeps_meaningful_words(self):
        tokens = ["python", "developer", "flask", "experience"]
        result = remove_stopwords(tokens)
        assert "python" in result
        assert "developer" in result
        assert "flask" in result

    def test_removes_non_alpha_tokens(self):
        # Digits and punctuation tokens should be filtered out
        tokens = ["python", "5", "years", "2023"]
        result = remove_stopwords(tokens)
        assert "5" not in result
        assert "2023" not in result

    def test_empty_list(self):
        assert remove_stopwords([]) == []

    def test_all_stopwords_returns_empty(self):
        tokens = ["the", "is", "at", "which", "on"]
        assert remove_stopwords(tokens) == []

    def test_returns_list(self):
        assert isinstance(remove_stopwords(["python"]), list)


# ===========================================================================
# TestLemmatize
# ===========================================================================

class TestLemmatize:

    def test_returns_list(self):
        assert isinstance(lemmatize(["running"]), list)

    def test_plural_to_singular(self):
        result = lemmatize(["libraries", "skills", "years"])
        assert "library" in result
        assert "skill" in result
        assert "year" in result

    def test_verb_forms(self):
        # WordNetLemmatizer defaults to noun POS, so verb forms are partial
        result = lemmatize(["managed", "developed", "designed"])
        assert isinstance(result, list)
        assert len(result) == 3

    def test_already_base_form_unchanged(self):
        result = lemmatize(["python", "flask", "data"])
        assert result == ["python", "flask", "data"]

    def test_empty_list(self):
        assert lemmatize([]) == []

    def test_output_length_matches_input(self):
        tokens = ["running", "libraries", "managing"]
        assert len(lemmatize(tokens)) == len(tokens)


# ===========================================================================
# TestRejoin
# ===========================================================================

class TestRejoin:

    def test_joins_with_spaces(self):
        assert rejoin(["python", "developer"]) == "python developer"

    def test_single_token(self):
        assert rejoin(["python"]) == "python"

    def test_empty_list(self):
        assert rejoin([]) == ""

    def test_returns_string(self):
        assert isinstance(rejoin(["a", "b"]), str)


# ===========================================================================
# TestPreprocess (full pipeline)
# ===========================================================================

class TestPreprocess:

    def test_returns_string(self):
        assert isinstance(preprocess("I am a Python developer"), str)

    def test_output_is_lowercase(self):
        result = preprocess("I am a PYTHON DEVELOPER")
        assert result == result.lower()

    def test_stopwords_removed(self):
        result = preprocess("I am a Python developer with experience")
        for stopword in ["i", "am", "a", "with"]:
            # stopwords should not appear as standalone tokens
            assert stopword not in result.split()

    def test_urls_removed(self):
        result = preprocess("Visit https://github.com/user for my projects")
        assert "https" not in result
        assert "github" not in result

    def test_emails_removed(self):
        result = preprocess("Email me at john@example.com for contact")
        assert "@" not in result

    def test_punctuation_removed(self):
        result = preprocess("Python, Flask & REST-APIs!")
        for char in [",", "&", "-", "!"]:
            assert char not in result

    def test_empty_string_returns_empty(self):
        assert preprocess("") == ""

    def test_none_like_whitespace_returns_empty(self):
        assert preprocess("   ") == ""

    def test_meaningful_words_preserved(self):
        result = preprocess("Experienced Python developer with Flask skills")
        assert "python" in result
        assert "flask" in result
        assert "skill" in result  # lemmatized from "skills"

    def test_real_resume_snippet(self):
        snippet = """
        John Doe | john.doe@gmail.com | https://linkedin.com/in/johndoe
        Python Developer with 5+ years of experience in Flask, REST APIs,
        and machine learning. Managed cross-functional teams of 10+ engineers.
        """
        result = preprocess(snippet)

        # PII removed
        assert "@" not in result
        assert "linkedin" not in result

        # Key skills present
        assert "python" in result
        assert "flask" in result

        # Stopwords gone
        for word in ["with", "of", "and", "in"]:
            assert word not in result.split()

        # Result is a non-empty string
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_has_no_extra_spaces(self):
        result = preprocess("Python   developer    with   experience")
        assert "  " not in result

    def test_digits_only_string(self):
        # All tokens are non-alpha → should return empty after stopword filter
        result = preprocess("123 456 789")
        assert result == ""

    def test_single_meaningful_word(self):
        result = preprocess("Python")
        assert result == "python"


# ===========================================================================
# TestPreprocessBatch
# ===========================================================================

class TestPreprocessBatch:

    def test_returns_list(self):
        assert isinstance(preprocess_batch(["hello world"]), list)

    def test_output_length_matches_input(self):
        texts = ["Python developer", "Flask experience", "Machine learning"]
        assert len(preprocess_batch(texts)) == 3

    def test_each_element_is_string(self):
        results = preprocess_batch(["Python dev", "Flask API"])
        assert all(isinstance(r, str) for r in results)

    def test_empty_list_returns_empty_list(self):
        assert preprocess_batch([]) == []

    def test_processes_each_text_independently(self):
        texts = ["Python developer", "Java engineer"]
        results = preprocess_batch(texts)
        assert "python" in results[0]
        assert "java" in results[1]

    def test_empty_strings_in_batch(self):
        results = preprocess_batch(["", "Python developer", ""])
        assert results[0] == ""
        assert results[2] == ""
        assert "python" in results[1]

    def test_order_preserved(self):
        texts = ["alpha skills", "beta experience", "gamma projects"]
        results = preprocess_batch(texts)
        assert "alpha" in results[0]
        assert "beta" in results[1]
        assert "gamma" in results[2]