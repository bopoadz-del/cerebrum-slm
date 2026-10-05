# Sealed router eval

OWNER: sealed router eval needs 60 documents from Master Folder (or another corpus not yet used as training labels), labelled by a practitioner

This directory waits for that corpus. Master Folder, including DG2 Infra Pack 1, is a valid source: not all of Master Folder is in Fork, and nothing is sealed yet. Another corpus is valid when it has not yet been used as training labels. A practitioner labels the documents.

`labelling_sheet.csv` has 60 blank rows, five for each label in `configs/router/labels.json`. The practitioner reads the excerpt and ticks exactly one label from the document content. Do not infer a label from the filename, the folder, the document id, or the project name. Leave `filename_optional_blank` empty. Tick `unsure` when the text does not support one declared label. `unsure` is not a training label.

## sealed_labels.jsonl

The drop file is `sealed_labels.jsonl`. It ships empty. One JSON object per line, after the owner corpus exists:

```json
{"sheet_id": "SEAL-001", "label": "<one label from configs/router/labels.json>", "author": "<practitioner>"}
```

Do not add a row before that corpus exists. Do not invent excerpt text. Labelling tools in this repo refuse to read this directory.
