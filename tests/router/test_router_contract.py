"""The label set is config, and router code does not restate it."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from router.config import load_config

REPO = Path(__file__).resolve().parents[2]

EXPECTED_LABELS = (
    "RFI",
    "submittal",
    "transmittal",
    "VO/CO",
    "claim",
    "payment certificate",
    "drawing",
    "spec",
    "schedule",
    "report",
    "correspondence",
    "other",
)

_DOC_SUFFIXES = (".pdf", ".dwg", ".docx", ".xlsx", ".rvt", ".dwf")


def test_label_file_is_the_contract() -> None:
    config = load_config(REPO)
    assert config.labels == EXPECTED_LABELS
    assert config.task == "document_type"
    assert config.max_input_tokens == 512
    assert config.holdout_numerator == 15
    assert config.holdout_denominator == 100
    assert config.seal_rule == "largest_then_lowest_project_sha256"
    assert config.token_unit == "whitespace"


def test_router_code_does_not_hardcode_labels_or_suffix_rules() -> None:
    labels = set(EXPECTED_LABELS)
    for path in sorted((REPO / "scripts" / "router").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "import re" not in source
        assert "re.compile" not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            assert node.value not in labels
            for suffix in _DOC_SUFFIXES:
                assert suffix not in node.value


def test_readme_names_every_label() -> None:
    text = (REPO / "docs" / "router" / "README.md").read_text(encoding="utf-8")
    for label in EXPECTED_LABELS:
        assert label in text


def test_drop_zone_ships_no_export() -> None:
    raw = REPO / "data" / "raw" / "router"
    assert (raw / "README.md").is_file()
    payloads = [path.name for path in raw.iterdir() if path.suffix.lower() in {".jsonl", ".csv"}]
    assert payloads == []


def test_placeholder_seal_has_no_payload() -> None:
    text = (REPO / "docs" / "router" / "sealed-project.md").read_text(encoding="utf-8")
    assert "No project is sealed" in text
    assert "```" not in text
    data = json.loads((REPO / "configs" / "router" / "labels.json").read_text(encoding="utf-8"))
    assert data["labels"] == list(EXPECTED_LABELS)
