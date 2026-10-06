# Sealed router gate

This gate is registered before any scoring of `data/eval/router_unseen/`. `sealed_scoring` is false. This file is not a score.

The val gate in `scripts/router/majority_gate.py` and `scripts/router/val_metrics.py` is unchanged. This gate is separate and applies only to the sealed rows.

The model passes only if both checks below are true. Any other result is a fail. A tie does not pass.

The same rule is `RULE` in `scripts/router/sealed_gate.py`:

The model passes only if macro recall beats every constant single-label predictor on the sealed rows, and each of those constant predictors fails the existing majority gate. Macro recall is the mean of per-label recall over labels present in the sealed rows. The constant predictors include always-drawing, the training majority, and always-report, the sealed-set majority. A tie does not beat a constant predictor. The majority gate is scripts/router/majority_gate.py with majority_class_fail left unchanged. sealed_scoring stays false.

1. Macro recall on the sealed rows is strictly greater than the macro recall of every constant single-label predictor. A constant single-label predictor emits one declared label on every sealed row. That set includes always-`drawing` (the training majority) and always-`report` (the sealed-set majority).
2. Each of those constant predictors fails the existing majority gate. The gate is `scripts/router/majority_gate.py` with `majority_class_fail` left true, the value in `configs/router/sealed_eval.json`. That function fails a predictor when every prediction is the majority label on the rows being scored. Ties use the order in `configs/router/labels.json`.

Macro recall is the mean of per-label recall over labels present in the sealed rows. A label with no sealed row is left out of the mean. Per-label recall is `router.val_metrics.per_label_recall`.

The machine-readable field is `sealed_gate` in `configs/router/sealed_eval.json`.

The sealed labels are the owner's ticks. This gate does not read a proposal file and does not change a label.
