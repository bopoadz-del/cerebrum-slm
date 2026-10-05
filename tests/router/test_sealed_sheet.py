import csv
from pathlib import Path

from router.labels import load_labels, load_sealed_config
from router.sheet import header, sealed_rows


OWNER_LINE = (
    "OWNER: sealed router eval needs 60 documents from Master Folder "
    "(or another corpus not yet used as training labels), labelled by a practitioner"
)


def test_sealed_config_matches_the_label_file(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    config = load_sealed_config(repo_root / "configs" / "router" / "sealed_eval.json")
    assert config["n"] == 60
    assert config["per_label"] == 5
    assert config["n"] == config["per_label"] * len(labels)
    assert config["majority_class_fail"] is True
    assert config["agreement_threshold"] == 0.8
    assert config["teacher"]["provider"] is None
    assert config["teacher"]["model"] is None
    assert config["teacher"]["confidence_floor"] is None
    assert "Master Folder" in config["note"]
    assert "practitioner" in config["note"]
    assert config["labels_file"] == "configs/router/labels.json"


def test_in_pool_holdout_is_not_the_sealed_set(repo_root: Path) -> None:
    text = (repo_root / "docs" / "router" / "LABELS.md").read_text(encoding="utf-8")
    assert "extra in-pool check only" in text
    assert "It is not the sealed set." in text


def test_owner_line_and_empty_drop_zone(repo_root: Path) -> None:
    readme = (repo_root / "data" / "sealed" / "router" / "README.md").read_text(encoding="utf-8")
    assert OWNER_LINE in readme.splitlines()
    drop = repo_root / "data" / "sealed" / "router" / "sealed_labels.jsonl"
    assert drop.is_file()
    assert drop.read_bytes() == b""
    assert (repo_root / "data" / "sealed" / "router" / ".gitkeep").is_file()


def test_labelling_sheet_is_sixty_blank_rows(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    path = repo_root / "data" / "sealed" / "router" / "labelling_sheet.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == header(labels)
    assert rows[1:] == sealed_rows(labels, 60)
    for row in rows[1:]:
        assert row[1] == ""
        assert row[2] == ""
        assert all(cell == "" for cell in row[3:])
    assert "unsure" == rows[0][-1]
    assert "unsure" not in labels
