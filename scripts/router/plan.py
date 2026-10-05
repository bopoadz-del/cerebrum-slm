"""Choose the sealed project first, then stratify the rows that remain."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from router.config import DatasetConfig, load_config
from router.errors import RouterConfigError, SealError
from router.records import Corpus, DocumentRecord, load_corpus, sha256_text


@dataclass(frozen=True)
class Plan:
    train: tuple[DocumentRecord, ...]
    held_out: tuple[DocumentRecord, ...]
    sealed: tuple[DocumentRecord, ...]
    project_id_sha256: str
    seal_written: bool
    seal_matches_rule: bool


def holdout_count(population: int, numerator: int, denominator: int) -> int:
    """Round half up. A population of zero stays zero."""
    if population <= 0:
        return 0
    return (population * numerator + denominator // 2) // denominator


def choose_project_id(records: tuple[DocumentRecord, ...] | list[DocumentRecord], rule: str) -> str:
    if rule != "largest_then_lowest_project_sha256":
        raise RouterConfigError("seal rule is not implemented")
    counts: dict[str, int] = defaultdict(int)
    hashes: dict[str, str] = {}
    for record in records:
        counts[record.project_id] += 1
        hashes[record.project_id] = record.project_id_sha256
    return min(counts, key=lambda project_id: (-counts[project_id], hashes[project_id], project_id))


def seal_json_path(root: Path, config: DatasetConfig) -> Path:
    return root / config.eval_dir / "seal.json"


def read_frozen_project_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SealError("existing seal is not readable JSON") from exc
    if not isinstance(data, dict):
        raise SealError("existing seal is not an object")
    digest = data.get("project_id_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise SealError("existing seal has no project id hash")
    if any(char not in "0123456789abcdef" for char in digest.lower()):
        raise SealError("existing seal has no project id hash")
    return digest.lower()


def plan_split(corpus: Corpus, config: DatasetConfig, frozen_hash: str | None) -> Plan:
    if not corpus.records:
        raise SealError("nothing to split")
    ruled = choose_project_id(corpus.records, config.seal_rule)
    ruled_hash = sha256_text(ruled)
    if frozen_hash is None:
        project_hash = ruled_hash
        seal_written = False
        matches = True
    else:
        project_hash = frozen_hash
        seal_written = True
        matches = frozen_hash == ruled_hash
    sealed = tuple(record for record in corpus.records if record.project_id_sha256 == project_hash)
    if not sealed:
        raise SealError("sealed project is not in this export")
    remainder = [record for record in corpus.records if record.project_id_sha256 != project_hash]
    grouped: dict[str, list[DocumentRecord]] = defaultdict(list)
    for record in remainder:
        grouped[record.label].append(record)
    train: list[DocumentRecord] = []
    held: list[DocumentRecord] = []
    for label in config.labels:
        group = sorted(grouped.get(label, []), key=lambda item: item.sha256)
        take = holdout_count(len(group), config.holdout_numerator, config.holdout_denominator)
        held.extend(group[:take])
        train.extend(group[take:])
    train_rows = tuple(sorted(train, key=lambda item: item.sha256))
    held_rows = tuple(sorted(held, key=lambda item: item.sha256))
    sealed_rows = tuple(sorted(sealed, key=lambda item: item.sha256))
    _reject_overlap(train_rows, held_rows, sealed_rows)
    return Plan(
        train=train_rows,
        held_out=held_rows,
        sealed=sealed_rows,
        project_id_sha256=project_hash,
        seal_written=seal_written,
        seal_matches_rule=matches,
    )


def build_plan(root: Path) -> tuple[DatasetConfig, Corpus, Plan]:
    config = load_config(root)
    corpus = load_corpus(root, config)
    frozen = read_frozen_project_hash(seal_json_path(root, config))
    return config, corpus, plan_split(corpus, config, frozen)


def _reject_overlap(
    train: tuple[DocumentRecord, ...],
    held: tuple[DocumentRecord, ...],
    sealed: tuple[DocumentRecord, ...],
) -> None:
    sealed_sha = {item.sha256 for item in sealed}
    if sealed_sha & {item.sha256 for item in train}:
        raise SealError("sealed project overlapped train")
    if sealed_sha & {item.sha256 for item in held}:
        raise SealError("sealed project overlapped held-out")
