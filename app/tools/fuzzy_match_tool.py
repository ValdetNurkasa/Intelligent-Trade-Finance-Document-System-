from __future__ import annotations
import re
from rapidfuzz import fuzz

THRESHOLD = 0.85
_PUNCT = re.compile(r"[^\w\s]")


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return " ".join(_PUNCT.sub(" ", text.lower()).split())


def similarity(a: str, b: str) -> float:
    """Token-sort ratio 0..1."""
    return fuzz.token_sort_ratio(a.strip(), b.strip()) / 100.0


def is_match(a: str, b: str, threshold: float = THRESHOLD) -> bool:
    return similarity(a, b) >= threshold


def compare(a: str, b: str, threshold: float = THRESHOLD) -> dict:
    """
    Compare two string values.
    Returns {"match": bool, "score": float, "notes": str | None}.
    """
    if not a or not b:
        return {"match": False, "score": 0.0, "notes": "one or both values missing"}
    score = similarity(normalize(a), normalize(b))
    match = score >= threshold
    return {
        "match": match,
        "score": round(score, 4),
        "notes": None if match else f"score {score:.2f} below threshold {threshold}",
    }
