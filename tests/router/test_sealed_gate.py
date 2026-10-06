import hashlib
import json
from pathlib import Path

from router.labels import load_labels, load_sealed_config
from router.majority_gate import evaluate
from router.sealed_gate import RULE, RULE_V1, evaluate_sealed_gate

_FAIL = (
    "sealed gate: FAIL (gate defect: condition (b) unsatisfiable as written); "
    "router NOT marked passed"
)


def test_sealed_gate_field_is_registered_and_scoring_stays_off(repo_root: Path) -> None:
    config = load_sealed_config(repo_root / "configs" / "router" / "sealed_eval.json")
    gate = config["sealed_gate"]
    assert gate["version"] == 2
    assert gate["applies_to"] == "future_fresh_sealed_set"
    assert gate["sealed_scoring"] is False
    assert gate["constant_predictors_fail_majority_gate"] is True
    assert gate["training_majority"] == "drawing"
    assert gate["sealed_set_majority"] == "report"
    assert gate["majority_class_fail"] is True
    assert gate["val_gate_unchanged"] is True
    assert gate["comparison"] == "strictly_greater_than_every_constant_single_label_predictor"
    assert gate["doc"] == "docs/router/SEALED_GATE.md"
    doc = (repo_root / gate["doc"]).read_text(encoding="utf-8")
    assert RULE in doc
    assert RULE_V1 in doc
    assert "future fresh sealed set" in doc
    assert "Version 1 (history)" in doc
    serve = json.loads((repo_root / "configs" / "serve" / "router-epoch2.json").read_text(encoding="utf-8"))
    assert serve["sealed_scoring"] is False
    assert serve["sealed_scored"] is True
    assert serve["router_passed"] is False
    assert serve["status"] == "trained"
    assert serve["sealed_gate_result"] == _FAIL
    assert config["sealed_scored"] is True
    assert config["sealed_gate_result"] == _FAIL


def test_gate_config_is_satisfiable(repo_root: Path) -> None:
    """A perfect predictor passes, and every constant predictor fails."""
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    config = load_sealed_config(repo_root / "configs" / "router" / "sealed_eval.json")
    assert config["sealed_gate"]["majority_class_fail"] is True
    gold = list(labels)
    perfect = evaluate_sealed_gate(
        gold,
        list(gold),
        labels,
        majority_class_fail=True,
    )
    assert perfect["beats_every_constant"] is True
    assert perfect["every_constant_fails_majority_gate"] is True
    assert perfect["passed"] is True
    assert perfect["macro_recall"] == 1.0
    for label in labels:
        constant = evaluate_sealed_gate(
            gold,
            [label] * len(gold),
            labels,
            majority_class_fail=True,
        )
        assert constant["passed"] is False
        assert constant["beats_every_constant"] is False


def test_v1_defect_only_the_set_majority_constant_fails_evaluate(repo_root: Path) -> None:
    """Version 1 called evaluate on the real gold.

    That call fails only the set-majority constant, so condition (b) cannot
    hold when more than one label is present. Version 2 passes a perfect
    predictor on the same rows.
    """
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    gold = ["report", "report", "drawing"]
    order = ["drawing", "report"]
    failed = [
        label
        for label in order
        if evaluate(gold, [label] * len(gold), majority_class_fail=True, order=order).passed is False
    ]
    assert failed == ["report"]
    assert len(failed) != len(order)
    assert "drawing" in labels
    perfect = evaluate_sealed_gate(gold, list(gold), order, majority_class_fail=True)
    assert perfect["beats_every_constant"] is True
    assert perfect["every_constant_fails_majority_gate"] is True
    assert perfect["passed"] is True


def test_a_perfect_single_label_set_does_not_beat_its_constant() -> None:
    result = evaluate_sealed_gate(["drawing"], ["drawing"], ["drawing"], majority_class_fail=True)
    assert result["beats_every_constant"] is False
    assert result["every_constant_fails_majority_gate"] is True
    assert result["passed"] is False


def test_recorded_sealed_score_matches_its_sha256sums(repo_root: Path) -> None:
    directory = repo_root / "docs" / "router" / "runs" / "v2" / "sealed"
    listed = (directory / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    names = []
    for line in listed:
        if not line.strip() or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        names.append(name)
        actual = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        assert actual == digest
    assert names == [
        "sealed_scores.json",
        "sealed_predictions.jsonl",
        "SEALED_RESULT.md",
        "PRE_RUN_NOTE.txt",
    ]


def test_v5_change_order_rows_stay_recorded_as_unsure(repo_root: Path) -> None:
    """The spent v5 predictions are not re-parsed under the alias map."""
    path = repo_root / "docs" / "router" / "runs" / "v2" / "sealed" / "sealed_predictions.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    change = [row for row in rows if row["raw"] == "change order"]
    assert [row["sheet_id"] for row in change] == ["S5-011", "S5-062", "S5-064"]
    assert all(row["gold"] == "VO/CO" and row["pred"] == "unsure" for row in change)


def test_flag_off_means_constants_do_not_fail_the_majority_gate() -> None:
    gold = ["report", "report", "drawing"]
    result = evaluate_sealed_gate(gold, gold, ["drawing", "report"], majority_class_fail=False)
    assert result["every_constant_fails_majority_gate"] is False
    assert result["passed"] is False
