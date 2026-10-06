import json
from pathlib import Path

from router.labels import load_labels, load_sealed_config
from router.majority_gate import evaluate
from router.sealed_gate import RULE, evaluate_sealed_gate


def test_sealed_gate_field_is_registered_and_scoring_stays_off(repo_root: Path) -> None:
    config = load_sealed_config(repo_root / "configs" / "router" / "sealed_eval.json")
    gate = config["sealed_gate"]
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
    serve = json.loads((repo_root / "configs" / "serve" / "router-epoch2.json").read_text(encoding="utf-8"))
    assert serve["sealed_scoring"] is False


def test_sealed_gate_uses_the_unchanged_majority_function(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    gold = ["report", "report", "drawing"]
    pred = list(gold)
    result = evaluate_sealed_gate(gold, pred, ["drawing", "report"], majority_class_fail=True)
    assert result["beats_every_constant"] is True
    assert result["every_constant_fails_majority_gate"] is False
    assert result["passed"] is False
    drawing = evaluate(gold, ["drawing"] * 3, majority_class_fail=True, order=["drawing", "report"])
    report = evaluate(gold, ["report"] * 3, majority_class_fail=True, order=["drawing", "report"])
    assert drawing.passed is True
    assert report.passed is False
    assert "drawing" in labels
    assert "report" in labels


def test_a_perfect_single_label_set_does_not_beat_its_constant() -> None:
    result = evaluate_sealed_gate(["drawing"], ["drawing"], ["drawing"], majority_class_fail=True)
    assert result["beats_every_constant"] is False
    assert result["every_constant_fails_majority_gate"] is True
    assert result["passed"] is False


def test_flag_off_means_constants_do_not_fail_the_majority_gate() -> None:
    gold = ["report", "report", "drawing"]
    result = evaluate_sealed_gate(gold, gold, ["drawing", "report"], majority_class_fail=False)
    assert result["every_constant_fails_majority_gate"] is False
    assert result["passed"] is False
