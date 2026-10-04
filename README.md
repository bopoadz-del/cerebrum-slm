# cerebrum-slm

Posture model for construction. The weights learn how to refuse, qualify, name a missing input, and route to a formula. Rates, clause text, formula values, brands, and site names stay in retrieval.

The retrieval source is The Fork. This repository does not add a Cerebrum Blocks Store block.

## Raw archive

`data/raw/slm-datasets.zip` is the dataset archive, committed byte for byte. `data/raw/SHA256SUMS` is its sha256 manifest. CI rejects a zip that does not match the manifest.

## Gates

CI (`.github/workflows/ci.yml`) runs on pull requests.

```bash
PYTHONPATH=scripts python -m gates.run
```

1. **No hardwiring.** `src/` may not contain a probe id or a domain name taken from the sealed catalog, and may not contain a word list. A training pair whose record hash, or whose normalized user/assistant hash, is in the sealed eval hashes fails. The catalog is built at run time from `data/eval/**` and from eval-only records in the raw archive (`*_adversarial`, `governance_blind`, `unroutable`, and records with `eval_only: true`). It is not a list checked into `src/`. The content hash is the user and assistant text, so a schema rewrite that keeps that text still matches. A system prompt is not part of the hash.

2. **The split.** A training assistant turn fails when it carries a number with a unit, a currency, a clause plus an edition (a standard designation such as `BS 8110` or `ACI 318-19` counts), a brand, or a site name. Brands, site names, and clause titles are read from retrieval rows in the raw archive and from `data/retrieval/**`. A posture turn with none of those passes. A clause number with no edition passes.

3. **Blind-set seal.** Every file under `data/eval/**` is hashed. Training code (`src/`, `scripts/train/`, and top-level `train*.py`) may not read that tree. `training_open` rejects `data/eval/**` before opening it. A shared sha256 between a training file and a blind file fails the build, so the training manifest and the blind manifest stay disjoint.

Training files are `*.jsonl` and `*.json` under `data/`, except `data/raw/`, `data/eval/`, and `data/retrieval/`.

`gates.run` plants a probe id, a domain name, a word list, a sealed-hash copy, fact-bearing assistant turns, and a blind read in a temporary tree. Each plant is red, then removed, then green. Those files are not written into this repository.

## What this branch does not do

No training run. No new pairs. `data/eval/` is hashed when present; this branch does not fill it. Paths outside `.github/`, `scripts/gates/`, `tests/gates/`, this README, `pyproject.toml`, `requirements.txt`, and `data/raw/` are left untouched.

## Local run

```bash
python -m pip install -r requirements.txt
PYTHONPATH=scripts python -m gates.run
PYTHONPATH=scripts python -m pytest tests/gates
```
