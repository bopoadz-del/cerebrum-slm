"""Write the sealed project as hashes in docs and a sealed payload under data/eval.

The markdown file records hashes and counts. It does not record document text,
filenames, or the project name. An existing seal stays on that project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from router.config import DatasetConfig
from router.errors import SealError
from router.plan import Plan, build_plan
from router.records import DocumentRecord, render_prompt
from router.report import finish, public_plan

_NOTE_TOKENS = frozenset(
    {
        "artifact_sha256",
        "document_type",
        "exports_sha256",
        "item_count",
        "largest_then_lowest_project_sha256",
        "project_id_sha256",
        "seal_matches_rule",
        "seal_rule",
    }
)


def sealed_row(record: DocumentRecord, config: DatasetConfig) -> dict:
    if record.label not in config.labels:
        raise SealError("sealed target is not a configured label")
    return {
        "completion": record.label,
        "meta": {
            "project_id_sha256": record.project_id_sha256,
            "sha256": record.sha256,
            "split": "sealed",
            "task": config.task,
        },
        "prompt": render_prompt(config.input_template, record.filename, record.prefix),
    }


def jsonl_bytes(rows: list[dict]) -> bytes:
    lines = [
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) for row in rows
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def hash_note(
    *,
    task: str,
    rule: str,
    matches: bool,
    project_id_sha256: str,
    exports_sha256: str,
    artifact: str,
    artifact_sha256: str,
    label_counts: list[tuple[str, int]],
    item_sha256: list[str],
) -> str:
    """Markdown with hashes and counts only. Callers must not pass document text."""
    lines = [
        "# Router sealed project",
        "",
        "Hashes and counts for one sealed project. This file has no document text, filenames, or project name.",
        "",
        f"- task: {task}",
        f"- seal_rule: {rule}",
        f"- seal_matches_rule: {str(matches).lower()}",
        f"- project_id_sha256: {project_id_sha256}",
        f"- exports_sha256: {exports_sha256}",
        f"- artifact: {artifact}",
        f"- artifact_sha256: {artifact_sha256}",
        f"- item_count: {len(item_sha256)}",
        "",
        "## Label counts",
        "",
        "| label | count |",
        "| --- | --- |",
    ]
    for label, count in label_counts:
        safe = label.replace("|", "/")
        lines.append(f"| {safe} | {count} |")
    lines.extend(["", "## Item sha256", ""])
    lines.extend(f"- {digest}" for digest in item_sha256)
    lines.append("")
    return "\n".join(lines)


def write_seal(root: Path) -> dict:
    config, corpus, plan = build_plan(root)
    rows = [sealed_row(record, config) for record in plan.sealed]
    payload = jsonl_bytes(rows)
    digest = hashlib.sha256(payload).hexdigest()
    counts = _counts(plan, config)
    if sum(count for _, count in counts) != len(rows):
        raise SealError("seal count does not match label counts")
    note = hash_note(
        task=config.task,
        rule=config.seal_rule,
        matches=plan.seal_matches_rule,
        project_id_sha256=plan.project_id_sha256,
        exports_sha256=corpus.exports_sha256,
        artifact=f"{config.eval_dir}/{config.sealed_artifact}",
        artifact_sha256=digest,
        label_counts=counts,
        item_sha256=[record.sha256 for record in plan.sealed],
    )
    _reject_note(note, plan, config.labels)
    eval_dir = root / config.eval_dir
    eval_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = eval_dir / config.sealed_artifact
    artifact_path.write_bytes(payload)
    seal = {
        "algorithm": "sha256",
        "artifact": config.sealed_artifact,
        "count": len(rows),
        "exports_sha256": corpus.exports_sha256,
        "item_sha256": [record.sha256 for record in plan.sealed],
        "label_counts": {label: count for label, count in counts},
        "project_id_sha256": plan.project_id_sha256,
        "seal_matches_rule": plan.seal_matches_rule,
        "seal_rule": config.seal_rule,
        "sha256": digest,
        "task": config.task,
    }
    (eval_dir / "seal.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    doc_path = root / config.seal_doc
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(note, encoding="utf-8")
    written = Plan(
        train=plan.train,
        held_out=plan.held_out,
        sealed=plan.sealed,
        project_id_sha256=plan.project_id_sha256,
        seal_written=True,
        seal_matches_rule=plan.seal_matches_rule,
    )
    report = public_plan(config, corpus, written)
    report["artifact_sha256"] = digest
    return report


def _counts(plan: Plan, config: DatasetConfig) -> list[tuple[str, int]]:
    tally = {label: 0 for label in config.labels}
    for record in plan.sealed:
        tally[record.label] += 1
    return [(label, tally[label]) for label in config.labels]


def _reject_note(note: str, plan: Plan, labels: tuple[str, ...]) -> None:
    """The hash note must not echo a sealed filename, project id, or document."""
    for record in plan.sealed:
        if _leaked(record.filename, note, labels) or _leaked(record.project_id, note, labels):
            raise SealError("seal note contains a sealed identifier")
        if len(record.prefix) >= 40 and record.prefix in note:
            raise SealError("seal note contains document text")
        if len(record.text) >= 40 and record.text in note:
            raise SealError("seal note contains document text")


def _leaked(needle: str, note: str, labels: tuple[str, ...]) -> bool:
    if len(needle) < 8 or needle in _NOTE_TOKENS or needle in labels:
        return False
    return needle in note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seal one whole project before any training pairs.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()

    def action() -> dict:
        return write_seal(root)

    return finish(action)


if __name__ == "__main__":
    raise SystemExit(main())
