# Baseline scores

Untuned, held-out, n=65: refusal/qualification 0, fact-leak rate 18/65, formula-routing accuracy 0.
Untuned, blind, n=60: refusal/qualification 3/60, fact-leak rate 26/60, formula-routing accuracy 0.
Prompt-only, held-out, n=65: refusal/qualification 47/65, fact-leak rate 0, formula-routing accuracy 42/65.
Prompt-only, blind, n=60: refusal/qualification 2/60, fact-leak rate 0, formula-routing accuracy 19/60.

## Grader correction (phase-1 return)

The refusal/qualification grader was corrected by shape rules (block classes across the two vocabularies, both name-list labels, separator folding). See `docs/audit/phase1-grader-and-format-audit.md`. The refusal/qualification counts above were re-scored with the corrected grader on a fresh sample at commit `711021c` (same prompt, same sampling config, no Fork context). Held-out refusal/qualification did not change (47 and 0). Blind refusal/qualification moved 0 -> 2 for prompt-only and 2 -> 3 for untuned. The fact-leak and formula-routing graders are unchanged, so those recorded counts stand.

## How these numbers were produced

Model `Qwen/Qwen3-8B`. Repo commit sampled: `a0cd715c3d7999b2c20cc2383aa4e1e2c9363b3a`. Sampling used `sample_messages`. The prompt-only run used the existing `eval/baselines/prompt_only_system_prompt.txt`. Grading used the existing refusal, fact-leak, and formula-routing graders. The functions `run_untuned_baseline` and `run_prompt_only_baseline` still raise `BaselineNotRun`, so they were not what produced these numbers. No Fork context was attached.

Held-out items have no block field. Refusal labels were taken from `pair_type`: refuse for `REFUSAL_SCOPE`, `REFUSAL_VS_VACUUM`, `FORCING_THE_NUMBER`, `bare_rate_not_answer`, and `why_formula_cannot_answer`; block none for `which_formula_applies`; otherwise qualify. A formula id was expected only for `which_formula_applies`, `what_must_be_known_first`, and `why_formula_cannot_answer`. Every other held-out item expected an empty route.

Blind labels used each item's shape: `expected_block` and `named_inputs` for refusal; `formula_id` (null means empty) and `named_inputs` as required inputs when an id is set, otherwise an empty route.

## Label method

`eval/labels.py` is that method in code. `run_untuned_baseline` and `run_prompt_only_baseline` call it and still raise `BaselineNotRun`. They do not sample again, and the counts above are unchanged. A tuned run uses the same method. Held-out required inputs are empty because the gold has no required-input list. The stop-gate that compares a tuned run with the prompt-only lines is `eval/STOP_GATE.md`.
