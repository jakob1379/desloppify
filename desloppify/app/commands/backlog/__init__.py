"""Backlog command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_backlog(args: SimpleNamespace) -> None:
    """Dispatch to the backlog command implementation."""
    from .cmd import cmd_backlog as _cmd_backlog

    _cmd_backlog(args)

__all__ = ["cmd_backlog"]
