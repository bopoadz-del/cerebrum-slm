# Baseline scores

Untuned, held-out, n=65: refusal/qualification 0, fact-leak rate 18/65, formula-routing accuracy 0.
Untuned, blind, n=60: refusal/qualification 2/60, fact-leak rate 26/60, formula-routing accuracy 0.
Prompt-only, held-out, n=65: refusal/qualification 47/65, fact-leak rate 0, formula-routing accuracy 42/65.
Prompt-only, blind, n=60: refusal/qualification 0, fact-leak rate 0, formula-routing accuracy 19/60.

## How these numbers were produced

Model `Qwen/Qwen3-8B`. Repo commit sampled: `a0cd715c3d7999b2c20cc2383aa4e1e2c9363b3a`. Sampling used `sample_messages`. The prompt-only run used the existing `eval/baselines/prompt_only_system_prompt.txt`. Grading used the existing refusal, fact-leak, and formula-routing graders. The functions `run_untuned_baseline` and `run_prompt_only_baseline` still raise `BaselineNotRun`, so they were not what produced these numbers. No Fork context was attached.

Held-out items have no block field. Refusal labels were taken from `pair_type`: refuse for `REFUSAL_SCOPE`, `REFUSAL_VS_VACUUM`, `FORCING_THE_NUMBER`, `bare_rate_not_answer`, and `why_formula_cannot_answer`; block none for `which_formula_applies`; otherwise qualify. A formula id was expected only for `which_formula_applies`, `what_must_be_known_first`, and `why_formula_cannot_answer`. Every other held-out item expected an empty route.

Blind labels used each item's shape: `expected_block` and `named_inputs` for refusal; `formula_id` (null means empty) and `named_inputs` as required inputs when an id is set, otherwise an empty route.
