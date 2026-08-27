"""Run a whole migration somewhere else, and read the verdict back honestly.

:mod:`bumpsmith.fanout` needs jobs. This module makes one kind: a job that runs
the entire loop inside the harness's sandbox -- clone, edit, run the suite,
revert if it did not go green -- and brings back what happened.

Why the whole loop goes over there
----------------------------------
``python -m bumpsmith --sandbox`` refuses, and the refusal is right: it would
edit a checkout here and run the suite there, so the suite would answer a
question about code the edits never reached. The way past that is not to relax
the rule but to stop splitting. The package installs from its own public
repository in about ten seconds, so the sandbox can hold the agent as easily as
it can hold the tests, and then editing and testing happen on one filesystem
again -- just not this one. Nothing about the loop changes. It does not know it
is in a sandbox, and :class:`~bumpsmith.run.LocalRunner` is the correct runner
there, because the tree really is local to the process running it.

What comes back is a report, and a report is not a migration
------------------------------------------------------------
The sandbox is gone by the time anybody reads the result. What survives is the
JSON that ``--json`` wrote: a *summary* of the run, not the objects the loop
produced. :class:`~bumpsmith.migrate.Migration` stores three things and derives
everything else, precisely so a conclusion can never disagree with the evidence
for it. A report cannot honour that -- its evidence stayed in the sandbox -- so
rebuilding one would mean fabricating the :class:`~bumpsmith.rules.Scan` and
:class:`~bumpsmith.rewrite.Plan` objects that ``complete`` is derived from, and
handing back something typed as a ``Migration`` that was assembled here out of a
summary. It would be indistinguishable from the real thing to every caller and
to every reviewer.

So this module returns a :class:`Reported` instead, which says in its type what
it is. It stores what a report actually witnesses and derives the rest by the
same rules :class:`~bumpsmith.migrate.Migration` uses -- literally the same
function, see :func:`~bumpsmith.migrate.outcome_of` -- so the two agree by
construction rather than by having been written to match.

The redundancy in the report is a checksum, not a second opinion
---------------------------------------------------------------
``outcome``, ``kept`` and ``applied`` are all *derived* on a ``Migration`` and
all *written down* in its report. That is a courtesy to whoever reads the JSON,
and it is a hazard to anything that parses it: taking a stated ``outcome`` at
face value means believing a conclusion instead of checking it, and a report
that was truncated, hand-edited, or produced by a different version of this
package would be believed too.

:func:`read_report` therefore derives every derivable field from the steps and
the stop reason, and then compares its answer to the one the file states. A
disagreement is not repaired and not preferred in either direction -- it raises.
A file whose summary contradicts its own steps is not evidence about a
repository, whichever half happens to be right.

What this module refuses to do
------------------------------
**It will not turn a report it could not read into a migration that found
nothing to do.** Every refusal below raises, and :func:`~bumpsmith.fanout.fan_out`
turns a raising job into an :class:`~bumpsmith.fanout.Unreached` -- a subject
with no verdict, which is exactly what an unreadable report leaves behind. The
alternative is a default: a missing ``steps`` key read as no steps, a missing
``stop`` read as green, and a subject nobody ever migrated reported as a
subject that needed no migration.
"""

from __future__ import annotations

import json
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import final

from bumpsmith.fixtures import Fixture
from bumpsmith.migrate import Outcome, Stop, outcome_of
from bumpsmith.run import Completed, RunError, SandboxRunner
from bumpsmith.trueforge import Client, SandboxExec, TransportError

DEFAULT_MODEL = "bedrock-mantle/qwen-3-coder-480b"

# A whole migration is one `exec`, and `exec` is a tool call inside a turn that
# has to be polled to completion. The client's own default is 300s, which is
# generous for a shell command and not necessarily generous for a cold sandbox
# that clones a repository, installs a dependency tree and then runs a suite
# once per break. Fixture B measured 26s end to end on 27 Aug 2026; fixture C
# has fourteen times as many tests. This is the margin, not the expectation.
DEFAULT_POLL_LIMIT = 1500.0

