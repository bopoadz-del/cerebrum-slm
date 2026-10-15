"""Sealed per-label counts, computed once from the sealed manifest.

The sealed manifest is ``configs/router/sealed_eval.json`` -> ``v9_sealed.sets``:
an ordered list of ``sealed_labels.jsonl`` files. Per-label ``n`` is counted
here, from those files, for exactly the sets that were scored. No count table
is stored in config, so a report can never quote counts of a different set
selection than the one its score was computed on.

Every consumer (the ``router_passed`` n >= ``MIN_SEALED_PER_LABEL`` rule,
reports, analysis notes) takes counts from :func:`sealed_counts` or, for an
existing score, :func:`counts_for_scores`, which recounts the manifest for the
scored sets and refuses a score whose per-label ``n`` disagrees.

Reads only gold labels. Writes nothing. Never emits document text.
Counting is a label-only stream: the ``label`` field is copied out and every
other byte is discarded before any parse, so excerpt text and other raw row
content never reach ``json.loads``. An empty labels file fails loudly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from router.labels import load_labels, load_sealed_config, repo_root
from router.sealed_gate import MIN_SEALED_PER_LABEL, per_label_n

COMBINED = "combined"


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


# The key token only. Matched as a sliding window so no other field is retained.
_LABEL_KEY = '"label"'


def _read_label_stream(path: Path) -> list[str]:
    """Copy the ``label`` string out of each row. No other field is parsed.

    The reader keeps a window the size of the key and the current label token.
    Once the label value closes, the rest of the row is dropped and never
    parsed, including when that tail is not valid JSON.
    """
    labels: list[str] = []
    window = ""
    token: list[str] = []
    state = "scan"
    escape = False
    line_marked = False
    saw_label = False

    def reject() -> None:
        raise SealedCountError(f"sealed row without a label in {path}")

    def end_line() -> None:
        nonlocal window, token, state, escape, line_marked, saw_label
        if state == "string" or (line_marked and not saw_label):
            reject()
        window = ""
        token = []
        state = "scan"
        escape = False
        line_marked = False
        saw_label = False

    with path.open(encoding="utf-8") as handle:
        while True:
            char = handle.read(1)
            if char == "":
                if state in {"colon", "value", "string"} or (line_marked and not saw_label):
                    reject()
                break
            if char == "\n":
                end_line()
                continue
            if char not in " \t\r":
                line_marked = True
            if state == "skip":
                continue
            if state == "scan":
                window = (window + char)[-len(_LABEL_KEY) :]
                if window == _LABEL_KEY:
                    state = "colon"
                    window = ""
                continue
            if state == "colon":
                if char in " \t\r":
                    continue
                if char == ":":
                    state = "value"
                    continue
                state = "scan"
                window = char
                continue
            if state == "value":
                if char in " \t\r":
                    continue
                if char != '"':
                    reject()
                token = ['"']
                escape = False
                state = "string"
                continue
            token.append(char)
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char != '"':
                continue
            try:
                value = json.loads("".join(token))
            except json.JSONDecodeError:
                reject()
            if not isinstance(value, str) or not value:
                reject()
            labels.append(value)
            saw_label = True
            token = []
            state = "skip"
    return labels


def _gold_rows(path: Path) -> list[str]:
    """Labels only from a sealed_labels.jsonl. Never parses a non-label field."""
    if not path.is_file():
        raise SealedCountError(f"sealed labels file is missing: {path}")
    labels = _read_label_stream(path)
    if not labels:
        raise SealedCountError(f"sealed labels file is empty (no labels): {path}")
    return labels


def sealed_gold(root: Path, v9: dict, names: list[str] | None = None) -> dict[str, list[str]]:
    """``{set name: [gold label, ...]}`` read from the manifest files, manifest order."""
    out: dict[str, list[str]] = {}
    for item in select_sets(v9, names):
        gold = _gold_rows(root / item["sealed_labels"])
        declared = item.get("rows")
        if isinstance(declared, int) and declared != len(gold):
            raise SealedCountError(f"set {item['name']}: file has {len(gold)} rows, manifest says {declared}")
        out[item["name"]] = gold
    return out


def sealed_counts(root: Path, v9: dict, labels: list[str], names: list[str] | None = None) -> dict:
    """Per-label sealed ``n`` for the selected sets, counted from the manifest files."""
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
    manifest files of its scored sets. A mismatch (counts taken from another
    set selection, a stale table, or predictions) raises ``SealedCountError``.
    """
    names = scored_set_names(scores)
    counts = sealed_counts(root, v9, labels, names)
    views = {name: scores["sets"][name] for name in names}
    if COMBINED in scores["sets"]:
        views[COMBINED] = scores["sets"][COMBINED]
    for view, result in views.items():
        expected = counts["per_label_n"] if view == COMBINED else per_label_n(sealed_gold(root, v9, [view])[view], labels)
        got = {row["label"]: row["n"] for row in result.get("per_label", [])}
        if got and got != expected:
            diff = sorted(label for label in expected if got.get(label) != expected[label])
            raise SealedCountError(f"score view {view}: per-label n differs from the sealed manifest for {diff}")
        if isinstance(result.get("n"), int) and result["n"] != sum(expected.values()):
            raise SealedCountError(f"score view {view}: n={result['n']} but the manifest has {sum(expected.values())} rows")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sealed per-label counts from the sealed manifest (counts only)")
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
