"""Test path setup — repo scripts and the collect tooling are importable."""

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
for sub in ("scripts", "scripts/collect"):
    p = str(_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)


def _offrepo_path_hashes() -> set[str]:
    manifest = _ROOT / "data" / "OFFREPO_MANIFEST.json"
    if not manifest.is_file():
        return set()
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return set()
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        return set()
    return {item["path_sha256"] for item in entries if isinstance(item, dict) and isinstance(item.get("path_sha256"), str)}


_PATH_IN_TEXT = re.compile(r"(?:[\w.-]+/)+[\w.-]+\.(?:jsonl|json|csv|zip)")


def _missing_offrepo(err: BaseException) -> bool:
    filename = getattr(err, "filename", None)
    if not filename:
        return False
    try:
        rel = Path(filename).resolve().relative_to(_ROOT.resolve()).as_posix()
    except ValueError:
        return False
    listed = hashlib.sha256(rel.encode("utf-8")).hexdigest() in _offrepo_path_hashes()
    return listed and not (_ROOT / rel).is_file()


def _chain(err: BaseException):
    seen: set[int] = set()
    current: BaseException | None = err
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _names_absent_offrepo(err: BaseException) -> bool:
    hashes = _offrepo_path_hashes()
    if not hashes:
        return False
    for item in _chain(err):
        if isinstance(item, FileNotFoundError) and _missing_offrepo(item):
            return True
        for match in _PATH_IN_TEXT.findall(str(item)):
            rel = match.lstrip("./")
            if hashlib.sha256(rel.encode("utf-8")).hexdigest() not in hashes:
                continue
            if not (_ROOT / rel).is_file():
                return True
    return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed or call.excinfo is None:
        return
    if not _names_absent_offrepo(call.excinfo.value):
        return
    report.outcome = "skipped"
    report.longrepr = (str(item.nodeid), 0, "Skipped: off-repo data absent")
