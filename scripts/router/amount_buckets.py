"""Bucket exact amounts to magnitude tokens.

The generic redactor turns grouped digits into ``<AMT:~1eN>`` and leaves the
same amount written in words, plus spaced thousands-groups and two-decimal
leftovers. This pass replaces those with the same magnitude token.
``N`` is ``floor(log10(abs(value)))``; a zero amount is ``<AMT:~1e0>``.

Dates, clause numbers, percentages, years and existing amount tokens stay.
A single small cardinal ("one", "two") stays; a written amount is two or
more number-words, a hyphenated compound, or a scale word (hundred and up).
"""

from __future__ import annotations

import math
import re

_SMALL: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_SCALE: dict[str, int] = {
    "hundred": 100,
    "hundreds": 100,
    "thousand": 1_000,
    "thousands": 1_000,
    "lakh": 100_000,
    "lakhs": 100_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
}

_WORDS = sorted([*_SMALL, *_SCALE], key=len, reverse=True)
_WORD = "(?:" + "|".join(_WORDS) + ")"
_SMALL_ALT = "(?:" + "|".join(sorted(_SMALL, key=len, reverse=True)) + ")"
_SCALE_ALT = "(?:" + "|".join(sorted(_SCALE, key=len, reverse=True)) + ")"
_ATOM = rf"{_WORD}(?:-{_WORD})?"
_GAP = r"(?:\s*,\s*|\s+and\s+|\s+)"
_WORD_AMOUNT = re.compile(
    rf"(?i)\b(?:{_ATOM}(?:{_GAP}{_ATOM})+|{_SMALL_ALT}-{_SMALL_ALT}|{_SCALE_ALT})\b"
)
_FRAC_TAIL = re.compile(
    rf"(?i)\s*(?:,\s*)?(?:and\s+)?(?:fils|fills|cents?)\s+"
    rf"(?:\d{{1,3}}\s*/\s*100|{_ATOM}(?:{_GAP}{_ATOM})*)"
    rf"|\s+\d{{1,3}}\s*/\s*100"
)

# Grouped thousands (spaces allowed), including a short final group before
# a two-decimal tail. Then a plain two-decimal amount.
_EXACT_DIGITS = re.compile(
    r"(?<![\d./<>\-])\d{1,3}(?:\s*,\s*\d{3})+(?:\s*,\s*\d{1,3})?(?:\.\d{2})?(?![\d%])"
    r"|(?<![\d./<>\-])\d+\.\d{2}(?!\s*%)(?![\d.])"
)
_FILS_FRAC = re.compile(
    r"(?i)\b(?:fils|fills|cents?)\s+(\d{1,3}\s*/\s*100)\b"
)
_CUR_BEFORE = re.compile(
    r"(?i)\b(aed|usd|eur|gbp|sar|qar|dirhams?|dollars?|fils|fills|riyals?)\b"
    r"(\s*[:.]?\s*)(\d{2,}(?:\.\d+)?)(?!\s*%)"
)
_CUR_AFTER = re.compile(
    r"(?i)(?<![\d./<>\-])(\d{2,}(?:\.\d+)?)(\s+)"
    r"(aed|dirhams?|dollars?|fils|fills|riyals?)\b"
)
_MONTH_AFTER = re.compile(
    r"(?i)\s*[-/]?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b"
)
_STRUCT_BEFORE = re.compile(
    r"(?i)(?:sub-?\s*)?clauses?|sections?|tables?|\bno\.?\s*$"
)
_YEAR = re.compile(r"(?:19|20)\d{2}")


def magnitude_token(value: float) -> str:
    """``<AMT:~1eN>`` for the order of magnitude of ``value``."""
    absolute = abs(value)
    if absolute == 0:
        exponent = 0
    elif absolute < 1:
        exponent = math.floor(math.log10(absolute))
    else:
        exponent = math.floor(math.log10(absolute))
    return f"<AMT:~1e{exponent}>"


def _in_angle(text: str, start: int, end: int) -> bool:
    left = text.rfind("<", 0, start)
    if left < 0:
        return False
    right = text.find(">", left)
    return right >= end


