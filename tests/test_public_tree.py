"""The public tree must not track archives, checkpoints, or removed data locations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_ARCHIVE = {
    ".zip",
    ".tar",
    ".tgz",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".bundle",
}
_CHECKPOINT = {
    ".pt",
    ".pth",
    ".bin",
    ".safetensors",
    ".ckpt",
    ".gguf",
    ".onnx",
    ".h5",
    ".npz",
}
_BOX = "/" + "workspace" + "/"
_JSONL_PREFIXES = (
    "data/held_out/",
    "data/train/",
    "data/augment/",
    "data/router/",
    "data/eval/regression/",
    "data/eval/unseen/",
    "data/eval/temporary_works/",
    "data/retrieval/rates/",
    "data/retrieval/facilities/",
    "data/sources/",
    "docs/serve/",
    "docs/audit/",
)


def _tracked() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item.decode() for item in out.split(b"\0") if item]


def test_no_archive_or_checkpoint_blobs() -> None:
    bad = []
    for rel in _tracked():
        suffix = Path(rel).suffix.lower()
        if suffix in _ARCHIVE or suffix in _CHECKPOINT:
            bad.append(rel)
    assert bad == []


def test_removed_data_locations_are_untracked() -> None:
    bad = []
    for rel in _tracked():
        if _BOX in rel:
            bad.append(rel)
        if rel.startswith("data/router/v5_snapshot/"):
            bad.append(rel)
        if rel.startswith("data/sealed/") and Path(rel).suffix.lower() in {".json", ".jsonl", ".csv"}:
            bad.append(rel)
        if rel.endswith(".jsonl") and rel.startswith(_JSONL_PREFIXES):
            bad.append(rel)
        if rel.endswith("fact_pairs.jsonl") or rel.endswith("labelling_sheet.csv"):
            bad.append(rel)
        if rel.endswith("sealed_labels.jsonl") or rel.endswith("/held.jsonl"):
            bad.append(rel)
        if rel.endswith("isolation.json") and rel.startswith("data/eval/"):
            bad.append(rel)
        if rel.endswith("label_changes.json") and rel.startswith("data/eval/"):
            bad.append(rel)
        if rel.endswith("/inputs.json") and rel.startswith("docs/router/runs/"):
            bad.append(rel)
        if rel.startswith("eval/graders/data/") and rel.endswith(".json"):
            bad.append(rel)
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if _BOX in text:
            bad.append(rel)
    assert bad == []


def test_offrepo_manifest_is_hash_only() -> None:
    payload = json.loads((ROOT / "data" / "OFFREPO_MANIFEST.json").read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert entries
    categories = {"ARCHIVE", "OWNER_DATA", "SEALED", "CHECKPOINT"}
    for item in entries:
        assert item["category"] in categories
        assert len(item["sha256"]) == 64
        assert len(item["path_sha256"]) == 64
        assert " " not in item["path"]
        assert item["bytes"] >= 0
