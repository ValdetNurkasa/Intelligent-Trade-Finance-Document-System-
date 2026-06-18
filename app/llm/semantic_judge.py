"""P2-10: LLM-based semantic judge for ambiguous goods descriptions (gated by USE_LLM).

Compares two goods-description strings and flags potentially ambiguous or
inconsistent pairs for human review. NEVER sets a compliance verdict — it
only returns a flag and a reason string. The matching decision remains
100% rule-based in matching_rules.py.
"""
from __future__ import annotations

from app.config import settings
from app.llm.client import complete

_SYSTEM = (
    "You are a trade finance compliance reviewer. "
    "You compare goods descriptions across trade documents. "
    "You ONLY flag ambiguity — you never decide on compliance."
)

_PROMPT_TMPL = """\
Compare the two goods descriptions below and determine whether they are \
semantically equivalent or potentially referring to different goods.

Description A: {desc_a}
Description B: {desc_b}

Respond in exactly this format (two lines, nothing else):
AMBIGUOUS: yes/no
REASON: <one sentence, or 'none' if not ambiguous>"""


def judge_descriptions(desc_a: str, desc_b: str) -> dict:
    """Flag ambiguous goods-description pairs for human review.

    Returns:
        {
            "ambiguous": bool,        # True if descriptions may differ in meaning
            "flag_for_review": bool,  # Same as ambiguous — caller decides action
            "reason": str,            # LLM explanation or status message
        }

    Always returns ambiguous=False when USE_LLM=False.
    """
    if not settings.USE_LLM:
        return {
            "ambiguous": False,
            "flag_for_review": False,
            "reason": "LLM disabled (USE_LLM=false)",
        }

    prompt = _PROMPT_TMPL.format(desc_a=desc_a[:500], desc_b=desc_b[:500])
    try:
        text = complete(prompt, system=_SYSTEM, max_tokens=100).strip()
    except Exception as exc:
        return {"ambiguous": False, "flag_for_review": False, "reason": f"LLM call failed: {exc}"}

    ambiguous = False
    reason = ""
    for line in text.splitlines():
        upper = line.upper()
        if upper.startswith("AMBIGUOUS:"):
            ambiguous = "YES" in upper
        elif upper.startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()

    return {
        "ambiguous": ambiguous,
        "flag_for_review": ambiguous,
        "reason": reason if reason.lower() != "none" else "",
    }
