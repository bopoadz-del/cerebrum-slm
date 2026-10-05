"""The label set is the JSON file. Callers load it; they do not keep a copy."""

from __future__ import annotations

import json
from pathlib import Path


class LabelConfigError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def labels_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "configs" / "router" / "labels.json"


def sealed_config_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "configs" / "router" / "sealed_eval.json"


def load_labels(path: Path | None = None) -> list[str]:
    """Return the declared label strings in file order."""
    source = path or labels_path()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabelConfigError(f"label file is unreadable: {source}") from exc
    if not isinstance(data, dict):
        raise LabelConfigError("label file must be an object")
    labels = data.get("labels")
    if not isinstance(labels, list) or not labels:
        raise LabelConfigError("label file has no labels array")
    cleaned: list[str] = []
    for item in labels:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise LabelConfigError("each label must be a non-empty string")
        cleaned.append(item)
    if len(set(cleaned)) != len(cleaned):
        raise LabelConfigError("label file repeats a label")
    return cleaned


def load_sealed_config(path: Path | None = None) -> dict:
    source = path or sealed_config_path()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabelConfigError(f"sealed eval config is unreadable: {source}") from exc
    if not isinstance(data, dict):
        raise LabelConfigError("sealed eval config must be an object")
    _require_int(data, "n")
    _require_int(data, "per_label")
    threshold = data.get("agreement_threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise LabelConfigError("agreement_threshold must be a number")
    if not isinstance(data.get("majority_class_fail"), bool):
        raise LabelConfigError("majority_class_fail must be a boolean")
    teacher = data.get("teacher")
    if not isinstance(teacher, dict):
        raise LabelConfigError("teacher settings must be an object")
    for key in ("provider", "model", "temperature", "confidence_floor"):
        if key not in teacher:
            raise LabelConfigError(f"teacher.{key} is missing")
    note = data.get("note")
    if not isinstance(note, str) or not note.strip():
        raise LabelConfigError("sealed eval config needs a note")
    return data


def confidence_floor(config: dict) -> float | None:
    value = config["teacher"]["confidence_floor"]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LabelConfigError("teacher.confidence_floor must be a number or null")
    return float(value)


def _require_int(data: dict, key: str) -> None:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise LabelConfigError(f"{key} must be an integer")
