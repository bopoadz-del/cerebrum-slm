"""Render the reply a training pair is supervised on.

The tuned model is graded on one JSON object, the reply contract written in
the committed prompt-only system prompt. Run 1 trained on prose replies with
no system prompt, so the weights never saw the graded format. This module
renders each train pair into that contract, deterministically, from the
pair's own labels. No language model is called and no text is invented.

- ``block`` follows the same pair_type rule as the eval labels
  (``eval/labels.py``): refuse, none, or qualify.
- ``formula_id`` is the pair's ``meta.formula_id`` for the formula pair types
  the eval labels route, and empty otherwise.
- ``required_inputs`` are the required input names of that formula in the
  committed formula registry. An id the registry does not carry gets an empty
  list rather than a guess.
- ``missing_inputs`` are those required inputs when the pair asks what must
  be known first (the question supplies none of them), and empty otherwise.
- ``basis`` is ``unspecified``: no train pair establishes a basis.
- ``unsourced_figure`` is ``refused`` for a refuse block and
  ``not_applicable`` otherwise.

The registry is retrieval data. Only formula ids and input names are copied;
input names carry no number, unit, currency, clause, brand, or site.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

from eval.labels import _FORMULA_PAIR_TYPES, _NONE_PAIR_TYPE, _REFUSE_PAIR_TYPES

TARGET_FORMAT = "posture_json_v1"
MISSING_FIRST_PAIR_TYPE = "what_must_be_known_first"
_KEYS = ("basis", "block", "missing_inputs", "formula_id", "required_inputs", "unsourced_figure")


class TargetError(ValueError):
    """A pair cannot be rendered into the reply contract."""


@dataclass(frozen=True)
class PostureTarget:
    block: str
    formula_id: str
    required_inputs: tuple[str, ...]
    missing_inputs: tuple[str, ...]

    def as_object(self) -> dict:
        return {
            "basis": "unspecified",
            "block": self.block,
            "missing_inputs": list(self.missing_inputs),
            "formula_id": self.formula_id,
            "required_inputs": list(self.required_inputs),
            "unsourced_figure": "refused" if self.block == "refuse" else "not_applicable",
        }

    def render(self) -> str:
        return json.dumps(self.as_object(), ensure_ascii=False)


def registry_inputs(registry: Mapping) -> dict[str, tuple[str, ...]]:
    """Formula id -> required input names, in registry order."""
    formulas = registry.get("formulas") if isinstance(registry, Mapping) else None
    if not isinstance(formulas, list):
        raise TargetError("formula registry has no formulas list")
    found: dict[str, tuple[str, ...]] = {}
    for entry in formulas:
        if not isinstance(entry, Mapping):
            continue
        formula_id = entry.get("id")
        definition = entry.get("definition")
        if not isinstance(formula_id, str) or not isinstance(definition, Mapping):
            continue
        names = []
        for item in definition.get("inputs") or []:
            if isinstance(item, Mapping) and item.get("required") is True and isinstance(item.get("name"), str):
                names.append(item["name"].strip())
        found[formula_id.strip()] = tuple(names)
    return found


def block_for(pair_type: str) -> str:
    if pair_type in _REFUSE_PAIR_TYPES:
        return "refuse"
    if pair_type == _NONE_PAIR_TYPE:
        return "none"
    return "qualify"


def target_for(pair_type: str, formula_id: str, inputs: Mapping[str, tuple[str, ...]]) -> PostureTarget:
    pair_type = (pair_type or "").strip()
    if not pair_type:
        raise TargetError("train pair has no pair_type")
    block = block_for(pair_type)
    route = ""
    required: tuple[str, ...] = ()
    if pair_type in _FORMULA_PAIR_TYPES:
        route = (formula_id or "").strip()
        if not route:
            raise TargetError("formula pair has no formula_id")
        required = tuple(inputs.get(route, ()))
    missing = required if pair_type == MISSING_FIRST_PAIR_TYPE else ()
    return PostureTarget(block, route, required, missing)


def contract_keys() -> tuple[str, ...]:
    return _KEYS
