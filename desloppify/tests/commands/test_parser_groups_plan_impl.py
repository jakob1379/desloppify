"""CLI coverage for plan command wiring."""

from __future__ import annotations

from desloppify.tests.commands.cli_probe import CliParseProbe


def test_plan_command_and_show_subcommand_parse() -> None:
    args = CliParseProbe().parse_args(["plan", "--state", "state.json", "show"])
    assert args.command == "plan"
    assert args.state == "state.json"
    assert args.plan_action == "show"


def test_plan_cluster_update_preserves_multi_value_options() -> None:
    args = CliParseProbe().parse_args(
        ["plan", "cluster", "update", "alpha", "--issue-refs", "a", "b"]
    )
    assert args.command == "plan"
    assert args.plan_action == "cluster"
    assert args.cluster_action == "update"
    assert args.issue_refs == ["a", "b"]


def test_plan_policy_default_and_list_subcommand_parse() -> None:
    default_args = CliParseProbe().parse_args(["plan", "policy"])
    assert default_args.command == "plan"
    assert default_args.plan_action == "policy"
    assert default_args.policy_action is None

    list_args = CliParseProbe().parse_args(["plan", "policy", "list"])
    assert list_args.command == "plan"
    assert list_args.plan_action == "policy"
    assert list_args.policy_action == "list"
