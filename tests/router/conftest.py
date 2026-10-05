from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def router_root(tmp_path: Path) -> Path:
    for name in ("labels.json", "dataset.json"):
        dest = tmp_path / "configs" / "router" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "configs" / "router" / name, dest)
    (tmp_path / "data" / "raw" / "router").mkdir(parents=True)
    return tmp_path
