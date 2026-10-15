"""Sealed per-label counts, computed once from the seal-time label manifest.

The sealed manifest is ``configs/router/sealed_eval.json`` -> ``v9_sealed.sets``.
Per-label ``n`` is counted here for exactly the sets that were scored. No count
table is stored in config, so a report can never quote counts of a different
set selection than the one its score was computed on.

Every consumer (the ``router_passed`` n >= ``MIN_SEALED_PER_LABEL`` rule,
reports, analysis notes) takes counts from :func:`sealed_counts` or, for an
existing score, :func:`counts_for_scores`, which recounts the manifest for the
scored sets and refuses a score whose per-label ``n`` disagrees. An empty
per-label list on a score view is refused.

Reads only the seal-time label manifests (neutral row id and label, plus a
header sidecar with the row count and the sha256 of the sealed labels file).
Never opens a sealed labels file. Writes nothing. Never emits document text.
A missing manifest, an empty manifest, or a manifest whose row count disagrees
with the sealed set's recorded row count fails loudly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from router.labels import load_labels, load_sealed_config, repo_root
from router.seal_sealed import manifest_paths
from router.sealed_gate import MIN_SEALED_PER_LABEL, per_label_n

COMBINED = "combined"
_RECORD_KEYS = frozenset({"id", "label"})
_HEADER_KEYS = frozenset({"rows", "sealed_labels_sha256"})
_HEX = frozenset("0123456789abcdef")


class SealedCountError(ValueError):
    """The requested sets, the manifest files or a score do not agree."""


def select_sets(v9: dict, names: list[str] | None = None) -> list[dict]:
    """Registered sets in manifest order; ``names`` picks a subset (order kept)."""
    sets = list(v9.get("sets") or [])
    if not sets:
        raise SealedCountError("v9_sealed lists no sets")
    if names is None:
        return sets
    known = [item["name"] for item in sets]
    unknown = sorted(set(names) - set(known))
    if unknown:
        raise SealedCountError(f"unknown sealed set(s): {unknown}")
    if len(set(names)) != len(names):
        raise SealedCountError("a sealed set is named twice")
    wanted = set(names)
    return [item for item in sets if item["name"] in wanted]


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _read_manifest(sealed_labels: Path) -> list[str]:
    """Labels from the seal-time manifest beside ``sealed_labels``.

    ``sealed_labels`` is used only to locate the manifest. It is not opened.
    """
    records_path, header_path = manifest_paths(sealed_labels)
    if not records_path.is_file() or not header_path.is_file():
        missing = records_path if not records_path.is_file() else header_path
        raise SealedCountError(f"label manifest is missing: {missing}")
    header_text = header_path.read_text(encoding="utf-8")
    records_text = records_path.read_text(encoding="utf-8")
    if not header_text.strip() or not records_text.strip():
        raise SealedCountError(f"label manifest is empty: {records_path}")
    try:
        header = json.loads(header_text)
    except json.JSONDecodeError:
        raise SealedCountError(f"label manifest header is not JSON: {header_path}") from None
    if not isinstance(header, dict) or set(header) != _HEADER_KEYS:
        raise SealedCountError(f"label manifest header is not row count and sealed-file sha256: {header_path}")
    rows = header["rows"]
    digest = header["sealed_labels_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in _HEX for char in digest):
        raise SealedCountError(f"label manifest header is not row count and sealed-file sha256: {header_path}")
    labels: list[str] = []
    for line in records_text.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            raise SealedCountError(f"label manifest record is not JSON: {records_path}") from None
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            raise SealedCountError(f"label manifest record is not id and label only: {records_path}")
        if not _positive_int(record["id"]):
            raise SealedCountError(f"label manifest record is not id and label only: {records_path}")
        label = record["label"]
        if not isinstance(label, str) or not label or label != label.strip():
            raise SealedCountError(f"label manifest record has no label: {records_path}")
        labels.append(label)
    if not labels:
        raise SealedCountError(f"label manifest is empty: {records_path}")
    if not _positive_int(rows) or rows != len(labels):
        raise SealedCountError(f"label manifest row count {rows} disagrees with {len(labels)} records: {records_path}")
    return labels


def sealed_gold(root: Path, v9: dict, names: list[str] | None = None) -> dict[str, list[str]]:
    """``{set name: [gold label, ...]}`` from the label manifests, manifest order."""
    out: dict[str, list[str]] = {}
    for item in select_sets(v9, names):
        gold = _read_manifest(root / item["sealed_labels"])
        declared = item.get("rows")
        if isinstance(declared, int) and not isinstance(declared, bool) and declared != len(gold):
            raise SealedCountError(
                f"set {item['name']}: manifest row count {len(gold)} disagrees with recorded row count {declared}"
            )
        out[item["name"]] = gold
    return out


def sealed_counts(root: Path, v9: dict, labels: list[str], names: list[str] | None = None) -> dict:
    """Per-label sealed ``n`` for the selected sets, counted from the label manifests."""
    by_set = sealed_gold(root, v9, names)
    gold = [label for rows in by_set.values() for label in rows]
    outside = sorted(set(gold) - set(labels))
    if outside:
        raise SealedCountError(f"sealed gold uses labels outside the label set: {outside}")
    counts = per_label_n(gold, labels)
    return {
        "sets": list(by_set),
        "rows": len(gold),
        "per_label_n": counts,
        "min_sealed_per_label": MIN_SEALED_PER_LABEL,
        "below_min": [{"label": label, "n": counts[label]} for label in labels if counts[label] < MIN_SEALED_PER_LABEL],
    }


def scored_set_names(scores: dict) -> list[str]:
    """Set names a sealed_scores.json scored (its ``sets`` keys, minus the combined view)."""
    sets = scores.get("sets")
    if not isinstance(sets, dict) or not sets:
        raise SealedCountError("scores carry no per-set results")
    return [name for name in sets if name != COMBINED]


def counts_for_scores(root: Path, v9: dict, labels: list[str], scores: dict) -> dict:
    """Manifest counts for the sets a score covered; refuses a score that disagrees.

    The combined view of a score must count the same rows per label as the
    label manifests of its scored sets. A mismatch (counts taken from another
    set selection, a stale table, or predictions) raises ``SealedCountError``.
    A score view with an empty per-label list is refused.
    """
    names = scored_set_names(scores)
    counts = sealed_counts(root, v9, labels, names)
    views = {name: scores["sets"][name] for name in names}
    if COMBINED in scores["sets"]:
        views[COMBINED] = scores["sets"][COMBINED]
    for view, result in views.items():
        if not isinstance(result, dict):
            raise SealedCountError(f"score view {view}: result is not an object")
        expected = counts["per_label_n"] if view == COMBINED else per_label_n(sealed_gold(root, v9, [view])[view], labels)
        per_label = result.get("per_label")
        if not isinstance(per_label, list) or not per_label:
            raise SealedCountError(f"score view {view}: per-label list is empty")
        got: dict[str, int] = {}
        for row in per_label:
            if not isinstance(row, dict) or "label" not in row or "n" not in row:
                raise SealedCountError(f"score view {view}: per-label row is missing a count")
            got[row["label"]] = row["n"]
        if got != expected:
            diff = sorted(label for label in expected if got.get(label) != expected[label])
            raise SealedCountError(f"score view {view}: per-label n differs from the sealed manifest for {diff}")
        recorded_n = result.get("n")
        if isinstance(recorded_n, int) and not isinstance(recorded_n, bool) and recorded_n != sum(expected.values()):
            raise SealedCountError(f"score view {view}: n={recorded_n} but the manifest has {sum(expected.values())} rows")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sealed per-label counts from the label manifest (counts only)")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--sets", default=None, help="comma-separated set names; default all registered sets")
    parser.add_argument("--scores", type=Path, default=None, help="a sealed_scores.json; counts follow its scored sets")
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    v9 = load_sealed_config(root / "configs" / "router" / "sealed_eval.json")["v9_sealed"]
    labels = load_labels(root / v9["labels_file"])
    try:
        if args.scores is not None:
            if args.sets is not None:
                raise SealedCountError("pass --sets or --scores, not both")
            report = counts_for_scores(root, v9, labels, json.loads(args.scores.read_text(encoding="utf-8")))
        else:
            names = [name.strip() for name in args.sets.split(",") if name.strip()] if args.sets else None
            report = sealed_counts(root, v9, labels, names)
    except SealedCountError as exc:
        print(str(exc))
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
