# Router v5 (epoch 1) vs v6 (epoch 3): per-class sealed recall

Recall per gold class. `n` = gold rows in that set. Passable = n >= 12 (MIN_SEALED_PER_LABEL). `—` = no gold rows. `n/a (not scored)` = v5 was never scored on that set (not scored now either).

## v5_retick

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| RFI | 5 | no | 1.000 | 1.000 |
| submittal | 5 | no | 1.000 | 1.000 |
| transmittal | 5 | no | 1.000 | 1.000 |
| VO/CO | 5 | no | 0.000 | 1.000 |
| claim | 2 | no | 1.000 | 1.000 |
| payment application | 2 | no | 1.000 | 1.000 |
| payment certificate | 3 | no | 0.333 | 0.333 |
| drawing | 5 | no | 1.000 | 0.800 |
| specification | 6 | no | 0.500 | 0.167 |
| schedule | 5 | no | 0.600 | 1.000 |
| report | 8 | no | 0.625 | 0.375 |
| correspondence | 6 | no | 0.833 | 0.000 |
| other | 7 | no | 0.286 | 0.143 |

## v8_retick

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| RFI | 4 | no | 1.000 | 1.000 |
| submittal | 13 | yes | 1.000 | 0.846 |
| transmittal | 8 | no | 1.000 | 1.000 |
| VO/CO | 11 | no | 0.000 | 0.909 |
| claim | 2 | no | 0.000 | 1.000 |
| payment application | 1 | no | 1.000 | 0.000 |
| drawing | 13 | yes | 0.923 | 0.769 |
| specification | 12 | yes | 1.000 | 0.917 |
| schedule | 14 | yes | 0.857 | 1.000 |
| report | 13 | yes | 0.615 | 0.538 |
| correspondence | 12 | yes | 0.917 | 0.167 |
| BOQ | 12 | yes | 0.500 | 0.750 |
| contract | 12 | yes | 0.917 | 0.917 |
| method statement | 14 | yes | 0.929 | 1.000 |
| meeting minutes | 5 | no | 1.000 | 1.000 |
| NCR | 2 | no | 0.500 | 1.000 |
| site instruction | 8 | no | 0.750 | 1.000 |
| register/log | 15 | yes | 0.267 | 0.333 |
| other | 14 | yes | 0.571 | 0.357 |

## cr_addendum

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| change request | 14 | yes | 1.000 | 1.000 |

## thin_c_addendum

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| meeting minutes | 2 | no | n/a (not scored) | 1.000 |

## thin_d_addendum

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| payment application | 1 | no | n/a (not scored) | 1.000 |
| payment certificate | 1 | no | n/a (not scored) | 0.000 |
| report | 2 | no | n/a (not scored) | 0.000 |
| correspondence | 1 | no | n/a (not scored) | 0.000 |
| meeting minutes | 2 | no | n/a (not scored) | 1.000 |
| NCR | 6 | no | n/a (not scored) | 1.000 |

## combined

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| RFI | 9 | no | n/a (not scored) | 1.000 |
| submittal | 18 | yes | n/a (not scored) | 0.889 |
| transmittal | 13 | yes | n/a (not scored) | 1.000 |
| VO/CO | 16 | yes | n/a (not scored) | 0.938 |
| change request | 14 | yes | n/a (not scored) | 1.000 |
| claim | 4 | no | n/a (not scored) | 1.000 |
| payment application | 4 | no | n/a (not scored) | 0.750 |
| payment certificate | 4 | no | n/a (not scored) | 0.250 |
| drawing | 18 | yes | n/a (not scored) | 0.778 |
| specification | 18 | yes | n/a (not scored) | 0.667 |
| schedule | 19 | yes | n/a (not scored) | 1.000 |
| report | 23 | yes | n/a (not scored) | 0.435 |
| correspondence | 19 | yes | n/a (not scored) | 0.105 |
| BOQ | 12 | yes | n/a (not scored) | 0.750 |
| contract | 12 | yes | n/a (not scored) | 0.917 |
| method statement | 14 | yes | n/a (not scored) | 1.000 |
| meeting minutes | 9 | no | n/a (not scored) | 1.000 |
| NCR | 8 | no | n/a (not scored) | 1.000 |
| inspection request | 0 | no | n/a (not scored) | — |
| site instruction | 8 | no | n/a (not scored) | 1.000 |
| register/log | 15 | yes | n/a (not scored) | 0.333 |
| other | 21 | yes | n/a (not scored) | 0.286 |

## combined_263_v5_view

| class | n | passable | v5 | v6 |
|---|---|---|---|---|
| RFI | 9 | no | 1.000 | 1.000 |
| submittal | 18 | yes | 1.000 | 0.889 |
| transmittal | 13 | yes | 1.000 | 1.000 |
| VO/CO | 16 | yes | 0.000 | 0.938 |
| change request | 14 | yes | 1.000 | 1.000 |
| claim | 4 | no | 0.500 | 1.000 |
| payment application | 3 | no | 1.000 | 0.667 |
| payment certificate | 3 | no | 0.333 | 0.333 |
| drawing | 18 | yes | 0.944 | 0.778 |
| specification | 18 | yes | 0.833 | 0.667 |
| schedule | 19 | yes | 0.789 | 1.000 |
| report | 21 | yes | 0.619 | 0.476 |
| correspondence | 18 | yes | 0.889 | 0.111 |
| BOQ | 12 | yes | 0.500 | 0.750 |
| contract | 12 | yes | 0.917 | 0.917 |
| method statement | 14 | yes | 0.929 | 1.000 |
| meeting minutes | 5 | no | 1.000 | 1.000 |
| NCR | 2 | no | 0.500 | 1.000 |
| inspection request | 0 | no | — | — |
| site instruction | 8 | no | 0.750 | 1.000 |
| register/log | 15 | yes | 0.267 | 0.333 |
| other | 21 | yes | 0.476 | 0.286 |
