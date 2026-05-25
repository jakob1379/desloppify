"""Next command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_next(args: SimpleNamespace) -> None:
    """Dispatch to the next command implementation."""
    from .cmd import cmd_next as _cmd_next

    _cmd_next(args)

__all__ = ["cmd_next"]
