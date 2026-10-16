"""Sha256 manifest for the untouched raw archive."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from gates.findings import Finding
from gates.offrepo import entry_for, require_entry
from gates.records import RAW_ZIP, sha256_file

MANIFEST = Path("data/raw/SHA256SUMS")
ZIP_NAME = "slm-datasets.zip"
_DIGEST = re.compile(r"^[0-9a-fA-F]{64}$")


def parse_manifest(text: str) -> dict[str, str]:
    listed: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        if len(parts) == 1:
            if _DIGEST.fullmatch(parts[0]) is None:
                raise ValueError(stripped)
            listed.setdefault(ZIP_NAME, parts[0])
            continue
        digest, name = parts
        listed[name.strip().lstrip("*")] = digest
    return listed


def check_raw(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    zip_path = root / RAW_ZIP
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        findings.append(
            Finding("raw", MANIFEST.as_posix(), "sha256 manifest is missing")
        )
        if not zip_path.is_file():
            findings.append(Finding("raw", RAW_ZIP.as_posix(), "raw archive is missing"))
        return findings

    try:
        listed = parse_manifest(manifest_path.read_text(encoding="utf-8"))
    except ValueError:
        findings.append(
            Finding("raw", MANIFEST.as_posix(), "sha256 manifest line is not 'digest filename'")
        )
        return findings

    expected = listed.get(ZIP_NAME)
    if expected is None or _DIGEST.fullmatch(expected) is None:
        findings.append(
            Finding(
                "raw",
                MANIFEST.as_posix(),
                f"manifest must list {ZIP_NAME} with a sha256 digest",
            )
        )
        return findings

    if not zip_path.is_file():
        # Bytes are off-repo. The sums digest must still match the hash manifest.
        findings.extend(require_entry(root, RAW_ZIP.as_posix(), "raw"))
        item = entry_for(root, RAW_ZIP.as_posix())
        listed_digest = item.get("sha256") if item else None
        if isinstance(listed_digest, str) and listed_digest.lower() != expected.lower():
            findings.append(
                Finding(
                    "raw",
                    RAW_ZIP.as_posix(),
                    f"sha256 mismatch: manifest {expected.lower()} off-repo {listed_digest.lower()}",
                )
            )
        return findings

    actual = sha256_file(zip_path)
    if actual.lower() != expected.lower():
        findings.append(
            Finding(
                "raw",
                RAW_ZIP.as_posix(),
                f"sha256 mismatch: manifest {expected.lower()} archive {actual}",
            )
        )
    if not zipfile.is_zipfile(zip_path):
        findings.append(Finding("raw", RAW_ZIP.as_posix(), "raw archive is not a zip"))
    return findings
