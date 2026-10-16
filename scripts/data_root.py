"""Repo data root. SLM_DATA_ROOT overrides; otherwise this checkout."""

from __future__ import annotations

import os
from pathlib import Path


def code_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    override = os.environ.get("SLM_DATA_ROOT", "").strip()
    if override:
        return Path(override)
    return code_root()
