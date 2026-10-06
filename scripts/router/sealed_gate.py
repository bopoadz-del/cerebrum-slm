"""Sealed-set gate. Registered before any scoring.

This module does not read ``data/eval/`` and does not score a checkpoint.
The val gate in ``majority_gate.py`` is unchanged. Callers pass gold and
predictions in memory.
"""

from __future__ import annotations

from router.majority_gate import evaluate
from router.val_metrics import per_label_recall

RULE = (
    "The model passes only if macro recall beats every constant single-label "
    "predictor on the sealed rows, and each of those constant predictors fails "
    "the existing majority gate. Macro recall is the mean of per-label recall "
    "over labels present in the sealed rows. The constant predictors include "
    "always-drawing, the training majority, and always-report, the sealed-set "
    "majority. A tie does not beat a constant predictor. The majority gate is "
    "scripts/router/majority_gate.py with majority_class_fail left unchanged. "
    "sealed_scoring stays false."
)


def macro_recall(gold: list[str], pred: list[str], labels: list[str]) -> float | None:
    """Mean recall over labels that occur in ``gold``. A missing label stays out."""
    scores = per_label_recall(gold, pred, labels)
    present = [score for score in scores.values() if score is not None]
    if not present:
        return None
    return sum(present) / len(present)


def evaluate_sealed_gate(
    gold: list[str],
    pred: list[str],
    labels: list[str],
    *,
    majority_class_fail: bool,
) -> dict:
    """Apply the pre-registered sealed rule. Writes nothing."""
    if not labels or not gold or len(gold) != len(pred):
        return {
            "passed": False,
            "reason": "empty or mismatched",
            "macro_recall": None,
            "beats_every_constant": False,
            "every_constant_fails_majority_gate": False,
        }
    model = macro_recall(gold, pred, labels)
    beats: dict[str, bool] = {}
    constant_fails: dict[str, bool] = {}
    for label in labels:
        constant = [label] * len(gold)
        baseline = macro_recall(gold, constant, labels)
        beats[label] = model is not None and baseline is not None and model > baseline
        gate = evaluate(
            gold,
            constant,
            majority_class_fail=majority_class_fail,
            order=labels,
        )
        constant_fails[label] = gate.passed is False
    beats_every = all(beats.values())
    constants_fail = all(constant_fails.values())
    passed = beats_every and constants_fail
    return {
        "passed": passed,
        "reason": "sealed gate" if passed else "sealed gate failed",
        "macro_recall": model,
        "beats_every_constant": beats_every,
        "every_constant_fails_majority_gate": constants_fail,
    }
