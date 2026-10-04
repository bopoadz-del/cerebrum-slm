"""Grounding gate in front of any accepted answer.

An unsupported figure is BLOCKED. The answer is null and the reason is
stated. The verdict is arithmetic over the attached context and formula
return values. No language model is called.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from src.retrieval.context import AttachedContext

LOGGER = logging.getLogger("src.retrieval.grounding")

_SEPARATOR = re.compile(r"(?<=\d),(?=\d)")
_FIGURE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?")


@dataclass(frozen=True)
class GroundingVerdict:
    status: str
    answer: str | None
    reason: str | None

    @property
    def blocked(self) -> bool:
        return self.status == "BLOCKED"


def _scan_text(text: str) -> str:
    return _SEPARATOR.sub("", text or "")


def _canonical(token: str) -> str:
    body = token[1:] if token.startswith("-") else token
    sign = -1.0 if token.startswith("-") else 1.0
    if body.endswith("%"):
        body = body[:-1]
    value = sign * float(body)
    rendered = format(value, ".12f").rstrip("0").rstrip(".")
    if rendered in {"", "-0"}:
        return "0"
    return rendered


def figures_in(text: str) -> tuple[str, ...]:
    """Return figure tokens in first-seen order."""

    found: list[str] = []
    seen: set[str] = set()
    for match in _FIGURE.finditer(_scan_text(text)):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            found.append(token)
    return tuple(found)


def _support_keys(text: str) -> set[str]:
    return {_canonical(token) for token in figures_in(text)}


def _formula_text(formula_result: Any) -> str:
    if formula_result is None:
        return ""
    try:
        return json.dumps(formula_result, default=str, sort_keys=True)
    except TypeError:
        return str(formula_result)


def blocked(reason: str) -> GroundingVerdict:
    """Record a block decided by this gate, with the answer left null."""

    verdict = GroundingVerdict("BLOCKED", None, reason)
    _log(verdict)
    return verdict


def grounding_gate(
    proposed: str | None,
    context: AttachedContext,
    formula_result: Any = None,
    *,
    cited_source_ids: tuple[str, ...] = (),
) -> GroundingVerdict:
    """Accept ``proposed`` only when every figure is supported.

    Support is a figure whose numeric value occurs in the attached context
    text or in the value returned by a formula call. A figure also needs a
    source id that the decoder already allowed.
    """

    if proposed is None:
        verdict = GroundingVerdict("BLOCKED", None, "no answer was proposed")
        _log(verdict)
        return verdict

    supported = _support_keys(context.support_text)
    supported.update(_support_keys(_formula_text(formula_result)))
    unsupported = [
        token for token in figures_in(proposed) if _canonical(token) not in supported
    ]
    if unsupported:
        listed = ", ".join(unsupported)
        verdict = GroundingVerdict(
            "BLOCKED",
            None,
            f"unsupported figure: {listed}",
        )
        _log(verdict)
        return verdict

    if figures_in(proposed) and not cited_source_ids:
        verdict = GroundingVerdict(
            "BLOCKED",
            None,
            "figure requires a source id from the attached context",
        )
        _log(verdict)
        return verdict

    verdict = GroundingVerdict("PASS", proposed, None)
    _log(verdict)
    return verdict


def _log(verdict: GroundingVerdict) -> None:
    LOGGER.info(
        "grounding_verdict status=%s reason=%s",
        verdict.status,
        verdict.reason or "",
    )
