"""P2-07: LLM-based low-confidence field retry via OpenAI (gated by USE_LLM).

Only invoked for fields where low_confidence=True.
Result is marked llm_derived=True so auditors can distinguish it from
regex-extracted values. No-op when USE_LLM=false (the default).
"""
from __future__ import annotations

from app.config import settings
from app.schemas.extraction import ExtractedField


def retry_field(field_name: str, page_text: str, current: ExtractedField) -> ExtractedField:
    """Retry extracting field_name via OpenAI when the regex result is low-confidence.

    Returns the original field unchanged when:
    - USE_LLM is False (default)
    - The field is not low_confidence
    - The LLM returns an empty string
    - Any exception occurs
    """
    if not settings.USE_LLM or not current.low_confidence:
        return current

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=80,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a trade finance document parser. "
                        "Extract exactly one field value from the given document text. "
                        "Return only the raw extracted value — no explanation, no punctuation around it."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Field to extract: {field_name}\n\n"
                        f"Document text (first 2000 chars):\n{page_text[:2000]}"
                    ),
                },
            ],
        )
        value = response.choices[0].message.content.strip()
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
