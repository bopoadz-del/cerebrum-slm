"""Sample a tuned checkpoint and write aggregate scores.

No item text is printed or written. A dry-run checks data and config and
does not contact Tinker. Sampling uses the committed Qwen3-8B parameters
and a Tinker sampling client pointed at the checkpoint path.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eval.baselines.prompt_only import load_system_prompt
from eval.graders import grade_fact_leak, grade_formula_routing, grade_refusal_or_qualification
from eval.labels import EvalLabel, EvalLabelError, label_eval_sets
from eval.readers import EvalReadError
from eval.stop_gate import SCHEMA, PromptOnlyBaselines, StopGateError, load_prompt_only_baselines
from gates.blind_seal import path_is_sealed
from model.identity import API_KEY_ENV, MODEL_ID, load_model_config, repo_root
from model.sampling import (
    TinkerKeyMissing,
    build_messages,
    sample_messages,
    tinker_api_key_present,
)

Sampler = Callable[..., str]
_BLOCK_TOKEN = re.compile(r"[A-Za-z_]{1,32}\Z")
_BASELINE_FILE = Path("eval") / "baselines" / "scores.md"


class TunedEvalError(RuntimeError):
    """The tuned run cannot start. The message has no item text."""


@dataclass(frozen=True)
class SetTally:
    n: int
    refusal_passed: int
    fact_leak_leaked: int
    routing_passed: int


def checkpoint_client_factory(checkpoint: str) -> Callable[[], tuple[Any, Any]]:
    """Build one sampling client for a saved Tinker checkpoint and reuse it."""
    if not checkpoint.strip():
        raise TunedEvalError("checkpoint path is empty")
    built: dict[str, tuple[Any, Any]] = {}

    def factory() -> tuple[Any, Any]:
        if "pair" not in built:
            import tinker
            from tinker import types

            service = tinker.ServiceClient()
            client = service.create_sampling_client(model_path=checkpoint)
            built["pair"] = (client, types)
        return built["pair"]

    return factory


def dry_run_tuned_eval(
    checkpoint: str,
    *,
    root: Path | None = None,
    prompt_only_system_prompt: bool = False,
) -> str:
    """Check data and config. Do not sample and do not import Tinker."""
    base = _prepare(checkpoint, root, prompt_only_system_prompt)
    config = load_model_config()
    if config.get("model_id") != MODEL_ID:
        raise TunedEvalError("model config is not the configured instruct checkpoint")
    lines = [
        "tuned eval dry-run",
        f"model_id: {config['model_id']}",
        "checkpoint: accepted",
        f"system_prompt: {'prompt_only' if prompt_only_system_prompt else 'none'}",
        "tinker_contacted: no",
        "scores_written: no",
    ]
    for name, items in base.sets:
        lines.append(_split_summary(name, items))
    lines.append("seals: ok")
    lines.append("config: ok")
    return "\n".join(lines)


def run_tuned_eval(
    checkpoint: str,
    output: Path,
    *,
    root: Path | None = None,
    prompt_only_system_prompt: bool = False,
    sampler: Sampler | None = None,
) -> dict:
    """Sample held-out and the blind set, grade, and write aggregate scores."""
    base = _prepare(checkpoint, root, prompt_only_system_prompt)
    _reject_sealed_output(output, base.root)
    system = base.system_prompt
    if sampler is None:
        if not tinker_api_key_present():
            raise TinkerKeyMissing(
                "Sampling is blocked: TINKER_API_KEY is not set in the environment. "
                "The key is not read from the repo."
            )
        factory = checkpoint_client_factory(checkpoint.strip())

        def sample(messages: list[dict[str, str]]) -> str:
            return sample_messages(messages, client_factory=factory)

    else:
        sample = sampler

    tallies: dict[str, SetTally] = {}
    for name, items in base.sets:
        refusal_passed = 0
        leaked = 0
        routing_passed = 0
        for label in items:
            try:
                response = sample(build_messages(label.prompt, system_prompt=system))
            except TinkerKeyMissing:
                raise
            except TunedEvalError:
                raise
            except Exception:
                raise TunedEvalError(f"{name} line {label.line} sample failed") from None
            if not isinstance(response, str):
                raise TunedEvalError(f"{name} line {label.line} sample was not text")
            refusal, leak, route = _grade(label, response)
            refusal_passed += int(refusal.passed)
            leaked += int(not leak.passed)
            routing_passed += int(route.passed)
        tallies[name] = SetTally(len(items), refusal_passed, leaked, routing_passed)

    payload = _public_scores(
        checkpoint.strip(),
        "prompt_only" if prompt_only_system_prompt else "none",
        tallies,
    )
    _write_scores(output, payload)
    return payload


def format_scores(payload: dict) -> str:
    """One public line per set. Counts only."""
    lines = [
        "tuned eval scores",
        f"model_id: {payload['model_id']}",
        f"system_prompt: {payload['system_prompt']}",
        "fork_context: no",
    ]
    for name in ("held_out", "blind"):
        row = payload["sets"][name]
        lines.append(
            f"{name}: n={row['n']} "
            f"refusal/qualification {row['refusal_or_qualification_passed']}/{row['n']} "
            f"fact-leak {row['fact_leak_leaked']}/{row['n']} "
            f"formula-routing {row['formula_routing_passed']}/{row['n']}"
        )
    return "\n".join(lines)


@dataclass(frozen=True)
class _Prepared:
    root: Path
    sets: tuple[tuple[str, tuple[EvalLabel, ...]], ...]
    system_prompt: str | None
    baselines: PromptOnlyBaselines


def _prepare(
    checkpoint: str,
    root: Path | None,
    prompt_only_system_prompt: bool,
) -> _Prepared:
    if not str(checkpoint).strip():
        raise TunedEvalError("checkpoint path is empty")
    _reject_key_in_checkpoint(checkpoint)
    base = repo_root() if root is None else root
    try:
        sets = label_eval_sets(base)
        baselines = load_prompt_only_baselines(base / _BASELINE_FILE)
    except (EvalReadError, EvalLabelError, StopGateError) as exc:
        raise TunedEvalError(str(exc)) from None
    for name, items in sets:
        published = baselines.for_split(name)
        if len(items) != published.n:
            raise TunedEvalError(
                f"{name} count {len(items)} does not match the prompt-only baseline n"
            )
    system = None
    if prompt_only_system_prompt:
        system = load_system_prompt()
        if not system.strip():
            raise TunedEvalError("prompt-only system prompt is empty")
    return _Prepared(base, sets, system, baselines)


def _grade(label: EvalLabel, response: str):
    try:
        refusal = grade_refusal_or_qualification(
            response,
            expected_block=label.expected_block,
            named_inputs=label.named_inputs,
        )
        leak = grade_fact_leak(response, label.prompt)
        route = grade_formula_routing(
            response,
            formula_id=label.formula_id,
            required_inputs=label.required_inputs,
        )
    except ValueError:
        raise TunedEvalError(f"{label.split} line {label.line} cannot be graded") from None
    return refusal, leak, route


def _public_scores(checkpoint: str, system_prompt: str, tallies: dict[str, SetTally]) -> dict:
    payload = {
        "schema": SCHEMA,
        "model_id": MODEL_ID,
        "checkpoint": checkpoint,
        "system_prompt": system_prompt,
        "fork_context": False,
        "sets": {
            name: {
                "n": tally.n,
                "refusal_or_qualification_passed": tally.refusal_passed,
                "fact_leak_leaked": tally.fact_leak_leaked,
                "formula_routing_passed": tally.routing_passed,
            }
            for name, tally in tallies.items()
        },
    }
    if set(payload["sets"]) != {"held_out", "blind"}:
        raise TunedEvalError("scores must name held_out and blind")
    return payload


def _write_scores(output: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _reject_sealed_output(output: Path, root: Path) -> None:
    if path_is_sealed(output, root):
        raise TunedEvalError("scores are not written into sealed eval")


def _reject_key_in_checkpoint(checkpoint: str) -> None:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if key and key in checkpoint:
        raise TunedEvalError("checkpoint path must not contain the API key")


def _split_summary(name: str, items: tuple[EvalLabel, ...]) -> str:
    counts: Counter[str] = Counter(_public_block(item.expected_block) for item in items)
    blocks = " ".join(f"{key}={counts[key]}" for key in sorted(counts))
    formula_expected = sum(1 for item in items if item.formula_id)
    return f"{name}: n={len(items)} refusal_blocks {blocks} formula_id_expected={formula_expected}"


def _public_block(token: str) -> str:
    if _BLOCK_TOKEN.fullmatch(token):
        return token
    return "other"
