"""``python -m bumpsmith`` -- run the migration loop against a repository.

The command exists so that the answer to "how do I use this" is one line rather
than a paragraph about which functions to compose. Everything it does is
:func:`bumpsmith.migrate.migrate`; what is here is argument parsing, a report
somebody can read, and an exit code that means what exit codes mean.

It defaults to running the suite in a subprocess on this machine, which is the
honest default for a tool you have just cloned: it is what a developer running
pytest themselves already accepts, and it needs nothing running. ``--sandbox``
is parsed and refused, with the reason, because the refusal is the useful part
-- see :func:`_no_sandbox`.
"""

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from bumpsmith.apply import RevertError
from bumpsmith.migrate import DEFAULT_STEP_LIMIT, Migration, Outcome, Step, Stop, migrate
from bumpsmith.report import page as report_page
from bumpsmith.run import DEFAULT_TIMEOUT, LocalRunner

DEFAULT_COMMAND = (sys.executable, "-m", "pytest", "-q")
"""The suite command when none is given.

``sys.executable`` rather than ``python`` because the interpreter that matters
is the one with the *target* pydantic installed, and a bare name would resolve
against ``PATH`` to whichever came first. It is only a default: the repository
being migrated usually has its own environment, and passing it after ``--`` is
how you say so.
"""

_HEADLINE = {
    Outcome.ALREADY_GREEN: "already green -- the suite passed before anything was changed",
    Outcome.MIGRATED: "migrated -- the edits were kept",
    Outcome.REVERTED: "reverted -- the edits did not make it pass and were taken back",
    Outcome.UNTOUCHED: "untouched -- nothing was applied",
}


def _no_sandbox() -> str:
    """Why ``--sandbox`` is refused rather than wired up.

    Kept as prose in one place because it is the most likely question a reader
    of this repository has, given what the harness is for.
    """
    return (
        "--sandbox is not available yet, and the reason is worth stating.\n"
        "\n"
        "bumpsmith.run.SandboxRunner does run a suite in the harness's sandbox, and\n"
        "proofs/sandbox.py demonstrates it against a real Daytona instance. But the\n"
        "sandbox is a different filesystem from this one. The loop writes its edits\n"
        "here and would verify them there, against code the edits never reached --\n"
        "so a green result would keep a change that nothing had tested.\n"
        "\n"
        "That is the same defect bumpsmith.run exists to prevent, one level up, and a\n"
        "flag that quietly did it would be worse than no flag. Carrying the edits\n"
        "across is the missing piece; until it is written and reviewed, this refuses.\n"
    )


