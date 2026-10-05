"""Read a JSONL or CSV label export from data/raw/router.

No export means a wall. This command does not invent labels and does not write pairs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from router.config import load_config
from router.records import load_corpus
from router.report import finish, public_import


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import an external document-type label export.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()

    def action() -> dict:
        config = load_config(root)
        corpus = load_corpus(root, config)
        return public_import(config, corpus)

    return finish(action)


if __name__ == "__main__":
    raise SystemExit(main())
