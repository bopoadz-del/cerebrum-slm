"""Sealed per-label n is counted once, from the sealed manifest, for the sets actually scored.

Regression: a report quoted per-label n from a stored count table that covered every
registered set, next to a score made on a subset of those sets. The table is gone; the
count comes from router.sealed_counts, and a score whose n disagrees with the manifest
for its own sets is refused. No counts or label names are written into these tests.
"""

import json
from pathlib import Path

import pytest
from router.labels import load_labels, load_sealed_config
from router.sealed_counts import (
    SealedCountError,
    counts_for_scores,
    main,
    sealed_counts,
    sealed_gold,
    select_sets,
)
from router.sealed_gate import (
    MIN_SEALED_PER_LABEL,
    evaluate_sealed_gate_v8,
    per_label_n,
)


def _v9(root: Path) -> dict:
    return load_sealed_config(root / "configs" / "router" / "sealed_eval.json")["v9_sealed"]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _score(gold_by_set: dict[str, list[str]], labels: list[str]) -> dict:
    """A score shaped like sealed_scores.json, built from gold only (pred == gold)."""
    sets: dict = {}
    for name, gold in gold_by_set.items():
        sets[name] = {"n": len(gold), "per_label": evaluate_sealed_gate_v8(gold, list(gold), labels, majority_class_fail=True)["per_label"]}
    combined = [label for gold in gold_by_set.values() for label in gold]
    sets["combined"] = {"n": len(combined), "per_label": evaluate_sealed_gate_v8(combined, list(combined), labels, majority_class_fail=True)["per_label"]}
    return {"sets": sets}


@pytest.fixture
def tiny(tmp_path: Path, repo_root: Path):
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")[:3]
    first = [labels[0], labels[1], labels[0]]
    second = [labels[1], labels[2], labels[2], labels[2]]
    _write_jsonl(tmp_path / "a" / "sealed_labels.jsonl", [{"label": x} for x in first])
    _write_jsonl(tmp_path / "b" / "sealed_labels.jsonl", [{"label": x} for x in second])
    v9 = {
        "sets": [
            {"name": "set_a", "sealed_labels": "a/sealed_labels.jsonl", "rows": len(first)},
            {"name": "set_b", "sealed_labels": "b/sealed_labels.jsonl", "rows": len(second), "addendum": True},
        ],
        "combined": {"rows": len(first) + len(second)},
    }
    return tmp_path, v9, labels, first, second


def test_config_stores_no_per_label_count_table(repo_root: Path) -> None:
    """The old path read v9_sealed.combined.per_label_n; that stored table must not exist."""
    v9 = _v9(repo_root)
    assert "per_label_n" not in v9["combined"]
    for item in v9["sets"]:
        assert "per_label_n" not in item


def test_counts_follow_the_scored_sets_not_every_registered_set(tiny) -> None:
    root, v9, labels, first, _second = tiny
    subset = sealed_counts(root, v9, labels, ["set_a"])
    everything = sealed_counts(root, v9, labels)
    assert subset["sets"] == ["set_a"] and subset["rows"] == len(first)
    assert subset["per_label_n"] == per_label_n(first, labels)
    assert subset["per_label_n"] != everything["per_label_n"]
    gate = evaluate_sealed_gate_v8(first, list(first), labels, majority_class_fail=True)
    assert subset["per_label_n"] == {row["label"]: row["n"] for row in gate["per_label"]}
    assert subset["below_min"] == [{"label": k, "n": v} for k, v in subset["per_label_n"].items() if v < MIN_SEALED_PER_LABEL]


def test_score_on_a_subset_reconciles_and_a_full_manifest_table_is_refused(tiny) -> None:
    root, v9, labels, first, second = tiny
    score = _score({"set_a": first}, labels)
    assert counts_for_scores(root, v9, labels, score)["per_label_n"] == per_label_n(first, labels)
    # The old bug: per-label n of every registered set reported next to a subset score.
    stale = per_label_n(first + second, labels)
    score["sets"]["combined"]["per_label"] = [{"label": k, "n": v} for k, v in stale.items()]
    with pytest.raises(SealedCountError):
        counts_for_scores(root, v9, labels, score)


def test_selection_keeps_manifest_order_and_refuses_unknown_or_short_files(tiny) -> None:
    root, v9, _labels, *_ = tiny
    assert [s["name"] for s in select_sets(v9, ["set_b", "set_a"])] == ["set_a", "set_b"]
    with pytest.raises(SealedCountError):
        select_sets(v9, ["nope"])
    v9["sets"][0]["rows"] += 1
    with pytest.raises(SealedCountError):
        sealed_gold(root, v9)


def test_every_committed_v9_score_reconciles_with_the_manifest(repo_root: Path) -> None:
    v9 = _v9(repo_root)
    labels = load_labels(repo_root / v9["labels_file"])
    names = {item["name"] for item in v9["sets"]}
    checked = 0
    for path in sorted((repo_root / "docs" / "router" / "runs").rglob("sealed_scores.json")):
        scores = json.loads(path.read_text(encoding="utf-8"))
        sets = scores.get("sets")
        if not isinstance(sets, dict) or not (set(sets) - {"combined"}) or not (set(sets) - {"combined"}) <= names:
            continue
        counts = counts_for_scores(repo_root, v9, labels, scores)
        if "combined" in sets:
            assert counts["rows"] == sets["combined"]["n"], path
        checked += 1
    assert checked >= 1


def test_gate_counts_equal_manifest_counts_on_the_real_sealed_set(repo_root: Path) -> None:
    v9 = _v9(repo_root)
    labels = load_labels(repo_root / v9["labels_file"])
    gold = [label for rows in sealed_gold(repo_root, v9).values() for label in rows]
    gate = evaluate_sealed_gate_v8(gold, list(gold), labels, majority_class_fail=True)
    counts = sealed_counts(repo_root, v9, labels)
    assert counts["rows"] == v9["combined"]["rows"] == len(gold)
    assert counts["per_label_n"] == {row["label"]: row["n"] for row in gate["per_label"]}


def test_cli_prints_counts_only(tiny, capsys) -> None:
    root, v9, _labels, first, _ = tiny
    (root / "configs" / "router").mkdir(parents=True)
    full_labels = json.loads((Path(__file__).resolve().parents[2] / "configs" / "router" / "labels.json").read_text(encoding="utf-8"))
    (root / "configs" / "router" / "labels.json").write_text(json.dumps(full_labels), encoding="utf-8")
    real = json.loads((Path(__file__).resolve().parents[2] / "configs" / "router" / "sealed_eval.json").read_text(encoding="utf-8"))
    real["v9_sealed"] = {**real["v9_sealed"], **v9, "labels_file": "configs/router/labels.json"}
    (root / "configs" / "router" / "sealed_eval.json").write_text(json.dumps(real), encoding="utf-8")
    assert main(["--root", str(root), "--sets", "set_a"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert set(out) == {"sets", "rows", "per_label_n", "min_sealed_per_label", "below_min"}
    assert out["rows"] == len(first)
    assert main(["--root", str(root), "--sets", "nope"]) == 2