# Where a job works inside its own sandbox. A constant rather than a parameter
# because nothing shares a sandbox: every job creates its own session, so two
# jobs cannot collide on this path however many run at once.
WORKSPACE = "/tmp/bumpsmith-subject"  # noqa: S108 -- a path in the sandbox, not on this machine

REPO_URL = "https://github.com/aryangorde8/bumpsmith"

# Every script below changes directory as its first act, so this is only ever
# somewhere for the shell to start. It is named for that rather than for `/tmp`,
# so nobody later reads it as the place any of this happens.
_ANYWHERE = Path("/tmp")  # noqa: S108 -- a path in the sandbox, not on this machine


class ReportError(Exception):
    """A report could not be read as a verdict about a repository."""


@final
@dataclass(frozen=True, slots=True)
class ReportedStep:
    """One step of a migration, as its report recorded it.

    Carries what is needed to derive the migration's completeness and to label
    the step for a reader. It is deliberately not a
    :class:`~bumpsmith.migrate.Step`: there is no run, no rule object and no
    scan behind it, and a type that claimed otherwise would invite callers to
    reach for parts that were never brought back.
    """

    number: int
    break_class: str | None
    rule: str | None
    applied: bool

    scanned: bool
    """Whether this step got as far as scanning for sites."""

    unreadable: tuple[str, ...]
    """Candidate files the scan could not read. Empty when it read them all."""

    planned: bool
    """Whether this step got as far as planning edits."""

    skipped: tuple[str, ...]
    """Matched sites the rewriter declined to change. Empty when it changed all."""

    @property
    def is_complete(self) -> bool:
        """Whether every site this step's rule named was accounted for.

        The same two questions :class:`~bumpsmith.migrate.Migration` asks of a
        real step -- did the scan read everything, did the plan rewrite
        everything -- asked of the record instead of the objects. A step that
        never scanned is not incomplete; it never claimed a reach to fall short
        of.
        """
        if self.scanned and self.unreadable:
            return False
        return not (self.planned and self.skipped)


