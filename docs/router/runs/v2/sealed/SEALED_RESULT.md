# Router v2 epoch-2: sealed result

Scored once on 64 sealed rows (data/eval/router_unseen at 5a4c4a1fc6133bf927d94ce33bf95811337b3ca6); unsure excluded: 0.
Checkpoint `tinker://b0857111-57c4-56f6-bf9b-ed3f8021826b:train:0/sampler_weights/router-qwen3.5-4b-lora-r16-epoch2` (Qwen/Qwen3.5-4B), Tinker sampling temperature 0, same prompt as the val predictions.
Repeat after crash: False.

**Sealed gate: FAIL** (scripts/router/sealed_gate.py, pre-registered in docs/router/SEALED_GATE.md).

- constant predictors that do NOT fail majority_gate.evaluate: RFI, submittal, transmittal, VO/CO, claim, payment certificate, drawing, spec, schedule, correspondence, other

- beats every constant predictor: True
- every constant predictor fails the majority gate: False

Macro recall 0.7153; accuracy 0.6719.

| label | recall |
|---|---|
| RFI | 1.000 |
| submittal | 1.000 |
| transmittal | 1.000 |
| VO/CO | 0.000 |
| claim | 1.000 |
| payment certificate | 1.000 |
| drawing | 1.000 |
| spec | 0.500 |
| schedule | 1.000 |
| report | 0.750 |
| correspondence | 0.333 |
| other | 0.000 |

## Constant predictors

| constant | macro | accuracy | model beats | fails majority gate |
|---|---|---|---|---|
| RFI | 0.0833 | 0.0781 | True | False |
| submittal | 0.0833 | 0.0781 | True | False |
| transmittal | 0.0833 | 0.0781 | True | False |
| VO/CO | 0.0833 | 0.0781 | True | False |
| claim | 0.0833 | 0.0312 | True | False |
| payment certificate | 0.0833 | 0.0781 | True | False |
| drawing | 0.0833 | 0.0781 | True | False |
| spec | 0.0833 | 0.0938 | True | False |
| schedule | 0.0833 | 0.0781 | True | False |
| report | 0.0833 | 0.1250 | True | True |
| correspondence | 0.0833 | 0.0938 | True | False |
| other | 0.0833 | 0.1094 | True | False |

## Confusion matrix (rows gold, columns pred)

| gold \ pred | RFI | submittal | transmittal | VO/CO | claim | payment certificate | drawing | spec | schedule | report | correspondence | other | unsure (unparsed) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RFI | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| submittal | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transmittal | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| VO/CO | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 3 |
| claim | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| payment certificate | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| drawing | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| spec | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| schedule | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| report | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| correspondence | 1 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| other | 1 | 0 | 0 | 0 | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

Note: 3 predictions (S5-011, S5-062, S5-064, all gold VO/CO) had raw output "change order". The val parser (train_router._as_label, unchanged) maps that to unsure, so they count as misses. They were not remapped after scoring.

The sealed gate, as written in scripts/router/sealed_gate.py at 5a4c4a1, cannot pass for any model: majority_gate.evaluate fails only the constant that equals the sealed-set gold majority (report), so the other 11 constants pass it and condition (b) is false. This was noticed and logged in PRE_RUN_NOTE.txt before scoring. Condition (a) is recorded separately above.

Extra (repo literal majority check on the model): passed=True (not a majority-class predictor).

Router passed: False.
