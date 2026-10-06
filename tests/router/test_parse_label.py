import json

from router.labels import load_labels
from router.parse_label import parse_router_output
from router.teacher_label import eligible_for_train, parse_teacher_response
from router.train_router import _as_label


def test_models_and_baselines_share_one_parser(repo_root) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    samples = [
        "change order",
        "Change Order",
        "CHANGE ORDER",
        "variation order",
        "Variation Order",
        "variation",
        "VARIATION",
        "CO",
        "co",
        "Co",
        "  change   order  ",
        "VO/CO",
        "drawing",
        "payment certificate",
    ]
    for sample in samples:
        parsed = parse_router_output(sample, labels)
        assert _as_label(sample, labels) == parsed
        teacher = parse_teacher_response(
            json.dumps({"label": sample.strip(), "reason": "from text", "confidence": 0.91}),
            labels,
        )
        assert teacher["label"] == parse_router_output(sample.strip(), labels)
        assert teacher["label"] == parsed or sample != sample.strip()
    assert parse_router_output("change order", labels) == "VO/CO"
    assert parse_router_output("drawing", labels) == "drawing"


def test_alias_is_the_canonical_label_and_can_train(repo_root) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    parsed = parse_teacher_response(
        '{"label": "change order", "reason": "owner wording", "confidence": 0.9}',
        labels,
    )
    assert parsed["label"] == "VO/CO"
    assert eligible_for_train(parsed, labels, 0.5) is True
    bare = _as_label("variation order", labels)
    assert bare == "VO/CO"


def test_alias_is_inert_when_the_canonical_label_is_absent() -> None:
    labels = ["alpha-mark", "beta-mark"]
    assert parse_router_output("change order", labels) == "unsure"
    assert parse_router_output("CO", labels) == "unsure"
    parsed = parse_teacher_response('{"label": "variation", "reason": "", "confidence": 0.9}', labels)
    assert parsed["label"] == "unsure"


def test_near_misses_stay_unmatched(repo_root) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    unmatched = [
        "change orders",
        "change-order",
        "change order.",
        "a change order",
        "variation orders",
        "the variation",
        "VOC",
        "VO",
        "C",
        "CO.",
        "vo/co",
        "rfi",
        "Rfi",
        "Payment Certificate",
        "specification",
        "correspondence",
        "",
        "   ",
    ]
    expected = {
        "correspondence": "correspondence",
    }
    for sample in unmatched:
        assert parse_router_output(sample, labels) == expected.get(sample, "unsure")
        teacher = parse_teacher_response(
            json.dumps({"label": sample, "reason": "no", "confidence": 0.99}),
            labels,
        )
        assert teacher["label"] == expected.get(sample, "unsure")


def test_json_model_reply_uses_the_same_alias(repo_root) -> None:
    labels = load_labels(repo_root / "configs" / "router" / "labels.json")
    raw = '{"label": "CO", "reason": "short form", "confidence": 0.8}'
    assert _as_label(raw, labels) == "VO/CO"
    assert parse_teacher_response(raw, labels)["label"] == "VO/CO"
    assert parse_router_output("RFI", labels) == "RFI"
    assert _as_label('{"label": "invented-type"}', labels) == "unsure"
