"""Seal a practitioner-labelled router sheet.

The ticked column is the owner's label. It is copied, not edited, and not
inferred from a path, filename, folder, or id. Unsure rows and rows marked
excluded_from_eval are omitted. A hidden proposal file is used only for an
agreement statistic.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from router.guard import RouterWall
from router.labels import load_labels, load_sealed_config, repo_root
from router.sheet import UNSURE

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_TICK = {"1", "x", "y", "yes", "true", "t", "✓", "✔"}
_FALSE = {"", "0", "n", "no", "false", "f"}


def corpus_project(source_path: object) -> str | None:
    """Top-level corpus folder. A bare filename is not a project and not a label."""
    if not isinstance(source_path, str):
        return None
    text = source_path.strip().replace("\\", "/")
    parts = [part for part in text.split("/") if part not in {"", "."}]
    if len(parts) < 2:
        return None
    return parts[0]


def seal_sheet(
    sheet: Path,
    output_dir: Path,
    labels: list[str],
    *,
    proposed: Path | None = None,
) -> dict:
    """Validate the sheet and write sealed labels. Raises without writing on a bad tick."""
    header, rows = read_table(sheet)
    _require_header(header, labels)
    sealed, dropped = _select(rows, labels)
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / "sealed_labels.jsonl"
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in sealed)
    labels_path.write_text(payload, encoding="utf-8")
    written = ["sealed_labels.jsonl"]
    agreement_path = output_dir / "agreement.json"
    if proposed is not None:
        before = labels_path.read_bytes()
        stats = agreement(sealed, _read_proposed(proposed), labels)
        agreement_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if labels_path.read_bytes() != before:
            raise RouterWall("WALL: agreement rewrote a sealed label")
        written.append("agreement.json")
    _write_digests(output_dir, written)
    return {"sealed": len(sealed), "dropped": dropped, "files": written}


def agreement(sealed: list[dict], proposed: dict[str, str], labels: list[str]) -> dict:
    """Per-label and overall agreement. Does not return replacement labels."""
    per_label: dict[str, float | None] = {}
    compared = 0
    matched = 0
    for label in labels:
        owned = [row for row in sealed if row.get("label") == label and row.get("sheet_id") in proposed]
        if not owned:
            per_label[label] = None
            continue
        hits = sum(1 for row in owned if proposed[row["sheet_id"]] == label)
        per_label[label] = hits / len(owned)
        compared += len(owned)
        matched += hits
    return {
        "compared": compared,
        "overall": None if compared == 0 else matched / compared,
        "per_label": per_label,
        "note": "Agreement does not change sealed labels.",
    }


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".xlsx":
        return _read_xlsx(path)
    raise RouterWall("WALL: sheet must be csv or xlsx")


def _require_header(header: list[str], labels: list[str]) -> None:
    present = set(header)
    if any(label not in present for label in (*labels, UNSURE)):
        raise RouterWall("WALL: sheet header is missing a declared label column")


def _select(rows: list[dict[str, str]], labels: list[str]) -> tuple[list[dict], dict[str, int]]:
    allowed = [*labels, UNSURE]
    sealed: list[dict] = []
    dropped = {"unsure": 0, "excluded_from_eval": 0}
    for index, row in enumerate(rows, start=2):
        ticked = _ticked(row, allowed)
        sheet_id = row.get("sheet_id") or f"row-{index}"
        if len(ticked) != 1:
            raise RouterWall(f"WALL: {sheet_id} does not have exactly one tick")
        label = ticked[0]
        if _excluded(row.get("excluded_from_eval")):
            dropped["excluded_from_eval"] += 1
            continue
        if label == UNSURE:
            dropped["unsure"] += 1
            continue
        sealed.append(_sealed_row(row, label, sheet_id))
    return sealed, dropped


def _sealed_row(row: dict[str, str], label: str, sheet_id: str) -> dict:
    """Copy the owner tick. Path fields stay out of the label."""
    sealed = {
        "sheet_id": sheet_id,
        "label": label,
        "file_sha256": _blank_none(row.get("file_sha256")),
        "project": corpus_project(row.get("source_path")),
    }
    excerpt = row.get("excerpt")
    if isinstance(excerpt, str) and excerpt.strip():
        sealed["excerpt"] = excerpt
    return sealed


def _ticked(row: dict[str, str], columns: list[str]) -> list[str]:
    ticked: list[str] = []
    for column in columns:
        if _is_tick(row.get(column)):
            ticked.append(column)
    return ticked


def _is_tick(value: object) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    folded = text.casefold()
    if folded in _FALSE:
        return False
    return folded in _TICK or text in _TICK


def _excluded(value: object) -> bool:
    return _is_tick(value)


def _blank_none(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RouterWall("WALL: sheet has no header")
        header = [name for name in reader.fieldnames if name]
        rows = [{key: (value or "") for key, value in row.items() if key is not None} for row in reader]
    return header, rows


def _read_xlsx(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise RouterWall("WALL: xlsx is not a zip") from exc
    with archive:
        shared = _shared_strings(archive)
        sheet = _first_sheet(archive)
        grid = _sheet_rows(sheet, shared)
    if not grid:
        raise RouterWall("WALL: sheet has no header")
    header = [cell.strip() for cell in grid[0]]
    rows: list[dict[str, str]] = []
    width = len(header)
    for raw in grid[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        padded = raw + [""] * (width - len(raw))
        rows.append({header[index]: padded[index] for index in range(width) if header[index]})
    return header, rows


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("m:si", _NS):
        strings.append("".join(node.text or "" for node in item.iterfind(".//m:t", _NS)))
    return strings


def _first_sheet(archive: zipfile.ZipFile) -> bytes:
    names = [name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")]
    if not names:
        raise RouterWall("WALL: xlsx has no worksheet")
    return archive.read(sorted(names)[0])


def _sheet_rows(payload: bytes, shared: list[str]) -> list[list[str]]:
    root = ElementTree.fromstring(payload)
    rows: list[list[str]] = []
    for row in root.findall("m:sheetData/m:row", _NS):
        cells: dict[int, str] = {}
        for cell in row.findall("m:c", _NS):
            ref = cell.get("r") or ""
            column = _column_index(ref)
            cells[column] = _cell_text(cell, shared)
        if not cells:
            continue
        width = max(cells) + 1
        rows.append([cells.get(index, "") for index in range(width)])
    return rows


def _column_index(ref: str) -> int:
    letters = "".join(char for char in ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return max(index - 1, 0)


def _cell_text(cell: ElementTree.Element, shared: list[str]) -> str:
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iterfind(".//m:t", _NS))
    value = cell.find("m:v", _NS)
    if value is None or value.text is None:
        return ""
    if kind == "s":
        try:
            return shared[int(value.text)]
        except (ValueError, IndexError):
            return ""
    return value.text


def _read_proposed(path: Path) -> dict[str, str]:
    proposed: dict[str, str] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RouterWall(f"WALL: {path}:{lineno}: {exc}") from exc
        if not isinstance(obj, dict):
            raise RouterWall(f"WALL: {path}:{lineno}: record is not an object")
        sheet_id = obj.get("sheet_id")
        label = obj.get("proposed_label")
        if isinstance(sheet_id, str) and isinstance(label, str):
            proposed[sheet_id] = label
    return proposed


def _write_digests(directory: Path, names: list[str]) -> None:
    lines: list[str] = []
    for name in names:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        line = f"{digest}  {name}\n"
        lines.append(line)
        (directory / f"{name}.sha256").write_text(line, encoding="utf-8")
    (directory / "SHA256SUMS").write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seal a practitioner router labelling sheet")
    parser.add_argument("--sheet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--proposed", type=Path, default=None)
    parser.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    try:
        labels = load_labels(root / "configs" / "router" / "labels.json")
        config = load_sealed_config(root / "configs" / "router" / "sealed_eval.json")
        output_dir = args.output_dir or (root / config["sealed_dir"])
        report = seal_sheet(args.sheet, output_dir, labels, proposed=args.proposed)
    except RouterWall as exc:
        print(str(exc))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
