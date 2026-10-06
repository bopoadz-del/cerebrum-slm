import csv
import json
from pathlib import Path

import pytest

from router.guard import RouterWall
from router.human_sample import labels_not_for_train
from router.isolation import Exclusions
from router.labels import load_labels
from router.majority_gate import evaluate
from router.prepare_pool import prepare_pool
from router.split_projects import project_grouped_split
from router.teacher_label import main as teacher_main
from router.train_router import (
    WALL,
    fit_router,
    load_train_config,
    main,
    pool_report,
    training_examples,
)
from router.val_metrics import per_label_recall, refuse_sealed_score


def test_prepare_pool_drops_empty_and_duplicate_doc_ids() -> None:
    rows = [
        {"doc_id": "a", "first_512_tokens": "one"},
        {"doc_id": "a", "first_512_tokens": "two"},
        {"doc_id": "b", "first_512_tokens": "   "},
        {"doc_id": "c", "first_512_tokens": "three"},
    ]
    prepared = prepare_pool(rows, Exclusions(frozenset(), frozenset()))
    assert prepared.input_rows == 4
    assert prepared.empty_text == 1
    assert prepared.duplicate_doc_ids == 1
    assert prepared.sealed_overlaps == 0
    assert [row["doc_id"] for row in prepared.rows] == ["a", "c"]


def test_prepare_pool_refuses_a_sealed_sha() -> None:
    rows = [{"doc_id": "a", "first_512_tokens": "text", "content_sha256": "abc"}]
    with pytest.raises(RouterWall, match="sealed candidate"):
        prepare_pool(rows, Exclusions(frozenset({"abc"}), frozenset()))


def test_raw_pool_prep_counts_and_no_sealed_overlap(repo_root: Path) -> None:
    report = pool_report(repo_root)
    assert report == {
        "input_rows": 6580,
        "empty_text": 140,
        "duplicate_doc_ids": 813,
        "sealed_overlaps": 0,
        "kept": 5627,
    }


def test_project_split_keeps_a_project_on_one_side_and_does_not_clone() -> None:
    rows = []
    for project, count in (("p1", 10), ("p2", 2), ("p3", 1)):
        for index in range(count):
            rows.append({"project_id": project, "doc_id": f"{project}-{index}"})
    train, val = project_grouped_split(rows, val_fraction=0.15)
    ids = [row["doc_id"] for row in train + val]
    assert len(ids) == len(set(ids)) == 13
    assert {row["project_id"] for row in train}.isdisjoint({row["project_id"] for row in val})
    assert {row["project_id"] for row in val} == {"p3"}


def test_missing_label_recall_stays_unset() -> None:
    scores = per_label_recall(["alpha", "alpha"], ["alpha", "beta"], ["alpha", "beta"])
    assert scores["alpha"] == 0.5
    assert scores["beta"] is None


def test_majority_gate_still_fails_a_constant_predictor() -> None:
    gold = ["alpha", "alpha", "alpha"]
    result = evaluate(gold, gold, majority_class_fail=True, order=["alpha", "beta"])
    assert result.passed is False
    assert result.accuracy == 1.0


