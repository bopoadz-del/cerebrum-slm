"""Fixed system prompt for the prompt-only baseline.

The prompt is committed. The baseline is not run: the unseen set is not
sealed and the held-out split does not exist yet.
"""

from __future__ import annotations

from pathlib import Path

from eval.baselines.blocked import BaselineNotRun

_PROMPT_PATH = Path(__file__).resolve().parent / "prompt_only_system_prompt.txt"
_BLOCKED = (
    "The prompt-only baseline is not run. It waits until the unseen set "
    "is sealed and the held-out split exists."
)


def load_system_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def run_prompt_only_baseline(*_args, **_kwargs):
    raise BaselineNotRun(_BLOCKED)
