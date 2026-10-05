"""Import, dedupe, and the dry-run split. No pair files are written."""

from __future__ import annotations

import json

from router import import_export, split
from router.plan import build_plan, holdout_count
from router.records import load_corpus, sha256_text


def _row(project: str, filename: str, text: str, label: str, **extra: object) -> dict:
    body: dict = {
        "project_id": project,
        "filename": filename,
        "text": text,
        "label": label,
    }
    body.update(extra)
    return body


def _write(root, rows: list[dict], name: str = "rows.jsonl") -> None:
    path = root / "data" / "raw" / "router" / name
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_holdout_rounds_half_up() -> None:
    assert holdout_count(0, 15, 100) == 0
    assert holdout_count(1, 15, 100) == 0
    assert holdout_count(3, 15, 100) == 0
    assert holdout_count(4, 15, 100) == 1
    assert holdout_count(7, 15, 100) == 1
    assert holdout_count(10, 15, 100) == 2


def test_missing_export_is_a_wall(router_root, capsys) -> None:
    assert import_export.main(["--root", str(router_root)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "wall"
    assert payload["wall"] == "label export"
    assert split.main(["--root", str(router_root)]) == 2
    assert not (router_root / "data" / "eval").exists()
    assert not (router_root / "data" / "train").exists()


def test_empty_file_is_a_wall(router_root, capsys) -> None:
    (router_root / "data" / "raw" / "router" / "empty.jsonl").write_text("", encoding="utf-8")
    assert import_export.main(["--root", str(router_root)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["wall"] == "label export"
    assert "no labeled rows" in payload["detail"]


def test_unknown_label_is_not_relabelled(router_root) -> None:
    _write(
        router_root,
        [
            _row("p", "a.txt", "alpha body", "change order"),
            _row("p", "b.txt", "beta body", "VO / CO"),
            _row("p", "c.txt", "gamma body", "other"),
            _row("p", "d.txt", "delta body", "rfi"),
            _row("p", "e.txt", "epsilon body", "vo/co"),
            _row("p", "rfi_001.pdf", "filename is not a label", "drawing"),
        ],
    )
    corpus = load_corpus(router_root)
    labels = {record.filename: record.label for record in corpus.records}
    assert "a.txt" not in labels
    assert "b.txt" not in labels
    assert labels["c.txt"] == "other"
    assert labels["d.txt"] == "RFI"
    assert labels["e.txt"] == "VO/CO"
    assert labels["rfi_001.pdf"] == "drawing"
    reasons = {item.reason for item in corpus.rejects}
    assert "unknown_label" in reasons


def test_dedupe_conflicts_and_nfc(router_root) -> None:
    _write(
        router_root,
        [
            _row("p", "a.txt", "same body", "RFI"),
            _row("p", "b.txt", "same body", "RFI"),
            _row("p1", "c.txt", "shared body", "spec"),
            _row("p2", "d.txt", "shared body", "spec"),
            _row("p", "e.txt", "clash body", "claim"),
            _row("p", "f.txt", "clash body", "report"),
            _row("p", "g.txt", "caf\u00e9 note", "schedule"),
            _row("p", "h.txt", "cafe\u0301 note", "schedule"),
            _row("p", "i.txt", "alpha  beta", "RFI"),
            _row("p", "i.txt", "alpha beta", "drawing"),
            _row("p", "kept.txt", "unique keeper", "correspondence"),
        ],
    )
    corpus = load_corpus(router_root)
    filenames = {record.filename for record in corpus.records}
    assert corpus.duplicates == 2
    assert corpus.conflicts == 3
    assert "kept.txt" in filenames
    assert "c.txt" not in filenames
    assert "e.txt" not in filenames
    assert "i.txt" not in filenames
    folded = [record for record in corpus.records if record.text.casefold().startswith("caf")]
    assert len(folded) == 1


def test_prefix_is_512_tokens_and_sha_is_the_full_text(router_root) -> None:
    words = [f"w{index}" for index in range(600)]
    text = " ".join(words)
    _write(router_root, [_row("p", "long.txt", text, "spec")])
    corpus = load_corpus(router_root)
    record = corpus.records[0]
    assert record.prefix.split() == words[:512]
    assert "w512" not in record.prefix.split()
    assert record.sha256 == sha256_text(text)
    assert record.sha256 != sha256_text(record.prefix)


def test_stratified_holdout_excludes_the_whole_sealed_project(router_root, capsys) -> None:
    small = [_row("pool-small", f"s{index}.txt", f"small-body-{index:02d}", "RFI") for index in range(10)]
    large = [_row("pool-large", f"L{index}.txt", f"large-body-{index:02d}", "drawing") for index in range(11)]
    _write(router_root, small + large)
    assert split.main(["--root", str(router_root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["wrote_pairs"] is False
    assert payload["seal_written"] is False
    assert payload["seal_matches_rule"] is True
    assert payload["sealed"]["count"] == 11
    assert payload["sealed"]["by_label"]["drawing"] == 11
    assert payload["held_out"]["count"] == 2
    assert payload["held_out"]["by_label"]["RFI"] == 2
    assert payload["train"]["count"] == 8
    assert payload["by_label"]["RFI"] == 10
    assert "prompt" not in payload
    assert "text" not in payload
    assert not (router_root / "data" / "train").exists()
    assert not (router_root / "data" / "eval").exists()

    _config, corpus, plan = build_plan(router_root)
    sealed_projects = {record.project_id for record in plan.sealed}
    assert sealed_projects == {"pool-large"}
    expected = sorted((f"small-body-{index:02d}" for index in range(10)), key=sha256_text)[:2]
    assert sorted(record.text for record in plan.held_out) == expected
    assert {record.sha256 for record in plan.sealed}.isdisjoint(record.sha256 for record in plan.train)
    assert {record.sha256 for record in plan.sealed}.isdisjoint(record.sha256 for record in plan.held_out)


def test_only_project_is_sealed_and_not_trained(router_root) -> None:
    _write(
        router_root,
        [_row("solo", "a.txt", "one body", "report"), _row("solo", "b.txt", "two body", "report")],
    )
    _config, _corpus, plan = build_plan(router_root)
    assert len(plan.sealed) == 2
    assert plan.train == ()
    assert plan.held_out == ()


def test_csv_and_alias_and_sha_disagreement(router_root, capsys) -> None:
    text = "hello body"
    digest = sha256_text(text)
    wrong = "0" * 64
    path = router_root / "data" / "raw" / "router" / "rows.csv"
    path.write_text(
        "project,file_name,document_text,document_type,content_sha256\n"
        f"p,a.txt,{text},spec,{digest}\n"
        f"p,b.txt,other body,schedule,{wrong}\n",
        encoding="utf-8",
    )
    assert import_export.main(["--root", str(router_root)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["by_label"]["spec"] == 1
    assert payload["by_label"]["schedule"] == 1
    assert payload["sha_disagreements"] == 1
    assert payload["deduped"] == 2


def test_ambiguous_label_fields_are_rejected(router_root) -> None:
    _write(
        router_root,
        [
            {
                "project_id": "p",
                "filename": "a.txt",
                "text": "alpha",
                "label": "RFI",
                "document_type": "drawing",
            },
            _row("p", "b.txt", "beta", "claim"),
        ],
    )
    corpus = load_corpus(router_root)
    assert [record.filename for record in corpus.records] == ["b.txt"]
    assert corpus.rejects[0].reason == "ambiguous_field"


def test_target_is_the_label_when_the_document_states_a_fact(router_root) -> None:
    _write(
        router_root,
        [_row("p", "fact.txt", "Cover is 40 MPa in this note.", "spec")],
    )
    from router.seal import sealed_row
    from router.config import load_config

    config = load_config(router_root)
    corpus = load_corpus(router_root, config)
    row = sealed_row(corpus.records[0], config)
    assert row["completion"] == "spec"
    assert "40 MPa" not in row["completion"]
    assert "40 MPa" in row["prompt"]
    assert set(row["meta"]) == {"project_id_sha256", "sha256", "split", "task"}