def test_owner_override_does_not_change_the_agreement_gate(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    flagged = labels_not_for_train({label: 0.5 for label in labels}, 0.8, labels)
    assert flagged == labels
    override = load_train_config(repo_root)["train_before_human_agreement"]
    assert override["enabled"] is True
    assert override["recorded_at"] == "2026-10-06T03:45:00Z"
    assert override["owner_clock"] == "2026-10-06 07:45"


def test_pending_sample_is_a_header_only(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    path = repo_root / "data" / "router" / "human_sample_PENDING_OWNER.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    from router.sheet import header

    assert rows == [header(labels)]
    note = (repo_root / "data" / "router" / "HUMAN_AGREEMENT.md").read_text(encoding="utf-8")
    card = (repo_root / "docs" / "router" / "DATASET_CARD.md").read_text(encoding="utf-8")
    assert "PENDING_OWNER" in note
    assert "PENDING_OWNER" in card
    assert "training proceeds before" in card
    assert "2026-10-06T03:45:00Z" in card
    assert "Qwen/Qwen3-8B" in card


def test_pool_write_walls_on_the_missing_key_and_not_on_an_empty_seal(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    repo_root: Path,
) -> None:
    pool = tmp_path / "pool.jsonl"
    pool.write_text(
        json.dumps({"doc_id": "d1", "first_512_tokens": "body text", "project_id": "p"}) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "teacher_labels.jsonl"
    code = teacher_main(["--write", "--input", str(pool), "--output", str(output), "--root", str(repo_root)])
    captured = capsys.readouterr().out
    assert code == 2
    assert "TINKER_API_KEY is not set" in captured
    assert "sealed eval labels are absent" not in captured
    assert not output.exists()
    assert not (repo_root / "data" / "router" / "teacher_labels.jsonl").exists()


def test_sealed_set_is_not_scored(repo_root: Path) -> None:
    sealed = repo_root / "data" / "eval" / "router_unseen" / "sealed_labels.jsonl"
    with pytest.raises(RouterWall, match="sealed set is not scored"):
        refuse_sealed_score(sealed, repo_root)
    assert main(["--score", str(sealed), "--root", str(repo_root)]) == 2


def test_train_entry_walls_without_labels_and_hides_a_key(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    repo_root: Path,
) -> None:
    monkeypatch.setenv("TINKER_API_KEY", "super-secret-value")
    assert main(["--root", str(repo_root)]) == 2
    out = capsys.readouterr().out
    assert WALL in out
    assert "super-secret-value" not in out
    report = json.loads(out.splitlines()[-1])
    assert report["checkpoint"] is None
    assert report["kept"] == 5627
    assert report["sealed_overlaps"] == 0


def test_dry_run_with_labels_does_not_import_tinker(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    repo_root: Path,
) -> None:
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "tinker":
            raise AssertionError("tinker imported")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    monkeypatch.setenv("TINKER_API_KEY", "super-secret-value")
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    path = tmp_path / "teacher.jsonl"
    rows = []
    for project, count in (("keep", 4), ("hold", 1)):
        for index in range(count):
            rows.append(
                {
                    "doc_id": f"{project}-{index}",
                    "project_id": project,
                    "label": labels[0],
                    "excerpt": f"body {project} {index}",
                    "confidence": 0.9,
                }
            )
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    assert main(["--dry-run", "--labels", str(path), "--root", str(repo_root)]) == 0
    out = capsys.readouterr().out
    assert "super-secret-value" not in out
    report = json.loads(out)
    assert report["checkpoint"] is None
    assert report["train_rows"] == 4
    assert report["val_rows"] == 1
    assert report["status"] == "dry-run"


def test_training_examples_keep_filename_out_of_the_messages(repo_root: Path) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    examples = training_examples(
        [
            {
                "label": labels[0],
                "excerpt": "body text",
                "filename": "drawing.pdf",
                "fork_declared_type": "document",
                "project_id": "p",
                "doc_id": "d",
            }
        ],
        labels,
    )
    blob = json.dumps(examples[0]["messages"])
    assert "drawing.pdf" not in blob
    assert "fork_declared_type" not in blob
    assert examples[0]["messages"][1]["content"] == "body text"
    assert examples[0]["messages"][2]["content"] == labels[0]


class _Saved:
    def __init__(self, path: str) -> None:
        self.path = path

    def result(self):
        return self


class _Tokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt, enable_thinking=False):
        ids = [1]
        for message in messages:
            if message["role"] == "assistant":
                ids.append(9)
                ids.extend(ord(char) for char in message["content"])
            else:
                ids.append(2)
                ids.extend(ord(char) for char in message["content"][:4])
        if add_generation_prompt:
            ids.append(9)
        return ids

    def decode(self, tokens, skip_special_tokens=True):
        return "".join(chr(token) for token in tokens)


class _Client:
    def __init__(self) -> None:
        self.saved: list[str] = []
        self.forward_calls = 0

    def get_tokenizer(self):
        return _Tokenizer()

    def forward_backward(self, batch, loss_fn):
        self.forward_calls += 1
        return _Saved("ok")

    def optim_step(self, optim_params):
        return _Saved("ok")

    def save_weights_for_sampler(self, name):
        self.saved.append(name)
        return _Saved(f"tinker://sampler/{name}")


class _Service:
    def __init__(self, client: _Client) -> None:
        self.client = client
        self.kwargs = None
        self.closed = None

    def create_lora_training_client(self, **kwargs):
        self.kwargs = kwargs
        return self.client

    def close(self, status):
        self.closed = status
        return _Saved(status)


class _Sdk:
    def __init__(self) -> None:
        self.client = _Client()
        self.service = _Service(self.client)

        class Types:
            class SamplingParams:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

            class ModelInput:
                @staticmethod
                def from_ints(values):
                    return values

            class Datum:
                def __init__(self, model_input, loss_fn_inputs):
                    self.model_input = model_input
                    self.loss_fn_inputs = loss_fn_inputs

            class AdamParams:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

        self.types = Types

    def ServiceClient(self):
        return self.service


def test_fit_uses_rank_16_and_two_epochs(repo_root: Path) -> None:
    lora = json.loads((repo_root / "configs" / "lora" / "qwen3-4b-router-r16.json").read_text(encoding="utf-8"))
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    rows = training_examples(
        [{"label": labels[0], "excerpt": "body", "project_id": "p", "doc_id": "d"}],
        labels,
    )
    sdk = _Sdk()
    trained = fit_router(lora, rows, sdk=sdk)
    assert sdk.service.kwargs["rank"] == 16
    assert sdk.service.kwargs["base_model"] == "Qwen/Qwen3-4B"
    assert sdk.client.saved == [
        "router-qwen3-4b-lora-r16-epoch1",
        "router-qwen3-4b-lora-r16-epoch2",
    ]
    assert trained["epoch_sampler"] == "tinker://sampler/router-qwen3-4b-lora-r16-epoch2"
    assert sdk.service.closed == "success"
    serve = json.loads((repo_root / "configs" / "serve" / "router-epoch2.json").read_text(encoding="utf-8"))
    assert serve["checkpoint"] is None
    assert serve["status"] == "not_trained"
