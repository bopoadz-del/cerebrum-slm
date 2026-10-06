# Router block

The router block classifies a document from its first 512 content tokens into the label set in `configs/router/labels.json`. The user message is that text. Filename, path, document id, project, and `fork_declared_type` are not inputs.

The intended adapter is a Qwen3-4B LoRA, rank 16, alpha 16, two epochs, on teacher labels. The serve file is `configs/serve/router-epoch2.json`.

Status: `not_trained`. Checkpoint id: none (`checkpoint` is null). No sampler path was saved.

Teacher labelling and the LoRA fit did not run. The Tinker key was not available in this environment.

The sealed set `data/eval/router_unseen/sealed_labels.jsonl` is empty and is not scored. Scoring happens once, after the owner sheet is sealed.

Human stratified agreement is PENDING_OWNER. Training was ordered to proceed before that check. The majority-class gate and the agreement threshold are unchanged. See `docs/router/DATASET_CARD.md`.
