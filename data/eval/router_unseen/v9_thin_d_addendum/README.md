# Router sealed eval: v9 thin_d addendum

Sealed 2026-10-08 (Asia/Dubai) from the owner-ticked sheet
`router_sealed_labelling_sheet_v9_thin_d_LABELLED.xlsx` (Drive `SLM/router_sealed_v9_thin_d`).

- Rows: 13 (V9D-D003, D005–D013, D015–D017). Owner ticks copied unedited.
- Project diversity (rule: <=3 sealed rows per source project per class):
  NRC (www.nrc.gov/docs) NCR = 3; PPPL (ncsx.pppl.gov) NCR = 3; Ogunquit (ogunquit.gov/DocumentCenter)
  meeting minutes = 2; every other (project, class) pair = 1. Nothing exceeds 3.
- Domain note: the six NCR rows are NON-CONSTRUCTION domains (nuclear QA audits, fusion-coil fabrication).
  They are sealed for the NCR class but do not contribute construction-domain diversity.
- V9D-D014 (Ogunquit OAC-8 binder) is NOT sealed: it duplicates sealed V9TH-S078 (same binder). Dropped.
- V9D-D001, D002, D004 are blank templates -> internal `other` negatives (additions_thin_d.jsonl).
  V9D-D018, D019, D020 are filled PPPL NCRs over the 3-per-project cap -> internal NCR additions.
- Every sealed row carries source_url (collection rule 2026-10-08). Pre-sort was corrected by the owner:
  D005 is a completed G702 with the engineer's certificate -> payment certificate; D009 is a reply to a
  Notice of Nonconformance -> correspondence; D010/D011 are NRC Technical Review Packages -> report.
- New sealed file, addendum only. Nothing swapped in existing sealed files.
- Label set: v9. Registered in `configs/router/sealed_eval.json` -> `v9_sealed` (combined 277).
- Scored at most once per adapter. Do not put these documents or labels into training.
