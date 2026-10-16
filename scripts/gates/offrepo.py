"""Hash manifest for blobs removed from the public tree.

When a sealed or raw payload is in the tree, callers still hash the bytes.
When it is absent, callers require a well-formed entry here instead.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from gates.findings import Finding

MANIFEST = Path("data/OFFREPO_MANIFEST.json")
_DIGEST = re.compile(r"^[0-9a-fA-F]{64}$")


def path_sha256(relpath: str) -> str:
    return hashlib.sha256(relpath.encode("utf-8")).hexdigest()


def load_entries(root: Path) -> list[dict]:
    path = root / MANIFEST
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return []
    return [item for item in entries if isinstance(item, dict)]


def entry_for(root: Path, relpath: str) -> dict | None:
    digest = path_sha256(relpath)
    for item in load_entries(root):
        if item.get("path_sha256") == digest:
            return item
    return None


def checkout_absent(root: Path, relpath: str, gate: str) -> list[Finding]:
    """On a checkout, an absent payload must be in the hash manifest.

    Synthetic trees without pyproject.toml keep the previous behaviour:
    a missing file is simply not scanned.
    """
    if (root / relpath).is_file():
        return []
    if not (root / "pyproject.toml").is_file():
        return []
    return require_entry(root, relpath, gate)


def require_entry(root: Path, relpath: str, gate: str) -> list[Finding]:
    """Fail unless the manifest lists this path with a sha256 digest."""
    path = root / MANIFEST
    if not path.is_file():
        return [Finding(gate, MANIFEST.as_posix(), "off-repo hash manifest is missing")]
    item = entry_for(root, relpath)
    if item is None:
        return [Finding(gate, relpath, "absent payload is not in the off-repo hash manifest")]
    digest = item.get("sha256")
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        return [Finding(gate, relpath, "off-repo manifest sha256 is not a digest")]
    return []
