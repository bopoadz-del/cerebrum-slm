"""Counts and hashes for stdout. Document text is not copied into these objects."""

from __future__ import annotations

import json
from collections import Counter

from router.config import DatasetConfig
from router.errors import LabelExportMissing, RouterConfigError, SealError
from router.plan import Plan
from router.records import Corpus, DocumentRecord


def finish(action) -> int:
    try:
        payload = action()
    except LabelExportMissing as exc:
        payload = {"detail": exc.detail, "status": "wall", "wall": "label export"}
        if exc.rejected_by_reason:
            payload["rejected_by_reason"] = exc.rejected_by_reason
        _emit(payload)
        return 2
    except (RouterConfigError, SealError) as exc:
        _emit({"detail": str(exc), "status": "error"})
        return 1
    _emit(payload)
    return 0


def public_import(config: DatasetConfig, corpus: Corpus) -> dict:
    return {
        "by_label": _counts(corpus.records, config.labels),
        "conflicts": corpus.conflicts,
        "deduped": len(corpus.records),
        "duplicates": corpus.duplicates,
        "export_files": list(corpus.export_names),
        "exports_sha256": corpus.exports_sha256,
        "rejected_by_reason": _reasons(corpus),
        "rows": corpus.rows_read,
        "sha_disagreements": corpus.sha_disagreements,
        "status": "ok",
        "task": config.task,
    }


def public_plan(config: DatasetConfig, corpus: Corpus, plan: Plan) -> dict:
    payload = public_import(config, corpus)
    payload.update(
        {
            "held_out": _bucket(plan.held_out, config.labels),
            "max_input_tokens": config.max_input_tokens,
            "seal_matches_rule": plan.seal_matches_rule,
            "seal_rule": config.seal_rule,
            "seal_written": plan.seal_written,
            "sealed": {
                "by_label": _counts(plan.sealed, config.labels),
                "count": len(plan.sealed),
                "item_sha256": [item.sha256 for item in plan.sealed],
                "project_id_sha256": plan.project_id_sha256,
            },
            "status": "ok",
            "token_unit": config.token_unit,
            "train": _bucket(plan.train, config.labels),
            "wrote_pairs": False,
        }
    )
    return payload


def _bucket(records: tuple[DocumentRecord, ...], labels: tuple[str, ...]) -> dict:
    return {"by_label": _counts(records, labels), "count": len(records)}


def _counts(records: tuple[DocumentRecord, ...] | list[DocumentRecord], labels: tuple[str, ...]) -> dict[str, int]:
    tally = {label: 0 for label in labels}
    for record in records:
        tally[record.label] = tally.get(record.label, 0) + 1
    return tally


def _reasons(corpus: Corpus) -> dict[str, int]:
    return dict(sorted(Counter(item.reason for item in corpus.rejects).items()))


def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
