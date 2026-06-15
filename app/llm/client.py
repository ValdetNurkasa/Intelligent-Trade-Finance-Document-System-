import os
import anthropic
from app.config import settings


def create_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def complete(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    if not settings.USE_LLM:
        return ""
    client = create_client()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
