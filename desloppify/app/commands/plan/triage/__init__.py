"""Triage package boundaries.

`command.py` is the CLI entrypoint; `workflow.py` owns routing across stage,
runner, completion, and dashboard flows.
"""

from __future__ import annotations

from types import SimpleNamespace


def cmd_plan_triage(args: SimpleNamespace) -> None:
    """Dispatch to the triage command implementation."""
    from .command import cmd_plan_triage as _cmd_plan_triage

    _cmd_plan_triage(args)

__all__ = ["cmd_plan_triage"]
