"""Locate private data that is not stored in the working tree.

The working tree does not carry the archive, sealed labels, held-out shards,
or owner files. Callers outside training and dataset generation resolve a
repo-relative path here.

Resolution, for the repository root only (a temporary tree never consults
the environment):

1. ``root / relative`` when that path exists.
2. The specific environment variable for that path, when set.
3. ``$SLM_PRIVATE_ROOT / relative`` when ``SLM_PRIVATE_ROOT`` is set.

``require`` raises ``PrivateDataError`` when the file or directory is absent.
The message names the relative path and the environment variable. It does
not include file contents.

Specific variables:

- ``SLM_DATASETS_ZIP`` — ``data/raw/slm-datasets.zip``
- ``SLM_HELD_OUT_DIR`` — ``data/held_out``
- ``SLM_HELD_OUT_SHARDS`` — ``data/held_out/shards.json``
- ``SLM_HELD_OUT_PAIRS`` — ``data/held_out/pairs.jsonl``
- ``SLM_HELD_OUT_MANIFEST`` — ``data/held_out/manifest.json``
- ``SLM_TRANSCRIPTS_JSONL`` — ``docs/serve/transcripts-epoch2.jsonl``
- ``SLM_PRIVATE_ROOT`` — a directory laid out like the repo, used for every
  other private relative path (sealed labels, owner files, isolation files).
"""

from __future__ import annotations

import os
from pathlib import Path

SPECIFIC_ENV = {
    "data/raw/slm-datasets.zip": "SLM_DATASETS_ZIP",
    "data/held_out": "SLM_HELD_OUT_DIR",
    "data/held_out/shards.json": "SLM_HELD_OUT_SHARDS",
    "data/held_out/pairs.jsonl": "SLM_HELD_OUT_PAIRS",
    "data/held_out/manifest.json": "SLM_HELD_OUT_MANIFEST",
    "docs/serve/transcripts-epoch2.jsonl": "SLM_TRANSCRIPTS_JSONL",
}


class PrivateDataError(FileNotFoundError):
    """A private file or directory is not available. The message has no file contents."""


def _is_repo(root: Path) -> bool:
    return (root / "pyproject.toml").is_file() and (root / "scripts" / "private_data.py").is_file()


def env_for(relative: str) -> str:
    text = relative.replace("\\", "/").rstrip("/")
    if text in SPECIFIC_ENV:
        return SPECIFIC_ENV[text]
    if text == "data/held_out" or text.startswith("data/held_out/"):
        return "SLM_HELD_OUT_DIR"
    return "SLM_PRIVATE_ROOT"


def missing_message(relative: str, env: str | None = None) -> str:
    variable = env or env_for(relative)
    return (
        f"private data is absent: {relative}. "
        f"Set {variable} or SLM_PRIVATE_ROOT to an external path that contains {relative}. "
        "Refusing to continue without the file."
    )


def locate(root: Path, relative: str, env: str | None = None) -> Path:
    """Return the path to use. Does not require the file to exist."""
    rel = relative.replace("\\", "/").lstrip("/")
    local = root / rel
    if local.exists():
        return local
    if not _is_repo(root):
        return local
    variable = env or env_for(rel)
    override = os.environ.get(variable, "").strip()
    if override and variable != "SLM_PRIVATE_ROOT":
        if variable == "SLM_HELD_OUT_DIR" and rel.startswith("data/held_out/"):
            rest = rel[len("data/held_out/") :]
            return Path(override) / rest
        return Path(override)
    private = os.environ.get("SLM_PRIVATE_ROOT", "").strip()
    if private:
        return Path(private) / rel
    held = os.environ.get("SLM_HELD_OUT_DIR", "").strip()
    if held and (rel == "data/held_out" or rel.startswith("data/held_out/")):
        if rel == "data/held_out":
            return Path(held)
        return Path(held) / rel[len("data/held_out/") :]
    return local


def require(root: Path, relative: str, env: str | None = None) -> Path:
    """Return an existing file or directory, or raise ``PrivateDataError``."""
    path = locate(root, relative, env)
    if path.exists():
        return path
    raise PrivateDataError(missing_message(relative, env))
