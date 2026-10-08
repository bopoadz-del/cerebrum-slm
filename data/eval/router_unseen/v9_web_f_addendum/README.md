# Router sealed eval: v9 web_f addendum

Sealed 2026-10-08 (Asia/Dubai) under the owner's order of 16:57 +04. `scripts/router/seal_addendum.py` read the owner-ticked sheet
`router_sealed_labelling_sheet_v9_web_f_S080-S119_LABELLED.xlsx` (tab `Label`, 40 rows, `owner_tick` = True on every row) with an internal
meta file (content sha256, source-PDF key, source URL). It copied the owner's label ticks unedited.

- **Sealed: 34 rows**, only rows with `unsure` = False. By class: payment certificate 11, claim 5, meeting minutes 5, NCR 4,
  inspection request 3, RFI 3, payment application 2, site instruction 1. These match the owner's counts exactly.
- **Held: 6 rows** with `unsure` = True. They are in `held.jsonl` with the owner's notes, the owner's tentative tick and the owner's
  disposition. They are not sealed, not scored and never enter training. Their hashes are in
  `data/router/web_f_sealed_candidates_isolation.json` (status `held`).
  - Two are regulator permit-closure letters, not construction inspection requests. They are dropped from the inspection-request hunt.
    That class still needs at least 9 more rows from real ITR/WIR/MIR forms.
  - Three are G702 variants with ambiguous certificate blocks.
  - One is a meeting agenda, not minutes (see the eval note below).
- **Labels come from the owner's ticks only.** The sheet notes say the rows were first labelled from the PDF content by the assistant.
  The owner then ticked and returned all 40, and only the 34 not marked unsure are sealed. No filename, folder, source site or form number set a label.
- **Provenance:** every sealed row carries `source_url` and `file_sha256` (the sha256 of the candidate PDF). `isolation_key` is the first 8 hex of
  the source-PDF sha256. The seal tool holds any row that lacks URL or sha provenance; 0 rows were held for that.
  The sealed `excerpt` is the sheet excerpt (about the first 300 characters). No full text is stored here.
- **Per-(project, class) cap ≤ 3** (`router.seal_sealed.project_key`: URL host plus first path segment). The tool checks every pair the
  addendum touches against all registered sealed rows. Three pairs from this addendum sit exactly at the cap, and no existing sealed row shares a
  project with this addendum. `data/router/sealed_cap_exhaustion.json` lists every exhausted pair: 12 in all, 9 at cap and 3 legacy pairs over
  cap from older sets. It is derived from data by `router.seal_addendum.exhausted_pairs`, and a test recomputes it, so a later batch cannot add
  a row of that class from that project (`check_against_exhaustion`).
- **Isolation** (`isolation.json`):
  - `router.isolation` rejected 0 rows in train (1719), val (901), teacher_labels and every additions file at 92f8f0a.
    It also rejected 0 rows in v6's own training data (train 1712 / val 900 at 3f72300).
  - Box full-text checks on all 40 rows found 0 hits on sha256, text sha256, source-PDF sha256, first-300, source host on the training side,
    owner laptop archive and the _e pool. The highest 12-gram share was 0.217 against training text and 0.371 within the batch, both under the
    fixed 0.3 / 0.5 rule. These are AIA G702 form boilerplate, and two RFI forms from one project.
  - Cross-sealed: 0 of these documents or source PDFs are in any other sealed file.
  - The known precedent stays as registered: thin_d V9D-D003 is the same file and label as v5_retick S5-027, so it is counted twice in combined.
- **Combined:** 278 + 34 = **312**. Registered in `configs/router/sealed_eval.json` → `v9_sealed` (`web_f_addendum`). Nothing was swapped,
  removed or relabelled in any existing sealed file.
- **Gap table** (`gap_table.json`, sealed n vs the passable threshold 12):

| class | before | after | passable |
|---|---|---|---|
| RFI | 9 | 12 | yes (was no) |
| claim | 4 | 9 | no (3 short) |
| payment application | 4 | 6 | no (6 short) |
| payment certificate | 4 | 15 | yes (was no) |
| meeting minutes | 9 | 14 | yes (was no) |
| NCR | 8 | 12 | yes (was no) |
| inspection request | 0 | 3 | no (9 short) |
| site instruction | 8 | 9 | no (3 short) |
| all other classes | unchanged | unchanged | yes |

## Eval notes

- **Hard negative for meeting minutes.** One held row is an owner-construction meeting AGENDA: scheduled attendees and open items, but no
  record of discussion. The definition excludes agendas from meeting minutes. It is recorded here and in `held.jsonl` (`eval_note`) as a hard
  negative for meeting minutes. It is an eval note only and never goes into training.

Each set is scored at most once per adapter. Do not put these documents or labels into training. The v6 score on this addendum is in
`docs/router/runs/v6/web_f/`.
