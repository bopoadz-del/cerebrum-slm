"""Symbol <-> definition aliases come from the extracted corpus table and apply by one rule."""

from __future__ import annotations

import json

from eval.graders import grade_refusal_or_qualification
import pytest

from eval.graders.symbols import TABLE, _definitions_at, name_keys, symbol_for, table_path


def _reply(names):
    return json.dumps({"block": "qualify", "missing_inputs": names, "required_inputs": []})


def _need_table():
    if not table_path().is_file():
        pytest.skip("off-repo symbol table absent")


def test_table_is_the_extracted_notation_list():
    _need_table()
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    assert table["extracted_by"] == "scripts/eval/extract_symbol_table.py"
    assert table["source"]["publication"] == "FHWA-HIF-12-026"
    assert len(table["source"]["pdf_sha256"]) == 64
    assert table["count"] == len(table["symbols"]) > 100
    assert all(row["symbol"] and row["definition"] for row in table["symbols"])


def test_a_definition_identifies_its_symbol():
    _need_table()
    table = json.loads(table_path().read_text(encoding="utf-8"))
    rows = {row["symbol"]: row["definition"] for row in table["symbols"]}
    assert symbol_for(rows["ke"]) == "ke"
    assert "ke" in name_keys(rows["ke"])


def test_ambiguous_or_symbol_like_names_identify_nothing():
    assert symbol_for("velocity") is None
    assert symbol_for("area") is None
    assert symbol_for("A") is None
    assert symbol_for("not a notation entry at all") is None


def test_grader_accepts_either_form_for_a_named_input():
    _need_table()
    table = json.loads(table_path().read_text(encoding="utf-8"))
    definition = {row["symbol"]: row["definition"] for row in table["symbols"]}["ke"]
    descriptive = _reply([definition.lower().replace(" ", "_")])
    symbolic = _reply(["ke"])
    for reply in (descriptive, symbolic):
        assert grade_refusal_or_qualification(reply, expected_block="missing_input", named_inputs=["ke"]).passed
    wrong = _reply(["velocity"])
    assert not grade_refusal_or_qualification(wrong, expected_block="missing_input", named_inputs=["ke"]).passed


def test_rule_is_symmetric_for_a_descriptive_gold_name():
    _need_table()
    table = json.loads(table_path().read_text(encoding="utf-8"))


def test_synthetic_definition_matches_its_symbol(tmp_path, monkeypatch):
    table = tmp_path / "symbols.json"
    table.write_text(
        json.dumps({"symbols": [{"symbol": "zz", "definition": "zeta length marker"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SLM_SYMBOL_TABLE", str(table))
    _definitions_at.cache_clear()
    assert symbol_for("zeta length marker") == "zz"
    assert "zz" in name_keys("zeta length marker")
