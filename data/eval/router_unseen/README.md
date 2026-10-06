# Router sealed eval

This is the sealed router set. It is not a training set.

v5 seal: 64 public-web rows, owner-labelled, agreement 0.875, kappa 0.864. `scripts/router/seal_sealed.py` wrote the owner's ticks from the Labelling sheets. Unsure rows: 0. Excluded rows: 0. The script also writes `agreement.json` and `SHA256SUMS`. Agreement is computed only from the hidden proposals and does not change a sealed label. No document text is stored in this directory.

`file_sha256` (the document content sha256) and `project` (`web_public`) are exclusion keys. They are not labels. `isolation_key` is `web_public`.

Isolation: `router.isolation.require_isolated(load_exclusions(sealed_labels.jsonl))` passed on `data/router/train.jsonl` (1334), `data/router/val.jsonl` (683), and `data/router/teacher_labels.jsonl` (4555). Rejected 0 rows in each file.

The blank practitioner sheet stays in `data/sealed/router/`. The sealed set has not been scored. The pre-registered gate is `docs/router/SEALED_GATE.md`.
