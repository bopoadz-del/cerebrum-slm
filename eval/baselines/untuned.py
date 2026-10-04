"""Untuned baseline entry point.

Scoring waits until the unseen set is sealed and the held-out split exists.
This module does not call the model and does not record a score.
"""

from __future__ import annotations

from eval.baselines.blocked import BaselineNotRun

_BLOCKED = (
    "The untuned baseline is not run. It waits until the unseen set "
    "is sealed and the held-out split exists."
)


def run_untuned_baseline(*_args, **_kwargs):
    raise BaselineNotRun(_BLOCKED)
