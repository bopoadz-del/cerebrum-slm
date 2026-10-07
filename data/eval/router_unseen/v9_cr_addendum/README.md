# Router sealed eval: v9 change-request addendum

Sealed 2026-10-07 (Asia/Dubai) under owner order 21:33 +04. `scripts/router/seal_sealed.py` read the owner's returned sheet `router_sealed_labelling_sheet_v9_cr_LABELLED.xlsx` (Drive `SLM/router_sealed_v9_cr`) and wrote the owner's ticks unedited.

- Rows: 14 (V9CR-S001..S014). Every row is ticked `change request`. Unsure: 0. Excluded: 0.
- Owner notes: V9CR-S007 is a priced Request for Change Order about the works, so it is `change request`. The alternative would be `claim`, and the owner's notes flag it as a judgement call. V9CR-S002's "Accepted" box does not change its label: the text says the change will go on a future change order, so the document is still the request.
- The sheet notes say the rows were first labelled from the PDF text by the assistant. The owner checked and returned all 14 as owner gold, as for v8.
- Fields: sheet_id, label, file_sha256 (sha256 of the candidate PDF), project=web_public, isolation_key (first 8 hex of the source-PDF sha256), source_url, excerpt (the first 300 characters on the sheet). No PDFs and no full text are stored here.
- This is a NEW sealed file, an addendum only. No row was added to, removed from or relabelled in any existing sealed file (v5, v8, v9_retick/v5, v9_retick/v8).
- The `file_sha256` and source-domain sets equal the pre-registered candidates in `data/router/cr_v9_sealed_candidates_isolation.json`.
- Isolation (`isolation.json`):
  - `router.isolation` rejected 0 rows in train (1602), val (880), teacher_labels (5482) and every additions file.
  - 0 shared document hashes with the other sealed sets.
  - 0 shared source domains with the change-request train additions.
  - 0 excerpt 12-gram overlap with train or val.
  - Full-text 12-grams: 11 train/val rows share form boilerplate (at most 3.5% of one sealed document's 12-grams). These are different documents from different domains.
- Label set: v9 (`configs/router/labels.json`, 22 labels).
- Config: `configs/router/sealed_eval.json` → `v9_sealed` lists v5_retick (64) + v8_retick (185) + this addendum (14) = 263 combined rows. Change request has 14 sealed rows there, so it is passable at `MIN_SEALED_PER_LABEL = 12`. Scored alone, the addendum is single-label, so its own gate_v2 cannot pass. The gate is read on the combined set.
- Each set is scored at most once per adapter. Do not put these documents or labels into training.
