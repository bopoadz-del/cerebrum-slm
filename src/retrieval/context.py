"""Normalize context attached by The Fork's retriever.

Source, clause, and formula identifiers are taken from the retriever's
payload. Nothing here searches or ranks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

_ROLE_KEYS = frozenset({"citation", "clause", "source", "formula"})
_TEXT_KEYS = frozenset({"text", "chunk_text"})


def _is_identifier_key(key: str) -> bool:
    lowered = key.lower()
    return lowered == "id" or lowered.endswith("_id") or lowered in _ROLE_KEYS


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        dumped = dump()
        if isinstance(dumped, Mapping):
            return dumped
    if hasattr(value, "__dict__"):
        return {key: item for key, item in vars(value).items() if not key.startswith("_")}
    return None


def _stringify(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    return None


def _collect(value: Any, ids: set[str], texts: list[str], depth: int) -> None:
    mapping = _as_mapping(value)
    if mapping is None:
        if depth == 0 and isinstance(value, str) and value.strip():
            texts.append(value.strip())
        return
    for key, item in mapping.items():
        name = str(key)
        if _is_identifier_key(name):
            _add_identifier(item, ids)
            continue
        if name.lower() in _TEXT_KEYS and isinstance(item, str) and item.strip():
            texts.append(item.strip())
            continue
        nested = _as_mapping(item)
        if nested is not None and depth < 2:
            _collect(nested, ids, texts, depth + 1)


def _add_identifier(value: Any, ids: set[str]) -> None:
    if isinstance(value, (list, tuple)):
        for item in value:
            _add_identifier(item, ids)
        return
    text = _stringify(value)
    if text is not None:
        ids.add(text)


def _chunks_of(raw: Any) -> list[Any]:
    if raw is None:
        return []
    mapping = _as_mapping(raw)
    if mapping is not None and "chunks" in mapping:
        chunks = mapping.get("chunks") or []
        return list(chunks)
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [raw]


@dataclass(frozen=True)
class AttachedContext:
    """Context attached by one call to The Fork's retriever."""

    chunks: tuple[Any, ...]
    source_ids: frozenset[str]
    support_text: str

    @property
    def present(self) -> bool:
        return len(self.chunks) > 0

    @property
    def allowed_ids(self) -> frozenset[str]:
        return self.source_ids


def context_from_retrieve(raw: Any) -> AttachedContext:
    """Build attached context from whatever ``retrieve`` returned."""

    ids: set[str] = set()
    texts: list[str] = []
    chunks = tuple(_chunks_of(raw))
    for chunk in chunks:
        _collect(chunk, ids, texts, 0)
    return AttachedContext(
        chunks=chunks,
        source_ids=frozenset(ids),
        support_text="\n".join(texts),
    )


def context_from_chunks(chunks: Iterable[Any]) -> AttachedContext:
    return context_from_retrieve(list(chunks))
