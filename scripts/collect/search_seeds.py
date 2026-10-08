"""Search leg for batch _e (runs in Actions; not walled there).

Generic: queries are data (class + query string + link pattern). Results come
from Bing RSS; every returned link matching the pattern becomes a fetch seed.
No per-site code, no labels assigned here.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    "(+cerebrum-slm-collector; GitHub bopoadz-del/cerebrum-slm)"
)

QUERIES = [
    # priority order from the owner task
    {"class": "inspection request", "q": '"request for inspection" OR "inspection request" form pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "claim", "q": '"extension of time" claim "notice of claim" construction pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "payment certificate", "q": '"interim payment certificate" pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "payment application", "q": '"application and certificate for payment" G702 pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "NCR", "q": '"nonconformance report" construction DOT OR transit OR water pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "site instruction", "q": '"site instruction" form construction pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "RFI", "q": '"request for information" log construction project pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
    {"class": "meeting minutes", "q": '"OAC meeting minutes" pdf',
     "pattern": r"https?://[^\"\s<>]+\.pdf", "max": 8},
]


def search_bing(query: str, count: int = 20) -> list[str]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode(
        {"q": query, "format": "rss", "count": count}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        xml = r.read()
    root = ET.fromstring(xml)
    links = []
    for item in root.iter("item"):
        for child in item:
            if child.tag == "link" and child.text:
                links.append(child.text.strip())
    return links


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("./out"))
    ap.add_argument("--queries", type=Path, help="jsonl of {class, q, pattern, max}")
    args = ap.parse_args(argv)
    queries = QUERIES
    if args.queries:
        queries = [json.loads(l) for l in args.queries.read_text(encoding="utf-8").splitlines() if l.strip()]

    args.out.mkdir(parents=True, exist_ok=True)
    seeds = []
    report = []
    for spec in queries:
        try:
            links = search_bing(spec["q"])
        except Exception as e:  # noqa: BLE001
            report.append({"class": spec["class"], "query": spec["q"], "error": type(e).__name__, "n": 0})
            print(f"{spec['class']}: SEARCH FAILED {type(e).__name__}")
            continue
        pat = re.compile(spec["pattern"], re.I)
        kept = []
        for link in links:
            if pat.search(link) and link not in kept:
                kept.append(link)
            if len(kept) >= spec.get("max", 8):
                break
        report.append({"class": spec["class"], "query": spec["q"], "n": len(kept)})
        for link in kept:
            seeds.append({"url": link, "class": spec["class"]})
        print(f"{spec['class']}: {len(kept)} seeds from {len(links)} results")
        time.sleep(2)  # politeness between queries

    (args.out / "search_seeds.jsonl").write_text(
        "".join(json.dumps(s) + "\n" for s in seeds), encoding="utf-8"
    )
    (args.out / "search_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"total seeds: {len(seeds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
