"""Typer application for the public CLI surface."""

import platform
import sys
from enum import StrEnum
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from types import SimpleNamespace
from typing import Annotated, Any, ClassVar

import typer
from typer.core import TyperCommand

class ScanProfile(StrEnum):
    objective = "objective"
    full = "full"
    ci = "ci"


class IssueStatus(StrEnum):
    all = "all"
    open = "open"
    fixed = "fixed"
    suppressed = "suppressed"
    wontfix = "wontfix"
    false_positive = "false_positive"


class GroupMode(StrEnum):
    item = "item"
    file = "file"
    detector = "detector"


class OutputFormat(StrEnum):
    terminal = "terminal"
    json = "json"
    md = "md"


class TreeSort(StrEnum):
    loc = "loc"
    issues = "issues"
    coupling = "coupling"


class DetectCategory(StrEnum):
    imports = "imports"
    vars = "vars"
    params = "params"
    all = "all"


class QueueSort(StrEnum):
    priority = "priority"
    recent = "recent"


class Position(StrEnum):
    top = "top"
    bottom = "bottom"
    before = "before"
    after = "after"


class ReorderPosition(StrEnum):
    top = "top"
    bottom = "bottom"
    before = "before"
    after = "after"
    up = "up"
    down = "down"


class TriageStage(StrEnum):
    strategize = "strategize"
    observe = "observe"
    reflect = "reflect"
    organize = "organize"
    enrich = "enrich"
    sense_check = "sense-check"


class TriageRunner(StrEnum):
    codex = "codex"
    claude = "claude"
    rovodev = "rovodev"


class ReviewRunner(StrEnum):
    codex = "codex"
    opencode = "opencode"
    rovodev = "rovodev"


class ExternalRunner(StrEnum):
    claude = "claude"


class Effort(StrEnum):
    trivial = "trivial"
    small = "small"
    medium = "medium"
    large = "large"


class ExportFormat(StrEnum):
    text = "text"
    yaml = "yaml"


class Interface(StrEnum):
    amp = "amp"
    claude = "claude"
    codex = "codex"
    gemini = "gemini"
    opencode = "opencode"
    qwen = "qwen"
    rovodev = "rovodev"


def _expand_plus_options(args: list[str], options: set[str]) -> list[str]:
    expanded: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        expanded.append(token)
        index += 1
        if token not in options:
            continue
        first_value = True
        while index < len(args) and not args[index].startswith("-"):
            if not first_value:
                expanded.append(token)
            expanded.append(args[index])
            first_value = False
            index += 1
    return expanded


class _PlusOptionCommand(TyperCommand):
    plus_options: ClassVar[set[str]] = set()

    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:
        return super().parse_args(ctx, _expand_plus_options(args, self.plus_options))


class _ClusterUpdateCommand(_PlusOptionCommand):
    plus_options = {"--depends-on", "--issue-refs", "--steps"}


class _CommitLogRecordCommand(_PlusOptionCommand):
    plus_options = {"--only"}


def _cli_version_string() -> str:
    try:
        version_label = f"desloppify {get_version('desloppify')}"
    except PackageNotFoundError:
        version_label = "desloppify (version unknown)"
    return f"{version_label}\nPython {platform.python_version()} at {sys.executable}"


def _value(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, list):
        return [_value(item) for item in value]
    return value


def _clean(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _value(value) for key, value in values.items()}


def _merged_obj(ctx: typer.Context) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    cursor: typer.Context | None = ctx
    chain: list[typer.Context] = []
    while cursor is not None:
        chain.append(cursor)
        cursor = cursor.parent
    for item in reversed(chain):
        if isinstance(item.obj, dict):
            merged.update(item.obj)
    return merged


def _namespace(ctx: typer.Context, command: str, **values: Any) -> SimpleNamespace:
    return SimpleNamespace(command=command, **_merged_obj(ctx), **_clean(values))


def _params(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if key != "ctx"}


def _dispatch(ctx: typer.Context, command: str, **values: Any) -> None:
    from desloppify.cli import run_command

    run_command(_namespace(ctx, command, **values))