def _atom_kind(atom: str) -> tuple[str, int]:
    parts = atom.lower().split("-")
    if len(parts) == 2 and all(part in _SMALL or part in _SCALE for part in parts):
        if parts[1] in _SCALE:
            base = _SMALL.get(parts[0], 1) or 1
            return "scale", base * _SCALE[parts[1]]
        if parts[0] in _SMALL and parts[1] in _SMALL:
            return "small", _SMALL[parts[0]] + _SMALL[parts[1]]
    word = parts[0]
    if word in _SCALE:
        return "scale", _SCALE[word]
    return "small", _SMALL[word]


def _parse_words(phrase: str) -> int:
    total = 0
    current = 0
    for atom in re.findall(_ATOM, phrase, flags=re.I):
        kind, value = _atom_kind(atom)
        if kind == "scale" and value >= 1000 and "-" not in atom:
            total += (current or 1) * value
            current = 0
        elif kind == "scale" and value == 100:
            current = (current or 1) * 100
        elif kind == "scale":
            total += (current or 1) * value
            current = 0
        else:
            current += value
    return total + current


def _parse_digits(raw: str) -> float:
    cleaned = re.sub(r"[\s,]", "", raw)
    if "/" in cleaned:
        num, den = cleaned.split("/", 1)
        return float(num) / float(den)
    return float(cleaned)


def _structural(text: str, start: int, raw: str) -> bool:
    pre = text[max(0, start - 24) : start]
    if _STRUCT_BEFORE.search(pre):
        return True
    if _MONTH_AFTER.match(text[start + len(raw) : start + len(raw) + 16]):
        return True
    compact = re.sub(r"[\s,]", "", raw)
    if _YEAR.fullmatch(compact) and "." not in raw:
        return True
    return False


def _apply(text: str, spans: list[tuple[int, int, str]]) -> tuple[str, int]:
    if not spans:
        return text, 0
    # Longer span wins when two matches start together (grouped amount vs its head).
    spans.sort(key=lambda span: (span[0], -span[1]))
    out: list[str] = []
    last = 0
    count = 0
    prev_end = -1
    for start, end, token in spans:
        if start < prev_end:
            continue
        out.append(text[last:start])
        out.append(token)
        last = end
        prev_end = end
        count += 1
    out.append(text[last:])
    return "".join(out), count


def _word_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _WORD_AMOUNT.finditer(text):
        if _in_angle(text, match.start(), match.end()):
            continue
        end = match.end()
        tail = _FRAC_TAIL.match(text, end)
        if tail is not None and not _in_angle(text, tail.start(), tail.end()):
            end = tail.end()
        spans.append((match.start(), end, magnitude_token(_parse_words(match.group()))))
    return spans


def _digit_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _EXACT_DIGITS.finditer(text):
        if _in_angle(text, match.start(), match.end()):
            continue
        if _structural(text, match.start(), match.group()):
            continue
        spans.append((match.start(), match.end(), magnitude_token(_parse_digits(match.group()))))
    for match in _FILS_FRAC.finditer(text):
        if _in_angle(text, match.start(1), match.end(1)):
            continue
        spans.append(
            (match.start(1), match.end(1), magnitude_token(_parse_digits(match.group(1))))
        )
    for match in _CUR_BEFORE.finditer(text):
        if _in_angle(text, match.start(3), match.end(3)):
            continue
        if _structural(text, match.start(3), match.group(3)):
            continue
        spans.append((match.start(3), match.end(3), magnitude_token(_parse_digits(match.group(3)))))
    for match in _CUR_AFTER.finditer(text):
        if _in_angle(text, match.start(1), match.end(1)):
            continue
        if _structural(text, match.start(1), match.group(1)):
            continue
        spans.append((match.start(1), match.end(1), magnitude_token(_parse_digits(match.group(1)))))
    return spans


def bucket_amounts(text: str) -> tuple[str, int]:
    """Return text with exact amounts replaced, and how many replacements were made."""
    text, word_count = _apply(text, _word_spans(text))
    text, digit_count = _apply(text, _digit_spans(text))
    return text, word_count + digit_count
