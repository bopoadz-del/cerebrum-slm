# Router v8 sealed result (main + addendum, 185 rows)

Checkpoint `tinker://b0857111-57c4-56f6-bf9b-ed3f8021826b:train:0/sampler_weights/router-qwen3.5-4b-lora-r16-epoch2` (Qwen/Qwen3.5-4B LoRA r16, epoch 2). Repo `756ed728b6c42ed01af640d638eb6f12b58a6db9`.
Prompt `prompt_for(labels)`, temperature 0, max_tokens 32, parser `parse_router_output` (v8 exact aliases). Gate `evaluate_sealed_gate_v8` (gate v2 + MIN_SEALED_PER_LABEL=12), unchanged.

Every document was scored exactly once:
- Main V8-001..167 (164 rows) was scored on 2026-10-07 04:34:00 to 04:35:13 (Dubai), before the addendum was returned. Those predictions are reused unchanged and the main rows were not re-scored. No pre-run note was written for the main run.
- Addendum V8-168..188 (21 rows, 0 unsure) was scored at 05:28:32 (Dubai). PRE_RUN_NOTE.txt was written before that run.

Dropped before sealing (unsure ticked, no single label): V8-096, V8-110, V8-157.

**router_passed: False**. gate_v2.passed: True.

Combined: macro recall 0.4296; accuracy 0.4216 (78/185).
Main only (record): macro recall 0.4845; accuracy 69/164.
Addendum only: macro recall 0.3810; accuracy 9/21.

| label | n | recall | passable |
|---|---:|---:|---|
| RFI | 4 | 1.000 | not passable (n<12) |
| submittal | 13 | 0.846 | yes |
| transmittal | 8 | 1.000 | not passable (n<12) |
| VO/CO | 11 | 0.727 | not passable (n<12) |
| claim | 2 | 0.000 | not passable (n<12) |
| payment application | 1 | 1.000 | not passable (n<12) |
| payment certificate | 0 | n/a | not passable (n<12) |
| drawing | 13 | 0.923 | yes |
| specification | 12 | 1.000 | yes |
| schedule | 14 | 0.357 | yes |
| report | 13 | 1.000 | yes |
| correspondence | 12 | 0.167 | yes |
| BOQ | 12 | 0.000 | yes |
| contract | 12 | 0.000 | yes |
| method statement | 14 | 0.143 | yes |
| meeting minutes | 5 | 0.000 | not passable (n<12) |
| NCR | 2 | 0.000 | not passable (n<12) |
| inspection request | 0 | n/a | not passable (n<12) |
| site instruction | 8 | 0.000 | not passable (n<12) |
| register/log | 15 | 0.000 | yes |
| other | 14 | 0.000 | yes |

Labels with n<12 (not passable): RFI, transmittal, VO/CO, claim, payment application, payment certificate, meeting minutes, NCR, inspection request, site instruction. router_passed cannot be true while any label has n<12.

The adapter was trained on the old 12-label set (RFI, submittal, transmittal, VO/CO, claim, payment certificate, drawing, spec, schedule, report, correspondence, other). The v8 labels outside that set (payment application, BOQ, contract, method statement, meeting minutes, NCR, inspection request, site instruction, register/log) never appeared as training targets, so this adapter cannot be expected to predict them. Predictions it did emit for those labels: {"payment application": 15, "BOQ": 0, "contract": 0, "method statement": 2, "meeting minutes": 0, "NCR": 0, "inspection request": 0, "site instruction": 0, "register/log": 0}.

v8 is now spent for this adapter. It must not be re-scored or tuned on, and no sealed document or label goes into training.

## Constant predictors

| constant | macro | accuracy | model beats |
|---|---:|---:|---|
| RFI | 0.0526 | 0.0216 | True |
| submittal | 0.0526 | 0.0703 | True |
| transmittal | 0.0526 | 0.0432 | True |
| VO/CO | 0.0526 | 0.0595 | True |
| claim | 0.0526 | 0.0108 | True |
| payment application | 0.0526 | 0.0054 | True |
| payment certificate | 0.0000 | 0.0000 | True |
| drawing | 0.0526 | 0.0703 | True |
| specification | 0.0526 | 0.0649 | True |
| schedule | 0.0526 | 0.0757 | True |
| report | 0.0526 | 0.0703 | True |
| correspondence | 0.0526 | 0.0649 | True |
| BOQ | 0.0526 | 0.0649 | True |
| contract | 0.0526 | 0.0649 | True |
| method statement | 0.0526 | 0.0757 | True |
| meeting minutes | 0.0526 | 0.0270 | True |
| NCR | 0.0526 | 0.0108 | True |
| inspection request | 0.0000 | 0.0000 | True |
| site instruction | 0.0526 | 0.0432 | True |
| register/log | 0.0526 | 0.0811 | True |
| other | 0.0526 | 0.0757 | True |

Router passed: False.
