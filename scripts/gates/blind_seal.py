"""Blind-set seal: hash data/eval/** and keep the training path from reading it."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gates.findings import Finding
from gates.records import iter_training_files, relpath, sha256_file

_READS = (
    re.compile(r"data[/\\]+eval\b"),
    re.compile(r"""["']data["']\s*,\s*["']eval["']"""),
    re.compile(r"""["']data["']\s*\)?\s*/\s*["']eval["']"""),
)


class BlindSealError(Exception):
    """Raised when training code attempts to read data/eval/**."""

    def __init__(self, path: str) -> None:
        super().__init__(f"training path cannot read sealed eval file: {path}")
        self.path = path


@dataclass(frozen=True)
class SealedFile:
    relpath: str
    digest: str


def seal_manifest(root: Path) -> list[SealedFile]:
    base = root / "data" / "eval"
    if not base.is_dir():
        return []
    sealed: list[SealedFile] = []
    for path in sorted(item for item in base.rglob("*") if item.is_file()):
        sealed.append(SealedFile(relpath(path, root), sha256_file(path)))
    return sealed


def training_manifest(root: Path) -> list[SealedFile]:
    return [
        SealedFile(relpath(path, root), sha256_file(path))
        for path in iter_training_files(root)
    ]


def training_code_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for folder in (root / "src", root / "scripts" / "train"):
        if folder.is_dir():
            files.extend(path for path in folder.rglob("*") if path.is_file())
    files.extend(path for path in root.glob("train*.py") if path.is_file())
    return sorted(set(files))


def _resolved(path: Path, root: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (root.resolve() / path).resolve()


def path_is_sealed(path: Path, root: Path) -> bool:
    eval_root = (root.resolve() / "data" / "eval").resolve()
    try:
        _resolved(path, root).relative_to(eval_root)
    except ValueError:
        return False
    return True


def training_open(path: str | Path, root: Path, mode: str = "rb"):
    """The only training-path opener. It rejects data/eval/** before any read."""
    target = Path(path)
    if path_is_sealed(target, root):
        raise BlindSealError(target.as_posix())
    return _resolved(target, root).open(mode)


def opener_rejects_eval(root: Path) -> bool:
    probe = root / "data" / "eval" / "blind" / ".read-probe"
    try:
        handle = training_open(probe, root)
    except BlindSealError:
        return True
    else:
        handle.close()
        return False


def check_blind(root: Path) -> list[Finding]:
    findings = _static_reads(root)
    findings.extend(_hash_intersection(root))
    if not opener_rejects_eval(root):
        findings.append(
            Finding(
                "blind-seal",
                "data/eval",
                "training opener allowed a read of data/eval; the read must be rejected",
            )
        )
    return findings


def blind_summary(root: Path) -> str:
    sealed = seal_manifest(root)
    lines = [f"blind files hashed: {len(sealed)}"]
    lines.extend(f"  {item.digest}  {item.relpath}" for item in sealed)
    if _hash_intersection(root) or _static_reads(root):
        lines.append("training manifest ∩ blind ≠ ∅")
    else:
        lines.append("training manifest ∩ blind = ∅")
    if opener_rejects_eval(root):
        lines.append("training read attempt: REJECTED")
    else:
        lines.append("training read attempt: ALLOWED")
    return "\n".join(lines)


def _static_reads(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in training_code_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if any(pattern.search(text) for pattern in _READS):
            findings.append(
                Finding(
                    "blind-seal",
                    relpath(path, root),
                    "training code reads the sealed eval tree data/eval",
                )
            )
    return findings


def _hash_intersection(root: Path) -> list[Finding]:
    blind: dict[str, list[str]] = {}
    for item in seal_manifest(root):
        blind.setdefault(item.digest, []).append(item.relpath)
    findings: list[Finding] = []
    for item in training_manifest(root):
        blind_paths = blind.get(item.digest)
        if not blind_paths:
            continue
        shared = ", ".join(blind_paths)
        findings.append(
            Finding(
                "blind-seal",
                item.relpath,
                f"training manifest ∩ blind manifest share sha256 {item.digest} with {shared}",
            )
        )
    return findings
