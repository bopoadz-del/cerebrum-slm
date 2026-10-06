# Router labels

The label set is `configs/router/labels.json`. Code loads that file. It does not declare another set, and it does not add a label.

A label comes from document content. A filename, a folder, a document id, and a project id are not labels.

## Raw pool

Pull request #25 (`data/router-labels`) is the raw document pool. That file is not training data. `fork_declared_type` is the stored Fork type, kept as a reference column. Nothing trains on it. Rows that still carry `fork_declared_type` or `declared_type` are unlabelled.

## Sealed eval

The sealed set is 60 documents from Master Folder (or another corpus not yet used as training labels), labelled by a practitioner. Master Folder, including DG2 Infra Pack 1, is a valid source: not all of Master Folder is in Fork, and nothing is sealed yet. The blank sheet and the owner line are in `data/sealed/router/`. The sealed labels, when the owner returns the sheet, are written to `data/eval/router_unseen/` (`configs/router/sealed_eval.json`). That file is empty until then. `file_sha256` and the top-level corpus folder are exclusion keys, not labels.

Holding out one Fork project is an extra in-pool check only. It is not the sealed set.

A training split refuses a pool row whose document sha256 or project is already in `data/eval/router_unseen/sealed_labels.jsonl`. The training entry point does not read `data/eval/`.

## Scaffold

`scripts/router/teacher_label.py` dry-runs. It does not write training labels and it does not call a teacher API. `scripts/router/human_sample.py` draws a stratified sheet from content labels that already exist, including rare labels, without cloning rows. `scripts/router/report_counts.py` counts those labels. `scripts/router/majority_gate.py` fails a predictor that returns the majority label for every row, including when that predictor's accuracy is 1.

Teacher labelling has not been run. Human review has no labelled sample yet. No adapter is trained. The sealed set has not been scored.
