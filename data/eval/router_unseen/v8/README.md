# Router sealed eval - v8 (main + addendum)

Sealed 2026-10-07 (Asia/Dubai) with scripts/router/seal_sealed.py from the owner sheets
owner_return_v8.xlsx (V8-001..167) and owner_return_v8_addendum.xlsx (V8-168..188).

- Sealed rows: 185 (main 164 + addendum 21)
- Dropped (unsure ticked, no single label): V8-096, V8-110, V8-157
- Notes on rows say "labelled by Claude from excerpt only"; the owner returned them as owner gold labels.
- Fields: sheet_id, label, file_sha256, project=web_public, isolation_key, source_url, excerpt (sheet excerpt, about 600 chars). No PDFs.
- Isolation: router.isolation on v2 train (1334), v2 val (683), train (4533), val (22), teacher_labels (4555), teacher_labels_all (5627): 0 rejected. The addendum's first 300 characters do not appear in v2 train or val user text.
- Agreement with the hidden provisional proposals: 0.9676 overall (see agreement.json). Agreement does not change labels.
- The v5 seal at data/eval/router_unseen/sealed_labels.jsonl is untouched.

Scored once with the epoch-2 adapter. router_passed=False. See SEALED_RESULT.md. v8 is spent for this adapter.
Do not put these documents or labels into training.
