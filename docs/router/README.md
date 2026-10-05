# Document-type router

This adapter predicts one document-type label. It does not predict rates, clauses, or any other fact. The target of a pair is the label alone.

The label set is data in `configs/router/labels.json`. Product code loads that file. It does not keep a copy, and it does not map a filename, an extension, or document text onto a label. Copying the list into `src/` would also fail the word-list gate.

Ordered labels:

- RFI
- submittal
- transmittal
- VO/CO
- claim
- payment certificate
- drawing
- spec
- schedule
- report
- correspondence
- other

`other` is a label the export can name. Rows that do not match the list are rejected. They are not relabelled.

## Input

`configs/router/dataset.json` sets the contract.

- The model input is `filename: {filename}` plus the first 512 whitespace tokens of the normalized document.
- The sha256 used for dedupe is the full normalized document, not the 512-token prefix.
- Normalization is Unicode NFC, one newline style, and trimmed ends. The label and the project id also collapse internal whitespace. There is no synonym map.
- A provided 64-character sha is compared with that digest. A mismatch is counted. The computed digest stays the dedupe key.
- Identical text with two labels, or two project ids, is a conflict and is dropped. The same filename and prefix with two labels is a conflict too.

## Split

Eval is sealed before any pair exists.

1. Deduplicate.
2. Seal one whole project. The rule in config is `largest_then_lowest_project_sha256`: the largest project, ties broken by the lowest project-id hash. The project name is not in code.
3. From the other projects, hold out 15 percent in each label, round half up, taking the lowest content hashes. The rest is train.

`python -m router.split` prints counts and hashes only. It writes no train file and no held-out file.

An existing `data/eval/router/seal.json` stays on that project even if a later export would pick a different one. Documents from the sealed project stay out of train and held-out. There is no switch that moves the seal.

## Commands

```bash
PYTHONPATH=scripts python -m router.import_export
PYTHONPATH=scripts python -m router.seal
PYTHONPATH=scripts python -m router.split
```

Exit code 2 is `WALL: label export`. That is a missing file, or a file with no labeled rows. Exit code 0 prints a JSON object of counts and hashes. These commands do not call Tinker.

`router.seal` writes:

- `data/eval/router/items.jsonl` — sealed model inputs (filename and prefix) and the label as `completion`
- `data/eval/router/seal.json` — sha256 of that file, plus project and item hashes
- `docs/router/sealed-project.md` — the same hashes and label counts, with no document text, filenames, or project name

Do not quote sealed item text in a pull request.

Whitespace tokens are the unit this scaffold counts. Another token unit is refused until a later change implements it. Training and baselines are not part of this scaffold.
