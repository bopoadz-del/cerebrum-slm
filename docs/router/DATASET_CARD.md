# Router dataset card

Status: teacher labels and a Qwen3.5-4B LoRA are recorded. Human agreement is still PENDING_OWNER.

Model version: Qwen/Qwen3-8B

The fixed teacher is `Qwen/Qwen3-8B`, provider `tinker`, temperature `0`. The laptop run used that model on the pool.

The prompt is the template `_PROMPT` in `scripts/router/teacher_label.py`. `{label_list}` is filled from `configs/router/labels.json` at call time. The template is:

```
You assign one document-type label from the document text only.
Choose exactly one label from the list, or unsure when the text does not support one label.
The list is the only label set. Do not add a label.
Use only the document text in the next message.
Do not use a filename, a folder, a document id, or a project name. They are not provided.
Reply with one JSON object and no other text:
{"label": "<one list entry or unsure>", "reason": "<one line>", "confidence": 0}
Allowed labels:
{label_list}
```

Each teacher row is one label from that file, or `unsure`, plus a reason and a confidence. `unsure`, a label outside the file, a missing confidence, and a confidence below `teacher.confidence_floor` (0.7) are excluded. Labels are read from `first_512_tokens` only. `fork_declared_type`, filename, path, and project are not sent to the teacher and are not labels.

## Pool preparation

`data/raw/router/labels.jsonl`, after dropping empty text and keeping the first row per `doc_id`:

| count | value |
| --- | ---: |
| input rows | 6580 |
| empty text dropped | 140 |
| duplicate doc ids dropped | 813 |
| sealed sha256 or project overlaps | 0 |
| rows labelled | 5627 |

Isolation on the v5 seal (`project` `web_public` and the 64 content sha256 values) rejected 0 of 1334 train rows, 0 of 683 val rows, and 0 of 4555 teacher rows. The sealed set was not scored.

## Teacher counts

Kept for training (on-list label, confidence >= 0.7): 4555. Excluded: 1072. That is 60 off-list labels mapped to `unsure` (the teacher never said `unsure`; 0 replies were unparseable) and 1012 below 0.7 (753 of those were `other`, mostly confidence 0). Missing confidence: 0. No rare class was duplicated or synthesized.

| label | all | kept | low confidence |
| --- | ---: | ---: | ---: |
| RFI | 125 | 120 | 5 |
| submittal | 27 | 25 | 2 |
| transmittal | 17 | 17 | 0 |
| VO/CO | 6 | 6 | 0 |
| claim | 6 | 6 | 0 |
| payment certificate | 14 | 14 | 0 |
| drawing | 3899 | 3692 | 207 |
| spec | 202 | 194 | 8 |
| schedule | 144 | 110 | 34 |
| report | 251 | 248 | 3 |
| correspondence | 121 | 121 | 0 |
| other | 755 | 2 | 753 |
| unsure | 60 | 0 | 0 |

Kept rows are `data/router/teacher_labels.jsonl`. Counts are `docs/router/runs/v2/teacher_counts.json`. The unfiltered teacher file `teacher_labels_all.jsonl` was not in the upload. Its sha256 is `a7498a7f9e1ffb4723c7478ecd7cece10f616dbe76e074c0240da1d80f7c90b3` (`docs/router/runs/v2/SHA256SUMS`).

## Human agreement

Human stratified agreement: **PENDING_OWNER**. The sample file `data/router/human_sample_PENDING_OWNER.csv` is still the tick-sheet header and no rows. The owner has not labelled it.

By owner order, training proceeds before that check.

The agreement gate code is unchanged. `labels_not_for_train` still flags a label under `agreement_threshold` 0.8, and a label with no paired judgements. The recorded override is only a flag:

- enabled: true
- recorded_at: 2026-10-06T03:45:00Z
- owner_clock: 2026-10-06 07:45
- owner_order: CHADi: Go. Training proceeds before the human stratified agreement check.

## Split v2

`scripts/router/split_v2.py` groups by document series. The pool has no folder path, so the series is taken from the filename (numbering `PKG-AREA-NNN|TYPE|DISC|LVL`, otherwise a normalised stem). Groups merge when rows share a filename, an excerpt, or a sha. `project_id` is not part of the key. The filename is not a label and is not model input. Seed `20261006`. 537 groups, 27 in val, 0 in both.

Isolation: `router.isolation.require_isolated` on every example before the split.

Drawing is capped at 600 in train only (3138 drawing rows before the cap), seed `20261006`. Val is not capped. No row was copied.

| split | rows |
| --- | ---: |
| examples | 4555 |
| train before the drawing cap | 3872 |
| train | 1334 |
| val | 683 |

Val label counts: RFI 18, submittal 4, transmittal 3, VO/CO 1, claim 1, payment certificate 2, drawing 554, spec 29, schedule 16, report 37, correspondence 18, other 0. `other` has 2 kept rows and both stayed in train. Rows were not added to fill it.

## Training

Tinker does not serve `Qwen/Qwen3-4B`. The run used `Qwen/Qwen3.5-4B`, LoRA rank 16, alpha 16, 2 epochs, learning rate 0.000473, batch 16, seed 0, 168 steps. Max sequence length was raised from 2048 to 3072 because 130 train rows were over 2048 (the longest was 2996).

Checkpoint: `tinker://b0857111-57c4-56f6-bf9b-ed3f8021826b:train:0/sampler_weights/router-qwen3.5-4b-lora-r16-epoch2`

`configs/serve/router-epoch2.json` status is `trained`.

Val per-label recall at epoch 2 (n in val):

| label | n | recall |
| --- | ---: | ---: |
| RFI | 18 | 0.50 |
| submittal | 4 | 0.75 |
| transmittal | 3 | 1.00 |
| VO/CO | 1 | 1.00 |
| claim | 1 | 0.00 |
| payment certificate | 2 | 1.00 |
| drawing | 554 | 0.971 |
| spec | 29 | 0.759 |
| schedule | 16 | 0.375 |
| report | 37 | 0.946 |
| correspondence | 18 | 0.000 |
| other | 0 | unset |

Macro recall over the 11 labels present in val: 0.664. Accuracy: 0.906.

Majority-class gate on the model predictions: passed (`not a majority-class predictor`). The constant `drawing` baseline fails that gate (accuracy 0.811, macro recall 0.091). The gate code is unchanged.

The sealed set was not scored. Metrics are in `docs/router/runs/v2/`.

WALL: Tinker does not serve Qwen/Qwen3-4B; trained on Qwen/Qwen3.5-4B with the same LoRA config. The pool has no folder path, so the split uses a document series from the filename.
