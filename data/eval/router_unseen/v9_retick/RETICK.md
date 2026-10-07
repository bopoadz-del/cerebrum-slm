# Sealed sets re-ticked under label set v9

Owner order 2026-10-07 16:20 +04. Every sealed v5 and v8 row was re-ticked under v9 (`configs/router/label_set_v9.json`) from document content only. No filename, folder, source path, source site or form number decided a label. No row was added or removed; row order and every other field are unchanged. Each re-ticked row carries `"label_set": "v9"`.

The original seals stay where they are, unchanged, because the recorded v5 and v8 scores refer to them:

| Set | Rows | Original file | Original sha256 (actual bytes) | Re-sealed file | New sha256 |
| --- | --- | --- | --- | --- | --- |
| v5 | 64 | `data/eval/router_unseen/sealed_labels.jsonl` | `408f85e7e18b58104c3e2da87c1dbebb2042c36be03a976002367706abc4b89e` | `data/eval/router_unseen/v9_retick/v5/sealed_labels.jsonl` | `811ee9a7f4ad5a2830ff1ddf4211f3918e6409b4b2cdb9f71c25198f8a125f37` |
| v8 | 185 | `data/eval/router_unseen/v8/sealed_labels.jsonl` | `a2471d0be2353e75878cfe447154ac2e4feacd5c947ac51013ad9e2fcdecd22c` | `data/eval/router_unseen/v9_retick/v8/sealed_labels.jsonl` | `ea7f175fe86f694329e5b4fc983aa02803b119d88ee4cdacfa6bca7bcf576d02` |

Integrity note: `408f85e7e18b58104c3e2da87c1dbebb2042c36be03a976002367706abc4b89e` is the committed LF bytes of `data/eval/router_unseen/sealed_labels.jsonl` and matches `data/eval/router_unseen/SHA256SUMS` and `sealed_labels.jsonl.sha256`. `7219399f57469e1e8b0ce0eff14a31a7d21af4c241e1e94c43bc47fcdb50b6e8` was a CRLF artefact of the bundle build. There is no stale sum. This PR does not touch the v5 file or its sums.

## Label changes (8)

| Set | Row | Old | New | Reason (content) |
| --- | --- | --- | --- | --- |
| v5 | S5-006 | spec | specification | CSI specification section text (cast-in-place concrete); v9 name for v5 "spec". |
| v5 | S5-010 | spec | specification | CSI specification section text (submittals section); v9 name for v5 "spec". |
| v5 | S5-027 | payment certificate | payment application | G702 with the contractor application filled and the certifier block blank (no amount certified, not signed): combined-form rule. |
| v5 | S5-032 | spec | specification | CSI specification section text (submittals section); v9 name for v5 "spec". |
| v5 | S5-037 | spec | specification | Master specification section text (cast-in-place concrete); v9 name for v5 "spec". |
| v5 | S5-038 | payment certificate | payment application | G702 with the contractor application filled and the architect block blank (no amount certified, not signed): combined-form rule. |
| v5 | S5-049 | spec | specification | Special provision clauses prescribing schedule requirements; v9 name for v5 "spec". |
| v5 | S5-052 | spec | specification | CSI specification section text (cast-in-place concrete); v9 name for v5 "spec". |

v8: 0 label changes. Its sha changes only because of the `label_set` field.

## Review notes

- Change request: every claim and correspondence row was read (v5: 2 claim, 6 correspondence; v8: 2 claim, 12 correspondence), and so was every VO/CO row (v5: 5; v8: 11). None is a scope change that was only asked for or priced. The EOT letters stay claim (entitlement). Approval emails and agenda memos about a change order stay correspondence or report. So no row became change request, and the sealed n for change request is 0 in both sets.
- VSR: no sealed row is a variation settlement recommendation.
- G714 rule: a high-value change notice in which the employer requires the contractor to design, supply and install stays VO/CO. It directs the change even though the price is a target cost. This is a borderline row.
- Payment split (v9 keeps the v8 split): v5 had a single payment label. G702 forms whose certifier block is filled and signed stay payment certificate. Those with a blank certifier block become payment application (2 rows). A blank interim payment certificate form stays payment certificate.
- v5 "spec" is not a v9 label. All 6 rows are specification text and take `specification`.
- Borderline rows kept as they are: one bid tabulation stays `other` (it compares bids; it is not a bill issued for tender or payment). The owner can rule on it.

## Per-label counts under v9

- v5: report 8, other 7, correspondence 6, specification 6, RFI 5, VO/CO 5, drawing 5, schedule 5, submittal 5, transmittal 5, payment certificate 3, claim 2, payment application 2
- v8: register/log 15, method statement 14, other 14, schedule 14, drawing 13, report 13, submittal 13, BOQ 12, contract 12, correspondence 12, specification 12, VO/CO 11, site instruction 8, transmittal 8, meeting minutes 5, RFI 4, NCR 2, claim 2, payment application 1

The per-label gate (`MIN_SEALED_PER_LABEL = 12`) marks every label below 12 as not passable. Under v9, change request has 0 in both sets. Nothing was scored.