def create_app(*, langs: list[str], detector_names: list[str]) -> typer.Typer:
    lang_help = ", ".join(langs) if langs else "registered languages"
    detector_help = ", ".join(detector_names)

    app = typer.Typer(
        name="desloppify",
        help="Desloppify - codebase health tracker",
        no_args_is_help=True,
    )
    plan_app = typer.Typer(help="Living plan: generate, show, resolve, skip, cluster, triage", no_args_is_help=False)
    cluster_app = typer.Typer(help="Manage issue clusters", no_args_is_help=True)
    commit_log_app = typer.Typer(help="Track commits and resolved issues for PR updates", no_args_is_help=False)
    policy_app = typer.Typer(help="Manage project policy rules", no_args_is_help=False)
    config_app = typer.Typer(help="Show/set/unset project configuration", no_args_is_help=False)
    zone_app = typer.Typer(help="Show/set/clear zone classifications", no_args_is_help=False)
    directives_app = typer.Typer(help="View/set agent directives for phase transitions", no_args_is_help=False)
    dev_app = typer.Typer(help="Developer utilities", no_args_is_help=True)

    @app.callback(invoke_without_command=True)
    def root(
        ctx: typer.Context,
        lang: Annotated[str | None, typer.Option("--lang", help=f"Language to scan ({lang_help}). Auto-detected if omitted.")] = None,
        exclude: Annotated[list[str] | None, typer.Option("--exclude", metavar="PATTERN", help="Path pattern to exclude (component/prefix match; repeatable)")] = None,
        version: Annotated[bool, typer.Option("--version", "-V", is_eager=True, help="Show version and exit.")] = False,
    ) -> None:
        if version:
            typer.echo(_cli_version_string())
            raise typer.Exit()
        ctx.obj = {"lang": lang, "exclude": exclude}

    @app.command("scan", help="Run all detectors, update state, show diff", rich_help_panel="workflow")
    def scan(
        ctx: typer.Context,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        by_language: Annotated[bool, typer.Option("--by-language", help="Run independent scans for each detected language state")] = False,
        reset_subjective: Annotated[bool, typer.Option("--reset-subjective", help="Reset subjective measures to 0 before running scan")] = False,
        skip_slow: Annotated[bool, typer.Option("--skip-slow", help="Skip slow detectors (dupes)")] = False,
        profile: Annotated[ScanProfile | None, typer.Option("--profile", help="Scan profile: objective, full, or ci")] = None,
        force_resolve: Annotated[bool, typer.Option("--force-resolve", help="Bypass suspect-detector protection (use when a detector legitimately went to 0)")] = False,
        no_badge: Annotated[bool, typer.Option("--no-badge", help="Skip scorecard image generation (also: DESLOPPIFY_NO_BADGE=true)")] = False,
        badge_path: Annotated[str | None, typer.Option("--badge-path", metavar="PATH", help="Output path for scorecard image (default: scorecard.png)")] = None,
        lang_opt: Annotated[list[str] | None, typer.Option("--lang-opt", metavar="KEY=VALUE", help="Language runtime option override (repeatable, e.g. --lang-opt roslyn_cmd='dotnet run ...')")] = None,
        force_rescan: Annotated[bool, typer.Option("--force-rescan", help="Bypass queue completion check (requires --attest)")] = False,
        attest: Annotated[str | None, typer.Option("--attest", metavar="TEXT", help="Attestation for --force-rescan")] = None,
    ) -> None:
        _dispatch(ctx, "scan", **_params(locals()))

    @app.command("status", help="Full project dashboard: score, dimensions, progress, coaching", rich_help_panel="workflow")
    def status(
        ctx: typer.Context,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
        by_language: Annotated[bool, typer.Option("--by-language", help="Show independent score rows for detected language states")] = False,
    ) -> None:
        _dispatch(ctx, "status", state=state, json=json_output, by_language=by_language)

    @app.command("show", help="Dig into issues by file, directory, detector, or ID", rich_help_panel="investigate")
    def show(
        ctx: typer.Context,
        pattern: Annotated[str | None, typer.Argument(help="File path, directory, detector name, issue ID, or glob")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        status: Annotated[IssueStatus, typer.Option("--status", help="Filter by status (default: open)")] = IssueStatus.open,
        top: Annotated[int, typer.Option("--top", help="Max files to show (default: 20)")] = 20,
        output: Annotated[str | None, typer.Option("--output", metavar="FILE", help="Write JSON to file instead of terminal")] = None,
        chronic: Annotated[bool, typer.Option("--chronic", help="Show issues that have been reopened 2+ times (chronic reopeners)")] = False,
        code: Annotated[bool, typer.Option("--code", help="Show inline code snippets for each issue")] = False,
        notes: Annotated[str | None, typer.Option("--notes", metavar="FILE", help="Path to investigation notes file to attach to a issue")] = None,
        no_budget: Annotated[bool, typer.Option("--no-budget", help="Bypass per-detector noise budget (show all matching issues)")] = False,
    ) -> None:
        _dispatch(ctx, "show", **_params(locals()))

    @app.command("next", help="Show the next execution item from the living plan", rich_help_panel="workflow")
    def next_cmd(
        ctx: typer.Context,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        count: Annotated[int, typer.Option("--count", help="Number of items to show (default: 1)")] = 1,
        scope: Annotated[str | None, typer.Option("--scope", help="Optional scope filter (path, detector, ID prefix, or glob)")] = None,
        status: Annotated[IssueStatus, typer.Option("--status", help="Status filter for queue items (default: open)")] = IssueStatus.open,
        group: Annotated[GroupMode, typer.Option("--group", help="Group output by item, file, or detector")] = GroupMode.item,
        output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format (default: terminal)")] = OutputFormat.terminal,
        explain: Annotated[bool, typer.Option("--explain", help="Show ranking rationale")] = False,
        cluster: Annotated[str | None, typer.Option("--cluster", metavar="NAME", help="Filter to a specific plan cluster")] = None,
        include_skipped: Annotated[bool, typer.Option("--include-skipped", help="Include skipped items in the queue")] = False,
        output: Annotated[str | None, typer.Option("--output", metavar="FILE", help="Write JSON/Markdown to file (with --format json|md)")] = None,
    ) -> None:
        _dispatch(
            ctx,
            "next",
            state=state,
            count=count,
            scope=scope,
            status=status,
            group=group,
            format=output_format,
            explain=explain,
            cluster=cluster,
            include_skipped=include_skipped,
            output=output,
        )

    @app.command("backlog", help="Show broader backlog items not currently driving execution", rich_help_panel="workflow")
    def backlog(
        ctx: typer.Context,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        count: Annotated[int, typer.Option("--count", help="Number of items to show (default: 1)")] = 1,
        scope: Annotated[str | None, typer.Option("--scope", help="Optional scope filter (path, detector, ID prefix, or glob)")] = None,
        status: Annotated[IssueStatus, typer.Option("--status", help="Status filter for backlog items (default: open)")] = IssueStatus.open,
        group: Annotated[GroupMode, typer.Option("--group", help="Group output by item, file, or detector")] = GroupMode.item,
        output_format: Annotated[OutputFormat, typer.Option("--format", help="Output format (default: terminal)")] = OutputFormat.terminal,
        explain: Annotated[bool, typer.Option("--explain", help="Show ranking rationale")] = False,
        output: Annotated[str | None, typer.Option("--output", metavar="FILE", help="Write JSON/Markdown to file (with --format json|md)")] = None,
    ) -> None:
        _dispatch(
            ctx,
            "backlog",
            state=state,
            count=count,
            scope=scope,
            status=status,
            group=group,
            format=output_format,
            explain=explain,
            output=output,
        )

    @app.command("suppress", help="Permanently silence issues matching a pattern (false positives / accepted debt)", rich_help_panel="improve")
    def suppress(
        ctx: typer.Context,
        pattern: Annotated[str, typer.Argument(help="File path, glob, or detector::prefix. Use detector::*::rule to keep a suppression across file moves.")],
        attest: Annotated[str | None, typer.Option("--attest", help="Required anti-gaming attestation.")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
    ) -> None:
        _dispatch(ctx, "suppress", **_params(locals()))

    @app.command("exclude", help="Exclude paths from scanning entirely", rich_help_panel="improve")
    def exclude_cmd(
        ctx: typer.Context,
        pattern: Annotated[str, typer.Argument(help="Path pattern to exclude from scanning")],
    ) -> None:
        _dispatch(ctx, "exclude", **_params(locals()))

    @app.command("autofix", help="Auto-fix mechanical issues", rich_help_panel="improve")
    def autofix(
        ctx: typer.Context,
        fixer: Annotated[str, typer.Argument(help="What to fix")],
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would change without modifying files")] = False,
    ) -> None:
        _dispatch(ctx, "autofix", **_params(locals()))

    @app.command("detect", help="Run a single detector directly (bypass state)", epilog=f"detectors: {detector_help}", rich_help_panel="investigate")
    def detect(
        ctx: typer.Context,
        detector: Annotated[str, typer.Argument(help="Detector to run")],
        top: Annotated[int, typer.Option("--top", help="Max items to show (default: 20)")] = 20,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
        fix: Annotated[bool, typer.Option("--fix", help="Auto-fix detected issues (logs detector only)")] = False,
        category: Annotated[DetectCategory, typer.Option("--category", help="Filter unused by category")] = DetectCategory.all,
        threshold: Annotated[float | None, typer.Option("--threshold", help="LOC threshold (large) or similarity (dupes)")] = None,
        file: Annotated[str | None, typer.Option("--file", help="Show deps for specific file")] = None,
        lang_opt: Annotated[list[str] | None, typer.Option("--lang-opt", metavar="KEY=VALUE", help="Language runtime option override (repeatable)")] = None,
    ) -> None:
        _dispatch(
            ctx,
            "detect",
            detector=detector,
            top=top,
            path=path,
            json=json_output,
            fix=fix,
            category=category,
            threshold=threshold,
            file=file,
            lang_opt=lang_opt,
        )

    @app.command("tree", help="Annotated codebase tree (text)", rich_help_panel="investigate")
    def tree(
        ctx: typer.Context,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        depth: Annotated[int, typer.Option("--depth", help="Max depth (default: 2)")] = 2,
        focus: Annotated[str | None, typer.Option("--focus", help="Zoom into subdirectory (e.g. shared/components/MediaLightbox)")] = None,
        min_loc: Annotated[int, typer.Option("--min-loc", help="Hide items below this LOC")] = 0,
        sort: Annotated[TreeSort, typer.Option("--sort", help="Sort order (default: loc)")] = TreeSort.loc,
        detail: Annotated[bool, typer.Option("--detail", help="Show issue summaries per file")] = False,
    ) -> None:
        _dispatch(ctx, "tree", **_params(locals()))

    @app.command("viz", help="Generate interactive HTML treemap", rich_help_panel="investigate")
    def viz(
        ctx: typer.Context,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        output: Annotated[str | None, typer.Option("--output", help="Output file path")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
    ) -> None:
        _dispatch(ctx, "viz", **_params(locals()))

    @app.command("move", help="Move a file or directory and update all import references", rich_help_panel="improve")
    def move(
        ctx: typer.Context,
        source: Annotated[str, typer.Argument(help="File or directory to move (relative to project root)")],
        dest: Annotated[str, typer.Argument(help="Destination path (file or directory)")],
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without modifying files")] = False,
    ) -> None:
        _dispatch(ctx, "move", **_params(locals()))

    @app.command("review", help="Prepare or import holistic subjective review", rich_help_panel="improve")
    def review(
        ctx: typer.Context,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        prepare: Annotated[bool, typer.Option("--prepare", help="Prepare review data (output to query.json)")] = False,
        import_file: Annotated[str | None, typer.Option("--import", metavar="FILE", help="Import review issues from JSON file")] = None,
        validate_import_file: Annotated[str | None, typer.Option("--validate-import", metavar="FILE", help="Validate review import payload and selected trust mode without mutating state")] = None,
        allow_partial: Annotated[bool, typer.Option("--allow-partial", help="Allow partial review import when invalid issues are skipped")] = False,
        dimensions: Annotated[str | None, typer.Option("--dimensions", help="Comma-separated dimensions to evaluate")] = None,
        retrospective: Annotated[bool, typer.Option("--retrospective/--no-retrospective", help="Include historical review issue status/note context in the packet")] = True,
        retrospective_max_issues: Annotated[int, typer.Option("--retrospective-max-issues", help="Max recent historical issues to include in review context (default: 30)")] = 30,
        retrospective_max_batch_items: Annotated[int, typer.Option("--retrospective-max-batch-items", help="Max history items included per batch focus slice (default: 20)")] = 20,
        force_review_rerun: Annotated[bool, typer.Option("--force-review-rerun", help="Bypass the objective-plan-drained gate for review reruns")] = False,
        external_start: Annotated[bool, typer.Option("--external-start", help="Start a cloud external review session")] = False,
        external_submit: Annotated[bool, typer.Option("--external-submit", help="Submit external reviewer JSON via a started session")] = False,
        session_id: Annotated[str | None, typer.Option("--session-id", help="External review session id for --external-submit")] = None,
        external_runner: Annotated[ExternalRunner, typer.Option("--external-runner", help="External reviewer runner for --external-start (default: claude)")] = ExternalRunner.claude,
        session_ttl_hours: Annotated[int, typer.Option("--session-ttl-hours", help="External review session expiration in hours (default: 24)")] = 24,
        run_batches: Annotated[bool, typer.Option("--run-batches", help="Run holistic investigation batches with subagents and merge/import output")] = False,
        runner: Annotated[ReviewRunner, typer.Option("--runner", help="Subagent runner backend (default: codex)")] = ReviewRunner.codex,
        parallel: Annotated[bool, typer.Option("--parallel", help="Run selected batches in parallel")] = False,
        max_parallel_batches: Annotated[int, typer.Option("--max-parallel-batches", help="Max concurrent subagent batches when --parallel is enabled (default: 3)")] = 3,
        batch_timeout_seconds: Annotated[int, typer.Option("--batch-timeout-seconds", help="Per-batch runner timeout in seconds (default: 1200)")] = 1200,
        batch_max_retries: Annotated[int, typer.Option("--batch-max-retries", help="Retries per failed batch for transient runner/network errors (default: 1)")] = 1,
        batch_retry_backoff_seconds: Annotated[float, typer.Option("--batch-retry-backoff-seconds", help="Base backoff delay for transient batch retries in seconds (default: 2.0)")] = 2.0,
        batch_heartbeat_seconds: Annotated[float, typer.Option("--batch-heartbeat-seconds", help="Progress heartbeat interval during parallel batch runs in seconds (default: 15.0)")] = 15.0,
        batch_stall_warning_seconds: Annotated[int, typer.Option("--batch-stall-warning-seconds", help="Emit warning when a running batch exceeds this elapsed time")] = 0,
        batch_stall_kill_seconds: Annotated[int, typer.Option("--batch-stall-kill-seconds", help="Terminate a batch when output state is unchanged and streams are idle")] = 120,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Generate packet/prompts only (skip runner/import)")] = False,
        run_log_file: Annotated[str | None, typer.Option("--run-log-file", help="Optional explicit path for live run log output")] = None,
        packet: Annotated[str | None, typer.Option("--packet", help="Use an existing immutable packet JSON instead of preparing a new one")] = None,
        only_batches: Annotated[str | None, typer.Option("--only-batches", help="Comma-separated 1-based batch indexes to run (e.g. 1,3,5)")] = None,
        scan_after_import: Annotated[bool, typer.Option("--scan-after-import", help="Run `scan` after successful merged import")] = False,
        import_run_dir: Annotated[str | None, typer.Option("--import-run", metavar="DIR", help="Re-import results from a completed run directory")] = None,
        manual_override: Annotated[bool, typer.Option("--manual-override", help="Allow untrusted assessment score imports")] = False,
        attested_external: Annotated[bool, typer.Option("--attested-external", help="Accept external blind-run assessments as durable scores")] = False,
        attest: Annotated[str | None, typer.Option("--attest", help="Required with --manual-override or --attested-external")] = None,
        merge: Annotated[bool, typer.Option("--merge", help="Merge conceptually duplicate open review issues")] = False,
        similarity: Annotated[float, typer.Option("--similarity", help="Summary similarity threshold for merge (0-1, default: 0.8)")] = 0.8,
    ) -> None:
        _dispatch(ctx, "review", **_params(locals()))

    @app.command("langs", help="List all available language plugins with depth and tools", rich_help_panel="configure")
    def langs_cmd(ctx: typer.Context) -> None:
        _dispatch(ctx, "langs")

    @app.command("setup", help="Install desloppify skill globally for AI coding assistants", rich_help_panel="configure")
    def setup(
        ctx: typer.Context,
        interface: Annotated[Interface | None, typer.Option("--interface", help="Install for a specific interface only")] = None,
    ) -> None:
        _dispatch(ctx, "setup", **_params(locals()))

    @app.command("update-skill", help="Install or update the desloppify skill/agent document", rich_help_panel="configure")
    def update_skill(
        ctx: typer.Context,
        interface: Annotated[str | None, typer.Argument(help="Agent interface. Auto-detected on updates if omitted.")] = None,
    ) -> None:
        _dispatch(ctx, "update-skill", **_params(locals()))

    @plan_app.callback(invoke_without_command=True)
    def plan_root(
        ctx: typer.Context,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
        output: Annotated[str | None, typer.Option("--output", metavar="FILE", help="Write to file instead of stdout (refuses to overwrite existing files)")] = None,
    ) -> None:
        ctx.obj = {**_merged_obj(ctx), "state": state, "output": output}
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "plan", plan_action=None)

    @plan_app.command("show", help="Show plan metadata summary")
    def plan_show(ctx: typer.Context) -> None:
        _dispatch(ctx, "plan", plan_action="show")

    @plan_app.command("queue", help="Compact table of execution queue items")
    def plan_queue(
        ctx: typer.Context,
        top: Annotated[int, typer.Option("--top", help="Max items (default: 30, 0=all)")] = 30,
        cluster: Annotated[str | None, typer.Option("--cluster", metavar="NAME", help="Filter to a specific cluster")] = None,
        include_skipped: Annotated[bool, typer.Option("--include-skipped", help="Include skipped items at end")] = False,
        sort: Annotated[QueueSort, typer.Option("--sort", help="Sort order (default: priority)")] = QueueSort.priority,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="queue", **_params(locals()))

    @plan_app.command("reset", help="Reset plan to empty")
    def plan_reset(ctx: typer.Context) -> None:
        _dispatch(ctx, "plan", plan_action="reset")

    @plan_app.command("promote", help="Promote backlog issues or clusters into the queue")
    def plan_promote(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN", help="Issue ID(s), detector, file path, glob, or cluster name")],
        position: Annotated[Position, typer.Argument(help="Where to insert in the active queue (default: bottom)")] = Position.bottom,
        target: Annotated[str | None, typer.Option("-t", "--target", help="Required for before/after (issue ID or cluster name)")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="promote", **_params(locals()))

    @plan_app.command("reorder", help="Reposition issues in the queue")
    def plan_reorder(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN", help="Issue ID(s), detector, file path, glob, or cluster name")],
        position: Annotated[ReorderPosition, typer.Argument(help="Where to move")],
        target: Annotated[str | None, typer.Option("-t", "--target", help="Required for before/after and up/down")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="reorder", **_params(locals()))

    @plan_app.command("describe", help="Set augmented description")
    def plan_describe(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        text: Annotated[str, typer.Argument(help="Description text")],
    ) -> None:
        _dispatch(ctx, "plan", plan_action="describe", **_params(locals()))

    @plan_app.command("note", help="Set note on issues")
    def plan_note(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        text: Annotated[str, typer.Argument(help="Note text")],
    ) -> None:
        _dispatch(ctx, "plan", plan_action="note", **_params(locals()))

    @plan_app.command("skip", help="Skip issues: temporary (default), --permanent (wontfix), or --false-positive")
    def plan_skip(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        reason: Annotated[str | None, typer.Option("--reason", help="Why this is being skipped")] = None,
        review_after: Annotated[int | None, typer.Option("--review-after", metavar="N", help="Re-surface after N scans (temporary only)")] = None,
        permanent: Annotated[bool, typer.Option("--permanent", help="Mark as wontfix (score-affecting, requires --note and --attest)")] = False,
        false_positive: Annotated[bool, typer.Option("--false-positive", help="Mark as false positive (requires --attest)")] = False,
        note: Annotated[str | None, typer.Option("--note", help="Explanation (required for --permanent)")] = None,
        attest: Annotated[str | None, typer.Option("--attest", help="Attestation (required for --permanent and --false-positive)")] = None,
        confirm: Annotated[bool, typer.Option("--confirm", help="Required when skipping more than 5 items at once")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="skip", **_params(locals()))

    @plan_app.command("unskip", help="Bring skipped issues back to queue")
    def plan_unskip(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        force: Annotated[bool, typer.Option("--force", help="Also unskip protected items (permanent/false_positive with notes)")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="unskip", **_params(locals()))

    @plan_app.command("backlog", help="Move deferred items to backlog")
    def plan_backlog(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
    ) -> None:
        _dispatch(ctx, "plan", plan_action="backlog", **_params(locals()))

    @plan_app.command("reopen", help="Reopen resolved issues and move back to queue")
    def plan_reopen(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
    ) -> None:
        _dispatch(ctx, "plan", plan_action="reopen", **_params(locals()))

    @plan_app.command("resolve", help="Mark issues as fixed (shows score movement + next step)")
    def plan_resolve(
        ctx: typer.Context,
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        note: Annotated[str | None, typer.Option("--note", help="Explanation of the fix")] = None,
        attest: Annotated[str | None, typer.Option("--attest", help="Required anti-gaming attestation")] = None,
        confirm: Annotated[bool, typer.Option("--confirm", help="Auto-generate attestation from --note (requires --note)")] = False,
        force_resolve: Annotated[bool, typer.Option("--force-resolve", help="Bypass triage guardrail when new issues are pending triage")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="resolve", **_params(locals()))

    @plan_app.command("focus", help="Set or clear active cluster focus")
    def plan_focus(
        ctx: typer.Context,
        cluster_name: Annotated[str | None, typer.Argument(help="Cluster name")] = None,
        clear: Annotated[bool, typer.Option("--clear", help="Clear focus")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="focus", **_params(locals()))

    @plan_app.command("triage", help="Staged triage workflow for review issues")
    def plan_triage(
        ctx: typer.Context,
        stage: Annotated[TriageStage | None, typer.Option("--stage", help="Stage to record")] = None,
        report: Annotated[str | None, typer.Option("--report", help="Stage report text")] = None,
        report_file: Annotated[str | None, typer.Option("--report-file", help="Read stage report text from a file (--report takes precedence)")] = None,
        complete: Annotated[bool, typer.Option("--complete", help="Mark triage complete")] = False,
        strategy: Annotated[str | None, typer.Option("--strategy", help="Strategy summary (for --complete)")] = None,
        confirm_existing: Annotated[bool, typer.Option("--confirm-existing", help="Fast-track confirmation of existing plan")] = False,
        note: Annotated[str | None, typer.Option("--note", help="Note for --confirm-existing")] = None,
        start: Annotated[bool, typer.Option("--start", help="Manually start triage")] = False,
        confirm: Annotated[TriageStage | None, typer.Option("--confirm", help="Confirm a completed stage")] = None,
        attestation: Annotated[str | None, typer.Option("--attestation", help="Attestation text confirming stage review")] = None,
        confirmed: Annotated[str | None, typer.Option("--confirmed", help="Plan validation text for --confirm-existing")] = None,
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview mode")] = False,
        show_requirements: Annotated[bool, typer.Option("--show-requirements", help="Print validation requirements")] = False,
        run_stages: Annotated[bool, typer.Option("--run-stages", help="Preferred: run triage stages via the staged runner")] = False,
        runner: Annotated[TriageRunner, typer.Option("--runner", help="Runner for --run-stages (default: codex)")] = TriageRunner.codex,
        stage_timeout_seconds: Annotated[int, typer.Option("--stage-timeout-seconds", help="Per-stage timeout in seconds (default: 1800, codex only)")] = 1800,
        only_stages: Annotated[str | None, typer.Option("--only-stages", help="Comma-separated list of stages to run (default: all)")] = None,
        stage_prompt: Annotated[TriageStage | None, typer.Option("--stage-prompt", help="Print the current prompt for a stage")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="triage", **_params(locals()))

    @plan_app.command("scan-gate", help="Check or skip the scan requirement for workflow items")
    def plan_scan_gate(
        ctx: typer.Context,
        skip: Annotated[bool, typer.Option("--skip", help="Mark the scan requirement as satisfied without running a scan")] = False,
        note: Annotated[str | None, typer.Option("--note", help="Explanation for skipping")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="scan-gate", **_params(locals()))

    @plan_app.command("repair-state", help="Rebuild state.json from surviving plan metadata")
    def plan_repair_state(ctx: typer.Context) -> None:
        _dispatch(ctx, "plan", plan_action="repair-state")

    @cluster_app.command("create", help="Create a cluster")
    def cluster_create(
        ctx: typer.Context,
        cluster_name: Annotated[str, typer.Argument(help="Cluster name (slug)")],
        description: Annotated[str | None, typer.Option("--description", help="Cluster description")] = None,
        action: Annotated[str | None, typer.Option("--action", help="Primary action/command for this cluster")] = None,
        priority: Annotated[int | None, typer.Option("--priority", help="Priority (lower = higher priority)")] = None,
        steps_file: Annotated[str | None, typer.Option("--steps-file", "-f", help="Load steps from numbered-steps text file")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="create", **_params(locals()))

    @cluster_app.command("add", help="Add issues to a cluster")
    def cluster_add(
        ctx: typer.Context,
        cluster_name: Annotated[str, typer.Argument(help="Cluster name")],
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without saving")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="add", **_params(locals()))

    @cluster_app.command("remove", help="Remove issues from a cluster")
    def cluster_remove(
        ctx: typer.Context,
        cluster_name: Annotated[str, typer.Argument(help="Cluster name")],
        patterns: Annotated[list[str], typer.Argument(metavar="PATTERN")],
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without saving")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="remove", **_params(locals()))

    @cluster_app.command("delete", help="Delete a cluster")
    def cluster_delete(ctx: typer.Context, cluster_name: Annotated[str, typer.Argument(help="Cluster name")]) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="delete", **_params(locals()))

    @cluster_app.command("reorder", help="Reorder cluster(s) as a block")
    def cluster_reorder(
        ctx: typer.Context,
        cluster_names: Annotated[str, typer.Argument(help="Cluster name(s), comma-separated for multiple")],
        position: Annotated[ReorderPosition, typer.Argument(help="Where to move")],
        target: Annotated[str | None, typer.Argument(help="Target issue/cluster or integer offset")] = None,
        item_pattern: Annotated[str | None, typer.Option("--item", metavar="PATTERN", help="Move a specific item within the cluster")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="reorder", **_params(locals()))

    @cluster_app.command("show", help="Show cluster details and members")
    def cluster_show(ctx: typer.Context, cluster_name: Annotated[str, typer.Argument(help="Cluster name")]) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="show", **_params(locals()))

    @cluster_app.command("list", help="List all clusters")
    def cluster_list(
        ctx: typer.Context,
        verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show queue position, steps count, and description as a table")] = False,
        missing_steps: Annotated[bool, typer.Option("--missing-steps", help="Show only clusters that need action steps")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="list", **_params(locals()))

    @cluster_app.command("merge", help="Merge source cluster into target")
    def cluster_merge(
        ctx: typer.Context,
        source: Annotated[str, typer.Argument(help="Source cluster name (will be deleted)")],
        target: Annotated[str, typer.Argument(help="Target cluster name (receives issues)")],
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="merge", **_params(locals()))

    @cluster_app.command("update", cls=_ClusterUpdateCommand, help="Update cluster description and/or action steps")
    def cluster_update(
        ctx: typer.Context,
        cluster_name: Annotated[str, typer.Argument(help="Cluster name")],
        description: Annotated[str | None, typer.Option("--description", help="Cluster description")] = None,
        steps: Annotated[list[str] | None, typer.Option("--steps", metavar="STEP", hidden=True)] = None,
        steps_file: Annotated[str | None, typer.Option("--steps-file", "-f", help="Load steps from numbered-steps text file")] = None,
        add_step: Annotated[str | None, typer.Option("--add-step", metavar="TITLE", help="Append a single step")] = None,
        detail: Annotated[str | None, typer.Option("--detail", help="Body text for --add-step or --update-step")] = None,
        update_title: Annotated[str | None, typer.Option("--update-title", metavar="TITLE", help="Replacement title for --update-step")] = None,
        update_step: Annotated[int | None, typer.Option("--update-step", metavar="N", help="Update step N (1-based)")] = None,
        remove_step: Annotated[int | None, typer.Option("--remove-step", metavar="N", help="Remove step N (1-based)")] = None,
        done_step: Annotated[int | None, typer.Option("--done-step", metavar="N", help="Mark step N (1-based) as done")] = None,
        undone_step: Annotated[int | None, typer.Option("--undone-step", metavar="N", help="Mark step N (1-based) as not done")] = None,
        priority: Annotated[int | None, typer.Option("--priority", help="Set cluster priority (lower = higher priority)")] = None,
        effort: Annotated[Effort | None, typer.Option("--effort", help="Effort tag for --add-step or --update-step")] = None,
        depends_on: Annotated[list[str] | None, typer.Option("--depends-on", metavar="CLUSTER", help="Cluster(s) this cluster depends on")] = None,
        issue_refs: Annotated[list[str] | None, typer.Option("--issue-refs", metavar="REF", help="Issue refs for --add-step or --update-step")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="update", **_params(locals()))

    @cluster_app.command("export", help="Export cluster steps to editable format")
    def cluster_export(
        ctx: typer.Context,
        cluster_name: Annotated[str, typer.Argument(help="Cluster name")],
        export_format: Annotated[ExportFormat, typer.Option("--format", help="Output format (default: text)")] = ExportFormat.text,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="export", cluster_name=cluster_name, export_format=export_format)

    @cluster_app.command("import", help="Bulk create/update clusters from YAML")
    def cluster_import(
        ctx: typer.Context,
        file: Annotated[str, typer.Argument(help="YAML file path")],
        dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without saving")] = False,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="cluster", cluster_action="import", **_params(locals()))

    @commit_log_app.callback(invoke_without_command=True)
    def commit_log_root(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "plan", plan_action="commit-log", commit_log_action=None)

    @commit_log_app.command("record", cls=_CommitLogRecordCommand, help="Record a commit with resolved issues")
    def commit_log_record(
        ctx: typer.Context,
        sha: Annotated[str | None, typer.Option("--sha", help="Commit SHA (default: auto-detect HEAD)")] = None,
        branch: Annotated[str | None, typer.Option("--branch", help="Branch name (default: auto-detect)")] = None,
        note: Annotated[str | None, typer.Option("--note", help="Commit rationale/description")] = None,
        only: Annotated[list[str] | None, typer.Option("--only", metavar="PATTERN", help="Record only matching issues (glob patterns)")] = None,
    ) -> None:
        _dispatch(ctx, "plan", plan_action="commit-log", commit_log_action="record", **_params(locals()))

    @commit_log_app.command("history", help="Show commit records")
    def commit_log_history(ctx: typer.Context, top: Annotated[int, typer.Option("--top", help="Number of records to show (default: 10)")] = 10) -> None:
        _dispatch(ctx, "plan", plan_action="commit-log", commit_log_action="history", **_params(locals()))

    @commit_log_app.command("pr", help="Print PR body markdown (dry run)")
    def commit_log_pr(ctx: typer.Context) -> None:
        _dispatch(ctx, "plan", plan_action="commit-log", commit_log_action="pr")

    @policy_app.callback(invoke_without_command=True)
    def policy_root(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "plan", plan_action="policy", policy_action=None)

    @policy_app.command("add", help="Add a policy rule")
    def policy_add(ctx: typer.Context, rule_text: Annotated[str, typer.Argument(help="Rule text")]) -> None:
        _dispatch(ctx, "plan", plan_action="policy", policy_action="add", **_params(locals()))

    @policy_app.command("remove", help="Remove a policy rule by number")
    def policy_remove(ctx: typer.Context, rule_index: Annotated[int, typer.Argument(help="Rule number to remove")]) -> None:
        _dispatch(ctx, "plan", plan_action="policy", policy_action="remove", **_params(locals()))

    @policy_app.command("list", help="List project policy rules")
    def policy_list(ctx: typer.Context) -> None:
        _dispatch(ctx, "plan", plan_action="policy", policy_action="list")

    @config_app.callback(invoke_without_command=True)
    def config_root(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "config", config_action=None)

    @config_app.command("show", help="Show all config values")
    def config_show(ctx: typer.Context) -> None:
        _dispatch(ctx, "config", config_action="show")

    @config_app.command("set", help="Set a config value")
    def config_set(
        ctx: typer.Context,
        config_key: Annotated[str, typer.Argument(help="Config key name")],
        config_value: Annotated[str, typer.Argument(help="Value to set")],
    ) -> None:
        _dispatch(ctx, "config", config_action="set", **_params(locals()))

    @config_app.command("unset", help="Reset a config key to default")
    def config_unset(ctx: typer.Context, config_key: Annotated[str, typer.Argument(help="Config key name")]) -> None:
        _dispatch(ctx, "config", config_action="unset", **_params(locals()))

    @zone_app.callback(invoke_without_command=True)
    def zone_root(
        ctx: typer.Context,
        path: Annotated[str | None, typer.Option("--path", help="Project root directory (default: auto-detected)")] = None,
        state: Annotated[str | None, typer.Option("--state", help="Path to state file")] = None,
    ) -> None:
        ctx.obj = {**_merged_obj(ctx), "path": path, "state": state}
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "zone", zone_action=None)

    @zone_app.command("show", help="Show zone classifications for all files")
    def zone_show(ctx: typer.Context) -> None:
        _dispatch(ctx, "zone", zone_action="show")

    @zone_app.command("set", help="Override zone for a file")
    def zone_set(
        ctx: typer.Context,
        zone_path: Annotated[str, typer.Argument(help="Relative file path")],
        zone_value: Annotated[str, typer.Argument(help="Zone (production, test, config, generated, script, vendor)")],
    ) -> None:
        _dispatch(ctx, "zone", zone_action="set", **_params(locals()))

    @zone_app.command("clear", help="Remove zone override for a file")
    def zone_clear(ctx: typer.Context, zone_path: Annotated[str, typer.Argument(help="Relative file path")]) -> None:
        _dispatch(ctx, "zone", zone_action="clear", **_params(locals()))

    @directives_app.callback(invoke_without_command=True)
    def directives_root(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            _dispatch(ctx, "directives", directives_action=None)

    @directives_app.command("show", help="Show all configured directives")
    def directives_show(ctx: typer.Context) -> None:
        _dispatch(ctx, "directives", directives_action="show")

    @directives_app.command("set", help="Set a directive for a lifecycle phase")
    def directives_set(
        ctx: typer.Context,
        phase: Annotated[str, typer.Argument(help="Lifecycle phase name")],
        message: Annotated[str, typer.Argument(help="Message to show at this transition")],
    ) -> None:
        _dispatch(ctx, "directives", directives_action="set", **_params(locals()))

    @directives_app.command("unset", help="Remove a directive for a lifecycle phase")
    def directives_unset(ctx: typer.Context, phase: Annotated[str, typer.Argument(help="Lifecycle phase name")]) -> None:
        _dispatch(ctx, "directives", directives_action="unset", **_params(locals()))

    @dev_app.command("scaffold-lang", help="Generate a standardized language plugin scaffold")
    def dev_scaffold_lang(
        ctx: typer.Context,
        name: Annotated[str, typer.Argument(help="Language name (snake_case)")],
        extension: Annotated[list[str] | None, typer.Option("--extension", metavar="EXT", help="Source file extension (repeatable, e.g. --extension .go --extension .gomod)")] = None,
        marker: Annotated[list[str] | None, typer.Option("--marker", metavar="FILE", help="Project-root detection marker file (repeatable)")] = None,
        default_src: Annotated[str, typer.Option("--default-src", metavar="DIR", help="Default source directory for scans (default: src)")] = "src",
        force: Annotated[bool, typer.Option("--force", help="Overwrite existing scaffold files")] = False,
        wire_pyproject: Annotated[bool, typer.Option("--wire-pyproject/--no-wire-pyproject", help="Edit pyproject.toml testpaths array")] = True,
    ) -> None:
        _dispatch(ctx, "dev", dev_action="scaffold-lang", **_params(locals()))

    @dev_app.command("test-hermes", help="Test Hermes model switching (switch and switch back)")
    def dev_test_hermes(ctx: typer.Context) -> None:
        _dispatch(ctx, "dev", dev_action="test-hermes")

    plan_app.add_typer(cluster_app, name="cluster", help="Manage issue clusters")
    plan_app.add_typer(commit_log_app, name="commit-log", help="Track commits and resolved issues for PR updates")
    plan_app.add_typer(policy_app, name="policy", help="Manage project policy rules")
    app.add_typer(plan_app, name="plan", help="Living plan: generate, show, resolve, skip, cluster, triage", rich_help_panel="workflow")
    app.add_typer(config_app, name="config", help="Show/set/unset project configuration", rich_help_panel="configure")
    app.add_typer(zone_app, name="zone", help="Show/set/clear zone classifications", rich_help_panel="configure")
    app.add_typer(directives_app, name="directives", help="View/set agent directives for phase transitions", rich_help_panel="configure")
    app.add_typer(dev_app, name="dev", help="Developer utilities", rich_help_panel="configure")
    return app


__all__ = ["create_app"]
