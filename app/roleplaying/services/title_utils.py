"""Utility helpers for normalizing scenario titles."""

import re
from typing import Iterable


def compact_title(
    raw_title: str,
    *,
    banned_phrases: Iterable[str],
    fallback: str = "Key Discussion Focus",
    max_length: int = 50
) -> str:
    """
    Remove disallowed phrases from a title and ensure it stays short.

    Args:
        raw_title: Title returned from the LLM (may include roles or be empty).
        banned_phrases: Role names or other tokens that must not appear.
        fallback: Safe default when the cleaned title is empty.
        max_length: Maximum allowed characters.

    Returns:
        Sanitized title limited to max_length characters.
    """
    title = (raw_title or "").strip()

    for phrase in banned_phrases:
        if not phrase:
            continue
        pattern = re.compile(re.escape(phrase), flags=re.IGNORECASE)
        title = pattern.sub("", title)

    title = re.sub(r"\s+", " ", title).strip(" -|,:;")
    if not title:
        title = fallback

    if len(title) > max_length:
        title = title[:max_length].rstrip()

    return title
