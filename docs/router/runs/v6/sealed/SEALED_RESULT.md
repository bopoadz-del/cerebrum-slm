# Router v6 epoch 3: sealed result (v9 label set, scored once)

Adapter `tinker://93552b55-3c20-5862-8bbf-2320fb04b236:train:0/sampler_weights/router-v6-qwen3.5-4b-lora-r16-epoch3`,
epoch chosen on val macro recall before any sealed read. Scored on main `39945a967dc6c720bf36987e0e3b6f3e53e8bdde`
(fresh blob-verified rebuild, 383 blobs). Settings, parser and gate identical to the v5 sealed run.

## Scores (each set once; combined = concatenation, nothing re-sampled)

| set | n | macro recall | accuracy | gate_v2 | router_passed |
|---|---|---|---|---|---|
| v5_retick | 64 | 0.6783 | 0.6094 | pass | false |
| v8_retick | 185 | 0.7633 | 0.7459 | pass | false |
| cr_addendum | 14 | 1.0000 | 1.0000 | fail (single-label set, degenerate; read on combined) | false |
| thin_c_addendum | 2 | 1.0000 | 1.0000 | fail (single-label set, degenerate) | false |
| thin_d_addendum | 13 | 0.5000 | 0.6923 | pass | false |
| combined | 278 | 0.7665 | 0.7266 | pass | false |

`router_passed` is false everywhere because the gate also needs every declared label at n >= 12; on the combined view
RFI 9, claim 4, payment application 4, payment certificate 4, meeting minutes 9, NCR 8, site instruction 8 and
inspection request 0 are below 12.

VO/CO recall: combined 15/16 = 0.938 (v5: 0/16 = 0.000 on the same 263-row view). v5_retick 5/5, v8_retick 10/11;
the one miss is predicted site instruction.

For comparison, v5 epoch 1 on the 263-row combined view: macro 0.726, acc 0.730. v6 on that same view is computed in
`V5_VS_V6.md` from the stored predictions.

## Passable classes (combined, n >= 12)

submittal 18, transmittal 13, VO/CO 16, change request 14, drawing 18, specification 18, schedule 19, report 23,
correspondence 19, BOQ 12, contract 12, method statement 14, register/log 15, other 21.

Not passable: RFI 9, claim 4, payment application 4, payment certificate 4, meeting minutes 9, NCR 8,
site instruction 8, inspection request 0.

## Name-blind check (PR #50 party-only blanker, blanked side only)

| view | rows with a blanked field | flips | on passable classes | gate |
|---|---|---|---|---|
| v5_retick | 39/64 | 4 | 0 | PASS |
| v8_retick | 89/185 | 2 | 2 (correspondence, drawing) | FAIL |
| cr_addendum | 11/14 | 0 | 0 | PASS |
| thin_c_addendum | 1/2 | 0 | 0 | PASS |
| thin_d_addendum | 8/13 | 0 | 0 | PASS |
| combined | 148/278 | 6 | 6 (correspondence 2, drawing, other, report, submittal) | FAIL |

No flip on any row where nothing was blanked. Before and after read per flip (6 rows):

| class (gold) | before -> after | what was blanked | cause |
|---|---|---|---|
| correspondence (v5_retick) | wrong -> wrong | addressee, signatory, contractor name and address, and the greeting and a certificate date | party names plus over-blanking (greeting and a date are not party values); wrong both ways |
| other (v5_retick) | right -> wrong | the value of a "Procedure Name:" field (the document's own title) and an approval word | over-blanking: a title field read as a name field |
| report (v5_retick) | wrong -> wrong | project title, addressee, author firm, attendee list | genuine party/project names; already wrong before blanking |
| submittal (v5_retick) | right -> wrong | a run of empty form labels on a blank form (job no., submittal no.) | over-blanking: form labels with no value were blanked, which removed the class cue |
| correspondence (v8_retick) | wrong -> right | the project/site name in the subject line | genuine project name; the prediction was keyed on the heading, blanking corrected it |
| drawing (v8_retick) | wrong -> right | empty title-block labels (contents, scale) | over-blanking of empty title-block labels |

Four of the six flips involve the blanker taking something that is not a party value (title field, empty labels,
greeting/date). Both right -> wrong flips are of that kind. The two genuine project-name flips moved wrong -> right or
stayed wrong. The blanker is not changed in this bundle.

## Notes

- Isolation: v6 train 1712 + val 900 vs every set, router.isolation: 0 rejected (`isolation_v6.json`).
- Duplicate across sealed sets: thin_d V9D-D003 is the same file and label as v5_retick S5-027; combined counts it twice, as registered.
- thin_d candidate text was built from the sealed PDFs (sha-matched) because none existed; see `inputs.json`.
- The name-blind phase was interrupted at 248/278 rows; the re-run sampled only the 30 missing rows (`score.log`).
- The on-box pre-run note was overwritten by a concurrent process after scoring began; `PRE_RUN_NOTE.txt` here is the restored original (see its header).
