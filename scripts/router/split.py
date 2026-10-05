"""Dry-run the router split. Prints counts and hashes and writes no pairs."""

from __future__ import annotations

import argparse
from pathlib import Path

from router.plan import build_plan
from router.report import finish, public_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run the router split. Writes no pairs.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    def action() -> dict:
        config, corpus, plan = build_plan(args.root.resolve())
        return public_plan(config, corpus, plan)

    return finish(action)


if __name__ == "__main__":
    raise SystemExit(main())
