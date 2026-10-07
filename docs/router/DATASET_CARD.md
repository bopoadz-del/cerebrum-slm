# Router dataset card

Status: v8 21-label teacher relabel of the cleaned training pool, plus owner-laptop additions and a thin-label public/laptop top-up. Human agreement remains as recorded (0.875, kappa 0.864). Sealed v5 and sealed v8 are untouched. No training run in this PR.

Model version: Qwen/Qwen3-8B

The teacher is `Qwen/Qwen3-8B`, provider `tinker`, temperature `0`, max_tokens `128`. Relabel used the fixed confidence placeholder from main at 1a94dcf (PR #36): the prompt asks for a number between 0 and 1 instead of a literal `0`. On the 5627-row cleaned pool the teacher returned 0.95 on 5297 rows, so the 0.7 floor barely discriminates; treat confidence as a coarse filter.

The current builder in `scripts/router/teacher_label.py` loads definitions from `configs/router/label_set_v8.json`. The recorded template is:

```
You assign one document-type label from the document text only.
Choose exactly one label from the list, or unsure when the text does not support one label.
The list is the only label set. Do not add a label.
Use only the document text in the next message.
Do not use a filename, a folder, a document id, or a project name. They are not provided.
Reply with one JSON object and no other text:
{"label": "<one list entry or unsure>", "reason": "<one line>", "confidence": <your confidence, a number between 0 and 1>}
Allowed labels:
{label_list}
```

Labels come from document content only. Filename, folder, source path, source site and form number do not decide a label and do not appear in training text.

## Pool preparation

`data/raw/router/labels.jsonl` is unchanged in this PR. After empty-text and duplicate-doc drops: 5627 rows labelled. Isolation against sealed v5 and sealed v8 (sha + project) rejected 0.

Before this PR's relabel, 102 pool rows were removed for 12-word phrase overlap with sealed v8/v5 (including 72 DG2 Jacobs-copyright rows). The 6 synthetic CANARY_A/B fixture rows were dropped from the training pool. See `data/router/removed_overlap.json`.

## Teacher counts (21 labels, after overlap + canary drop, floor 0.7)

`data/router/teacher_labels.jsonl` holds the relabelled pool only (5482 rows). Owner-laptop and public thin-label additions are in `data/router/additions_owner_laptop.jsonl` with `provenance` set (`owner laptop, content-labelled` or `public web, content-labelled`). No paths. `project_id` is taken from content.

Pool kept at floor (by label):

| label | count |
| --- | ---: |
| drawing | 3951 |
| other | 771 |
| report | 147 |
| correspondence | 78 |
| meeting minutes | 68 |
| contract | 68 |
| specification | 63 |
| schedule | 57 |
| site instruction | 56 |
| BOQ | 43 |
| RFI | 36 |
| inspection request | 34 |
| register/log | 29 |
| submittal | 27 |
| method statement | 23 |
| transmittal | 13 |
| VO/CO | 8 |
| NCR | 4 |
| payment application | 3 |
| payment certificate | 2 |
| claim | 1 |

Combined pool + additions kept at floor: 5647 rows (see `data/router/split_counts.json`).

## Split v2 (proposed, 21 labels)

`scripts/router/split_v2.py` series-grouped stratified split, seed `20261006`. Drawing capped at **400** in train. **Other capped at 300** in train (sampled across projects, same helper). Val is left as the repo split produces it (drawing-heavy); macro recall is per-label, so that is fine.

Isolation: `router.isolation.require_isolated` on every example against sealed v5 and sealed v8. Path guard: `require_no_paths` on train and val.

| | rows |
| --- | ---: |
| train | 1482 |
| val | 848 |
| drawing before train cap | 3299 |
| other before train cap | 718 |

### Train label counts

| label | train | val |
| --- | ---: | ---: |
| RFI | 29 | 7 |
| submittal | 29 | 4 |
| transmittal | 12 | 1 |
| VO/CO | 7 | 1 |
| claim | 1 | 0 |
| payment application | 4 | 1 |
| payment certificate | 7 | 1 |
| drawing | 400 | 652 |
| specification | 66 | 3 |
| schedule | 49 | 8 |
| report | 107 | 43 |
| correspondence | 71 | 7 |
| BOQ | 73 | 2 |
| contract | 134 | 11 |
| method statement | 29 | 3 |
| meeting minutes | 58 | 10 |
| NCR | 4 | 0 |
| inspection request | 27 | 7 |
| site instruction | 48 | 8 |
| register/log | 27 | 3 |
| other | 300 | 76 |

### Thin labels (train &lt; 30)

RFI=29, submittal=29, transmittal=12, VO/CO=7, claim=1, payment application=4, payment certificate=7, method statement=29, NCR=4, inspection request=27, register/log=27

Full machine-readable summary: `data/router/split_counts.json`.

## Human agreement

Unchanged from the previous card (done; 0.875 / kappa 0.864). Sealed gate records unchanged. `sealed_scoring` stays false.

## Provenance notes

- Additions batch (145) and thin-label top-up from the owner's laptop: provenance `owner laptop, content-labelled`. Outside DG2/Master Folder. Per-project caps about 10.
- Public thin-label top-up: real project documents from NSIP published packs and other public archives. Domains already used for sealed v8 were excluded entirely. 12-word phrase check against sealed rows. Bot-check walls logged, never bypassed (see agent walls log).
- Nothing from sealed v5 or sealed v8 enters training.
