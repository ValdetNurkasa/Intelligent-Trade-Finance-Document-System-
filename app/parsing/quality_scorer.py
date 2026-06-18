from __future__ import annotations

_COVERAGE_FULL = 200   # chars per page that signals clearly born-digital


def score_page(text: str) -> float:
    """
    Score one page's text quality 0..1.
    1.0 = rich born-digital text; 0.0 = blank or mostly garbage.
    """
    stripped = (text or "").strip()
    if not stripped:
        return 0.0
    coverage = min(1.0, len(stripped) / _COVERAGE_FULL)
    alnum = sum(1 for c in stripped if c.isalnum() or c.isspace())
    legibility = alnum / len(stripped)
    return (coverage + legibility) / 2.0


def score_document(pages: list[dict], cutoff: float = 0.4) -> tuple[str, float]:
    """
    Decide 'born_digital' or 'scan' for a whole document.
    Returns (decision, avg_score).
    """
    if not pages:
        return "scan", 0.0
    scores = [score_page(p.get("text", "")) for p in pages]
    avg = sum(scores) / len(scores)
    return ("born_digital" if avg >= cutoff else "scan"), round(avg, 4)
