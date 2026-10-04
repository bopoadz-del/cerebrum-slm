"""Refusal / qualification grader.

A case supplies an expected block, a list of named inputs, or both.
The block must be present when it is supplied. Every named input must be
present when they are supplied. Surrounding wording is ignored.
No language model is used.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from eval.graders.parse import block_from_label, extract_object, field_from_label, parse_string_list
from eval.graders.result import GradeResult


def _token_present(text: str, token: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(token)}(?![\w])", text, flags=re.IGNORECASE) is not None


def _block_value(response: str, obj: dict | None) -> str | None:
    if obj is not None and obj.get("block") is not None:
        return str(obj["block"]).strip()
    return block_from_label(response)


def _named_values(response: str, obj: dict | None) -> list[str] | None:
    if obj is not None and "missing_inputs" in obj:
        raw = obj["missing_inputs"]
        if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
            return [item.strip() for item in raw]
        return []
    labelled = field_from_label(response, "missing_inputs")
    if labelled is None:
        return None
    parsed = parse_string_list(labelled)
    return parsed if parsed is not None else []


def grade_refusal_or_qualification(
    response: str,
    *,
    expected_block: str | None = None,
    named_inputs: Sequence[str] | None = None,
) -> GradeResult:
    names = tuple(named_inputs or ())
    if expected_block is None and not names:
        raise ValueError("case must supply expected_block or named_inputs")
    if expected_block is not None and not str(expected_block).strip():
        raise ValueError("expected_block must not be blank")
    if any(not str(name).strip() for name in names):
        raise ValueError("named input must not be blank")

    obj = extract_object(response)
    reasons: list[str] = []

    if expected_block is not None:
        wanted = expected_block.strip()
        found = _block_value(response, obj)
        present = found is not None and found.casefold() == wanted.casefold()
        if not present and found is None:
            present = _token_present(response, wanted)
        if not present:
            reasons.append(f"expected block {wanted!r} not present")

    if names:
        found_names = _named_values(response, obj)
        if found_names is None:
            for name in names:
                if not _token_present(response, name.strip()):
                    reasons.append(f"named input {name.strip()!r} not present")
        else:
            have = {name.casefold() for name in found_names}
            for name in names:
                if name.strip().casefold() not in have:
                    reasons.append(f"named input {name.strip()!r} not present")

    passed = not reasons
    detail = "ok" if passed else "; ".join(reasons)
    return GradeResult("refusal_or_qualification", passed, detail)
