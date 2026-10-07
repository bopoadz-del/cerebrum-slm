"""pr2 additions: sealed isolation, template negatives train-only, black-bar redaction."""

import json
from pathlib import Path

from router.isolation import Exclusions, load_exclusions, rejected_rows

ADD = "data/router/additions_owner_sources_pr2.jsonl"
TYPED = ("[PROJECT]", "[LOCATION]", "[ORG]")


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _sealed(repo_root: Path) -> Exclusions:
    e5 = load_exclusions(repo_root / "data/eval/router_unseen/sealed_labels.jsonl")
    e8 = load_exclusions(repo_root / "data/eval/router_unseen/v8/sealed_labels.jsonl")
    return Exclusions(e5.file_sha256 | e8.file_sha256, e5.projects | e8.projects)


def test_pr2_rows_hold_no_sealed_doc_or_project(repo_root: Path) -> None:
    ex = _sealed(repo_root)
    assert ex.file_sha256, "sealed exclusions must load"
    for rel in (ADD, "data/router/train.jsonl", "data/router/val.jsonl"):
        assert rejected_rows(_rows(repo_root / rel), ex) == [], rel


def test_pr2_additions_shas_not_sealed(repo_root: Path) -> None:
    ex = _sealed(repo_root)
    shas = {r["file_sha256"].casefold() for r in _rows(repo_root / ADD)}
    assert not shas & ex.file_sha256


def test_pr2_templates_are_other_and_never_in_val(repo_root: Path) -> None:
    rows = _rows(repo_root / ADD)
    templates = [r for r in rows if "template" in (r.get("tags") or [])]
    assert templates and all(r["label"] == "other" and r["provenance"] == "template" for r in templates)
    ids = {r["doc_id"] for r in templates}
    val = _rows(repo_root / "data/router/val.jsonl")
    train = _rows(repo_root / "data/router/train.jsonl")
    assert not any(r.get("doc_id") in ids for r in val)
    assert sum(r.get("doc_id") in ids for r in train) == len(ids)


def test_pr2_redaction_uses_black_bar_only(repo_root: Path) -> None:
    rows = _rows(repo_root / ADD)
    assert all(r.get("redacted") is True for r in rows)
    assert not any(tag in r["excerpt"] for r in rows for tag in TYPED)
