from __future__ import annotations

from pathlib import Path

import pytest

from gates.blind_seal import (
    BlindSealError,
    check_blind,
    opener_rejects_eval,
    path_is_sealed,
    seal_manifest,
    training_open,
)


def test_missing_eval_tree_hashes_empty_and_rejects_a_read(tmp_path: Path) -> None:
    assert seal_manifest(tmp_path) == []
    assert opener_rejects_eval(tmp_path)
    assert check_blind(tmp_path) == []
    probe = tmp_path / "data" / "eval" / "blind" / ".read-probe"
    with pytest.raises(BlindSealError):
        training_open(probe, tmp_path)
    assert not probe.exists()


def test_read_attempt_fails_the_build_then_removed_is_green(tmp_path: Path) -> None:
    sealed = tmp_path / "data" / "eval" / "blind" / "case.jsonl"
    sealed.parent.mkdir(parents=True)
    sealed.write_text('{"instruction":"q","output":"a"}\n', encoding="utf-8")
    train = tmp_path / "src" / "train_step.py"
    train.parent.mkdir(parents=True)
    train.write_text('def load():\n    return open("data/eval/blind/case.jsonl").read()\n', encoding="utf-8")
    findings = check_blind(tmp_path)
    assert any("data/eval" in finding.message for finding in findings)

    joined = tmp_path / "scripts" / "train" / "fit.py"
    joined.parent.mkdir(parents=True)
    joined.write_text('from pathlib import Path\nroot = Path("data") / "eval"\n', encoding="utf-8")
    assert any(finding.path.endswith("fit.py") for finding in check_blind(tmp_path))

    train.unlink()
    joined.unlink()
    copied = tmp_path / "data" / "train" / "copied.jsonl"
    copied.parent.mkdir(parents=True)
    copied.write_bytes(sealed.read_bytes())
    byte_findings = check_blind(tmp_path)
    assert any("training manifest ∩ blind" in finding.message for finding in byte_findings)
    copied.unlink()
    assert check_blind(tmp_path) == []
    assert len(seal_manifest(tmp_path)) == 1


def test_training_can_read_outside_the_seal(tmp_path: Path) -> None:
    allowed = tmp_path / "data" / "train" / "ok.txt"
    allowed.parent.mkdir(parents=True)
    allowed.write_text("ok", encoding="utf-8")
    with training_open(allowed, tmp_path) as handle:
        assert handle.read() == b"ok"
    escaped = tmp_path / "data" / "eval" / ".." / "train" / "ok.txt"
    assert path_is_sealed(tmp_path / "data" / "eval" / "blind" / "x.jsonl", tmp_path)
    assert not path_is_sealed(escaped, tmp_path)
    with training_open(escaped, tmp_path) as handle:
        assert handle.read() == b"ok"
