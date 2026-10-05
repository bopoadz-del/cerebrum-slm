# Router label export

Put a JSONL or CSV file in this directory, next to this README. Export files are gitignored. This directory is not a training set.

Each row needs a project id, a filename, the document text, and one label. The label has to match `configs/router/labels.json` after trimming and case folding. The importer does not read a label out of the filename or the text.

Column names are the aliases in `configs/router/dataset.json`. A shape, not a corpus row:

```json
{"project_id": "PROJECT", "filename": "FILE", "text": "TEXT", "label": "other"}
```

If this directory has no JSONL or CSV file, the router commands stop with `WALL: label export` and do not invent rows.
