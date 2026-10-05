"""The seal stores one project and writes hashes, not document text, into the note."""

from __future__ import annotations

import json

from gates.blind_seal import check_committed_seals
from gates.catalog import build_catalog
from gates.no_hardwiring import check_hardwiring
from gates.records import content_hash
from router import seal, split
from router.plan import build_plan
from router.records import sha256_text
from router.seal import write_seal


def _row(project: str, filename: str, text: str, label: str) -> dict:
    return {"project_id": project, "filename": filename, "text": text, "label": label}


def _write(root, rows: list[dict], name: str = "rows.jsonl") -> None:
    path = root / "data" / "raw" / "router" / name
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _canary(count: int) -> list[dict]:
    pad = "pad " * 12
    return [
        _row(
            "CANARYPROJECT",
            f"CANARYFILE-{index}.txt",
            f"CANARYTOKEN sealed body {index} {pad}",
            "drawing",
        )
        for index in range(count)
    ]


def _assert_public_has_no_canary(text: str) -> None:
    assert "CANARYTOKEN" not in text
    assert "CANARYFILE" not in text
    assert "CANARYPROJECT" not in text


def test_seal_writes_hashes_and_keeps_text_out_of_the_note(router_root, capsys) -> None:
    _write(router_root, _canary(2) + [_row("other-pool", "o.txt", "outside body", "spec")])
    assert seal.main(["--root", str(router_root)]) == 0
    stdout = capsys.readouterr().out
    _assert_public_has_no_canary(stdout)
    payload = json.loads(stdout)
    assert payload["seal_written"] is True
    assert payload["wrote_pairs"] is False
    assert payload["sealed"]["count"] == 2
    assert len(payload["sealed"]["project_id_sha256"]) == 64

    note = (router_root / "docs" / "router" / "sealed-project.md").read_text(encoding="utf-8")
    seal_json = (router_root / "data" / "eval" / "router" / "seal.json").read_text(encoding="utf-8")
    items = (router_root / "data" / "eval" / "router" / "items.jsonl").read_text(encoding="utf-8")
    _assert_public_has_no_canary(note)
    _assert_public_has_no_canary(seal_json)
    assert "CANARYTOKEN" in items
    assert "CANARYFILE-0.txt" in items
    assert "CANARYPROJECT" not in items
    assert "outside body" not in items
    assert check_committed_seals(router_root) == []

    first = json.loads(items.splitlines()[0])
    assert first["completion"] == "drawing"
    assert first["prompt"].startswith("filename: ")
    catalog = build_catalog(router_root)
    assert content_hash(first["prompt"], first["completion"]) in catalog.content_hashes
    leaked = router_root / "data" / "train" / "leaked.jsonl"
    leaked.parent.mkdir(parents=True)
    leaked.write_text(json.dumps({"prompt": first["prompt"], "completion": first["completion"]}) + "\n")
    findings = check_hardwiring(router_root)
    assert any("content hash" in finding.message for finding in findings)

    items_bytes = (router_root / "data" / "eval" / "router" / "items.jsonl").read_bytes()
    seal_bytes = (router_root / "data" / "eval" / "router" / "seal.json").read_bytes()
    note_bytes = note.encode("utf-8")
    write_seal(router_root)
    assert (router_root / "data" / "eval" / "router" / "items.jsonl").read_bytes() == items_bytes
    assert (router_root / "data" / "eval" / "router" / "seal.json").read_bytes() == seal_bytes
    assert (router_root / "docs" / "router" / "sealed-project.md").read_bytes() == note_bytes


def test_frozen_project_stays_sealed_when_another_project_grows(router_root, capsys) -> None:
    _write(router_root, _canary(3) + [_row("BETA-PROJECT", "b.txt", "BETATOKEN lone body", "report")])
    write_seal(router_root)
    grown = _canary(3) + [
        _row("BETA-PROJECT", f"b{index}.txt", f"BETATOKEN grown body {index}", "report") for index in range(12)
    ]
    _write(router_root, grown)
    assert split.main(["--root", str(router_root)]) == 0
    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    assert payload["seal_written"] is True
    assert payload["seal_matches_rule"] is False
    assert payload["sealed"]["count"] == 3
    assert payload["train"]["count"] + payload["held_out"]["count"] == 12
    _assert_public_has_no_canary(stdout)

    write_seal(router_root)
    items = (router_root / "data" / "eval" / "router" / "items.jsonl").read_text(encoding="utf-8")
    note = (router_root / "docs" / "router" / "sealed-project.md").read_text(encoding="utf-8")
    assert "BETATOKEN" not in items
    assert "CANARYTOKEN" in items
    assert "BETATOKEN" not in note
    assert "CANARYPROJECT" not in note
    _config, _corpus, plan = build_plan(router_root)
    assert {record.project_id for record in plan.sealed} == {"CANARYPROJECT"}
    assert all(record.project_id == "BETA-PROJECT" for record in plan.train + plan.held_out)


def test_tie_breaks_on_the_lower_project_hash(router_root) -> None:
    left = "tie-aaa"
    right = "tie-bbb"
    rows = []
    for project in (left, right):
        rows.append(_row(project, f"{project}-1.txt", f"{project} one", "spec"))
        rows.append(_row(project, f"{project}-2.txt", f"{project} two", "claim"))
    _write(router_root, rows)
    _config, _corpus, plan = build_plan(router_root)
    expected = min((left, right), key=sha256_text)
    assert {record.project_id for record in plan.sealed} == {expected}
    assert all(record.project_id != expected for record in (*plan.train, *plan.held_out))


def test_missing_export_does_not_write_a_seal(router_root, capsys) -> None:
    assert seal.main(["--root", str(router_root)]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["wall"] == "label export"
    assert not (router_root / "data" / "eval" / "router").exists()
    note = router_root / "docs" / "router" / "sealed-project.md"
    assert not note.exists()
