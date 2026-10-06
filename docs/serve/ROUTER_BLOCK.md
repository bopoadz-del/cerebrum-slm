# Router block

The router block classifies a document from its first 512 content tokens into the label set in `configs/router/labels.json`. The user message is that text. Filename, path, document id, project, and `fork_declared_type` are not inputs.

The served adapter is a Qwen3.5-4B LoRA, rank 16, alpha 16, two epochs, 168 steps. Tinker does not serve `Qwen/Qwen3-4B`, so the run used `Qwen/Qwen3.5-4B`. Max sequence length for that run is 3072. The serve file is `configs/serve/router-epoch2.json`.

Status: `trained`.

Checkpoint: `tinker://b0857111-57c4-56f6-bf9b-ed3f8021826b:train:0/sampler_weights/router-qwen3.5-4b-lora-r16-epoch2`

Epoch 2 val accuracy is 0.906. The majority-class gate passes because the model is not a constant predictor. The constant `drawing` baseline fails that gate. Per-label recall is in `docs/router/DATASET_CARD.md`.

The sealed set `data/eval/router_unseen/sealed_labels.jsonl` is empty and was not scored. Scoring happens once, after the owner sheet is sealed.

Human stratified agreement is PENDING_OWNER. Training proceeded before that check by owner order. The majority-class gate and the agreement threshold are unchanged.
