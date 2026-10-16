"""Symbol <-> definition aliases from the corpus notation list.

``eval/graders/data/hds5_symbols.json`` is the blind corpus's own LIST OF
SYMBOLS, extracted by ``scripts/eval/extract_symbol_table.py`` (not typed by
hand). A named input is compared through its keys:

- every name has its folded spelling as a key (case folded, runs of spaces,
  hyphens, and underscores collapsed);
- a descriptive name also has the folded symbol it identifies: the one symbol
  whose printed definition contains every word of the name. The name must carry
  at least one word of four or more letters, and if more than one symbol's
  definition contains all its words the name identifies none.

Two names match when their key sets meet. The rule is the same for every item
and every model.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

_RELATIVE = Path("eval/graders/data/hds5_symbols.json")


def table_path() -> Path:
    override = os.environ.get("SLM_SYMBOL_TABLE", "").strip()
    if override:
        return Path(override)
    root = os.environ.get("SLM_DATA_ROOT", "").strip()
    base = Path(root) if root else Path(__file__).resolve().parents[2]
    return base / _RELATIVE


TABLE = table_path()
_SEPARATORS = re.compile(r"[\s\-_]+")
_WORD = re.compile(r"[a-z0-9]+")
_MIN_WORD = 4


def fold(text: str) -> str:
    return _SEPARATORS.sub("_", str(text).strip().casefold()).strip("_")


def _words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(str(text).casefold()))


@lru_cache(maxsize=4)
def _definitions_at(path_text: str) -> tuple[tuple[str, frozenset[str]], ...]:
    path = Path(path_text)
    if not path.is_file():
        return ()
    table = json.loads(path.read_text(encoding="utf-8"))
    return tuple((fold(row["symbol"]), _words(row["definition"])) for row in table["symbols"])


def _definitions() -> tuple[tuple[str, frozenset[str]], ...]:
    return _definitions_at(str(table_path()))


def symbol_for(name: str) -> str | None:
    """The folded symbol a descriptive name identifies, or None."""
    words = _words(name)
    if not any(len(word) >= _MIN_WORD and word.isalpha() for word in words):
        return None
    hits = {symbol for symbol, definition in _definitions() if words <= definition}
    return hits.pop() if len(hits) == 1 else None


def name_keys(name: str) -> frozenset[str]:
    keys = {fold(name)}
    symbol = symbol_for(name)
    if symbol:
        keys.add(symbol)
    return frozenset(keys)
