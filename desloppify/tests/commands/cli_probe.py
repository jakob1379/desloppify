"""Test helper for inspecting Typer command arguments without running handlers."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from typer.testing import CliRunner

import desloppify.cli as cli_mod


class CliParseProbe:
    """Small parse-only facade for legacy parser-focused tests."""

    def parse_args(self, argv: list[str]) -> SimpleNamespace:
        """Parse CLI arguments while intercepting command dispatch.

        Temporarily replaces ``cli_mod.run_command`` with a capture list append,
        then restores the original function before returning. If dispatch is
        captured, returns the parsed ``SimpleNamespace``. Otherwise writes Typer
        output to stdout on success or stderr on failure, then raises
        ``SystemExit`` with the command exit code.
        """
        if not argv:
            return SimpleNamespace(command=None)

        captured: list[SimpleNamespace] = []
        original_run_command = cli_mod.run_command
        try:
            cli_mod.run_command = captured.append
            result = CliRunner().invoke(cli_mod.create_typer_app(), argv)
        finally:
            cli_mod.run_command = original_run_command

        if captured:
            return captured[0]

        if result.output:
            stream = sys.stdout if result.exit_code == 0 else sys.stderr
            stream.write(result.output)
        raise SystemExit(result.exit_code)
