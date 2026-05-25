"""Review command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_review(args: SimpleNamespace) -> None:
    """Dispatch to the review command implementation."""
    from .cmd import cmd_review as _cmd_review

    _cmd_review(args)

__all__ = ["cmd_review"]
