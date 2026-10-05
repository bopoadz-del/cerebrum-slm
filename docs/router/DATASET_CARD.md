# Router dataset card

Status: no training labels.

Model version: unset

The label set is `configs/router/labels.json`.

Inputs are document content (`excerpt`, `first_512_tokens`, or `first_512`). Filename, document id, project id, and `fork_declared_type` are not model inputs.

`unsure` is an abstain. It is not a member of the label set. A row is excluded from training when its label is outside the declared set, when confidence is missing, or when `teacher.confidence_floor` in `configs/router/sealed_eval.json` is unset or the confidence is below that floor.

This card records the teacher model version when a labelling run is allowed. A dry run does not set it. No labelling run has been recorded.
