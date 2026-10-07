# Router dataset card

Status: pr5 adds the unmasked pr2 owner-source rows and v9 change-request rows and re-runs the split on the v9 label set (see the pr5 section). Earlier status: v8 21-label teacher relabel of the cleaned training pool, plus owner-laptop additions and a thin-label public/laptop top-up. Human agreement remains as recorded (0.875, kappa 0.864). Sealed v5 and sealed v8 are untouched. No training run in this PR.

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

## pr5: unmasked pr2 owner sources and v9 change-request rows (label set v9, 22 labels)

Masking ruling (owner, 2026-10-07): the router adapter trains on unmasked rows. See `docs/audit/router_masking_ruling.md`. The name-blind check (`scripts/router/name_blind.py`) is the gate that replaces masking for the router.

- `data/router/additions_owner_sources_pr2.jsonl`: the 219 pr2 owner-source rows in their ORIGINAL unmasked text (196 positives, 23 blank-template negatives). 19 rows keep the label note `label_source: v8_definition_rule` with `teacher_label` for owner review. Templates are label `other`, train only, inside the other cap, never in val. Provenance: owner sources, internal only. Project ids are opaque (`pr2_pNN`).
- AAZ isolation result (recorded before this PR): 71 AAZ rows against sealed v5 (64) and v8 (185): sha hits 0, first-300 hits 0, 12-word shingle pairs 4 (at most 2 shared shingles each), max 5-shingle Jaccard 0.012. Isolated.
- v9 relabel applied to the pr2 rows by content (change-request type content -> change request; variation settlement recommendation -> report): 0 rows qualified, 0 label changes.
- `data/router/additions_change_request_v9.jsonl`: 26 rows from public FILLED change-request documents (COR, PCO, proposal requests, change proposals) about the works, from 15 projects. Labelled by the v9 teacher (Qwen/Qwen3-8B, temperature 0, v9 prompt) at the 0.7 floor: 25 change request, 1 VO/CO. One near-duplicate row dropped. Project ids are opaque (`cr9_pNN`); each project is one split group. Source sites are not stored; a domain hash is kept for the isolation test. Internal only.
- Sealed v9 change-request candidates (14, from other projects and other domains) are with the owner for ticking. They are not in the sealed set and not in training. `data/router/cr_v9_sealed_candidates_isolation.json` holds only their hashes.
- Isolation: sha + project against sealed v5, v8 and both v9 re-tick copies (rejected 0); 12-word shingles against sealed v8 excerpts: 0; change-request source domains are disjoint from every sealed set and from the pending candidates.

Split re-run on v9 labels, same procedure (CANARY drop, 0.7 floor, split_v2 series-grouped stratified, seed 20261006, drawing cap 400, other cap 300). Train 1602, val 880 (were 1482 / 848). pr2 rows in val: 0. Change-request rows: train 23, val 3 (new rows only).

| label | train before | train after | val before | val after |
| --- | ---: | ---: | ---: | ---: |
| RFI | 27 | 27 | 7 | 7 |
| submittal | 29 | 31 | 4 | 4 |
| transmittal | 12 | 12 | 1 | 1 |
| VO/CO | 5 | 5 | 0 | 1 |
| change request | 3 | 24 | 0 | 4 |
| claim | 1 | 10 | 0 | 1 |
| payment application | 4 | 9 | 1 | 1 |
| payment certificate | 7 | 11 | 1 | 2 |
| drawing | 400 | 400 | 652 | 658 |
| specification | 66 | 66 | 3 | 7 |
| schedule | 49 | 50 | 8 | 8 |
| report | 108 | 123 | 44 | 43 |
| correspondence | 71 | 79 | 7 | 10 |
| BOQ | 73 | 76 | 2 | 8 |
| contract | 134 | 136 | 11 | 11 |
| method statement | 29 | 27 | 3 | 5 |
| meeting minutes | 58 | 58 | 10 | 10 |
| NCR | 4 | 19 | 0 | 2 |
| inspection request | 27 | 48 | 7 | 7 |
| site instruction | 48 | 48 | 8 | 8 |
| register/log | 27 | 43 | 3 | 6 |
| other | 300 | 300 | 76 | 76 |

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
