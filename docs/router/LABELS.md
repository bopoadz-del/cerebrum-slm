# Router labels

The label set is `configs/router/labels.json`. Code loads that file. It does not declare another set, and it does not add a label.

A label comes from document content. A filename, a folder, a document id, and a project id are not labels.

## Output aliases

The router output parser maps an exact case-insensitive alias onto one canonical label. The match is the whole string after whitespace is collapsed. There is no fuzzy match. The label docs name no other alias.

| alias | canonical |
| --- | --- |
| change order | VO/CO |
| variation order | VO/CO |
| variation | VO/CO |
| CO | VO/CO |

The router model, the teacher, and a baseline share that parser (`scripts/router/parse_label.py`). The v5 sealed predictions were not re-parsed. The three v5 outputs that said `change order` stay recorded as misses.

## Raw pool

Pull request #25 (`data/router-labels`) is the raw document pool. That file is not training data. `fork_declared_type` is the stored Fork type, kept as a reference column. Nothing trains on it. Rows that still carry `fork_declared_type` or `declared_type` are unlabelled.

## Sealed eval

The v5 sealed set is 64 public-web documents, labelled by the owner. The blank 60-row sheet and the owner line stay in `data/sealed/router/`. The sealed labels are `data/eval/router_unseen/sealed_labels.jsonl` (`configs/router/sealed_eval.json`). `file_sha256` and `project` (`web_public` for this seal) are exclusion keys, not labels. The sealed set was scored once under sealed gate version 1. `sealed_scoring` stays false. sealed gate: FAIL (gate defect: condition (b) unsatisfiable as written); router NOT marked passed. Version 2 in `docs/router/SEALED_GATE.md` applies only to a future fresh sealed set. The v5 predictions were not re-scored or re-graded.

Holding out one Fork project is an extra in-pool check only. It is not the sealed set.

A training split refuses a pool row whose document sha256 or project is already in `data/eval/router_unseen/sealed_labels.jsonl`. The training entry point does not read `data/eval/`.

## Training path

`scripts/router/teacher_label.py` labels a pool from content when a key is set. It still refuses `data/sealed/` and `data/eval/router_unseen/`. An empty sealed file does not block the pool. `scripts/router/human_sample.py` draws a stratified sheet from content labels that already exist, including rare labels, without cloning rows. `scripts/router/report_counts.py` counts those labels. `scripts/router/majority_gate.py` fails a predictor that returns the majority label for every row, including when that predictor's accuracy is 1.

Human agreement is done (0.875, kappa 0.864). `data/router/human_sample_PENDING_OWNER.csv` is still a header only. By owner order, training proceeded before that check. The override is recorded in `configs/router/train.json`. It does not change the agreement gate.

The fixed teacher is `Qwen/Qwen3-8B` at temperature 0. The laptop run labelled the pool and trained a LoRA. Tinker does not serve `Qwen/Qwen3-4B`, so the adapter is `Qwen/Qwen3.5-4B`, rank 16, two epochs, 168 steps. The checkpoint is in `configs/serve/router-epoch2.json`. Split v2 (`scripts/router/split_v2.py`) groups by document series because the pool has no folder path, and caps drawing at 600 in train only. Human agreement is done (0.875, kappa 0.864). The sealed set was scored once and the router is not marked passed. Counts are in `docs/router/DATASET_CARD.md`.
