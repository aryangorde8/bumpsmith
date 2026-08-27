"""Migrate several real repositories at once, each in a sandbox of its own.

This is the third of the hackathon's harness surfaces and the one that is
hardest to fake: not "the agent can call a model", but *how many agents are
running right now, against what, and how do you know*. Every subject goes out
at the same time, each one gets its own TrueForge session and therefore its own
Daytona sandbox, and each sandbox runs an entire ``bumpsmith`` migration --
clone, read the failure, write the rule, edit, re-run the suite, keep it only if
green. How many subjects there are is a question for ``EXTRAS``, which is the
only place a measured environment exists; today that is two real ones and the
unreachable one below.

Nothing about the loop changes when it runs there. It is the same package,
installed from this repository, and it does not know it is in a sandbox.

What makes this a proof rather than a demonstration
---------------------------------------------------
Three things, and the third is the only one that is hard.

*A negative control.* Fixture C is already on pydantic v2. An agent that
"migrates" it is broken, and an orchestrator that reports every subject green
without noticing that one of them was green on arrival is reporting a number
rather than a result. C has to come back ``already-green`` **and** with its
files byte-for-byte unchanged, and both are checked -- the report and the disk
are separate claims, and a report is not a filesystem.

*An unreachable subject.* One job is pointed at a port nobody is listening on.
It exists because "three subjects, none migrated" and "three sandboxes, none
reached" are the same number and opposite facts, and the only way to show a
report keeps them apart is to make one happen.

*A count nobody accumulated.* Every figure printed below is derived from the
attempts by :mod:`bumpsmith.fanout`, which is also what writes the JSON. There
is no counter in this file to disagree with it.

Needs a running TrueForge with a sandbox provider, and needs this repository to
be public -- each sandbox installs the package from it. See ``proofs/README.md``.
"""

import argparse
import json
import shlex
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from bumpsmith.fanout import DEFAULT_TIMEOUT, Fanout, Job, Unreached, fan_out
from bumpsmith.fixtures import load_manifest
from bumpsmith.migrate import Outcome
from bumpsmith.remote import (
    DEFAULT_MODEL,
    WORKSPACE,
    Recipe,
    Reported,
    SandboxJob,
    SubjectError,
    jobs_for,
)
from bumpsmith.run import RunError
from bumpsmith.trueforge import TransportError

CONTROL = "C"
"""The fixture that is already migrated. Named so the checks below can say why."""

END_OF_STATUS = "END_OF_STATUS"
"""Printed after `git status`, so an empty answer is told apart from no answer.

A clean tree and a command that produced nothing both print nothing, and only
one of them is evidence."""

UNREACHABLE_URL = "http://127.0.0.1:9/api/v1"
"""Port 9 is discard. Nothing listens, so the connection is refused rather than
hanging -- an unreachable sandbox, not a slow one, which is the fact this
subject is here to produce."""

# What each subject needs beyond what `fixtures.toml` already records. The suite
# arguments and the pinned commit are *not* here: they live in the manifest, and
# a second copy of them here would be a second place for them to be true.
# What each subject needs beyond what `fixtures.toml` already records. The suite
# arguments and the pinned commit are *not* here: they live in the manifest, and
# a second copy of them here would be a second place for them to be true.
#
# Every list below was measured in a sandbox on 27 Aug 2026 rather than guessed,
# and each one is a fixture's own test environment, not a common denominator.
# Guessing produces a red suite that has nothing to do with pydantic, which the
# loop reports, correctly and uselessly, as a break it cannot classify.
EXTRAS: dict[str, dict[str, object]] = {
    "B": {
        "package": "emnify",
        # Its own metadata pins pydantic <2, so its dependencies stay out --
        # installing them would undo the move to v2 and with it the break.
        "install": ("pydantic>=2", "vcrpy", "pytest"),
        "with_dependencies": False,
    },
    "C": {
        # C's dev dependencies live in a Poetry group, which `pip install` does
        # not see; without them three test modules fail at collection. Its own
        # pyproject also sets `addopts = --cov=...`, so pytest exits 4 with no
        # pytest-cov -- an invocation failure the loop would read as a break.
        "install": (
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "pytest-asyncio>=0.20,<0.21",
            "fs",
            "responses",
            "pytest-httpx>=0.20",
            "Faker",
        ),
        # Already on v2, so its declared list is what makes the suite runnable
        # rather than what undoes the setup.
        "with_dependencies": True,
    },
}