@final
@dataclass(frozen=True, slots=True)
class Reported:
    """A migration's verdict, read back from the report it wrote somewhere else.

    Stores exactly what :class:`~bumpsmith.migrate.Migration` stores -- the
    steps, why the loop stopped, and what it said about that -- and derives
    exactly what a ``Migration`` derives, so a caller can ask either of them the
    same questions and cannot ask this one for evidence that stayed behind.

    Satisfies :class:`~bumpsmith.fanout.Verdict`, which is the only thing
    :mod:`bumpsmith.fanout` ever wanted from either type.
    """

    steps: tuple[ReportedStep, ...]
    stop: Stop
    reason: str

    @property
    def applied(self) -> int:
        """How many steps wrote to disk."""
        return sum(1 for step in self.steps if step.applied)

    @property
    def outcome(self) -> Outcome:
        """What became of the repository, by the same rule the loop uses."""
        return outcome_of(self.stop, self.applied)

    @property
    def complete(self) -> bool:
        """Whether every site the rules matched was accounted for."""
        return all(step.is_complete for step in self.steps)

    @property
    def kept(self) -> bool:
        """Whether the edits were still on disk when the report was written."""
        return self.outcome is Outcome.MIGRATED

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail."""
        return {
            "outcome": self.outcome.value,
            "stop": self.stop.value,
            "reason": self.reason,
            "applied": self.applied,
            "kept": self.kept,
            "complete": self.complete,
            "steps": [
                {
                    "step": step.number,
                    "break_class": step.break_class,
                    "rule": step.rule,
                    "applied": step.applied,
                    "complete": step.is_complete,
                }
                for step in self.steps
            ],
        }


def _require(body: Mapping[str, object], key: str) -> object:
    if key not in body:
        raise ReportError(f"the report has no {key!r}")
    return body[key]


def _strings(value: object, key: str) -> tuple[str, ...]:
    """A list of paths from the report, however the report chose to carry them.

    ``unreadable`` holds objects with a path and a reason; ``skipped`` holds
    bare strings. Both are read here rather than in two places, because what
    this module needs from either is the same: whether it is empty, and what to
    name if it is not.
    """
    if not isinstance(value, list):
        raise ReportError(f"{key!r} is {type(value).__name__}, not a list")
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, Mapping) and isinstance(item.get("path"), str):
            path = item["path"]
            reason = item.get("reason")
            out.append(f"{path}: {reason}" if isinstance(reason, str) else str(path))
        else:
            raise ReportError(f"{key!r} holds {item!r}, which names no path")
    return tuple(out)


def _read_step(raw: object, index: int) -> ReportedStep:
    where = f"step {index + 1}"
    if not isinstance(raw, Mapping):
        raise ReportError(f"{where} is {type(raw).__name__}, not an object")

    number = raw.get("step")
    if isinstance(number, bool) or not isinstance(number, int):
        raise ReportError(f"{where} has step number {number!r}, which is not a number")

    applied = raw.get("applied")
    if not isinstance(applied, bool):
        # Not coerced. A step's `applied` is the difference between a tree that
        # was written to and one that was not, and reading a truthy string as
        # "yes" is how a report about an untouched repository becomes a report
        # about a migrated one.
        raise ReportError(f"{where} has applied={applied!r}, which is not true or false")

    # `sites` is null exactly when there was no scan, and `rewritten` is null
    # exactly when there was no plan. Both are read as presence rather than as
    # counts, because the count is not what completeness turns on.
    scanned = raw.get("sites") is not None
    planned = raw.get("rewritten") is not None

    unreadable = _strings(raw.get("unreadable", []), f"{where} unreadable")
    skipped = _strings(raw.get("skipped", []), f"{where} skipped")

    # The report states `scan_complete` as well as listing what was unreadable.
    # Checked against each other rather than one being chosen: they are the same
    # fact written twice, and a file where they differ is not describing a scan
    # this module can report on.
    stated = raw.get("scan_complete")
    if scanned:
        if not isinstance(stated, bool):
            raise ReportError(f"{where} scanned and has scan_complete={stated!r}")
        if stated is bool(unreadable):
            raise ReportError(
                f"{where} says scan_complete={stated} and lists "
                f"{len(unreadable)} unreadable file(s); the report disagrees with itself"
            )
    elif stated is not None:
        raise ReportError(f"{where} did not scan and still has scan_complete={stated!r}")

    return ReportedStep(
        number=number,
        break_class=_optional_str(raw.get("break_class"), f"{where} break_class"),
        rule=_optional_str(raw.get("rule"), f"{where} rule"),
        applied=applied,
        scanned=scanned,
        unreadable=unreadable,
        planned=planned,
        skipped=skipped,
    )


def _optional_str(value: object, what: str) -> str | None:
    if value is None or isinstance(value, str):
        return value
    raise ReportError(f"{what} is {type(value).__name__}, not text")


def read_report(text: str) -> Reported:
    """Read one ``--json`` report as a verdict, or refuse to.

    Refuses on anything it cannot account for. The check worth naming is the
    last one: every field the report states *and* this module can derive is
    derived first and compared. A report is the only thing that comes back from
    a sandbox, so a report that contradicts itself is the only warning anybody
    is going to get.
    """
    try:
        raw = json.loads(text)
    except ValueError as exc:
        raise ReportError(f"the report is not JSON ({exc})") from exc
    if not isinstance(raw, Mapping):
        raise ReportError(f"the report is {type(raw).__name__}, not an object")

    stop_value = _require(raw, "stop")
    try:
        stop = Stop(stop_value)
    except ValueError as exc:
        # A stop reason this version does not have is version drift, not a
        # migration. Guessing a nearby member would put a verdict behind a word
        # that meant something else when it was written.
        raise ReportError(f"{stop_value!r} is not a stop reason this package knows") from exc

    reason = _require(raw, "reason")
    if not isinstance(reason, str):
        raise ReportError(f"the report's reason is {type(reason).__name__}, not text")

    raw_steps = _require(raw, "steps")
    if not isinstance(raw_steps, list):
        raise ReportError(f"the report's steps are {type(raw_steps).__name__}, not a list")

    reported = Reported(
        steps=tuple(_read_step(step, i) for i, step in enumerate(raw_steps)),
        stop=stop,
        reason=reason,
    )
    _agrees(raw, reported)
    return reported


def _agrees(raw: Mapping[str, object], reported: Reported) -> None:
    """Check the report's own summary against what its steps actually say.

    Pure, and separate from the parsing, because this is the check that has no
    other way of being noticed. Everything else in this module fails loudly on
    a malformed file; a summary that quietly disagrees with its steps parses
    perfectly and means something false.
    """
    for key, derived in (
        ("outcome", reported.outcome.value),
        ("applied", reported.applied),
        ("kept", reported.kept),
        ("complete", reported.complete),
    ):
        if key not in raw:
            # An older or newer report may not state it. Derived is the answer
            # either way; only a *stated* value can contradict one.
            continue
        stated = raw[key]
        if stated != derived or isinstance(stated, bool) is not isinstance(derived, bool):
            raise ReportError(
                f"the report says {key}={stated!r} and its steps say {derived!r}; "
                f"a report that disagrees with itself is not evidence about a repository"
            )


class SubjectError(Exception):
    """A subject could not be prepared, so nothing was migrated."""


@final
@dataclass(frozen=True, slots=True)
class Recipe:
    """What one subject needs beyond what its manifest already records.

    ``fixture`` is the manifest entry, and it is held rather than copied from:
    the suite arguments, the pinned commit and the upstream URL all live there,
    and a recipe that restated any of them would be a second place for them to
    be true. The only thing here that ``fixtures.toml`` does not know is how to
    move this subject's environment to pydantic v2 -- which is per-subject,
    because the fixtures genuinely differ. One needs a recording library,
    another pins a client at a major version. A common denominator guessed here
    would produce a red suite that has nothing to do with pydantic, and the loop
    would faithfully report it as a break it could not classify.
    """

    fixture: Fixture
    package: str | None = None
    install: tuple[str, ...] = ()

    with_dependencies: bool = False
    """Whether to install the subject's own declared dependencies as well.

    Off by default, and the default is the interesting half. A project written
    for pydantic v1 pins pydantic below 2 in its own metadata, so installing its
    dependency list *after* moving the environment to v2 quietly moves it back
    -- and the suite then passes, the loop reports nothing to migrate, and the
    break this fixture exists to demonstrate never happens. Fixture B is exactly
    that case.

    On for a subject already written against v2, where the declared list is what
    makes the suite runnable at all rather than what undoes the setup. Fixture C
    is that case, and its baseline of 347 does not reproduce without it.
    """


def setup_script(recipe: Recipe, *, manifest: str, workspace: str = WORKSPACE) -> str:
    """The shell that puts one subject, and this package, inside a sandbox.

    Written as one command because every ``exec`` is a whole model turn -- five
    commands is five turns and five chances for a turn to be lost, for a saving
    of nothing. ``&&`` throughout, so the first thing that fails is the last
    thing that runs: a clone that failed followed by an install that succeeded
    would otherwise report a ready workspace with no repository in it.

    The package is installed from its own public repository rather than copied
    in, because the harness offers no way to put a file into a sandbox -- there
    is a download endpoint and no upload. The clone also carries
    ``fixtures.toml``, which is a repository file and not package data, so one
    clone answers both needs. A probe that installed only the wheel found that
    out by failing to describe any fixture at all.

    ``rm -rf`` first, and it matters more than it looks. Every later step reads
    what an earlier one wrote, and the last thing this job does is read a report
    out of this directory. A workspace left over from a previous attempt could
    hand back that attempt's report as this one's verdict, and it would parse
    perfectly.
    """
    root = PurePosixPath(workspace)
    fixture_root = root / "fixtures"
    subject = fixture_root / recipe.fixture.id
    steps = [
        f"rm -rf {shlex.quote(str(root))}",
        f"mkdir -p {shlex.quote(str(root))}",
        f"cd {shlex.quote(str(root))}",
        f"git clone --depth 1 -q {shlex.quote(REPO_URL)} bumpsmith",
        "python -m pip install -q ./bumpsmith",
        f"python -m bumpsmith.fixtures {shlex.quote(recipe.fixture.id)} "
        f"--manifest {shlex.quote(manifest)} --root fixtures",
    ]
    if recipe.install:
        steps.append("python -m pip install -q " + " ".join(shlex.quote(r) for r in recipe.install))
    # The subject goes in last so that whatever `install` moved is what stands,
    # and `--no-deps` unless the recipe says otherwise -- see `with_dependencies`.
    deps = "" if recipe.with_dependencies else "--no-deps "
    steps.append(f"python -m pip install -q {deps}-e {shlex.quote(str(subject))}")
    steps.append("echo SUBJECT_READY")
    return " && ".join(steps)


READY = "SUBJECT_READY"
"""Printed by the last step of :func:`setup_script`.

