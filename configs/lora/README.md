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
- **Loss on assistant turns only.** Checked on all train pairs with the Qwen3-8B tokenizer: weight 0 through the system, user, and generation header, weight 1 on the reply and its end-of-turn token.
- **Loss detail.** `forward_backward(..., "cross_entropy")` gets a shift-by-one datum: weights are 0 through the prompt, including the generation header, and 1 on the assistant tokens. System and user tokens are not trained. Weights stay 0 or 1.

## Format: the same system prompt and the graded reply (phase-1 fix)

Run 1 trained every pair with an empty system turn and a prose target, while the eval grades one JSON object and the tuned+prompt eval stacks `eval/baselines/prompt_only_system_prompt.txt`. That was the defect (see `docs/audit/phase1-grader-and-format-audit.md`).

- `system_prompt_file` must be `eval/baselines/prompt_only_system_prompt.txt`. Every train pair gets that system turn, so train and tuned+prompt eval see the same prompt and the same Qwen3 template.
- `target_format` must be `posture_json_v1`. `scripts/train/posture_target.py` renders each target from the pair's own labels: block by the eval label rule, formula id from the pair, required inputs from the committed formula registry. No model writes target text. The rendered target passes the Split check.
- `--log-json PATH` writes step losses and checkpoint paths (no key, no item text).

## Rank-16 run: `qwen3-8b-posture-r16.json`

Used once, after the data change, with the same format.

- **Rank 16, alpha 16.** More capacity for about 1,500 examples. The LoRA primer notes the optimal LR does not depend on rank.
- **Learning rate 0.000473.** Tinker's recommended LoRA LR, `tinker_cookbook.hyperparam_utils.get_lr("Qwen/Qwen3-8B", is_lora=True)` = `5e-5 * 10 * (2000 / 4096) ** 0.0775` (base LR 5e-5, LoRA multiplier 10, Qwen exponent 0.0775, hidden size 4096). Sources: https://tinker-docs.thinkingmachines.ai/cookbook/api-reference/hyperparam_utils/get_lr/ and https://tinker-docs.thinkingmachines.ai/tinker/lora-primer/ ("LoRA requires a much larger LR than full fine-tuning, typically about 10x").
- **Two epochs, batch 16.** A sampler checkpoint is saved after each epoch (`<name>-epoch<N>`).
- **Early stop on held-out leak.** Each epoch checkpoint is scored by `scripts/eval/run_tuned_eval.py`. The served candidate is the last epoch before the first epoch whose held-out fact-leak is above 0. The training script itself never reads held-out.
- **Max sequence length 2048.** Train rows now carry the system prompt and, for hard negatives, an attached Fork context.

The script renders with the tokenizer from `TrainingClient.get_tokenizer()`, calling `apply_chat_template(..., enable_thinking=False)`. That is the same Qwen3 chat template the sampling client uses. If the rendered prompt is not a prefix of the full conversation, the run stops instead of guessing the assistant span.

Before any step, the entry point re-checks the train file: every row is a train-split pair, the manifest count matches, `fact_count` is 0, and no assistant turn carries a number with a unit, a currency amount, a clause plus an edition, a brand, or a site name. That check uses the existing split terms. It does not open the sealed eval tree. The sealed-hash comparison stays in CI, which is the gate allowed to read that tree.