def _recipes(manifest: Path, ids: Sequence[str]) -> list[Recipe]:
    fixtures = load_manifest(manifest)
    missing = [i for i in ids if i not in fixtures]
    if missing:
        raise SystemExit(f"{manifest} has no fixture(s) named {', '.join(missing)}")
    unmeasured = [i for i in ids if i not in EXTRAS]
    if unmeasured:
        # Said rather than defaulted. A plausible environment guessed for a
        # fixture nobody has run produces a red suite about the environment, and
        # the loop would classify it as a migration break with total sincerity.
        raise SystemExit(
            f"no measured environment for fixture(s) {', '.join(unmeasured)}. "
            f"Add one to EXTRAS after running it, rather than letting this guess."
        )
    return [Recipe(fixture=fixtures[i], **EXTRAS[i]) for i in ids]  # type: ignore[arg-type]


class Unreachable:
    """A subject whose sandbox never comes up.

    Deliberately a real :class:`~bumpsmith.remote.SandboxJob` pointed somewhere
    empty, rather than a stub that raises. A stub would prove that
    :func:`~bumpsmith.fanout.fan_out` records an exception, which is already
    tested; this proves the thing above it -- that a sandbox failing to answer
    arrives as a subject nobody reached and not as a repository with nothing to
    migrate.
    """

    def __init__(self, recipe: Recipe, manifest: str) -> None:
        self._job = SandboxJob(recipe, manifest=manifest, base_url=UNREACHABLE_URL)

    @property
    def subject(self) -> str:
        return f"{self._job.subject}-unreachable"

    def __call__(self) -> Reported:
        return self._job()


def _control_is_untouched(job: SandboxJob) -> tuple[bool, dict[str, object]]:
    """Ask the control's own sandbox whether its files changed.

    The report already says ``already-green``, and this asks the disk instead,
    because those are two claims and only one of them is about a filesystem. A
    loop that edited the control and then reverted it perfectly would produce
    the same report as one that never touched it.

    It has to be *that* sandbox. An earlier version of this function built its
    own `SandboxExec`, which opens a new session and therefore a new, empty
    sandbox -- where the control checkout does not exist at all, and where
    "nothing changed" would be answered by a filesystem that never held the
    subject. The docstring said so at the time and the code did the opposite;
    Qodo caught it (finding 119).

    Nothing in the porcelain output is dropped. An earlier version filtered
    every ``??`` line, which let an agent that *added* a file pass a check whose
    whole claim is that the files are unchanged. Untracked paths are reported as
    evidence either way, and an untracked Python file fails outright -- a
    coverage report is what running the suite leaves behind, and a new module is
    not.
    """
    subject = f"{job.workspace}/fixtures/{job.subject}"
    command = f"cd {shlex.quote(subject)} && git status --porcelain && echo {END_OF_STATUS}"
    try:
        seen = job.exec_in_its_sandbox(command, "/tmp")  # noqa: S108
    except (RunError, TransportError, SubjectError) as exc:
        return False, {"asked": False, "why": f"the sandbox could not be asked: {exc}"}
    if seen.returncode != 0 or END_OF_STATUS not in seen.output:
        return False, {"asked": False, "why": f"git status did not complete (rc={seen.returncode})"}

    lines = [
        line.strip()
        for line in seen.output.splitlines()
        if line.strip() and line.strip() != END_OF_STATUS
    ]
    tracked = [line for line in lines if not line.startswith("??")]
    untracked = [line[2:].strip() for line in lines if line.startswith("??")]
    added_source = [path for path in untracked if path.endswith(".py")]

    evidence: dict[str, object] = {
        "asked": True,
        "session": job.session_id(),
        "tracked_changes": tracked,
        "untracked": untracked,
        "added_python_files": added_source,
    }
    if tracked:
        evidence["why"] = f"{len(tracked)} tracked file(s) differ: {tracked[:3]}"
        return False, evidence
    if added_source:
        evidence["why"] = f"the migration left new Python file(s) behind: {added_source}"
        return False, evidence
    evidence["why"] = "no tracked file differs" + (
        f"; {len(untracked)} untracked artefact(s) from running the suite" if untracked else ""
    )
    return True, evidence


