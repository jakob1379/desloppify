"""Show command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_show(args: SimpleNamespace) -> None:
    """Dispatch to the show command implementation."""
    from .cmd import cmd_show as _cmd_show

    _cmd_show(args)

__all__ = ["cmd_show"]
