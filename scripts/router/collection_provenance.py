"""Collection provenance rule — every collected router row records its source.

The rule (owner order 2026-10-08): a row may enter a labelling sheet only when
it records, at fetch time:

    source_url       the full URL the document was fetched from
    fetch_timestamp  ISO-8601 UTC fetch time
    http_status      the HTTP status of the fetch
    content_sha256   sha256 of the fetched bytes
    page_title       the fetched page's title

"domain sha256 only" provenance is retired. Legacy rows that predate the rule
carry ``provenance_status: "no-provenance"`` and are validation-visible but
never count as rule-compliant.

Validation is structural: it checks field presence/types on the recorded row.
It never reads document content, filenames or labels.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FIELDS: tuple[str, ...] = (
    "source_url",
    "fetch_timestamp",
    "http_status",
    "content_sha256",
    "page_title",
)

NO_PROVENANCE = "no-provenance"


@dataclass(frozen=True)
class RowResult:
    row_index: int
    missing: tuple[str, ...] = ()
    legacy: bool = False

    @property
    def ok(self) -> bool:
        return not self.missing


@dataclass
class FileResult:
    path: str
    rows: int = 0
    violations: list[RowResult] = field(default_factory=list)
    legacy_rows: int = 0

    @property
    def ok(self) -> bool:
        return not self.violations


def _is_url(value: object) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _is_timestamp(value: object) -> bool:
    # ISO-8601: 2026-10-07T19:24:54Z or with offset — structural only
    if not isinstance(value, str) or len(value) < 16:
        return False
    return value[4] == "-" and value[10] in ("T", " ") and value[13] == ":"


def _is_http_status(value: object) -> bool:
    return isinstance(value, int) and 100 <= value <= 599


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdefABCDEF" for c in value
    )


_FIELD_CHECKS = {
    "source_url": _is_url,
    "fetch_timestamp": _is_timestamp,
    "http_status": _is_http_status,
    "content_sha256": _is_sha256,
    "page_title": lambda v: isinstance(v, str) and bool(v.strip()),
}


def validate_row(row: dict, index: int) -> RowResult:
    """Structural check of one additions row. Content is never read."""
    missing = tuple(
        name for name in REQUIRED_FIELDS if not _FIELD_CHECKS[name](row.get(name))
    )
    legacy = row.get("provenance_status") == NO_PROVENANCE
    if missing and legacy:
        return RowResult(row_index=index, missing=(), legacy=True)
    return RowResult(row_index=index, missing=missing, legacy=legacy)


def validate_file(path: Path) -> FileResult:
    result = FileResult(path=str(path))
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            result.violations.append(RowResult(row_index=index, missing=("<not an object>",)))
            continue
        row = validate_row(obj, index)
        result.rows += 1
        if row.legacy:
            result.legacy_rows += 1
        elif not row.ok:
            result.violations.append(row)
    return result


def validate_paths(paths: list[Path]) -> list[FileResult]:
    return [validate_file(p) for p in paths]


# Paths the CI provenance step checks. Present files are validated; absent
# files must be listed in the off-repo hash manifest.
CI_PATHS: tuple[str, ...] = (
    "data/router/additions_thin_v9.jsonl",
    "data/router/additions_thin_v9b.jsonl",
    "data/router/additions_thin_v9c.jsonl",
    "data/router/additions_thin_v9f.jsonl",
    "data/router/additions_thin_d.jsonl",
    "data/router/additions_change_request_v9.jsonl",
    "data/router/additions_owner_sources_pr2.jsonl",
    "data/router/additions_owner_laptop.jsonl",
)


def gate(root: Path) -> int:
    """Validate present addition files; require a hash-manifest entry when absent."""
    import sys as _sys

    scripts = Path(__file__).resolve().parents[1]
    if str(scripts) not in _sys.path:
        _sys.path.insert(0, str(scripts))
    from gates.offrepo import require_entry

    failed = False
    present: list[Path] = []
    for rel in CI_PATHS:
        path = root / rel
        if path.is_file():
            present.append(path)
            continue
        findings = require_entry(root, rel, "provenance")
        if findings:
            failed = True
            for finding in findings:
                print(finding.format(), file=_sys.stderr)
        else:
            print(f"{rel}: absent, off-repo hash manifest ok")
    if present:
        results = validate_paths(present)
        for res in results:
            print(f"{res.path}: {res.rows} rows, {res.legacy_rows} no-provenance")
            for violation in res.violations:
                failed = True
                print(f"  row {violation.row_index}: missing/invalid {', '.join(violation.missing)}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        from data_root import data_root

        return gate(data_root())
    results = validate_paths([Path(p) for p in argv])
    failed = False
    for res in results:
        print(f"{res.path}: {res.rows} rows, {res.legacy_rows} no-provenance")
        for v in res.violations:
            failed = True
            print(f"  row {v.row_index}: missing/invalid {', '.join(v.missing)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