Checked for rather than trusting the exit status alone. The status says the
shell finished; this says the shell finished *the last thing in it*, which is
the claim that matters when every earlier step is what the migration reads.
"""

REPORT_MARKER = "===BUMPSMITH-REPORT==="
"""Separates the run's log from the JSON that follows it.

The one measurement in this project that had to be thrown away was thrown away
because it read a field off a payload it had not checked the shape of, and four
sandboxes returning nothing looked like four sandboxes returning success. A
marker is the cheapest possible version of not doing that again: no marker, no
report, and nothing to mistake for one.
"""


def migrate_script(recipe: Recipe, *, workspace: str = WORKSPACE) -> str:
    """The shell that runs the whole loop against one prepared subject.

    One ``exec`` covers the run *and* the read-back. Splitting them would put a
    second turn between a migration that happened and the only record of what it
    did -- and a lost turn there loses the verdict for a subject that really was
    migrated, which is the one thing :mod:`bumpsmith.fanout` is built to avoid
    miscounting.

    The suite command is the fixture's own, from the manifest, rather than a
    plausible one written here. A subject whose tests are invoked differently
    than its manifest says would produce failures that belong to the invocation,
    and the loop would classify them as breaks with perfect sincerity.
    """
    root = PurePosixPath(workspace)
    subject = root / "fixtures" / recipe.fixture.id
    suite = shlex.join(["python", "-m", "pytest", "-q", *recipe.fixture.pytest_args])
    command = [
        "python",
        "-m",
        "bumpsmith",
        str(subject),
        "--json",
        str(root / "report.json"),
    ]
    if recipe.package is not None:
        command += ["--package", recipe.package]
    line = shlex.join(command) + " -- " + suite
    log = shlex.quote(str(root / "migration.log"))
    return " && ".join(
        [
            f"cd {shlex.quote(str(root))}",
            # No pipe. A pipeline reports the exit status of its last stage, so
            # `bumpsmith ... | tail` reports `tail` -- which succeeds whatever
            # happened upstream. An early version of the probe that found this
            # module's shape printed a zero for a run that had failed outright.
            f"{{ {line} ; }} > {log} 2>&1; echo RC=$?; tail -40 {log}; "
            f"echo {shlex.quote(REPORT_MARKER)}; cat {shlex.quote(str(root / 'report.json'))}",
        ]
    )


@final
class SandboxJob:
    """One subject's entire migration, in a sandbox of its own.

    Satisfies :class:`~bumpsmith.fanout.Job`. Every instance builds its own
    :class:`~bumpsmith.trueforge.Client` and its own
    :class:`~bumpsmith.trueforge.SandboxExec`, so two jobs never share a
    session and therefore never share a sandbox. That is not an optimisation.
    :mod:`bumpsmith.migrate` refuses to edit in one place and test in another,
    and two subjects checked out into one sandbox would be exactly that refusal
    violated from the outside -- one subject's revert running against a tree the
    other was mid-way through.
    """

    def __init__(
        self,
        recipe: Recipe,
        *,
        manifest: str,
        base_url: str | None = None,
        model: str = DEFAULT_MODEL,
        workspace: str = WORKSPACE,
        poll_limit: float = DEFAULT_POLL_LIMIT,
    ) -> None:
        self._recipe = recipe
        self._manifest = manifest
        self._base_url = base_url
        self._model = model
        self._workspace = workspace
        self._poll_limit = poll_limit

    @property
    def subject(self) -> str:
        """Which fixture this job migrates."""
        return self._recipe.fixture.id

    def _runner(self) -> SandboxRunner:
        client = (
            Client(poll_limit=self._poll_limit)
            if self._base_url is None
            else Client(self._base_url, poll_limit=self._poll_limit)
        )
        return SandboxRunner(SandboxExec(client, self._model))

    def __call__(self) -> Reported:
        """Prepare the subject, migrate it, and bring back the verdict.

        Raises on everything that is not a verdict. :func:`~bumpsmith.fanout.fan_out`
        reads a raising job as a subject it could not reach, which is the honest
        reading of all of these: a sandbox that never came up, a clone that
        failed, a report that never appeared. None of them say anything about
        whether the repository needed migrating.
        """
        runner = self._runner()
        try:
            prepared = runner.run(
                [
                    "sh",
                    "-c",
                    setup_script(self._recipe, manifest=self._manifest, workspace=self._workspace),
                ],
                _ANYWHERE,
            )
        except (RunError, TransportError) as exc:
            raise SubjectError(f"{self.subject} was never prepared: {exc}") from exc
        if prepared.returncode != 0 or READY not in prepared.output:
            raise SubjectError(
                f"{self.subject} was not prepared (rc={prepared.returncode}): "
                f"{prepared.output.strip()[-400:]}"
            )

        try:
            ran = runner.run(
                ["sh", "-c", migrate_script(self._recipe, workspace=self._workspace)],
                _ANYWHERE,
            )
        except (RunError, TransportError) as exc:
            raise SubjectError(f"{self.subject} was migrating and the run was lost: {exc}") from exc

        return read_run(ran, self.subject)


def read_run(ran: Completed, subject: str) -> Reported:
    """Pull the verdict out of what the migration command printed.

    Split from :class:`SandboxJob` so the rule can be tested against recorded
    output with no harness in the way -- the same reason
    :func:`bumpsmith.run._read_exec_result` is its own function.

    The command's exit status is deliberately *not* the discriminator. A loop
    that peeled three breaks and then reverted exits non-zero and is a complete,
    correct verdict about a repository; a loop that could not start exits
    non-zero too. What separates them is whether a report exists, and the
    workspace is cleared before every run precisely so the report that exists
    can only be this one's.
    """
    marker = f"\n{REPORT_MARKER}\n"
    _, found, tail = ran.output.partition(marker)
    if not found:
        raise ReportError(
            f"{subject}: the migration printed no report "
            f"(rc={ran.returncode}): {ran.output.strip()[-400:]}"
        )
    if not tail.strip():
        raise ReportError(f"{subject}: the report is empty (rc={ran.returncode})")
    try:
        return read_report(tail)
    except ReportError as exc:
        raise ReportError(f"{subject}: {exc}") from exc


def jobs_for(
    recipes: Sequence[Recipe],
    *,
    manifest: str,
    base_url: str | None = None,
    model: str = DEFAULT_MODEL,
    poll_limit: float = DEFAULT_POLL_LIMIT,
) -> tuple[SandboxJob, ...]:
    """One job per recipe, ready for :func:`~bumpsmith.fanout.fan_out`."""
    return tuple(
        SandboxJob(
            recipe,
            manifest=manifest,
            base_url=base_url,
            model=model,
            poll_limit=poll_limit,
        )
        for recipe in recipes
    )
