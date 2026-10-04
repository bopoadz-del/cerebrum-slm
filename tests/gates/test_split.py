from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from gates.records import pair_view
from gates.split import EMPTY_TERMS, check_split, leak_kinds, load_retrieval_terms

_POSTURE = (
    "Name the missing input and refuse an unsourced figure. "
    "Where a measured record exists it governs over a default."
)


@pytest.mark.parametrize(
    "text",
    ["12 mm", "12mm", "40 MPa", "3.5 m", "28-day", "15%", "120 kW", "2 hours"],
)
def test_number_with_unit_fails(text: str) -> None:
    assert "number-unit" in leak_kinds(text, EMPTY_TERMS)


@pytest.mark.parametrize(
    "text",
    ["6 USD", "USD", "SAR 12", "$6", "6 riyals", "The allowance is 6 USD."],
)
def test_currency_fails(text: str) -> None:
    assert "currency" in leak_kinds(text, EMPTY_TERMS)


@pytest.mark.parametrize(
    "text",
    ["Apply ACI 318-19.", "Follow BS 8110.", "See EN 1992-1-1.", "ASTM A416"],
)
def test_standard_designator_fails(text: str) -> None:
    assert leak_kinds(text, EMPTY_TERMS) == ["clause-edition"]


def test_clause_needs_an_edition() -> None:
    assert leak_kinds("See section 2 before deciding.", EMPTY_TERMS) == []
    assert leak_kinds("Apply clause 5.", EMPTY_TERMS) == []
    assert "clause-edition" in leak_kinds("See section 2 of the 2019 edition.", EMPTY_TERMS)
    assert "clause-edition" in leak_kinds("Apply clause 5 of the 2024 edition.", EMPTY_TERMS)


@pytest.mark.parametrize(
    "text",
    [
        _POSTURE,
        "INV-1 violation: the label is not a unit.",
        "Levels run L1-L5.",
        "Eq. 19.2.2.1b",
        "3.5 more cover is a phrase, not a metre.",
    ],
)
def test_posture_and_labels_pass(text: str) -> None:
    assert leak_kinds(text, EMPTY_TERMS) == []


def test_brand_and_site_come_from_retrieval(tmp_path: Path) -> None:
    row = {
        "market": "North Wharf",
        "source": "AcmePlant Handbook 2024",
        "currency": "USD",
        "rate": 6,
        "unit": "hour",
    }
    path = tmp_path / "data" / "retrieval" / "rates.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    terms = load_retrieval_terms(tmp_path)
    assert "acmeplant" in {brand.casefold() for brand in terms.brands}
    assert "north wharf" in {site.casefold() for site in terms.sites}
    assert leak_kinds("Take the AcmePlant value.", terms) == ["brand"]
    assert leak_kinds("Sequence the works at North Wharf.", terms) == ["site"]
    assert leak_kinds(_POSTURE, terms) == []


def test_retrieval_and_eval_files_are_not_training_pairs(tmp_path: Path) -> None:
    fact = {"instruction": "q", "input": "", "output": "Allow 12 mm and charge 6 USD in Dubai."}
    for relative in (
        "data/retrieval/rates.jsonl",
        "data/eval/blind/case.jsonl",
        "data/raw/extracted.jsonl",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(fact) + "\n", encoding="utf-8")
    assert check_split(tmp_path) == []

    train = tmp_path / "data" / "train" / "fact.jsonl"
    train.parent.mkdir(parents=True)
    train.write_text(json.dumps(fact) + "\n", encoding="utf-8")
    findings = check_split(tmp_path)
    assert findings
    assert "number-unit" in findings[0].message
    train.unlink()
    assert check_split(tmp_path) == []


def test_messages_schema_checks_each_assistant_turn(tmp_path: Path) -> None:
    row = {
        "messages": [
            {"role": "user", "content": "The drawing says 12 mm."},
            {"role": "assistant", "content": _POSTURE},
        ]
    }
    path = tmp_path / "data" / "train" / "posture.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert check_split(tmp_path) == []
    row["messages"].append({"role": "assistant", "content": "Use 12 mm."})
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert check_split(tmp_path)


def test_archived_posture_passes_and_standard_names_fail(repo_root: Path) -> None:
    terms = load_retrieval_terms(repo_root)
    assert "aecom" in {brand.casefold() for brand in terms.brands}
    assert "turner & townsend" in {brand.casefold() for brand in terms.brands}
    assert "dubai" in {site.casefold() for site in terms.sites}
    assert any("diriyah" in site.casefold() for site in terms.sites)
    assert leak_kinds("Use the AECOM handbook.", terms) == ["brand"]
    assert leak_kinds("The works are in Dubai.", terms) == ["site"]
    assert leak_kinds("Quote the Synthetic Practice Note 2024.", terms) == ["clause-edition"]
    assert leak_kinds("The Synthetic Practice Note describes a shape.", terms) == []
    assert leak_kinds(_POSTURE, terms) == []

    zip_path = repo_root / "data" / "raw" / "slm-datasets.zip"
    posture_members = {
        "slm-datasets/concrete/concrete_pairs.jsonl",
        "slm-datasets/site/site_pairs.jsonl",
        "slm-datasets/plant/plant_fleet_maintenance.jsonl",
        "slm-datasets/mech-water/mech_water_epc.jsonl",
        "slm-datasets/governance/governance.jsonl",
        "slm-datasets/rates/rate_handling.jsonl",
    }
    formula_members = {
        "slm-datasets/formulas/formula_selection.jsonl",
        "slm-datasets/formulas/from-source/formula_selection.jsonl",
    }
    with zipfile.ZipFile(zip_path) as archive:
        for name in posture_members:
            for line in archive.read(name).decode("utf-8").splitlines():
                if not line.strip():
                    continue
                view = pair_view(json.loads(line))
                assert view is not None
                assert leak_kinds(view.assistant, terms) == [], view.assistant
        clause_hits = 0
        currency_hits = 0
        for name in formula_members:
            for line in archive.read(name).decode("utf-8").splitlines():
                if not line.strip():
                    continue
                view = pair_view(json.loads(line))
                assert view is not None
                kinds = leak_kinds(view.assistant, terms)
                # Routing text may name a standard or write "sar" as a price unit.
                # A number+unit, brand, or site name is still a leak.
                assert "number-unit" not in kinds, view.assistant
                assert "brand" not in kinds, view.assistant
                assert "site" not in kinds, view.assistant
                if "clause-edition" in kinds:
                    clause_hits += 1
                if "currency" in kinds:
                    currency_hits += 1
        assert clause_hits >= 5
        assert currency_hits >= 3
