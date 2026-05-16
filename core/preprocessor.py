"""
core/preprocessor.py
--------------------
NLP Text Preprocessing Pipeline for HireMatch.
"""

import logging
import re
from typing import Optional

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

logger = logging.getLogger(__name__)

# Download NLTK data silently
for _pkg in ["punkt_tab", "stopwords", "wordnet", "omw-1.4"]:
    nltk.download(_pkg, quiet=True)

# Module-level singletons
_STOPWORDS: set[str] = set(stopwords.words("english"))
_LEMMATIZER: WordNetLemmatizer = WordNetLemmatizer()

# Pre-compiled regex
_URL_PATTERN   = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
_PUNCT_PATTERN = re.compile(r"[^\w\s]")
_SPACE_PATTERN = re.compile(r"\s+")


def to_lowercase(text: str) -> str:
    return text.lower()


def remove_urls(text: str) -> str:
    return _URL_PATTERN.sub(" ", text)


def remove_emails(text: str) -> str:
    return _EMAIL_PATTERN.sub(" ", text)


def remove_punctuation(text: str) -> str:
    return _PUNCT_PATTERN.sub(" ", text)


def collapse_whitespace(text: str) -> str:
    return _SPACE_PATTERN.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    return word_tokenize(text)


def remove_stopwords(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in _STOPWORDS and t.isalpha()]


def lemmatize(tokens: list[str]) -> list[str]:
    return [_LEMMATIZER.lemmatize(t) for t in tokens]


def rejoin(tokens: list[str]) -> str:
    return " ".join(tokens)


def preprocess(text: str) -> str:
    if not text or not text.strip():
        logger.warning("preprocess() received empty or None input.")
        return ""
    text = collapse_whitespace(text)
    text = to_lowercase(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = remove_punctuation(text)
    text = collapse_whitespace(text)
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = lemmatize(tokens)
    return rejoin(tokens)


def preprocess_batch(texts: list[str]) -> list[str]:
    if not texts:
        return []
    return [preprocess(t) for t in texts]
