import json
from pathlib import Path

import pytest

from router.guard import RouterWall
from router.labels import load_labels
from router.teacher_label import (
    dry_run_report,
    eligible_for_train,
    filter_for_train,
    label_rows,
    main,
    messages_for,
    parse_teacher_response,
    prompt_for,
    with_model_version,
)


def test_prompt_uses_the_file_and_not_a_label_outside_it(tmp_path: Path) -> None:
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"labels": ["alpha-mark", "beta-mark"], "task": "document_type"}), encoding="utf-8")
    labels = load_labels(path)
    prompt = prompt_for(labels)
    assert "alpha-mark" in prompt
    assert "beta-mark" in prompt
    assert "RFI" not in prompt


def test_messages_carry_excerpt_only() -> None:
    labels = ["alpha-mark"]
    row = {
        "doc_id": "doc-1",
        "project_id": "project-9",
        "filename": "rfi-from-the-name.pdf",
        "fork_declared_type": "document",
        "first_512_tokens": "excerpt body",
    }
    messages = messages_for(row, labels)
    assert messages is not None
    assert messages[1]["content"] == "excerpt body"
    blob = json.dumps(messages)
    assert "rfi-from-the-name.pdf" not in blob
    assert "project-9" not in blob
    assert "doc-1" not in blob
    assert "fork_declared_type" not in blob


def test_filename_alone_is_not_content() -> None:
    assert messages_for({"filename": "drawing.pdf", "project_id": "p"}, ["alpha-mark"]) is None


def test_unknown_model_label_becomes_unsure_and_stays_out_of_train() -> None:
    labels = ["alpha-mark", "beta-mark"]
    parsed = parse_teacher_response(
        '{"label": "invented-type", "reason": "no support", "confidence": 0.99}',
        labels,
    )
    assert parsed["label"] == "unsure"
    assert eligible_for_train(parsed, labels, 0.5) is False


def test_filter_drops_unsure_and_low_confidence() -> None:
    labels = ["alpha-mark"]
    rows = [
        {"label": "alpha-mark", "confidence": 0.9, "reason": "ok"},
        {"label": "alpha-mark", "confidence": 0.2, "reason": "low"},
        {"label": "unsure", "confidence": 0.99, "reason": "no"},
        {"label": "alpha-mark", "confidence": None, "reason": "missing"},
    ]
    kept = filter_for_train(rows, labels, 0.5)
    assert kept == [rows[0]]
    assert filter_for_train(rows, labels, None) == []


def test_mocked_teacher_does_not_copy_filename(tmp_path: Path) -> None:
    labels = ["alpha-mark"]

    def respond(messages):
        assert "drawing.pdf" not in messages[1]["content"]
        return '{"label": "alpha-mark", "reason": "from text", "confidence": 0.8}'

    rows = label_rows(
        [
            {
                "doc_id": "d1",
                "filename": "drawing.pdf",
                "excerpt": "body text",
                "project_id": "project-keep",
                "content_sha256": "abc123",
                "fork_declared_type": "document",
            }
        ],
        labels,
        respond,
    )
    assert rows == [
        {
            "label": "alpha-mark",
            "reason": "from text",
            "confidence": 0.8,
            "doc_id": "d1",
            "project_id": "project-keep",
            "file_sha256": "abc123",
            "excerpt": "body text",
        }
    ]
    assert "filename" not in rows[0]
    assert "fork_declared_type" not in rows[0]


def test_dry_run_prints_no_secret_and_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    monkeypatch.setenv("TINKER_API_KEY", "super-secret-value")
    card = repo_root / "docs" / "router" / "DATASET_CARD.md"
    before = card.read_text(encoding="utf-8")
    code = main(["--root", str(repo_root)])
    assert code == 0
    assert card.read_text(encoding="utf-8") == before
    captured = json.dumps(dry_run_report([], ["alpha-mark"]))
    assert "super-secret-value" not in captured
    assert captured.find("true") != -1 or "api_key_present" in captured


def test_dry_run_cli_hides_the_key(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo_root: Path) -> None:
    monkeypatch.setenv("ROUTER_TEACHER_API_KEY", "super-secret-value")
    assert main(["--root", str(repo_root)]) == 0
    out = capsys.readouterr().out
    assert "super-secret-value" not in out
    report = json.loads(out)
    assert report["labelled"] == 0
    assert report["wrote"] is False
    assert report["content_rows"] == 0
    assert report["api_key_present"] is True


def test_write_is_refused_while_sealed_file_is_empty(capsys: pytest.CaptureFixture[str], repo_root: Path) -> None:
    assert main(["--write", "--root", str(repo_root)]) == 2
    assert "WALL:" in capsys.readouterr().out
    assert not (repo_root / "data" / "train" / "router.jsonl").exists()


def test_sealed_input_is_refused(capsys: pytest.CaptureFixture[str], repo_root: Path) -> None:
    target = repo_root / "data" / "sealed" / "router" / "sealed_labels.jsonl"
    assert main(["--input", str(target), "--root", str(repo_root)]) == 2
    assert "WALL: sealed corpus" in capsys.readouterr().out


def test_model_version_updates_a_card_copy() -> None:
    card = "Status: no training labels.\n\nModel version: unset\n"
    updated = with_model_version(card, "teacher-model-stub")
    assert "Model version: teacher-model-stub" in updated
    with pytest.raises(RouterWall):
        with_model_version(card, "line\nbreak")
