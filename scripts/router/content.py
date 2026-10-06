"""Content fields the labeller may read. Names, ids, and Fork types are not content."""

from __future__ import annotations

# Excerpt columns, first match wins. `text` is accepted only when no excerpt
# column is present, because the raw pool's text column repeated the excerpt.
_EXCERPT_KEYS = ("excerpt", "first_512_tokens", "first_512")
_TEXT_KEY = "text"


def content_text(row: dict) -> str | None:
    """Return document text, or None when the row has no content to label."""
    for key in _EXCERPT_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    if any(key in row for key in _EXCERPT_KEYS):
        return None
    value = row.get(_TEXT_KEY)
    if isinstance(value, str) and value.strip():
        return value
    return None


def model_user_text(row: dict) -> str | None:
    """The only string placed in the teacher user message."""
    return content_text(row)
