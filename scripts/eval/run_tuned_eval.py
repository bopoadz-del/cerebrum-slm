"""Sample a tuned checkpoint on held-out and the blind set.

Dry-run checks data and config and does not contact Tinker.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _entry in (_ROOT / "scripts", _ROOT / "src", _ROOT):
    _text = str(_entry)
    if _text not in sys.path:
        sys.path.insert(0, _text)

from eval.readers import EvalReadError
from eval.stop_gate import StopGateError
from eval.tuned import TunedEvalError, dry_run_tuned_eval, format_scores, run_tuned_eval
from model.sampling import TinkerKeyMissing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Grade a tuned Qwen3-8B checkpoint")
    parser.add_argument("--checkpoint", required=True, help="Tinker checkpoint path")
    parser.add_argument("--output", type=Path, help="Aggregate score JSON")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check data and config without contacting Tinker",
    )
    parser.add_argument(
        "--prompt-only-system-prompt",
        action="store_true",
        help="Put the prompt-only system prompt on the tuned checkpoint",
    )
    args = parser.parse_args(argv)
    try:
        if args.dry_run:
            print(dry_run_tuned_eval(
                args.checkpoint,
                prompt_only_system_prompt=args.prompt_only_system_prompt,
            ))
            return 0
        if args.output is None:
            parser.error("--output is required unless --dry-run is set")
        payload = run_tuned_eval(
            args.checkpoint,
            args.output,
            prompt_only_system_prompt=args.prompt_only_system_prompt,
        )
    except (TunedEvalError, TinkerKeyMissing, EvalReadError, StopGateError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(format_scores(payload))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
