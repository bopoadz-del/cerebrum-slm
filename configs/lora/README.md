# Posture LoRA — Qwen3-8B

Config: `configs/lora/qwen3-8b-posture.json`. Entry point: `scripts/train/train_lora.py`.

The adapter trains on `data/train/pairs.jsonl` only. Held-out rows and everything under the sealed eval tree stay out of this run. The base is the committed instruct checkpoint `Qwen/Qwen3-8B`. Thinking stays off, matching `configs/model/qwen3-8b.json`.

`scripts/train/train_lora.py --dry-run` checks the config and the train split and prints counts. It does not read `TINKER_API_KEY` and it does not construct a Tinker client. A real run reads that variable from the environment and refuses to start when it is missing or blank.

Checked against the Tinker Python SDK 0.32 signatures and the training docs: `ServiceClient.create_lora_training_client`, `TrainingClient.forward_backward` with `cross_entropy`, `TrainingClient.optim_step` with `AdamParams`, `save_state`, and `save_weights_for_sampler`. `LoraConfig` has rank, seed, and the three module flags. It has no alpha field.

## Hyperparameters

- **Rank 8.** The client default is 32. Rank 8 still has far more adapter parameters than the assistant tokens in about 209 short pairs, and it leaves less room to memorize them.
- **Alpha 8.** The training client does not take alpha. Alpha is recorded equal to rank so a later merge that scales by alpha/rank keeps scale 1, which is the update the client applies (`W' = W + BA`).
- **MLP and attention on, unembed off.** The LoRA primer finds that MLP layers carry small-data supervised learning and that attention-only adapters fall behind. The unembedding matrix is the full vocabulary; it stays frozen so this run does not retune every output token from 209 pairs.
- **Learning rate 0.00005.** `AdamParams` defaults to 0.0001, and the supervised examples often use 0.0002. One pass over a small split uses the lower half of the 0.00001–0.0005 band those notes describe. Beta1 0.9, beta2 0.95, eps 1e-12, and weight decay 0 are the `AdamParams` defaults.
- **Gradient clip 1.0.** The `AdamParams` default is 0, which disables clipping. The cap is there so one short batch cannot take an unbounded step.
- **One epoch.** A second pass over the same 209 answers is where memorization starts.
- **Batch size 8.** The primer notes that LoRA loses more from a large batch than full fine-tuning does. Eight gives 27 updates in the epoch, and the last batch is kept even though it is short of eight.
- **Max sequence length 1024.** Train replies are short posture turns. 1024 covers the Qwen3 chat template and refuses a long document. The model's native context is 32768 and is not used.
- **Seed 0.** This is the seed already fixed for sampling, so the adapter initialization and the shuffle are reproducible.
- **Loss on assistant turns only.** `forward_backward(..., "cross_entropy")` gets a shift-by-one datum: weights are 0 through the prompt, including the generation header, and 1 on the assistant tokens. System and user tokens are not trained. Weights stay 0 or 1.

The script renders with the tokenizer from `TrainingClient.get_tokenizer()`, calling `apply_chat_template(..., enable_thinking=False)`. That is the same Qwen3 chat template the sampling client uses. If the rendered prompt is not a prefix of the full conversation, the run stops instead of guessing the assistant span.

Before any step, the entry point re-checks the train file: every row is a train-split pair, the manifest count matches, `fact_count` is 0, and no assistant turn carries a number with a unit, a currency amount, a clause plus an edition, a brand, or a site name. That check uses the existing split terms. It does not open the sealed eval tree. The sealed-hash comparison stays in CI, which is the gate allowed to read that tree.
