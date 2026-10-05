"""Shared stop for baselines that wait on the sealed split."""


class BaselineNotRun(RuntimeError):
    """The untuned and prompt-only baselines are not run yet."""
