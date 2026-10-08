# Router sealed eval: v9 web_g addendum

Sealed 2026-10-09 (Asia/Dubai) from the owner's order on the web_g sheet (9 candidate rows, ticks applied from that order; the posted Drive sheet itself was still unticked). `scripts/router/seal_addendum.py` read the label-column ticks with an internal meta file (content sha256, source-PDF key, source URL). It copied those ticks unedited.

- **Sealed: 7 rows**, only rows the owner accepted, all with `unsure` = False. By class: payment application 4, site instruction 2, claim 1.
- **Held: 2 rows.** They are in `held.jsonl` and never enter training. Their hashes are in `data/router/web_g_sealed_candidates_isolation.json` (status `held`).
  - One row is a second extract of a source document already represented by another row in this batch. The two row sha256 values differ; the source-document sha256 is the same. Confirmed from the candidate manifest before the hold. Only one of them is sealed.
  - One row was not accepted under the suggested class. The owner classed it as correspondence. It is not sealed.
- **Labels come from the owner's order only.** No filename, folder, source site or form number set a label.
- **Provenance:** every sealed row carries `source_url` and `file_sha256` (the sha256 of the candidate PDF). `isolation_key` is the first 8 hex of the source-PDF sha256.
- **Per-(project, class) cap ≤ 3.** No pair this addendum touches exceeds the cap. One sealed claim shares its project key with one row already sealed; that pair is 2, under the cap. `data/router/sealed_cap_exhaustion.json` is recomputed from the registered sets (still 12 exhausted pairs; this addendum adds none).
- **Isolation** (`isolation.json`): `router.isolation` rejected 0 training rows. Box checks on all 9 rows found 0 hits on sha256, text sha256, source-PDF sha256, first-300 or source URL against train/val, teacher labels, additions files and every other sealed file. Max 12-gram share of the sealed rows was 0.1933 against training text and 0.2078 within the batch, both under the fixed 0.3 / 0.5 rule.
- **Combined:** 312 + 7 = **319**. Registered in `configs/router/sealed_eval.json` → `v9_sealed` (`web_g_addendum`). Nothing was swapped, removed or relabelled in any existing sealed file.
- **Gap table** (`gap_table.json`, sealed n vs the passable threshold 12):

| class | before | after | short of 12 |
|---|---|---|---|
| claim | 9 | 10 | 2 |
| payment application | 6 | 10 | 2 |
| inspection request | 3 | 3 | 9 |
| site instruction | 9 | 11 | 1 |
| every other class | unchanged | unchanged | 0 |

Each set is scored at most once per adapter. Do not put these documents or labels into training.