def _describe(result: Fanout) -> None:
    for attempt in result.attempts:
        if isinstance(attempt.result, Unreached):
            still = " (may still be running)" if attempt.result.still_running else ""
            print(f"  {attempt.subject:18} UNREACHED  {attempt.result.reason}{still}")
        elif isinstance(attempt.result, Reported):
            # Narrowed on purpose. `fan_out` hands back a `Verdict`, which
            # promises an outcome and nothing else -- the orchestrator is not
            # allowed to know more than that. This file *does* know: it built
            # the jobs, and they return reports. Reaching for `steps` through
            # the protocol instead would be widening what an orchestrator may
            # see, from a script that only wanted to print something.
            verdict = attempt.result
            print(
                f"  {attempt.subject:18} {verdict.outcome.value:14} "
                f"{verdict.applied} change(s), {len(verdict.steps)} step(s)"
            )
            print(f"  {'':18} {verdict.reason[:96]}")
        else:  # pragma: no cover -- a job in this file returning something else
            print(f"  {attempt.subject:18} {attempt.result!r}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python proofs/sandbox_fanout.py",
        description="Migrate several repositories at once, each in its own sandbox.",
    )
    parser.add_argument("--base-url", default=None, help="TrueForge API root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model to run the sessions as")
    parser.add_argument(
        "--subjects",
        default="B,C",
        help="fixture ids to migrate, comma separated (default: B,C)",
    )
    parser.add_argument(
        "--manifest", type=Path, default=Path("fixtures.toml"), help="the fixture manifest"
    )
    parser.add_argument("--workers", type=int, default=4, help="how many sandboxes at once")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds to wait")
    parser.add_argument(
        "--out", type=Path, default=Path("sandbox_fanout.json"), help="where to write the evidence"
    )
    args = parser.parse_args(argv)

    ids = [part.strip() for part in args.subjects.split(",") if part.strip()]
    if CONTROL not in ids:
        print(
            f"{CONTROL} is the negative control -- the fixture that is already on pydantic v2.\n"
            f"A fan-out without it cannot tell an agent that migrates from one that edits\n"
            f"everything it is pointed at. Add it to --subjects.",
            file=sys.stderr,
        )
        return 2

    try:
        recipes = _recipes(args.manifest, ids)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    # The manifest is read from inside each sandbox, out of the clone it makes
    # of this repository -- so the path is that clone's, not this machine's.
    remote_manifest = f"{WORKSPACE}/bumpsmith/fixtures.toml"
    jobs = list(
        jobs_for(recipes, manifest=remote_manifest, base_url=args.base_url, model=args.model)
    )
    everything: list[Job] = [*jobs, Unreachable(recipes[0], remote_manifest)]

    print(
        f"fanning out over {len(everything)} subjects "
        f"({', '.join(j.subject for j in everything)}) on {args.workers} workers\n"
        f"each one gets its own TrueForge session, and therefore its own sandbox\n",
        flush=True,
    )
    started = time.monotonic()
    result = fan_out(everything, workers=args.workers, timeout=args.timeout)
    wall = time.monotonic() - started

    print(f"\n{wall:.1f}s wall clock\n")
    _describe(result)
    print(
        f"\nreached {len(result.reached)}/{len(result.attempts)}, "
        f"complete={result.complete}, "
        f"migrated={result.counting(Outcome.MIGRATED)}, "
        f"already green={result.counting(Outcome.ALREADY_GREEN)}, "
        f"reverted={result.counting(Outcome.REVERTED)}",
        flush=True,
    )

    control = next(a for a in result.attempts if a.subject == CONTROL)
    # The job object, not a fresh one: the question is about the sandbox this
    # subject was migrated in, and only that job knows which session that was.
    control_job = next(j for j in jobs if j.subject == CONTROL)
    untouched, evidence = _control_is_untouched(control_job)
    print(f"\ncontrol {CONTROL}: report says {control.outcome}; disk says {evidence['why']}")
    left_behind = evidence.get("untracked")
    if isinstance(left_behind, list):
        for path in left_behind:
            print(f"  untracked: {path}")

    args.out.write_text(
        json.dumps(
            {
                "orchestrator": "bumpsmith.fanout.fan_out",
                "job": "bumpsmith.remote.SandboxJob",
                "model": args.model,
                "workers": args.workers,
                "wall_seconds": round(wall, 2),
                "control": {
                    "subject": CONTROL,
                    "outcome": None if control.outcome is None else control.outcome.value,
                    "files_unchanged": untouched,
                    "checked_on_disk": evidence,
                },
                "fanout": result.as_dict(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"evidence written to {args.out}")

    # Everything below is a reason this run proves less than it looks like it
    # does. Each one is checked separately, because "it finished" is not one of
    # them and would happily stand in for all of them.
    problems = []
    if not any(isinstance(a.result, Unreached) for a in result.attempts):
        problems.append(
            "the unreachable subject was reached, so nothing here shows that an "
            "unreached subject is told apart from one with nothing to migrate"
        )
    if control.outcome is not Outcome.ALREADY_GREEN:
        problems.append(
            f"the control {CONTROL} came back {control.outcome}, not already-green; "
            f"it is on pydantic v2 and there was nothing to migrate"
        )
    if not untouched:
        problems.append(f"the control's files changed in the sandbox: {evidence['why']}")
    reached_real = [a for a in result.attempts if a.ran and not a.subject.endswith("-unreachable")]
    if len(reached_real) != len(recipes):
        problems.append(
            f"{len(reached_real)} of {len(recipes)} real subjects were reached; "
            f"a fan-out that reached fewer proves less about running several at once"
        )
    if problems:
        print("\nthis run does not prove what it set out to:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
