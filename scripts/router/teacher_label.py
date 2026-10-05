"""Teacher labelling from document content. Dry-run writes nothing.

The prompt is fixed. The allowed labels are read from configs/router/labels.json
at call time. Unsure and low-confidence rows are not training rows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from router.content import model_user_text
from router.guard import RouterWall, refuse_sealed_input
from router.labels import confidence_floor, load_labels, load_sealed_config, repo_root
from router.sheet import UNSURE

_CARD = Path("docs/router/DATASET_CARD.md")
_MODEL_LINE = re.compile(r"^Model version:.*$", re.MULTILINE)

_PROMPT = """You assign one document-type label from the document text only.
Choose exactly one label from the list, or unsure when the text does not support one label.
The list is the only label set. Do not add a label.
Use only the document text in the next message.
Do not use a filename, a folder, a document id, or a project name. They are not provided.
Reply with one JSON object and no other text:
{{"label": "<one list entry or unsure>", "reason": "<one line>", "confidence": 0}}
Allowed labels:
{label_list}
"""

_KEY_ENV = ("TINKER_API_KEY", "ROUTER_TEACHER_API_KEY")


def prompt_for(labels: list[str]) -> str:
    lines = "\n".join(f"- {label}" for label in labels)
    return _PROMPT.format(label_list=lines)


def messages_for(row: dict, labels: list[str]) -> list[dict[str, str]] | None:
    """Build the teacher messages from content only. Returns None without content."""
    excerpt = model_user_text(row)
    if excerpt is None:
        return None
    return [
        {"role": "system", "content": prompt_for(labels)},
        {"role": "user", "content": excerpt},
    ]


def parse_teacher_response(text: str, labels: list[str]) -> dict:
    """One label from the file, or unsure. Anything else becomes unsure."""
    payload = _json_object(text)
    raw_label = payload.get("label")
    allowed = set(labels)
    if raw_label == UNSURE or raw_label not in allowed:
        label = UNSURE
    else:
        label = raw_label
    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""
    reason = " ".join(reason.split())
    confidence = _confidence(payload.get("confidence"))
    return {"label": label, "reason": reason, "confidence": confidence}


def eligible_for_train(
    row: dict,
    labels: list[str],
    floor: float | None,
) -> bool:
    """Unsure, unknown labels, missing confidence, and below-floor rows stay out."""
    label = row.get("label")
    if label not in set(labels):
        return False
    confidence = row.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return False
    if floor is None:
        return False
    return float(confidence) >= floor


def filter_for_train(
    rows: list[dict],
    labels: list[str],
    floor: float | None,
) -> list[dict]:
    return [row for row in rows if eligible_for_train(row, labels, floor)]


def label_rows(rows: list[dict], labels: list[str], respond) -> list[dict]:
    """Call respond(messages) for each content row. respond is injected by tests.

    The result keeps doc_id when the source had one, so a later sheet can join.
    Filename, project id, and Fork type are not copied onto the result.
    """
    labelled: list[dict] = []
    for row in rows:
        messages = messages_for(row, labels)
        if messages is None:
            continue
        parsed = parse_teacher_response(respond(messages), labels)
        if isinstance(row.get("doc_id"), str):
            parsed["doc_id"] = row["doc_id"]
        labelled.append(parsed)
    return labelled


def with_model_version(card: str, model: str) -> str:
    """Record a teacher model version on the dataset card text. Does not read env."""
    cleaned = model.strip()
    if not cleaned or any(char in cleaned for char in "\n\r"):
        raise RouterWall("WALL: model version missing")
    if not _MODEL_LINE.search(card):
        raise RouterWall("WALL: dataset card has no model line")
    return _MODEL_LINE.sub(f"Model version: {cleaned}", card, count=1)


def key_is_set() -> bool:
    """True when a teacher key is present. The value is never read out."""
    return any(bool(os.environ.get(name)) for name in _KEY_ENV)


def dry_run_report(rows: list[dict], labels: list[str]) -> dict:
    content_rows = sum(1 for row in rows if messages_for(row, labels) is not None)
    return {
        "status": "dry-run",
        "content_rows": content_rows,
        "labelled": 0,
        "wrote": False,
        "api_key_present": key_is_set(),
    }


def _load_input(path: Path | None, root: Path) -> list[dict]:
    if path is None:
        return []
    refuse_sealed_input(path, root)
    if not path.is_file():
        return []
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RouterWall(f"WALL: {path}:{lineno}: {exc}") from exc
        if not isinstance(obj, dict):
            raise RouterWall(f"WALL: {path}:{lineno}: record is not an object")
        rows.append(obj)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Teacher-label router documents from content")
    parser.add_argument("--input", type=Path, default=None, help="JSONL pool. Omit for a 0-row dry run.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Refused until a sealed owner corpus exists and a teacher client is configured.",
    )
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    try:
        labels = load_labels(root / "configs" / "router" / "labels.json")
        config = load_sealed_config(root / "configs" / "router" / "sealed_eval.json")
        rows = _load_input(args.input, root)
        if args.write:
            _refuse_write(root)
        report = dry_run_report(rows, labels)
        report["confidence_floor"] = confidence_floor(config)
    except RouterWall as exc:
        print(str(exc))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


def _refuse_write(root: Path) -> None:
    sealed = root / "data" / "sealed" / "router" / "sealed_labels.jsonl"
    # Size only. Do not parse sealed rows or model output.
    if not sealed.is_file() or sealed.stat().st_size == 0:
        raise RouterWall("WALL: sealed eval labels are absent; refusing to write training labels")
    raise RouterWall("WALL: teacher client is not configured; refusing to write training labels")


def _json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[A-Za-z0-9]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    return obj


def _confidence(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number < 0.0 or number > 1.0:
        return None
    return number


if __name__ == "__main__":
    raise SystemExit(main())
