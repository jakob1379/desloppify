"""Move command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_move(args: SimpleNamespace) -> None:
    """Dispatch to the move command implementation."""
    from .cmd import cmd_move as _cmd_move

    _cmd_move(args)

__all__ = ["cmd_move"]
