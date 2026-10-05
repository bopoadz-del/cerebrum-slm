"""Normalize an external label export. Nothing here assigns a label."""

from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from router.config import DatasetConfig, load_config
from router.errors import LabelExportMissing

_EXPORT_SUFFIXES = {".jsonl", ".csv"}


@dataclass(frozen=True)
class DocumentRecord:
    sha256: str
    project_id: str
    project_id_sha256: str
    filename: str
    text: str
    prefix: str
    label: str
    source: str
    line: int
    sha_disagreement: bool


@dataclass(frozen=True)
class Reject:
    source: str
    line: int
    reason: str


@dataclass(frozen=True)
class Corpus:
    records: tuple[DocumentRecord, ...]
    rejects: tuple[Reject, ...]
    duplicates: int
    conflicts: int
    sha_disagreements: int
    export_names: tuple[str, ...]
    exports_sha256: str
    rows_read: int


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    """NFC, one newline style, outer trim. Internal spaces stay for the sha."""
    cleaned = unicodedata.normalize("NFC", text).replace("\ufeff", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned.strip()


def normalize_filename(text: str) -> str:
    cleaned = normalize_text(text).replace("\\", "/")
    cleaned = cleaned.rsplit("/", 1)[-1]
    return " ".join(cleaned.split())


def normalize_token(text: str) -> str:
    return " ".join(normalize_text(text).split())


def prefix_text(text: str, limit: int) -> str:
    return " ".join(text.split()[:limit])


def canonicalize_label(token: str, labels: tuple[str, ...]) -> str | None:
    if token in labels:
        return token
    folded = token.casefold()
    matches = [label for label in labels if label.casefold() == folded]
    if len(matches) == 1:
        return matches[0]
    return None


def render_prompt(template: str, filename: str, prefix: str) -> str:
    marked = template.replace("{filename}", "\0fn\0").replace("{prefix}", "\0px\0")
    return marked.replace("\0fn\0", filename).replace("\0px\0", prefix)


def load_corpus(root: Path, config: DatasetConfig | None = None) -> Corpus:
    dataset = load_config(root) if config is None else config
    raw = root / dataset.raw_dir
    exports = _export_files(raw)
    if not exports:
        raise LabelExportMissing("no JSONL or CSV export under data/raw/router")
    accepted: list[DocumentRecord] = []
    rejects: list[Reject] = []
    rows_read = 0
    for path in exports:
        file_rejects, file_records, file_rows = _read_export(path, dataset)
        rejects.extend(file_rejects)
        accepted.extend(file_records)
        rows_read += file_rows
    kept, duplicates, conflicts = _dedupe(accepted)
    kept, prompt_conflicts = _drop_identical_inputs(kept)
    conflicts += prompt_conflicts
    if not kept:
        reasons = dict(sorted(Counter(item.reason for item in rejects).items()))
        raise LabelExportMissing("export has no labeled rows", reasons)
    disagreements = sum(1 for item in accepted if item.sha_disagreement)
    return Corpus(
        records=tuple(kept),
        rejects=tuple(rejects),
        duplicates=duplicates,
        conflicts=conflicts,
        sha_disagreements=disagreements,
        export_names=tuple(path.name for path in exports),
        exports_sha256=_hash_exports(exports, root),
        rows_read=rows_read,
    )


def _export_files(raw: Path) -> list[Path]:
    if not raw.is_dir():
        return []
    files = [
        path
        for path in raw.iterdir()
        if path.is_file() and path.suffix.lower() in _EXPORT_SUFFIXES
    ]
    return sorted(files, key=lambda path: path.name)


def _hash_exports(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _read_export(
    path: Path, config: DatasetConfig
) -> tuple[list[Reject], list[DocumentRecord], int]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return [Reject(path.name, 0, "not_utf8")], [], 0
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path.name, text, config)
    return _read_jsonl(path.name, text, config)


def _read_jsonl(
    source: str, text: str, config: DatasetConfig
) -> tuple[list[Reject], list[DocumentRecord], int]:
    rejects: list[Reject] = []
    records: list[DocumentRecord] = []
    rows = 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        rows += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            rejects.append(Reject(source, lineno, "invalid_json"))
            continue
        if not isinstance(obj, dict):
            rejects.append(Reject(source, lineno, "not_object"))
            continue
        record, reason = _parse_row(obj, config, source, lineno)
        if reason is not None or record is None:
            rejects.append(Reject(source, lineno, reason or "missing_label"))
            continue
        records.append(record)
    return rejects, records, rows


def _read_csv(
    source: str, text: str, config: DatasetConfig
) -> tuple[list[Reject], list[DocumentRecord], int]:
    rejects: list[Reject] = []
    records: list[DocumentRecord] = []
    rows = 0
    try:
        reader = csv.DictReader(text.splitlines())
        parsed_rows = list(reader)
    except csv.Error:
        return [Reject(source, 0, "invalid_csv")], [], 0
    if reader.fieldnames is None:
        return rejects, records, rows
    for lineno, row in enumerate(parsed_rows, 2):
        if row is None or _blank_row(row):
            continue
        rows += 1
        record, reason = _parse_row(row, config, source, lineno)
        if reason is not None or record is None:
            rejects.append(Reject(source, lineno, reason or "missing_label"))
            continue
        records.append(record)
    return rejects, records, rows


def _blank_row(row: dict) -> bool:
    return all(value is None or (isinstance(value, str) and not value.strip()) for value in row.values())


def _parse_row(
    row: dict, config: DatasetConfig, source: str, line: int
) -> tuple[DocumentRecord | None, str | None]:
    project, reason = _required(row, config.fields["project_id"], "missing_project")
    if reason or project is None:
        return None, reason
    filename, reason = _required(row, config.fields["filename"], "missing_filename")
    if reason or filename is None:
        return None, reason
    text, reason = _required(row, config.fields["text"], "missing_text")
    if reason or text is None:
        return None, reason
    label_token, reason = _required(row, config.fields["label"], "missing_label")
    if reason or label_token is None:
        return None, reason
    project_id = normalize_token(project)
    filename_text = normalize_filename(filename)
    document = normalize_text(text)
    label_text = normalize_token(label_token)
    if not project_id:
        return None, "missing_project"
    if not filename_text:
        return None, "missing_filename"
    if not document:
        return None, "missing_text"
    if not label_text:
        return None, "missing_label"
    label = canonicalize_label(label_text, config.labels)
    if label is None:
        return None, "unknown_label"
    sha_reason, disagreement = _provided_sha(row, config.fields["sha256"], document)
    if sha_reason:
        return None, sha_reason
    return (
        DocumentRecord(
            sha256=sha256_text(document),
            project_id=project_id,
            project_id_sha256=sha256_text(project_id),
            filename=filename_text,
            text=document,
            prefix=prefix_text(document, config.max_input_tokens),
            label=label,
            source=source,
            line=line,
            sha_disagreement=disagreement,
        ),
        None,
    )


def _required(row: dict, aliases: tuple[str, ...], missing: str) -> tuple[str | None, str | None]:
    value, reason = _pick(row, aliases)
    if reason:
        return None, reason
    if value is None:
        return None, missing
    return value, None


def _pick(row: dict, aliases: tuple[str, ...]) -> tuple[str | None, str | None]:
    folded = {str(key).casefold(): key for key in row if key is not None}
    found: list[str] = []
    for alias in aliases:
        key = folded.get(alias.casefold())
        if key is None:
            continue
        value = row[key]
        if value is None:
            continue
        if not isinstance(value, str):
            return None, "field_not_text"
        found.append(value.strip())
    if not found:
        return None, None
    if len(set(found)) > 1:
        return None, "ambiguous_field"
    return found[0], None


def _provided_sha(row: dict, aliases: tuple[str, ...], document: str) -> tuple[str | None, bool]:
    value, reason = _pick(row, aliases)
    if reason:
        return reason, False
    if value is None or not value.strip():
        return None, False
    token = value.strip().lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        return None, False
    return None, token != sha256_text(document)


def _dedupe(records: list[DocumentRecord]) -> tuple[list[DocumentRecord], int, int]:
    groups: dict[str, list[DocumentRecord]] = defaultdict(list)
    for record in records:
        groups[record.sha256].append(record)
    kept: list[DocumentRecord] = []
    duplicates = 0
    conflicts = 0
    for digest in sorted(groups):
        group = sorted(groups[digest], key=lambda item: (item.source, item.line))
        labels = {item.label for item in group}
        projects = {item.project_id for item in group}
        if len(labels) != 1 or len(projects) != 1:
            conflicts += 1
            continue
        kept.append(group[0])
        duplicates += len(group) - 1
    kept.sort(key=lambda item: item.sha256)
    return kept, duplicates, conflicts


def _drop_identical_inputs(records: list[DocumentRecord]) -> tuple[list[DocumentRecord], int]:
    """Drop rows that share a filename and prefix but disagree on the label.

    The model sees that pair as one input. Disagreeing labels are a conflict,
    not a tie for the code to break.
    """
    groups: dict[tuple[str, str], list[DocumentRecord]] = defaultdict(list)
    for record in records:
        groups[(record.filename, record.prefix)].append(record)
    kept: list[DocumentRecord] = []
    conflicts = 0
    for key in sorted(groups):
        group = groups[key]
        if len({item.label for item in group}) != 1:
            conflicts += 1
            continue
        kept.extend(group)
    kept.sort(key=lambda item: item.sha256)
    return kept, conflicts
