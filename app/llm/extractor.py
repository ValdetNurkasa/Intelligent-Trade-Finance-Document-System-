"""P2-07: LLM-based low-confidence field retry (gated by USE_LLM).

Only invoked for fields where low_confidence=True.
Result is marked llm_derived=True so auditors can distinguish it from
regex-extracted values. No-op when USE_LLM=false (the default).
"""
from __future__ import annotations

from app.config import settings
from app.llm.client import complete
from app.schemas.extraction import ExtractedField

_SYSTEM = (
    "You are a trade finance document parser. "
    "Extract exactly one field value from the given document text. "
    "Return only the raw extracted value — no explanation, no punctuation around it."
)


def retry_field(field_name: str, page_text: str, current: ExtractedField) -> ExtractedField:
    """Retry extracting field_name via LLM when the regex result is low-confidence.

    Returns the original field unchanged when:
    - USE_LLM is False (default)
    - The field is not low_confidence
    - The LLM returns an empty string
    - Any exception occurs
    """
    if not settings.USE_LLM or not current.low_confidence:
        return current

    prompt = (
        f"Field to extract: {field_name}\n\n"
        f"Document text (first 2000 chars):\n{page_text[:2000]}"
    )
    try:
        value = complete(prompt, system=_SYSTEM, max_tokens=80).strip()
    except Exception:
        return current

    if not value:
        return current

    return ExtractedField(
        field_name=field_name,
        value=value,
        confidence=0.75,
        page=current.page,
        bounding_box=current.bounding_box,
        low_confidence=False,
        manual_review_required=False,
        llm_derived=True,
    )
