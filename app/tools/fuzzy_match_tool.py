from rapidfuzz import fuzz


def similarity(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(a.strip(), b.strip()) / 100.0


def is_match(a: str, b: str, threshold: float = 0.85) -> bool:
    return similarity(a, b) >= threshold
