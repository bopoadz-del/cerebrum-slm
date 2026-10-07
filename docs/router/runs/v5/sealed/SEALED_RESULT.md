# Router v5 epoch 1: sealed score on the v9 sealed sets, plus the name-blind check

Owner order 2026-10-07 21:33 +04, step 2. Each set was scored ONCE on main 584443f (PR #45 and PR #46 merged). PRE_RUN_NOTE.txt was written before any sealed prediction.

- **Adapter:** `tinker://4ec9bca9-f838-5d1a-ad89-7157820a3f09:train:0/sampler_weights/router-v5-qwen3.5-4b-lora-r16-epoch1` (Qwen/Qwen3.5-4B LoRA r16, run v5, v9 22-label prompt).
- **Why epoch 1:** it was chosen before any sealed score, because its val macro recall was higher (0.6579 vs 0.5317 for epoch 2). See `docs/router/runs/v5/epoch_choice.json`.
- **Prompt:** `prompt_for(labels)`, using the v9 22 labels from `configs/router/labels.json`.
- **Input:** `content_text(candidate)`, after a content sha256 check against every sealed row.
- **Sampling:** temperature 0, max_tokens 32, seed 0, no thinking.
- **Parser:** `parse_router_output` (v9 exact aliases).
- **Gate:** `evaluate_sealed_gate_v8` (gate v2 + MIN_SEALED_PER_LABEL=12), unchanged.
- **Sets:** `configs/router/sealed_eval.json` `v9_sealed`.
  - v5_retick: 64 rows. v8_retick: 185 rows. cr_addendum: 14 rows.
  - **combined** is the same 263 predictions concatenated in that order. Nothing was re-sampled, swapped or dropped.
  - The addendum on its own is single-label, so its own gate_v2 is degenerate. Its gate is read on the combined view.

| set | n | macro recall | accuracy | gate_v2 | router_passed | name-blind flips (passable / not passable) | name-blind gate |
|---|---:|---:|---:|---|---|---|---|
| v5_retick | 64 | 0.7060 | 0.6719 | PASS | False | 2 (0 / 2) | PASS |
| v8_retick | 185 | 0.7235 | 0.7297 | PASS | False | 3 (3 / 0) | FAIL |
| cr_addendum | 14 | 1.0000 | 1.0000 | FAIL | False | 0 (0 / 0) | PASS |
| combined | 263 | 0.7260 | 0.7300 | PASS | False | 5 (5 / 0) | FAIL |

## v5_retick (64 rows)

**router_passed: False**. gate_v2.passed: True (beats every constant: True; every constant fails majority gate: True).
Macro recall 0.7060; accuracy 0.6719; unsure/off-list outputs 0.

| label | n | recall | passable | predicted |
|---|---:|---:|---|---:|
| RFI | 5 | 1.000 | not passable (n<12) | 6 |
| submittal | 5 | 1.000 | not passable (n<12) | 7 |
| transmittal | 5 | 1.000 | not passable (n<12) | 5 |
| VO/CO | 5 | 0.000 | not passable (n<12) | 0 |
| change request | 0 | n/a | not passable (n<12) | 7 |
| claim | 2 | 1.000 | not passable (n<12) | 4 |
| payment application | 2 | 1.000 | not passable (n<12) | 4 |
| payment certificate | 3 | 0.333 | not passable (n<12) | 1 |
| drawing | 5 | 1.000 | not passable (n<12) | 5 |
| specification | 6 | 0.500 | not passable (n<12) | 3 |
| schedule | 5 | 0.600 | not passable (n<12) | 3 |
| report | 8 | 0.625 | not passable (n<12) | 5 |
| correspondence | 6 | 0.833 | not passable (n<12) | 6 |
| BOQ | 0 | n/a | not passable (n<12) | 0 |
| contract | 0 | n/a | not passable (n<12) | 0 |
| method statement | 0 | n/a | not passable (n<12) | 0 |
| meeting minutes | 0 | n/a | not passable (n<12) | 2 |
| NCR | 0 | n/a | not passable (n<12) | 0 |
| inspection request | 0 | n/a | not passable (n<12) | 1 |
| site instruction | 0 | n/a | not passable (n<12) | 0 |
| register/log | 0 | n/a | not passable (n<12) | 3 |
| other | 7 | 0.286 | not passable (n<12) | 2 |

## v8_retick (185 rows)

**router_passed: False**. gate_v2.passed: True (beats every constant: True; every constant fails majority gate: True).
Macro recall 0.7235; accuracy 0.7297; unsure/off-list outputs 0.

| label | n | recall | passable | predicted |
|---|---:|---:|---|---:|
| RFI | 4 | 1.000 | not passable (n<12) | 4 |
| submittal | 13 | 1.000 | yes | 14 |
| transmittal | 8 | 1.000 | not passable (n<12) | 12 |
| VO/CO | 11 | 0.000 | not passable (n<12) | 0 |
| change request | 0 | n/a | not passable (n<12) | 14 |
| claim | 2 | 0.000 | not passable (n<12) | 0 |
| payment application | 1 | 1.000 | not passable (n<12) | 4 |
| payment certificate | 0 | n/a | not passable (n<12) | 1 |
| drawing | 13 | 0.923 | yes | 18 |
| specification | 12 | 1.000 | yes | 16 |
| schedule | 14 | 0.857 | yes | 15 |
| report | 13 | 0.615 | yes | 8 |
| correspondence | 12 | 0.917 | yes | 14 |
| BOQ | 12 | 0.500 | yes | 6 |
| contract | 12 | 0.917 | yes | 11 |
| method statement | 14 | 0.929 | yes | 13 |
| meeting minutes | 5 | 1.000 | not passable (n<12) | 5 |
| NCR | 2 | 0.500 | not passable (n<12) | 1 |
| inspection request | 0 | n/a | not passable (n<12) | 2 |
| site instruction | 8 | 0.750 | not passable (n<12) | 7 |
| register/log | 15 | 0.267 | yes | 7 |
| other | 14 | 0.571 | yes | 13 |

## cr_addendum (14 rows)

**router_passed: False**. gate_v2.passed: False (beats every constant: False; every constant fails majority gate: True).
Macro recall 1.0000; accuracy 1.0000; unsure/off-list outputs 0.

This set is single-label (change request). A constant `change request` predictor has the same macro recall, so `beats_every_constant` is False by construction. This is the degenerate case that the pr9 config records. It is not a model finding. Change request is read on the combined view.

| label | n | recall | passable | predicted |
|---|---:|---:|---|---:|
| RFI | 0 | n/a | not passable (n<12) | 0 |
| submittal | 0 | n/a | not passable (n<12) | 0 |
| transmittal | 0 | n/a | not passable (n<12) | 0 |
| VO/CO | 0 | n/a | not passable (n<12) | 0 |
| change request | 14 | 1.000 | yes | 14 |
| claim | 0 | n/a | not passable (n<12) | 0 |
| payment application | 0 | n/a | not passable (n<12) | 0 |
| payment certificate | 0 | n/a | not passable (n<12) | 0 |
| drawing | 0 | n/a | not passable (n<12) | 0 |
| specification | 0 | n/a | not passable (n<12) | 0 |
| schedule | 0 | n/a | not passable (n<12) | 0 |
| report | 0 | n/a | not passable (n<12) | 0 |
| correspondence | 0 | n/a | not passable (n<12) | 0 |
| BOQ | 0 | n/a | not passable (n<12) | 0 |
| contract | 0 | n/a | not passable (n<12) | 0 |
| method statement | 0 | n/a | not passable (n<12) | 0 |
| meeting minutes | 0 | n/a | not passable (n<12) | 0 |
| NCR | 0 | n/a | not passable (n<12) | 0 |
| inspection request | 0 | n/a | not passable (n<12) | 0 |
| site instruction | 0 | n/a | not passable (n<12) | 0 |
| register/log | 0 | n/a | not passable (n<12) | 0 |
| other | 0 | n/a | not passable (n<12) | 0 |

## combined (263 rows)

**router_passed: False**. gate_v2.passed: True (beats every constant: True; every constant fails majority gate: True).
Macro recall 0.7260; accuracy 0.7300; unsure/off-list outputs 0.

| label | n | recall | passable | predicted |
|---|---:|---:|---|---:|
| RFI | 9 | 1.000 | not passable (n<12) | 10 |
| submittal | 18 | 1.000 | yes | 21 |
| transmittal | 13 | 1.000 | yes | 17 |
| VO/CO | 16 | 0.000 | yes | 0 |
| change request | 14 | 1.000 | yes | 35 |
| claim | 4 | 0.500 | not passable (n<12) | 4 |
| payment application | 3 | 1.000 | not passable (n<12) | 8 |
| payment certificate | 3 | 0.333 | not passable (n<12) | 2 |
| drawing | 18 | 0.944 | yes | 23 |
| specification | 18 | 0.833 | yes | 19 |
| schedule | 19 | 0.789 | yes | 18 |
| report | 21 | 0.619 | yes | 13 |
| correspondence | 18 | 0.889 | yes | 20 |
| BOQ | 12 | 0.500 | yes | 6 |
| contract | 12 | 0.917 | yes | 11 |
| method statement | 14 | 0.929 | yes | 13 |
| meeting minutes | 5 | 1.000 | not passable (n<12) | 7 |
| NCR | 2 | 0.500 | not passable (n<12) | 1 |
| inspection request | 0 | n/a | not passable (n<12) | 3 |
| site instruction | 8 | 0.750 | not passable (n<12) | 7 |
| register/log | 15 | 0.267 | yes | 10 |
| other | 21 | 0.476 | yes | 15 |

## Reading

- **router_passed is False** on every set and on the combined view. In the combined view, gate_v2 passes (macro 0.7260 beats every constant).
  - Eight labels have n<12 and are not passable: inspection request 0, NCR 2, payment application 3, payment certificate 3, claim 4, meeting minutes 5, site instruction 8, RFI 9.
- **Change request:** recall 1.000 on its 14 sealed rows, but it is over-predicted (35 predictions, 14 correct).
  - Gold of the change-request predictions: VO/CO 15, change request 14, report 2, other 1, BOQ 1, register/log 1, site instruction 1.
- **VO/CO** (n=16 combined, passable) has recall 0.000. Its predictions were: change request 15, site instruction 1.
  - The adapter does not separate an instructed or agreed variation from a request for one. This is the v6 training-mechanism target; no label or sealed row is changed for it.
- **Weakest passable classes in the combined view:** register/log 0.267, other 0.476, BOQ 0.500, report 0.619.
- **Compared with v3 epoch 1 on the same re-ticked sets** (docs/router/runs/v3_sealed_v9): v5_retick macro 0.6399 -> 0.7060, v8_retick 0.6585 -> 0.7235.

## Name-blind check

The same rows were re-classified with the title-block and party field values blanked by position (`scripts/router/name_blind.py`, sha256 ddab8598...e9b47bdeabf, unchanged). The adapter, prompt, sampling and parser were the same.
A flip is a changed prediction. Any flip on a passable class (n>=12 in that set or view) is a FAIL. The fix is more rows from other projects, never a patch.

### v5_retick: PASS

Rows with at least one blanked field: 41/64; fields blanked: 122; flips: 2 (passable 0, not passable 2); accuracy 0.6719 -> 0.6406.
Failing passable classes: none.

| gold class | n | passable | flips | correct before | correct after |
|---|---:|---|---:|---:|---:|
| RFI | 5 | no | 0 | 5 | 5 |
| submittal | 5 | no | 0 | 5 | 5 |
| transmittal | 5 | no | 0 | 5 | 5 |
| VO/CO | 5 | no | 0 | 0 | 0 |
| claim | 2 | no | 0 | 2 | 2 |
| payment application | 2 | no | 0 | 2 | 2 |
| payment certificate | 3 | no | 0 | 1 | 1 |
| drawing | 5 | no | 0 | 5 | 5 |
| specification | 6 | no | 0 | 3 | 3 |
| schedule | 5 | no | 0 | 3 | 3 |
| report | 8 | no | 0 | 5 | 5 |
| correspondence | 6 | no | 2 | 5 | 3 |
| other | 7 | no | 0 | 2 | 2 |

### v8_retick: FAIL

Rows with at least one blanked field: 95/185; fields blanked: 239; flips: 3 (passable 3, not passable 0); accuracy 0.7297 -> 0.7297.
Failing passable classes: BOQ, other, register/log.

| gold class | n | passable | flips | correct before | correct after |
|---|---:|---|---:|---:|---:|
| RFI | 4 | no | 0 | 4 | 4 |
| submittal | 13 | yes | 0 | 13 | 13 |
| transmittal | 8 | no | 0 | 8 | 8 |
| VO/CO | 11 | no | 0 | 0 | 0 |
| claim | 2 | no | 0 | 0 | 0 |
| payment application | 1 | no | 0 | 1 | 1 |
| drawing | 13 | yes | 0 | 12 | 12 |
| specification | 12 | yes | 0 | 12 | 12 |
| schedule | 14 | yes | 0 | 12 | 12 |
| report | 13 | yes | 0 | 8 | 8 |
| correspondence | 12 | yes | 0 | 11 | 11 |
| BOQ | 12 | yes | 1 | 6 | 7 |
| contract | 12 | yes | 0 | 11 | 11 |
| method statement | 14 | yes | 0 | 13 | 13 |
| meeting minutes | 5 | no | 0 | 5 | 5 |
| NCR | 2 | no | 0 | 1 | 1 |
| site instruction | 8 | no | 0 | 6 | 6 |
| register/log | 15 | yes | 1 | 4 | 4 |
| other | 14 | yes | 1 | 8 | 7 |

### cr_addendum: PASS

Rows with at least one blanked field: 11/14; fields blanked: 27; flips: 0 (passable 0, not passable 0); accuracy 1.0000 -> 1.0000.
Failing passable classes: none.

| gold class | n | passable | flips | correct before | correct after |
|---|---:|---|---:|---:|---:|
| change request | 14 | yes | 0 | 14 | 14 |

### combined: FAIL

Rows with at least one blanked field: 147/263; fields blanked: 388; flips: 5 (passable 5, not passable 0); accuracy 0.7300 -> 0.7224.
Failing passable classes: BOQ, correspondence, other, register/log.

| gold class | n | passable | flips | correct before | correct after |
|---|---:|---|---:|---:|---:|
| RFI | 9 | no | 0 | 9 | 9 |
| submittal | 18 | yes | 0 | 18 | 18 |
| transmittal | 13 | yes | 0 | 13 | 13 |
| VO/CO | 16 | yes | 0 | 0 | 0 |
| change request | 14 | yes | 0 | 14 | 14 |
| claim | 4 | no | 0 | 2 | 2 |
| payment application | 3 | no | 0 | 3 | 3 |
| payment certificate | 3 | no | 0 | 1 | 1 |
| drawing | 18 | yes | 0 | 17 | 17 |
| specification | 18 | yes | 0 | 15 | 15 |
| schedule | 19 | yes | 0 | 15 | 15 |
| report | 21 | yes | 0 | 13 | 13 |
| correspondence | 18 | yes | 2 | 16 | 14 |
| BOQ | 12 | yes | 1 | 6 | 7 |
| contract | 12 | yes | 0 | 11 | 11 |
| method statement | 14 | yes | 0 | 13 | 13 |
| meeting minutes | 5 | no | 0 | 5 | 5 |
| NCR | 2 | no | 0 | 1 | 1 |
| site instruction | 8 | no | 0 | 6 | 6 |
| register/log | 15 | yes | 1 | 4 | 4 |
| other | 21 | yes | 1 | 10 | 9 |

Flipped rows (sheet id, gold, before -> after):

- v5_retick S5-021: gold correspondence, correspondence -> payment application (5 fields blanked)
- v5_retick S5-023: gold correspondence, correspondence -> site instruction (4 fields blanked)
- v8_retick V8-029: gold register/log, transmittal -> other (1 fields blanked)
- v8_retick V8-040: gold BOQ, schedule -> BOQ (3 fields blanked)
- v8_retick V8-113: gold other, other -> payment certificate (2 fields blanked)

After this run, v5_retick, v8_retick and cr_addendum are spent for this adapter. None may be re-scored or tuned on, and no sealed document or label goes into training.
