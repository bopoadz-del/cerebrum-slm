# v7 sealed result (scored once)

See ../README.md for the full record.

## Sealed result (312 rows, scored once, epoch 3)

| set | n | macro recall | accuracy |
|---|---|---|---|
| v5_retick | 64 | 0.7482 | 0.7031 |
| v8_retick | 185 | 0.7730 | 0.7622 |
| cr_addendum | 14 | 1.0000 | 1.0000 |
| thin_c_addendum | 2 | 0.5000 | 0.5000 |
| thin_d_addendum | 13 | 0.6389 | 0.7692 |
| web_f_addendum | 34 | 0.8131 | 0.7059 |
| combined | 312 | 0.7843 | 0.7532 |

v6 combined: macro 0.7857, accuracy 0.7372. gate_v2 passed; router gate (incl. name-blind) not passed.

## Per class v6 -> v7 (combined 312)

| label | n | recall v6 | recall v7 | precision v6 | precision v7 | predicted v6 | predicted v7 |
|---|---|---|---|---|---|---|---|
| RFI | 12 | 1.000 | 1.000 | 1.000 | 1.000 | 12 | 12 |
| submittal | 18 | 0.889 | 0.889 | 0.842 | 0.762 | 19 | 21 |
| transmittal | 13 | 1.000 | 0.923 | 1.000 | 1.000 | 13 | 12 |
| VO/CO | 16 | 0.938 | 0.875 | 0.938 | 0.933 | 16 | 15 |
| change request | 14 | 1.000 | 1.000 | 0.636 | 0.933 | 22 | 15 |
| claim | 9 | 0.889 | 1.000 | 0.800 | 0.818 | 10 | 11 |
| payment application | 6 | 0.833 | 1.000 | 0.357 | 0.286 | 14 | 21 |
| payment certificate | 15 | 0.467 | 0.400 | 0.700 | 0.750 | 10 | 8 |
| drawing | 18 | 0.778 | 1.000 | 0.519 | 0.621 | 27 | 29 |
| specification | 18 | 0.667 | 0.778 | 1.000 | 0.933 | 12 | 15 |
| schedule | 19 | 1.000 | 1.000 | 0.826 | 0.704 | 23 | 27 |
| report | 23 | 0.435 | 0.913 | 1.000 | 0.724 | 10 | 29 |
| correspondence | 19 | 0.105 | 0.158 | 0.667 | 1.000 | 3 | 3 |
| BOQ | 12 | 0.750 | 0.750 | 0.900 | 0.818 | 10 | 11 |
| contract | 12 | 0.917 | 1.000 | 0.846 | 0.600 | 13 | 20 |
| method statement | 14 | 1.000 | 0.929 | 1.000 | 1.000 | 14 | 13 |
| meeting minutes | 14 | 1.000 | 0.857 | 0.875 | 0.923 | 16 | 13 |
| NCR | 12 | 1.000 | 0.500 | 0.800 | 1.000 | 15 | 6 |
| inspection request | 3 | 1.000 | 1.000 | 0.500 | 0.500 | 6 | 6 |
| site instruction | 9 | 1.000 | 0.778 | 0.346 | 0.875 | 26 | 8 |
| register/log | 15 | 0.333 | 0.267 | 1.000 | 0.800 | 5 | 5 |
| other | 21 | 0.286 | 0.238 | 0.462 | 0.417 | 13 | 12 |

Precision rule: for "no class precision < 0.5": every label that is predicted at least once or present in gold on the 312 rows is
checked. precision = TP / rows predicted as that label. A label present in gold but never predicted counts as precision 0 (fails).
'unsure' is not a label and is not checked.

## Acceptance (owner, Oct 8 20:09)

| criterion | v7 | result |
|---|---|---|
| correspondence recall >= 0.5 | 0.158 | FAIL |
| payment certificate recall >= 0.75 | 0.4 | FAIL |
| no class precision < 0.5 (labels predicted or present; never-predicted present label = 0) | {'payment application': 0.2857142857142857, 'other': 0.4166666666666667} | FAIL |
| VO/CO >= 15/16 | 14/16 | FAIL |
| change request precision >= 0.75 | 0.933 | PASS |

**Not promoted.** v6 stays the serving router.

## Name-blind (same checkpoint, same parser, filenames/titles blanked)

| set | flips v6 | flips v7 | gate |
|---|---|---|---|
| v5_retick | 4 | 1 | pass |
| v8_retick | 2 | 1 | FAIL other |
| cr_addendum | 0 | 0 | pass |
| thin_c_addendum | 0 | 0 | pass |
| thin_d_addendum | 0 | 1 | pass |
| web_f_addendum | 0 | 0 | pass |
| combined | 6 | 3 | FAIL NCR, other, submittal |

Combined flips (3): one submittal row went right -> wrong (submittal -> transmittal, 2 fields blanked); one `other` row went wrong -> right
(payment certificate -> other, 4 fields blanked); one NCR row went right -> wrong with 0 fields blanked, i.e. sampler nondeterminism at
temperature 0, not a name dependency.
