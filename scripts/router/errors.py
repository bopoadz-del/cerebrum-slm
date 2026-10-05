"""Failures for the document-type router. Messages carry no document text."""

from __future__ import annotations


class RouterError(Exception):
    """Base error. Subclasses keep document text out of the message."""


class RouterConfigError(RouterError):
    """The router config files are missing or inconsistent."""


class LabelExportMissing(RouterError):
    """No usable labeled export. Callers stop; they do not invent rows."""

    def __init__(self, detail: str, rejected_by_reason: dict[str, int] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.rejected_by_reason = rejected_by_reason or {}


class SealError(RouterError):
    """The seal cannot be written or no longer matches the export."""
