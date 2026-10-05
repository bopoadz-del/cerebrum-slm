"""Extract the HDS-5 equation list (id, name, inputs) from the blind corpus PDF.

Same approach as ``scripts/eval/extract_symbol_table.py``: poppler ``pdftotext
-layout`` on the pages that carry the chapter-3 and Appendix-A equation numbers
printed in FHWA-HIF-12-026. Output is committed as data and attached as the
blind routing registry. Nothing is typed by hand.

    python scripts/eval/extract_hds5_equations.py --pdf hif12026.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "eval" / "graders" / "data" / "hds5_equations.json"
SYMBOLS = ROOT / "eval" / "graders" / "data" / "hds5_symbols.json"
SOURCE = {
    "title": "Hydraulic Design of Highway Culverts, Hydraulic Design Series Number 5, Third Edition (April 2012)",
    "publication": "FHWA-HIF-12-026",
    "url": "https://www.fhwa.dot.gov/engineering/hydraulics/pubs/12026/hif12026.pdf",
    "section": "Chapter 3 Culvert Hydraulic Design; Appendix A Inlet Control Equations",
}

TARGET_IDS = (
    "3.1", "3.2", "3.3", "3.4a", "3.4b", "3.4c", "3.4d", "3.4e",
    "3.5", "3.6a", "3.6b", "3.7", "3.8", "3.9",
    "A.1", "A.2", "A.3", "A.4",
)
PAGE_RANGES = ((91, 97), (190, 192))

_EQ_MARK = re.compile(r"\(\s*(?P<num>(?:3\.\d+[a-z]?|A\.\d+))\s*\)\s*$")
_JOIN_SUB = re.compile(r"\b([A-Z])\s+([a-z0-9]+)\b")
_PROSE = re.compile(
    r"^(The |In |If |This |For |Equation |When |Likewise|Values |Based |Bend |"
    r"Overtopping |Flow |Hydraulics |Composite |Unsubmerged |Submerged |Form |"
    r"Where|Average |Full |Inserting |Using |g is |Qo = Overtopping|Since |"
    r"Therefore|A direct|Between |Careful|Develop |From |Note |To make)"
)
_EXTRA = {
    "Hg", "Ku", "Ks", "Vu", "HV", "Hc", "hc", "yh", "Ap", "Tp", "Fr",
    "Qc", "Sf", "ke", "n1", "n2", "p1", "p2", "nc", "G", "Y", "M", "K",
}


def _page_text(pdf: Path, page: int) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _load_allowed() -> frozenset[str]:
    payload = json.loads(SYMBOLS.read_text(encoding="utf-8"))
    names = {row["symbol"] for row in payload["symbols"] if isinstance(row.get("symbol"), str)}
    names.update(_EXTRA)
    return frozenset(names)


def _normalize(text: str) -> str:
    text = text.replace("\uf8ed", "(").replace("\uf8ec", "(")
    text = text.replace("−", "-").replace("–", "-")
    text = _JOIN_SUB.sub(r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip(" =\t")
    text = re.sub(r"\bHW r\b", "HWr", text)
    text = re.sub(r"\bk e\b", "ke", text)
    return text


def _is_prose(line: str) -> bool:
    return bool(_PROSE.match(line.strip()))


def _expression(lines: list[str], index: int) -> str:
    parts: list[str] = []
    for j in range(max(0, index - 2), min(len(lines), index + 3)):
        raw = _EQ_MARK.sub("", lines[j]).rstrip()
        if not raw.strip():
            continue
        stripped = raw.strip()
        if j != index and (_is_prose(stripped) or len(stripped) > 70):
            continue
        if j != index and not (
            "=" in stripped
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", stripped)
            or re.search(r"[A-Za-z0-9]\s*[+\-/*^]\s*[A-Za-z0-9]", stripped)
            or re.fullmatch(r"[0-9A-Za-z().^\s/+*-]+", stripped)
        ):
            continue
        parts.append(stripped)
    expr = _normalize(" ".join(parts))
    if " is the " in expr:
        expr = expr.split(" is the ", 1)[0].rstrip(" ,")
    if not expr:
        expr = "Equation"
    return expr[:180]


def _definition_inputs(lines: list[str], start: int, allowed: frozenset[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for line in lines[start : start + 22]:
        stripped = line.rstrip()
        if not stripped.strip():
            continue
        if _EQ_MARK.search(stripped):
            break
        left = stripped.lstrip()
        if _is_prose(left) and names:
            break
        match = re.match(r"^([A-Za-z][A-Za-z0-9]*)\b", left)
        if match is None:
            continue
        if not (
            re.match(r"^[A-Za-z][A-Za-z0-9]*\s{2,}", left)
            or re.match(r"^[A-Za-z][A-Za-z0-9]*\s+=", left)
            or " = " in left
        ):
            continue
        sym = match.group(1)
        if sym not in allowed:
            continue
        if sym not in seen:
            seen.add(sym)
            names.append(sym)
    return names


def _expr_inputs(expr: str, allowed: frozenset[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for sym in sorted(allowed, key=len, reverse=True):
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(sym)}(?![A-Za-z0-9])")
        if pattern.search(expr) and sym not in seen:
            seen.add(sym)
            names.append(sym)
    return names


def parse_pages(pages: list[tuple[int, str]], allowed: frozenset[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    where_a: list[str] = []
    for page, text in pages:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            match = _EQ_MARK.search(line.rstrip())
            if match is None:
                continue
            number = match.group("num")
            if number not in TARGET_IDS:
                continue
            formula_id = f"HDS5-{number}"
            if formula_id in found:
                continue
            name = _expression(lines, index)
            inputs = _definition_inputs(lines, index + 1, allowed)
            if not inputs:
                inputs = _expr_inputs(name, allowed)
            found[formula_id] = {
                "id": formula_id,
                "number": number,
                "name": name,
                "inputs": inputs,
                "pdf_page": page,
            }
        if page == 191:
            for index, line in enumerate(lines):
                if line.strip().startswith("Where") or re.match(r"^\s*HW\s*i\b", line) or re.match(r"^\s*HWi\b", line):
                    start = index + (1 if "Where" in line else 0)
                    where_a = _definition_inputs(lines, start, allowed)
                    if where_a:
                        break
    if where_a:
        for num in ("A.1", "A.2", "A.3"):
            key = f"HDS5-{num}"
            if key in found:
                found[key]["inputs"] = list(dict.fromkeys(found[key]["inputs"] + where_a))
    return found


def extract(pdf: Path) -> dict:
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    allowed = _load_allowed()
    pages: list[tuple[int, str]] = []
    for start, end in PAGE_RANGES:
        for page in range(start, end + 1):
            pages.append((page, _page_text(pdf, page)))
    equations = parse_pages(pages, allowed)
    missing = [f"HDS5-{num}" for num in TARGET_IDS if f"HDS5-{num}" not in equations]
    if missing:
        raise RuntimeError(f"equation extraction missed: {missing}")
    empty = [row["id"] for row in equations.values() if not row["inputs"]]
    if empty:
        raise RuntimeError(f"equation extraction produced empty inputs for: {empty}")
    ordered = [equations[f"HDS5-{num}"] for num in TARGET_IDS]
    return {
        "source": dict(SOURCE, pdf_sha256=digest, pdf_pages=sorted({row["pdf_page"] for row in ordered})),
        "extracted_by": "scripts/eval/extract_hds5_equations.py",
        "count": len(ordered),
        "equations": ordered,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    table = extract(args.pdf)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"equations: {table['count']} from pages {table['source']['pdf_pages']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
