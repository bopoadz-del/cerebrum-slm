"""Bucket exact amounts to magnitude tokens.

The generic redactor turns comma-grouped digits into ``<AMT:~1eN>`` and leaves
the same amount written in words. This pass replaces written amounts and exact
digit amounts with the same magnitude token. Thousands groups count only when
every separator is the same character, repeated via a backreference: comma
(with the same surrounding spaces), space, nbsp, thin space, or narrow nbsp.
``N`` is ``floor(log10(abs(value)))`` of the separator-stripped value; a zero
amount is ``<AMT:~1e0>``.

A one- or two-digit minor-unit column printed immediately after an amount
token folds into that token. An ``and NN/100`` tail, with an optional
minor-unit word, folds into the preceding amount. Slash-coded reference
numbers (three or more segments, or an alphanumeric code) become one
``<REF>`` token. The repo has no earlier reference-token form; name bars
stay bars.

Dates, clause numbers, percentages, years, page fractions and existing
``<...>`` tokens stay. A single small cardinal ("one", "two") stays; a
written amount is two or more number-words, a hyphenated compound, or a
scale word (hundred and up).
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

# One separator for the whole amount. The comma alternative keeps the same
# surrounding spaces; a space separator is exactly one character, so a wider
# column gap does not join cells.
_SEP = r"(?P<sep>(?:[ \t]*,[ \t]*)|[ \u00a0\u2009\u202f])"
_GROUPED_NUM = (
    r"(?!0)\d{1,3}"
    + _SEP
    + r"\d{3}(?:(?P=sep)\d{3})*(?:(?P=sep)\d{1,2}(?=\.\d{2}))?(?:\.\d{2})?"
)
_GROUPED = re.compile(rf"(?<![\d./<>\-])(?P<num>{_GROUPED_NUM})(?![\d%])")
# A plain two-decimal amount. Fixed-width lookbehinds keep this off the tail
# of a grouped number (that tail would keep the leading groups and a wrong magnitude).
_PLAIN_DECIMAL = re.compile(
    r"(?<![\d./<>\-])"
    r"(?<!\d )"
    r"(?<!\d\u00a0)"
    r"(?<!\d\u2009)"
    r"(?<!\d\u202f)"
    r"(?<!\d,)"
    r"(?<!\d, )"
    r"\d+\.\d{2}(?!\s*%)(?![\d.])"
)
_FILS_FRAC = re.compile(
    r"(?i)\b(?:fils|fills|cents?)\s+(\d{1,3}\s*/\s*100)\b"
)
_CUR_WORD = r"aed|usd|eur|gbp|sar|qar|dirhams?|dollars?|fils|fills|riyals?"
_AMOUNT_LABEL = rf"{_CUR_WORD}|amount|sum|total"
_CUR_BEFORE = re.compile(
    rf"(?i)\b({_CUR_WORD})\b"
    rf"(\s*[:.]?\s*)({_GROUPED_NUM}|\d{{2,}}(?:\.\d+)?)(?!\s*%)"
)
_CUR_AFTER = re.compile(
    rf"(?i)(?<![\d./<>\-])({_GROUPED_NUM}|\d{{2,}}(?:\.\d+)?)(\s+)"
    rf"({_CUR_WORD})\b"
)
_LABEL_BEFORE = re.compile(rf"(?i)\b(?:{_AMOUNT_LABEL})\b\s*[:.]?\s*$")
_LABEL_AFTER = re.compile(rf"(?i)^\s*[:.]?\s*(?:{_AMOUNT_LABEL})\b")
_UNIT_AFTER = re.compile(
    r"(?i)[ \t\u00a0\u2009\u202f]*(?:m2|m3|m²|m³|kg|pcs|nos|days|m|t)\b"
)
_DATE_SHAPE = re.compile(
    r"(?i)^(?:"
    r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}"
    r"|\d{4}[./\-]\d{1,2}[./\-]\d{1,2}"
    r"|\d{1,2}[ \u00a0\u2009\u202f]\d{1,2}[ \u00a0\u2009\u202f]\d{2,4}"
    r")$"
)
_LEADING_ZERO_RUN = re.compile(
    r"(?<!\d)0+(?:[ \t]*,[ \t]*|[ \u00a0\u2009\u202f])$"
)
_PHONE_BEFORE = re.compile(r"(?:\+|(?<!\d)00|\()\s*$")
_MONTH_AFTER = re.compile(
    r"(?i)\s*[-/]?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b"
)
_STRUCT_BEFORE = re.compile(
    r"(?i)(?:sub-?\s*)?clauses?|sections?|tables?|\bno\.?\s*$"
)
_YEAR = re.compile(r"(?:19|20)\d{2}")

# Amount token already produced by this module or the generic redactor.
_AMT_TOKEN = r"<AMT(?::~1e-?\d+)?>"
_MINOR_UNIT = r"(?:fils|fills|cents?|halalas?)"
_MONTH_WORD = (
    r"(?:january|february|march|april|june|july|august|september|october|"
    r"november|december|jan|feb|mar|apr|may|jun|jul|aug|sept|sep|oct|nov|dec)"
)
_MONTHS = frozenset(re.findall(r"[a-z]+", _MONTH_WORD))
_HUNDREDTHS = re.compile(
    rf"(?i)(?P<amt>{_AMT_TOKEN})"
    rf"(?:[ \t\u00a0]*,[ \t\u00a0]*|[ \t\u00a0]+)"
    rf"and[ \t\u00a0]+"
    rf"(?:"
    rf"\d{{1,2}}[ \t\u00a0]*/[ \t\u00a0]*100(?!\d)"
    rf"(?:[ \t\u00a0]+{_MINOR_UNIT}\b)?"
    rf"|{_MINOR_UNIT}\b[ \t\u00a0]+\d{{1,2}}[ \t\u00a0]*/[ \t\u00a0]*100(?!\d)"
    rf")"
)
# 1-2 digits immediately after an amount. Not a longer number, a decimal,
# a percentage, a slash fraction, or the start of a calendar date.
_MINOR_AFTER = re.compile(
    rf"(?P<gap>[ \t\u00a0]+)(?P<digits>\d{{1,2}})"
    rf"(?![\w.])(?![ \t\u00a0]*%)(?![ \t\u00a0]*/)"
    rf"(?![ \t\u00a0]*[-/]?[ \t\u00a0]*{_MONTH_WORD}\b)",
    re.IGNORECASE,
)
_SLASH_RUN = re.compile(r"(?<![\w/<>])([A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)+)(?![\w/])")
_REF = "<REF>"


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


def _groups_of_three(raw: str) -> int:
    head = raw.split(".", 1)[0]
    return sum(len(part) == 3 for part in re.split(r"[, \u00a0\u2009\u202f]+", head) if part)


def _is_schedule_or_table_row(raw: str) -> bool:
    """Separate cells, a hyphenated index, or a dotted item index (1.2.3).

    A two-decimal amount is not an index: the cents tail is exactly two digits
    and there is only one dot.
    """
    if re.search(r"[ \t\u00a0]{2,}", raw):
        return True
    if re.fullmatch(r"\d{1,3}(?:-\d{1,3})+", raw):
        return True
    return re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){2,}", raw) is not None


def _blocked_amount(text: str, start: int, end: int, raw: str) -> bool:
    if _UNIT_AFTER.match(text, end):
        return True
    if _DATE_SHAPE.fullmatch(raw) or _is_schedule_or_table_row(raw):
        return True
    if _structural(text, start, raw):
        return True
    pre = text[max(0, start - 8) : start]
    if _LEADING_ZERO_RUN.search(pre) or _PHONE_BEFORE.search(pre):
        return True
    return False


def _label_adjacent(text: str, start: int, end: int) -> bool:
    pre = text[max(0, start - 24) : start]
    post = text[end : end + 24]
    return _LABEL_BEFORE.search(pre) is not None or _LABEL_AFTER.match(post) is not None


def _accept_grouped(text: str, start: int, end: int, raw: str) -> bool:
    """Two groups of three digits, a currency or amount label, or a cents tail.

    A single thousands group with no label and no cents tail is a count.
    """
    if _blocked_amount(text, start, end, raw):
        return False
    threes = _groups_of_three(raw)
    if threes >= 2:
        return True
    if _label_adjacent(text, start, end):
        return True
    return bool(re.search(r"\.\d{2}$", raw) and threes >= 1)


def _digit_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _GROUPED.finditer(text):
        start, end = match.start("num"), match.end("num")
        raw = match.group("num")
        if _in_angle(text, start, end) or not _accept_grouped(text, start, end, raw):
            continue
        spans.append((start, end, magnitude_token(_parse_digits(raw))))
    for match in _PLAIN_DECIMAL.finditer(text):
        if _in_angle(text, match.start(), match.end()):
            continue
        if _blocked_amount(text, match.start(), match.end(), match.group()):
            continue
        spans.append((match.start(), match.end(), magnitude_token(_parse_digits(match.group()))))
    for match in _FILS_FRAC.finditer(text):
        if _in_angle(text, match.start(1), match.end(1)):
            continue
        spans.append(
            (match.start(1), match.end(1), magnitude_token(_parse_digits(match.group(1))))
        )
    for pattern, group in ((_CUR_BEFORE, 3), (_CUR_AFTER, 1)):
        for match in pattern.finditer(text):
            start, end = match.start(group), match.end(group)
            raw = match.group(group)
            if _in_angle(text, start, end) or _blocked_amount(text, start, end, raw):
                continue
            if re.search(r"[, \u00a0\u2009\u202f]", raw) and not _accept_grouped(text, start, end, raw):
                continue
            spans.append((start, end, magnitude_token(_parse_digits(raw))))
    return spans


def _minor_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for amt in re.finditer(_AMT_TOKEN, text):
        tail = _MINOR_AFTER.match(text, amt.end())
        if tail is None:
            continue
        spans.append((tail.start(), tail.end(), ""))
    return spans


def _hundredths_spans(text: str) -> list[tuple[int, int, str]]:
    return [
        (match.start(), match.end(), match.group("amt"))
        for match in _HUNDREDTHS.finditer(text)
    ]


def _is_calendar_date(parts: list[str]) -> bool:
    """Slash or month dates stay: dd/mm/yyyy, dd/mm/yy, yyyy/mm/dd, dd/Mon/yy."""
    if any(part.lower() in _MONTHS for part in parts):
        return True
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return False
    lengths = [len(part) for part in parts]
    day_month_year = lengths[0] <= 2 and lengths[1] <= 2 and lengths[2] in (2, 4)
    year_month_day = lengths[0] == 4 and lengths[1] <= 2 and lengths[2] <= 2
    if day_month_year:
        day, month = int(parts[0]), int(parts[1])
    elif year_month_day:
        day, month = int(parts[2]), int(parts[1])
    else:
        return False
    return 1 <= day <= 31 and 1 <= month <= 12


def _is_ref(parts: list[str]) -> bool:
    """Three or more slash segments, or a shorter alphanumeric code. Not a date."""
    if _is_calendar_date(parts):
        return False
    if not any(ch.isdigit() for part in parts for ch in part):
        return False
    if len(parts) >= 3:
        return True
    has_letter = any(ch.isalpha() for part in parts for ch in part)
    return has_letter


def _ref_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for match in _SLASH_RUN.finditer(text):
        if _in_angle(text, match.start(), match.end()):
            continue
        parts = match.group(1).split("/")
        if _is_ref(parts):
            spans.append((match.start(), match.end(), _REF))
    return spans


def bucket_amounts(text: str) -> tuple[str, int]:
    """Return text with exact amounts replaced, and how many replacements were made."""
    text, word_count = _apply(text, _word_spans(text))
    text, digit_count = _apply(text, _digit_spans(text))
    text, minor_count = _apply(text, _minor_spans(text))
    text, tail_count = _apply(text, _hundredths_spans(text))
    text, ref_count = _apply(text, _ref_spans(text))
    return text, word_count + digit_count + minor_count + tail_count + ref_count
