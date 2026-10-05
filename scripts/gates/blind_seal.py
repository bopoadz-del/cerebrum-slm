"""Blind-set seal: hash data/eval/** and keep the training path from reading it."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from gates.findings import Finding
from gates.records import RAW_ZIP, iter_training_files, relpath, sha256_file

_DIGEST = re.compile(r"^[0-9a-fA-F]{64}$")

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
    findings.extend(check_committed_seals(root))
    if not opener_rejects_eval(root):
        findings.append(
            Finding(
                "blind-seal",
                "data/eval",
                "training opener allowed a read of data/eval; the read must be rejected",
            )
        )
    return findings


def check_committed_seals(root: Path) -> list[Finding]:
    """A payload under data/eval must match the seal committed beside it."""
    base = root / "data" / "eval"
    if not base.is_dir():
        return []
    findings: list[Finding] = []
    named: set[str] = set()
    for path in _files(base):
        if path.name.endswith(".sha256"):
            findings.extend(_check_sha256_sidecar(path, root, named))
        elif path.name == "seal.json":
            findings.extend(_check_seal_json(path, root, named))
    for path in _files(base):
        if not _payload_needs_seal(path):
            continue
        where = relpath(path, root)
        if where not in named:
            findings.append(Finding("blind-seal", where, "missing seal"))
    return findings


def _files(base: Path) -> list[Path]:
    return sorted(item for item in base.rglob("*") if item.is_file())


def _payload_needs_seal(path: Path) -> bool:
    if path.name == "seal.json":
        return False
    return path.suffix.lower() in {".json", ".jsonl"}


def _check_sha256_sidecar(path: Path, root: Path, named: set[str]) -> list[Finding]:
    where = relpath(path, root)
    try:
        parsed = _parse_sha256_lines(path.read_text(encoding="utf-8"))
    except UnicodeError:
        return [Finding("blind-seal", where, "sha256 seal is not UTF-8")]
    if parsed is None:
        return [Finding("blind-seal", where, "sha256 seal line is not 'digest filename'")]
    if not parsed:
        return [Finding("blind-seal", where, "sha256 seal lists no artifact")]
    findings: list[Finding] = []
    for digest, name in parsed:
        artifact = _resolve_artifact(path, name, root)
        if artifact is None:
            findings.append(
                Finding("blind-seal", where, f"seal artifact is outside data/eval: {name}")
            )
            continue
        _bind_artifact(artifact, digest, root, named, findings)
    return findings


def _check_seal_json(path: Path, root: Path, named: set[str]) -> list[Finding]:
    where = relpath(path, root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeError:
        return [Finding("blind-seal", where, "seal.json is not UTF-8")]
    except json.JSONDecodeError:
        return [Finding("blind-seal", where, "seal.json is not JSON")]
    if not isinstance(data, dict):
        return [Finding("blind-seal", where, "seal.json must be an object")]
    findings: list[Finding] = []
    algorithm = data.get("algorithm")
    artifact_name = data.get("artifact")
    digest = data.get("sha256")
    if algorithm != "sha256" or not isinstance(artifact_name, str) or not isinstance(digest, str):
        return [Finding("blind-seal", where, "seal.json must name a sha256 artifact")]
    if _DIGEST.fullmatch(digest) is None:
        return [Finding("blind-seal", where, "seal.json sha256 is not a digest")]
    artifact = _resolve_artifact(path, artifact_name, root)
    if artifact is None:
        return [
            Finding(
                "blind-seal",
                where,
                f"seal artifact is outside data/eval: {artifact_name}",
            )
        ]
    if not _bind_artifact(artifact, digest, root, named, findings):
        return findings
    if "count" in data:
        findings.extend(_check_count(artifact, data.get("count"), root))
    if "source_zip_sha256" in data:
        findings.extend(_check_source_zip(path, data.get("source_zip_sha256"), root))
    return findings


def _bind_artifact(
    artifact: Path,
    digest: str,
    root: Path,
    named: set[str],
    findings: list[Finding],
) -> bool:
    where = relpath(artifact, root)
    named.add(where)
    if not artifact.is_file():
        findings.append(Finding("blind-seal", where, "sealed artifact is missing"))
        return False
    actual = sha256_file(artifact)
    if actual.lower() != digest.lower():
        findings.append(
            Finding(
                "blind-seal",
                where,
                f"sha256 mismatch: seal {digest.lower()} file {actual}",
            )
        )
        return False
    return True


def _check_count(artifact: Path, count: object, root: Path) -> list[Finding]:
    where = relpath(artifact, root)
    if isinstance(count, bool) or not isinstance(count, int):
        return [Finding("blind-seal", where, "seal count is not an integer")]
    try:
        text = artifact.read_text(encoding="utf-8")
    except UnicodeError:
        return [Finding("blind-seal", where, "sealed artifact is not UTF-8")]
    actual = sum(1 for line in text.splitlines() if line.strip())
    if actual != count:
        return [
            Finding(
                "blind-seal",
                where,
                f"seal count mismatch: seal {count} file {actual}",
            )
        ]
    return []


def _check_source_zip(seal_path: Path, digest: object, root: Path) -> list[Finding]:
    where = relpath(seal_path, root)
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        return [Finding("blind-seal", where, "source_zip_sha256 is not a digest")]
    zip_path = root / RAW_ZIP
    if not zip_path.is_file():
        return [Finding("blind-seal", where, "source_zip_sha256 archive is missing")]
    actual = sha256_file(zip_path)
    if actual.lower() != digest.lower():
        return [
            Finding(
                "blind-seal",
                where,
                f"source_zip_sha256 mismatch: seal {digest.lower()} archive {actual}",
            )
        ]
    return []


def _parse_sha256_lines(text: str) -> list[tuple[str, str]] | None:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) != 2 or _DIGEST.fullmatch(parts[0]) is None:
            return None
        name = parts[1].strip()
        if name.startswith("*"):
            name = name[1:]
        if not name:
            return None
        rows.append((parts[0], name))
    return rows


def _resolve_artifact(seal_path: Path, name: str, root: Path) -> Path | None:
    relative = Path(name)
    if relative.is_absolute() or any(part == ".." for part in relative.parts):
        return None
    candidate = (seal_path.parent / relative).resolve()
    eval_root = (root.resolve() / "data" / "eval").resolve()
    try:
        candidate.relative_to(eval_root)
    except ValueError:
        return None
    return candidate


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
