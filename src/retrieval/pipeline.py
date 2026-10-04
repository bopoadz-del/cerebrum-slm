"""Cite source ids from context The Fork attached, and call formulas.

The model does not choose retrieval, the grounding verdict, or escalation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from src.decoding.constrained import CitationToken, decode
from src.policy.escalation import decide
from src.retrieval.fork import attach_context, call_formula
from src.retrieval.grounding import blocked, grounding_gate


@dataclass(frozen=True)
class TurnResult:
    answer: str | None
    citations: tuple[str, ...]
    reason: str | None
    grounding_status: str
    escalated: bool
    escalation_reasons: tuple[str, ...]
    formula_called: str | None


def answer(
    query: str,
    project_id: str,
    proposed_text: str,
    *,
    citations: Sequence[str] = (),
    clauses: Sequence[str] = (),
    sources: Sequence[str] = (),
    formula_id: str | None = None,
    formula_params: dict[str, Any] | None = None,
    confidence: float,
    task_type: str,
    k: int | None = None,
    intent: str | None = None,
) -> TurnResult:
    """Accept a proposed answer only with context-backed citations and figures."""

    context = attach_context(query, project_id, k=k, intent=intent)
    formula_result: Any = None
    formula_called: str | None = None
    formula_reason: str | None = None
    if formula_id and formula_id in context.allowed_ids:
        try:
            formula_result = call_formula(formula_id, formula_params)
            formula_called = formula_id
        except Exception as exc:
            formula_reason = f"formula call failed: {type(exc).__name__}"

    tokens = _tokens(citations, clauses, sources, formula_called)

    policy = decide(confidence, task_type, context.present)
    if formula_reason is not None:
        verdict = blocked(formula_reason)
        return _finish(
            answer_text=None,
            citations=(),
            reason=verdict.reason,
            grounding_status=verdict.status,
            policy_escalate=policy.escalate,
            policy_reasons=policy.reasons,
            formula_called=None,
        )

    decoded = decode(proposed_text, tokens, context.allowed_ids)
    if decoded.refused:
        return _finish(
            answer_text=None,
            citations=(),
            reason=decoded.reason,
            grounding_status="BLOCKED",
            policy_escalate=policy.escalate,
            policy_reasons=policy.reasons,
            formula_called=formula_called,
        )

    verdict = grounding_gate(
        decoded.text,
        context,
        formula_result,
        cited_source_ids=decoded.emitted,
    )
    if verdict.blocked:
        return _finish(
            answer_text=None,
            citations=(),
            reason=verdict.reason,
            grounding_status=verdict.status,
            policy_escalate=policy.escalate,
            policy_reasons=policy.reasons,
            formula_called=formula_called,
        )

    return _finish(
        answer_text=verdict.answer,
        citations=decoded.emitted,
        reason=None,
        grounding_status=verdict.status,
        policy_escalate=policy.escalate,
        policy_reasons=policy.reasons,
        formula_called=formula_called,
    )


def _tokens(
    citations: Sequence[str],
    clauses: Sequence[str],
    sources: Sequence[str],
    formula_called: str | None,
) -> tuple[CitationToken, ...]:
    raw: list[CitationToken] = []
    raw.extend(CitationToken("citation", item) for item in citations)
    raw.extend(CitationToken("clause", item) for item in clauses)
    raw.extend(CitationToken("source", item) for item in sources)
    if formula_called is not None:
        raw.append(CitationToken("source", formula_called))
    seen: set[tuple[str, str]] = set()
    unique: list[CitationToken] = []
    for token in raw:
        key = (token.kind, token.identifier)
        if key in seen:
            continue
        seen.add(key)
        unique.append(token)
    return tuple(unique)


def _finish(
    *,
    answer_text: str | None,
    citations: tuple[str, ...],
    reason: str | None,
    grounding_status: str,
    policy_escalate: bool,
    policy_reasons: tuple[str, ...],
    formula_called: str | None,
) -> TurnResult:
    return TurnResult(
        answer=answer_text,
        citations=citations if answer_text is not None else (),
        reason=reason,
        grounding_status=grounding_status,
        escalated=policy_escalate,
        escalation_reasons=policy_reasons,
        formula_called=formula_called,
    )
