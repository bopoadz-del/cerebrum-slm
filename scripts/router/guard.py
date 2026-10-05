"""Stops labelling tools from reading the sealed owner corpus."""

from __future__ import annotations

from pathlib import Path

from router.labels import repo_root


class RouterWall(Exception):
    """A blocking condition. No training labels were written."""


def refuse_sealed_input(path: Path, root: Path | None = None) -> None:
    base = ((root or repo_root()) / "data" / "sealed").resolve()
    try:
        path.resolve().relative_to(base)
    except ValueError:
        return
    raise RouterWall("WALL: sealed corpus")
