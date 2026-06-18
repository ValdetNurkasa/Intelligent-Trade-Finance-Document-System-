"""P2-10: LLM-based semantic judge for ambiguous goods descriptions via OpenAI (gated by USE_LLM).

Compares two goods-description strings and flags potentially ambiguous or
inconsistent pairs for human review. NEVER sets a compliance verdict — it
only returns a flag and a reason string. The matching decision remains
100% rule-based in matching_rules.py.
"""
from __future__ import annotations

from app.config import settings

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
            "reason": str,            # explanation or status message
        }

    Always returns ambiguous=False when USE_LLM=False.
    """
    if not settings.USE_LLM:
        return {
            "ambiguous": False,
            "flag_for_review": False,
            "reason": "LLM disabled (USE_LLM=false)",
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=100,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a trade finance compliance reviewer. "
                        "You compare goods descriptions across trade documents. "
                        "You ONLY flag ambiguity — you never decide on compliance."
                    ),
                },
                {
                    "role": "user",
                    "content": _PROMPT_TMPL.format(
                        desc_a=desc_a[:500],
                        desc_b=desc_b[:500],
                    ),
                },
            ],
        )
        text = response.choices[0].message.content.strip()
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