class _Parser(argparse.ArgumentParser):
    """An ``ArgumentParser`` that explains the one mistake this command invites.

    The suite command is a positional, and a suite command almost always has
    flags of its own. argparse claims those for itself and reports
    ``unrecognized arguments``, which is true and useless: the fix is ``--``,
    and nothing in the message says so. Only that one message is amended, so a
    genuine typo still reads as a typo.
    """

    def error(self, message: str) -> NoReturn:
        if message.startswith("unrecognized arguments"):
            message += (
                "\n\nIf those belong to the suite command, put `--` in front of it:\n"
                "  python -m bumpsmith PATH -- <command>"
            )
        super().error(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="python -m bumpsmith",
        description=(
            "Run a repository's test suite, read the pydantic v1-to-v2 break it "
            "reports, fix it, and run again -- keeping the changes only if the "
            "suite ends green."
        ),
        epilog=(
            "The suite command goes after the path, usually behind `--`:\n"
            "  python -m bumpsmith ./fixtures/B --package emnify -- "
            "./venv/bin/python -m pytest -q"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", type=Path, help="the repository to migrate")
    parser.add_argument(
        "command",
        nargs="*",
        help=f"argv that runs the suite, given after `--` (default: {' '.join(DEFAULT_COMMAND)})",
    )
    parser.add_argument(
        "--package",
        action="append",
        metavar="NAME",
        help=(
            "a top-level package this repository owns; repeatable. Used only to tell "
            "its own missing module from an unmigrated third-party one. Omitting it "
            "makes that distinction unavailable, which is reported rather than guessed"
        ),
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_STEP_LIMIT,
        metavar="N",
        help=f"how many times the repository may be changed (default: {DEFAULT_STEP_LIMIT})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help=f"seconds allowed for each run of the suite (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--json",
        type=Path,
        metavar="PATH",
        dest="json_path",
        help="also write the full report here, as JSON",
    )
    parser.add_argument(
        "--html",
        type=Path,
        metavar="PATH",
        dest="html_path",
        help=(
            "also write the report here as a self-contained HTML page -- the same "
            "report `--json` writes, rendered for a person to read"
        ),
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="run the suite in the harness's sandbox (refused; run with it to see why)",
    )
    return parser


def _count(number: int, noun: str) -> str:
    """``1 site``, ``3 sites``. The report is read by people."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _describe_step(step: Step) -> list[str]:
    """One step as the lines a person reads, most important first."""
    lines = [f"step {step.number}  rc={step.run.returncode}  ({step.run.where})"]
    if step.failure is not None:
        message = step.failure.message or "no message captured"
        lines.append(f"  break    [{step.failure.break_class.name}] {message}")
        if step.failure.culprit is not None:
            lines.append(f"  at       {step.failure.culprit}")
    if step.rule is not None:
        lines.append(f"  rule     {step.rule.summary}")
    if step.scan is not None:
        files = len({match.path for match in step.scan.matches})
        note = (
            ""
            if step.scan.is_complete
            else f"; {_count(len(step.scan.unreadable), 'unreadable file')}"
        )
        lines.append(
            f"  scan     {_count(step.scan.count, 'site')} in {_count(files, 'file')}{note}"
        )
        for unreadable in step.scan.unreadable:
            lines.append(f"           ? {unreadable.path}: {unreadable.reason}")
    if step.plan is not None:
        skipped_note = "" if step.plan.is_complete else f"; {len(step.plan.skipped)} skipped"
        lines.append(
            f"  plan     {_count(step.plan.rewritten, 'site')} across "
            f"{_count(len(step.plan.edits), 'file')}{skipped_note}"
        )
        for skipped in step.plan.skipped:
            lines.append(f"           - {skipped}")
    if step.applied:
        lines.append("  applied")
    return lines


def report(migration: Migration) -> str:
    """The whole run as text.

    Built and returned rather than printed so that what the tests read is what a
    user sees. A test that captures stdout is checking the same string through a
    keyhole.
    """
    lines: list[str] = []
    for step in migration.steps:
        lines.extend(_describe_step(step))
        lines.append("")
    lines.append(_HEADLINE[migration.outcome])
    lines.append(f"  {migration.reason}")
    if not migration.complete:
        lines.append(
            "  NOT COMPLETE -- a file could not be read, or a matched site was left "
            "alone. Some of the v1 code these rules named is still there; the steps "
            "above say which."
        )
    if migration.applied:
        verb = "kept" if migration.kept else "taken back"
        lines.append(f"  {_count(migration.applied, 'change')}, {verb}")
    return "\n".join(lines)


NO_RESULT = frozenset({Stop.NOT_RUN, Stop.WRONG_PLACE})
"""The stops that produced no usable answer about the suite.

Both exit ``2`` rather than ``1``. A missing interpreter and a failing test are
not two grades of the same thing, and automation that cannot tell them apart
retries the wrong one -- which is the same distinction :mod:`bumpsmith.run`
exists to keep, carried out to the process's exit status.
"""


def _status(stop: Stop) -> int:
    if stop is Stop.GREEN:
        return 0
    if stop in NO_RESULT:
        return 2
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit code.

    ``0`` means the suite ends green, ``1`` that it does not, and ``2`` that the
    run never got far enough to say -- a bad invocation, a suite that could not
    be started, or one that ran somewhere it could not have been testing these
    edits. A red suite is a result; a missing interpreter is not.
    """
    args = _build_parser().parse_args(argv)

    if args.sandbox:
        print(_no_sandbox(), file=sys.stderr)
        return 2
    if not args.path.is_dir():
        print(f"{args.path} is not a directory.", file=sys.stderr)
        return 2
    if args.steps < 0:
        print(f"--steps cannot be negative; got {args.steps}.", file=sys.stderr)
        return 2
    # `float("inf")` and `float("nan")` both parse, and neither is <= 0. `inf`
    # would silently remove the per-run cap this flag exists to set, and `nan`
    # compares false against everything, so the timeout check inside
    # `subprocess` never fires either. Both are invocation errors, not settings.
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        print(
            f"--timeout must be a positive, finite number of seconds; got {args.timeout}.",
            file=sys.stderr,
        )
        return 2

    # Checked here, before the suite is ever run: the migration takes minutes,
    # and the failure it would otherwise end in is one that could have been seen
    # from the command line alone. Compared resolved, because `out.html` and
    # `./out.html` are the same file and a check on the spellings would miss it.
    if (
        args.json_path is not None
        and args.html_path is not None
        and args.json_path.resolve() == args.html_path.resolve()
    ):
        print(
            f"--json and --html both name {args.json_path.resolve()}.\n"
            "  They would be written in turn and only the second would survive, "
            "so this refuses rather than\n  reporting two reports written and "
            "leaving one.",
            file=sys.stderr,
        )
        return 2

    command = tuple(args.command) if args.command else DEFAULT_COMMAND
    root = args.path.resolve()

    print(f"repository  {root}")
    print(f"suite       {' '.join(command)}")
    print()
    # Flushed because the loop can take minutes and the header is the only sign
    # that anything is happening; a piped stdout would hold it until the end.
    sys.stdout.flush()

    try:
        migration = migrate(
            root,
            LocalRunner(timeout=args.timeout),
            command,
            project_packages=frozenset(args.package or ()),
            step_limit=args.steps,
        )
    except RevertError as exc:
        # The one failure that is not a result. The working tree is in a state
        # nobody chose, and the next thing anybody does should be to look at it.
        print(f"\nSTOP: edits were applied and could not be taken back.\n  {exc}", file=sys.stderr)
        print(f"  {root} needs looking at before anything else runs.", file=sys.stderr)
        return 2

    print(report(migration))

    # One payload, however many renderings. `--json` and `--html` are two ways of
    # reading the same run, and building them from one mapping is what stops them
    # becoming two descriptions of it that drift.
    payload: dict[str, object] = {
        "repository": str(root),
        "command": list(command),
        **migration.as_dict(),
    }

    written: list[tuple[Path, str]] = []
    if args.json_path is not None:
        written.append((args.json_path, json.dumps(payload, indent=2) + "\n"))
    if args.html_path is not None:
        written.append((args.html_path, report_page(payload, title=f"bumpsmith — {root.name}")))

    for path, text in written:
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            sys.stdout.flush()
            print(f"could not write {path}: {exc}", file=sys.stderr)
            return 2
        print(f"\nreport written to {path}")

    return _status(migration.stop)


if __name__ == "__main__":
    raise SystemExit(main())
