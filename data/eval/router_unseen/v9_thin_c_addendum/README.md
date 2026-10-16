# Router sealed eval: v9 thin_c addendum

Sealed 2026-10-08 (Asia/Dubai). `scripts/router/seal_sealed.py` read the owner's returned sheet
`router_sealed_labelling_sheet_v9_thin_c_LABELLED.xlsx` (Drive `SLM/router_sealed_v9_thin_c`) with a meta file and
wrote the owner's tick unedited.

- Rows: 1 (V9TH-S078). Owner tick: `meeting minutes`. Unsure: 0. Excluded: 0.
- The other 8 thin_c rows stay WITHDRAW on provenance (no source URL recoverable) and are NOT sealed;
  they enter the internal additions pool flagged `provenance_status=no-provenance` (data/router/additions_thin_v9c.jsonl).
- Provenance (collection rule 2026-10-08): source_url = sha256:b851067d8eadbcf7
  (Town of Ogunquit DocumentCenter). Verified by exact page-text match (window ratio 1.0) of the Drive PDF against the
  fetched binder.
- Fields: sheet_id, label, file_sha256 (sha256 of the candidate PDF), project=web_public,
  isolation_key (first 8 hex of the source-PDF sha256), source_url, excerpt (sheet excerpt). No full text stored.
- This is a NEW sealed file, an addendum only. No row was added to, removed from or relabelled in any existing sealed file.
- Isolation (`isolation.json`): 0 shared document hashes and 0 shared projects with train, val, teacher labels and every
  additions file.
- Label set: v9 (`configs/router/labels.json`, 22 labels). Registered in `configs/router/sealed_eval.json` → `v9_sealed`.
- Scored at most once per adapter. Do not put this document or its label into training.
