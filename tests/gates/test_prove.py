from __future__ import annotations

from pathlib import Path

from gates.prove import run_proofs
from gates.run import evaluate, main


_RED_THEN_GREEN = (
    "probe-id",
    "domain",
    "word-list",
    "eval-hash",
    "number-unit",
    "currency",
    "clause-edition",
    "brand",
    "site",
    "blind-read",
    "blind-bytes",
)


def test_injection_is_red_then_removed_then_green(repo_root: Path) -> None:
    lines = run_proofs()
    text = "\n".join(lines)
    cursor = 0
    for label in _RED_THEN_GREEN:
        red = text.find(f"PROOF {label} RED", cursor)
        green = text.find(f"PROOF {label} GREEN", cursor)
        assert red != -1 and green != -1 and red < green, label
        cursor = green
    posture = text.find("PROOF posture GREEN")
    number = text.find("PROOF number-unit RED")
    assert posture != -1 and posture < number
    assert "PROOF training-read REJECTED" in text
    assert text.endswith("PROOF sequence complete")
    assert not (repo_root / "src").exists()
    assert not (repo_root / "data" / "eval").exists()
    assert not (repo_root / "data" / "train").exists()


def test_repo_gates_are_green(repo_root: Path, capsys) -> None:
    assert evaluate(repo_root) == []
    assert main(["--root", str(repo_root)]) == 0
    captured = capsys.readouterr()
    assert "blind files hashed: 0" in captured.out
    assert "training manifest ∩ blind = ∅" in captured.out
    assert "training read attempt: REJECTED" in captured.out
    assert "PROOF probe-id RED" in captured.out
    assert "PROOF probe-id GREEN" in captured.out
    assert "gates: green" in captured.out
    assert captured.err == ""
