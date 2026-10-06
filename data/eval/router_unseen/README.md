# Router sealed eval

This is the sealed router set. It is not a training set.

`sealed_labels.jsonl` is empty until `scripts/router/seal_sealed.py` writes the owner's ticks from the returned sheet. The script also writes `SHA256SUMS`. No rows are invented in this directory.

`file_sha256` and `project` (the source path's top-level corpus folder) are exclusion keys. They are not labels. A hidden `hidden_proposed.jsonl` may be compared with the owner's labels for `agreement.json`. That comparison does not change a sealed label.

The blank practitioner sheet stays in `data/sealed/router/`.
