"""Load the router label set and dataset contract from config files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from router.errors import RouterConfigError

_DATASET_FILE = Path("configs") / "router" / "dataset.json"
_REQUIRED_FIELDS = ("filename", "label", "project_id", "sha256", "text")
_SEAL_RULE = "largest_then_lowest_project_sha256"
_TOKEN_UNIT = "whitespace"


@dataclass(frozen=True)
class DatasetConfig:
    task: str
    labels: tuple[str, ...]
    max_input_tokens: int
    token_unit: str
    input_template: str
    holdout_numerator: int
    holdout_denominator: int
    seal_rule: str
    raw_dir: str
    eval_dir: str
    seal_doc: str
    sealed_artifact: str
    fields: dict[str, tuple[str, ...]]

    def path(self, root: Path, relative: str) -> Path:
        return root / relative


def load_config(root: Path) -> DatasetConfig:
    dataset_path = root / _DATASET_FILE
    dataset = _read_object(dataset_path)
    labels_rel = _relative(dataset.get("labels_file"), "labels_file")
    labels_obj = _read_object(root / labels_rel)
    task = _text(dataset.get("task"), "task")
    if _text(labels_obj.get("task"), "labels task") != task:
        raise RouterConfigError("labels task does not match the dataset task")
    labels = _labels(labels_obj.get("labels"))
    fields = _fields(dataset.get("fields"))
    template = _text(dataset.get("input_template"), "input_template")
    if template.count("{filename}") != 1 or template.count("{prefix}") != 1:
        raise RouterConfigError("input_template must contain {filename} and {prefix} once each")
    token_unit = _text(dataset.get("token_unit"), "token_unit")
    if token_unit != _TOKEN_UNIT:
        raise RouterConfigError("token unit is not implemented")
    seal_rule = _text(dataset.get("seal_rule"), "seal_rule")
    if seal_rule != _SEAL_RULE:
        raise RouterConfigError("seal rule is not implemented")
    numerator = _integer(dataset.get("holdout_numerator"), "holdout_numerator", 0)
    denominator = _integer(dataset.get("holdout_denominator"), "holdout_denominator", 1)
    if numerator > denominator:
        raise RouterConfigError("holdout numerator exceeds its denominator")
    return DatasetConfig(
        task=task,
        labels=labels,
        max_input_tokens=_integer(dataset.get("max_input_tokens"), "max_input_tokens", 1),
        token_unit=token_unit,
        input_template=template,
        holdout_numerator=numerator,
        holdout_denominator=denominator,
        seal_rule=seal_rule,
        raw_dir=_relative(dataset.get("raw_dir"), "raw_dir"),
        eval_dir=_relative(dataset.get("eval_dir"), "eval_dir"),
        seal_doc=_relative(dataset.get("seal_doc"), "seal_doc"),
        sealed_artifact=_artifact(dataset.get("sealed_artifact")),
        fields=fields,
    )


def _read_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RouterConfigError(f"{path.name} is not a JSON object") from exc
    if not isinstance(data, dict):
        raise RouterConfigError(f"{path.name} is not a JSON object")
    return data


def _labels(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RouterConfigError("labels must be a non-empty list")
    labels: list[str] = []
    for item in value:
        if not isinstance(item, str) or item.strip() != item or not item:
            raise RouterConfigError("a label is empty or padded")
        if any(char.isspace() and char != " " for char in item):
            raise RouterConfigError("a label contains a line break")
        labels.append(item)
    if len(set(labels)) != len(labels):
        raise RouterConfigError("labels are not unique")
    folded = [label.casefold() for label in labels]
    if len(set(folded)) != len(folded):
        raise RouterConfigError("labels collide under case folding")
    return tuple(labels)


def _fields(value: object) -> dict[str, tuple[str, ...]]:
    if not isinstance(value, dict):
        raise RouterConfigError("fields must be an object")
    if set(value) != set(_REQUIRED_FIELDS):
        raise RouterConfigError("fields must name filename, label, project_id, sha256, and text")
    fields: dict[str, tuple[str, ...]] = {}
    seen: set[str] = set()
    for name in _REQUIRED_FIELDS:
        aliases = value[name]
        if not isinstance(aliases, list) or not aliases:
            raise RouterConfigError(f"{name} aliases must be a non-empty list")
        cleaned: list[str] = []
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip() or alias != alias.strip():
                raise RouterConfigError(f"{name} has a blank alias")
            folded = alias.casefold()
            if folded in seen:
                raise RouterConfigError("field aliases overlap")
            seen.add(folded)
            cleaned.append(alias)
        fields[name] = tuple(cleaned)
    return fields


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RouterConfigError(f"{name} must be text")
    return value


def _relative(value: object, name: str) -> str:
    text = _text(value, name)
    path = Path(text)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise RouterConfigError(f"{name} must be a relative path")
    return path.as_posix()


def _artifact(value: object) -> str:
    text = _text(value, "sealed_artifact")
    path = Path(text)
    if len(path.parts) != 1 or path.name in {".", ".."}:
        raise RouterConfigError("sealed_artifact must be a file name")
    return path.name


def _integer(value: object, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RouterConfigError(f"{name} must be an integer")
    if value < minimum:
        raise RouterConfigError(f"{name} is below the minimum")
    return value
