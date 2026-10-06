# Router dataset card

Status: teacher labelling did not run. No training labels were written.

Model version: Qwen/Qwen3-8B

The fixed teacher is `Qwen/Qwen3-8B`, provider `tinker`, temperature `0`. That run did not happen. The model line records the model the pool labelling path is fixed to.

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

Each teacher row is one label from that file, or `unsure`, plus a reason and a confidence. `unsure`, a label outside the file, a missing confidence, and a confidence below `teacher.confidence_floor` (0.7) are excluded. Labels are read from `first_512_tokens` (or `excerpt` / `first_512`) only. `fork_declared_type`, filename, path, and project are not sent to the teacher and are not labels.

## Pool preparation

`data/raw/router/labels.jsonl` (the raw pool from pull request #25), after dropping empty text and keeping the first row per `doc_id`:

| count | value |
| --- | ---: |
| input rows | 6580 |
| empty text dropped | 140 |
| duplicate doc ids dropped | 813 |
| sealed sha256 or project overlaps | 0 |
| rows kept for labelling | 5627 |

The sealed file `data/eval/router_unseen/sealed_labels.jsonl` is empty, so the isolation guard excludes nothing today. Sealed candidates are Master Folder documents and a few public web documents, not this Fork pool. The guard runs again when the owner sheet is sealed. No pool row sha256 matched a sealed candidate, because no sealed candidate is in the file.

## Teacher counts

Per-label teacher counts are not available. Unsure and low-confidence exclusions are not available. Rare labels were not duplicated or synthesized.

## Human agreement

Human stratified agreement: **PENDING_OWNER**. The owner cannot label now. The sample file is `data/router/human_sample_PENDING_OWNER.csv`. It is the tick-sheet header from `configs/router/labels.json` and no rows, because there are no teacher labels to stratify and no excerpts were invented.

By owner order, training proceeds before that check.

The agreement gate code is unchanged. `labels_not_for_train` still flags a label under `agreement_threshold` 0.8, and a label with no paired judgements. The recorded override is only a flag:

- enabled: true
- recorded_at: 2026-10-06T03:45:00Z
- owner_clock: 2026-10-06 07:45
- owner_order: CHADi: Go. Training proceeds before the human stratified agreement check.

## Splits, validation, checkpoint

Train and val split sizes are not available. Project-grouped splitting is implemented and is not applied to unlabelled pool rows.

Val per-label recall was not run. A label with no validation rows stays unset. Rows are not added to fill a class.

The majority-class gate was not run on a validation split. The gate still fails a predictor that returns the majority label on every row, including when that predictor's accuracy is 1.0.

Checkpoint id: none. `configs/serve/router-epoch2.json` records `checkpoint: null` and `status: not_trained`.

The sealed set was not scored. It stays empty until the owner returns the sheet. Scoring happens once after sealing.

WALL: TINKER_API_KEY is not set; the owner key file was not reachable and the environment has no key. Teacher labelling and LoRA training did not run.
