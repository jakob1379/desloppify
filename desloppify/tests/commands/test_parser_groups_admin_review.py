"""CLI coverage for review command wiring."""

from __future__ import annotations

from desloppify.tests.commands.cli_probe import CliParseProbe


def test_review_command_accepts_core_flags() -> None:
    args = CliParseProbe().parse_args(["review", "--prepare", "--runner", "codex"])
    assert args.command == "review"
    assert args.prepare is True
    assert args.runner == "codex"


def test_review_command_accepts_opencode_runner() -> None:
    args = CliParseProbe().parse_args(["review", "--prepare", "--runner", "opencode"])
    assert args.command == "review"
    assert args.prepare is True
    assert args.runner == "opencode"
