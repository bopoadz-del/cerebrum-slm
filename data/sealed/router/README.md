# Sealed router eval

OWNER: sealed router eval needs 60 documents from a project outside the Fork pool, labelled by a practitioner

This directory waits for that corpus. The documents must come from a project that is not in the Fork pool. The person who labels them must be a different author from the author of any training labels.

`labelling_sheet.csv` has 60 blank rows, five for each label in `configs/router/labels.json`. The practitioner reads the excerpt and ticks exactly one label from the document content. Do not infer a label from the filename, the folder, the document id, or the project name. Leave `filename_optional_blank` empty. Tick `unsure` when the text does not support one declared label. `unsure` is not a training label.

## sealed_labels.jsonl

The drop file is `sealed_labels.jsonl`. It ships empty. One JSON object per line, after the owner corpus exists:

```json
{"sheet_id": "SEAL-001", "label": "<one label from configs/router/labels.json>", "author": "<practitioner>"}
```

Do not add a row before that corpus exists. Do not invent excerpt text. Labelling tools in this repo refuse to read this directory.
