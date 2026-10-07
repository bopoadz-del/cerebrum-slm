# Router run v5 (label set v9, 22 labels): PENDING

- Status: pending. v5 trains on main after this PR (pr7) merges. The results will come in a follow-up docs PR.
- History: the first v5 attempt, on main a35e160, stopped at preflight. One train row was about 24k tokens (an archive dumped as base64, label `other`), over max_sequence_length 6656. The repo's fit_router refuses over-limit rows, so nothing was trained and nothing was spent. Preflight at a35e160: train_max 26581, 1 row over 6656, val prompt max 6470.
- Fix: this PR adds a general content rule (`router.content.is_mostly_encoded`, ratio threshold 0.5) and re-runs the split. No limit was raised, and no row was dropped by id.
- Recipe (same as v4): Qwen/Qwen3.5-4B LoRA r16, alpha 16, 2 epochs, lr 4.73e-4, batch 16, seed 0, max_sequence_length 6656, v9 prompt. v3 used 6144; v4 raised it to 6656 because the v9 prompt is longer (longest v4 row 6387 tokens).
- Sealed sets: not read, not scored. Sealed scoring waits for the owner's ticks on the 14 change-request candidates and a new order.
