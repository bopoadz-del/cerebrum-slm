"""One output parser for every router model and baseline.

A declared label matches as written. An alias matches the whole string after
whitespace is collapsed, with case ignored. A substring, a plural, or a
near-miss stays unmatched. There is no fuzzy match.
"""

from __future__ import annotations

# One-to-one aliases. The label docs name no further aliases.
_ALIASES = {
    "change order": "VO/CO",
    "variation order": "VO/CO",
    "variation": "VO/CO",
    "co": "VO/CO",
}


def canonical_label(text: str, labels: list[str]) -> str | None:
    """Return a declared label, or None when ``text`` is not one."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return None
    allowed = set(labels)
    if cleaned in allowed:
        return cleaned
    target = _ALIASES.get(cleaned.casefold())
    if target in allowed:
        return target
    return None


def parse_router_output(text: str, labels: list[str]) -> str:
    """Parse one model or baseline string into a declared label or unsure.

    A bare label and a JSON teacher reply share ``canonical_label``. A constant
    baseline emits a canonical label, which this function returns unchanged.
    """
    direct = canonical_label(text, labels)
    if direct is not None:
        return direct
    from router.teacher_label import parse_teacher_response

    return parse_teacher_response(text, labels)["label"]
