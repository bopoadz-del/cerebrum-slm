# Sealed router eval

OWNER: sealed router eval needs 60 documents from Master Folder (or another corpus not yet used as training labels), labelled by a practitioner

This directory waits for that corpus. Master Folder, including DG2 Infra Pack 1, is a valid source: not all of Master Folder is in Fork, and nothing is sealed yet. Another corpus is valid when it has not yet been used as training labels. A practitioner labels the documents.

`labelling_sheet.csv` has 60 blank rows, five for each label in `configs/router/labels.json`. The practitioner reads the excerpt and ticks exactly one label from the document content. Do not infer a label from the filename, the folder, the document id, or the project name. Leave `filename_optional_blank` empty. Tick `unsure` when the text does not support one declared label. `unsure` is not a training label. A row that cannot be read is marked `excluded_from_eval` and is not sealed.

The returned sheet may be csv or xlsx. Optional columns are `source_path`, `file_sha256`, and `excluded_from_eval`. `source_path` supplies the top-level corpus folder as an exclusion key only. It is not a label.

## Sealed output

`scripts/router/seal_sealed.py` writes the owner's ticks to `data/eval/router_unseen/sealed_labels.jsonl` and a `SHA256SUMS` file. This directory is the blank sheet. It does not hold sealed labels. No sealed rows are invented here.
