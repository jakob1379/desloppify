"""Scan command package with a stable package-root entrypoint."""

from __future__ import annotations

from types import SimpleNamespace


def cmd_scan(args: SimpleNamespace) -> None:
    """Dispatch to the scan command implementation."""
    from .cmd import cmd_scan as _cmd_scan

    _cmd_scan(args)

__all__ = ["cmd_scan"]
