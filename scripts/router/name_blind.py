"""Name-blind check: blank title-block and party fields by field position.

A field is a party or title-block label followed by a colon. The value after the
colon is blanked up to the next "Label:" field, a line break, or a length cap.
Signature-block fields (Signature, Signed, Sign, By, Name) are blanked the same
way. The labels are layout words. No name, company, project or code is listed
here, and nothing is matched by the value it blanks.
"""

from __future__ import annotations

import re

MASK = "███"

# Party and title-block field labels (owner order 2026-10-07 17:03 +04), then signature-block fields.
PARTY_FIELDS = (
    "from",
    "to",
    "attn",
    "attention",
    "prepared by",
    "reviewed by",
    "approved by",
    "project",
    "contractor",
    "client",
    "consultant",
    "employer",
    "site",
)
SIGNATURE_FIELDS = ("signature", "signed", "signed by", "sign", "by", "name")

_QUALIFIER = r"(?:'s|’s)?(?:\s+(?:name|no\.?|number|ref\.?|reference|address|title|location|representative|rep\.?)){0,2}"
_FIELD_WORDS = "|".join(sorted((re.escape(f).replace(r"\ ", r"\s+") for f in PARTY_FIELDS + SIGNATURE_FIELDS), key=len, reverse=True))
_FIELD = re.compile(rf"(?<![\w'’])(?P<label>(?:{_FIELD_WORDS}){_QUALIFIER})\s*[:：]", re.IGNORECASE)
_COLON = re.compile(r"[:：]")
_WORD = re.compile(r"[\w'’./&#()-]+")
_MAX_VALUE = 80
_MAX_LABEL_WORDS = 4


def _label_start(text: str, colon: int, floor: int) -> int:
    """Start of the label that ends at ``colon``: the word before it, widened by layout only.

    A lowercase last word widens back to the nearest capitalised word ("Description of change").
    Otherwise the label is the single word before the colon, so a value is never cut short; a
    two-word label such as "Contract No" loses its first word to the blank (stricter, never looser).
    Never more than four words, never before ``floor``.
    """
    words = [m for m in _WORD.finditer(text, floor, colon)]
    if not words:
        return colon
    take = 1
    last = words[-1].group()
    if last[:1].islower():
        while take < min(len(words), _MAX_LABEL_WORDS) and not words[-take].group()[:1].isupper():
            take += 1
    return words[-take].start()


def _value_end(text: str, start: int) -> int:
    limit = min(len(text), start + _MAX_VALUE)
    newline = text.find("\n", start, limit)
    end = newline if newline != -1 else limit
    if newline == -1 and limit < len(text) and not text[limit].isspace():
        space = text.rfind(" ", start, limit)
        if space > start:
            end = space
    colon = _COLON.search(text, start, end)
    if colon is not None:
        end = max(start, _label_start(text, colon.start(), start))
    return end


def blank_fields(text: str) -> tuple[str, int]:
    """Return the text with field values blanked, and how many values were blanked."""
    out: list[str] = []
    cursor = 0
    blanked = 0
    for match in _FIELD.finditer(text):
        if match.start() < cursor:
            continue
        start = match.end()
        end = _value_end(text, start)
        value = text[start:end]
        out.append(text[cursor:start])
        if value.strip() and value.strip() != MASK:
            lead = value[: len(value) - len(value.lstrip())]
            trail = value[len(value.rstrip()):]
            out.append(f"{lead or ' '}{MASK}{trail or ' '}")
            blanked += 1
        else:
            out.append(value)
        cursor = end
    out.append(text[cursor:])
    return "".join(out), blanked


def flips(gold: list[str], before: list[str], after: list[str], labels: list[str]) -> dict:
    """Per-class prediction flips between the normal and the name-blind run, keyed by gold class."""
    if not (len(gold) == len(before) == len(after)):
        raise ValueError("gold, before and after must align")
    table = {label: {"n": 0, "flips": 0, "correct_before": 0, "correct_after": 0} for label in labels}
    for g, b, a in zip(gold, before, after):
        row = table.setdefault(g, {"n": 0, "flips": 0, "correct_before": 0, "correct_after": 0})
        row["n"] += 1
        row["flips"] += int(b != a)
        row["correct_before"] += int(b == g)
        row["correct_after"] += int(a == g)
    return table


def name_blind_gate(table: dict, min_per_label: int) -> dict:
    """FAIL when any passable class (n >= min_per_label) has a flip."""
    failing = sorted(label for label, row in table.items() if row["n"] >= min_per_label and row["flips"] > 0)
    return {"passed": not failing, "failing_passable_classes": failing, "min_per_label": min_per_label}
