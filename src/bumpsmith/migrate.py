"""Peel the chain: run, read the break, fix it, run again, keep only if green.

This is the agent. Every other module in the package is a part it uses, and
each of those parts was written to be right on its own; what is here is the
order they go in and the one decision that order exists to protect.

The decision is when to keep an edit. A migration that leaves a repository
changed and no better is worse than one that changes nothing, because somebody
now has to work out which of the two happened. So the edits from every step are
held open together and kept only at the end, only once a run has come back
green -- and :func:`bumpsmith.apply.attempt` makes reverting the default, so
forgetting is not a way to keep them.

Why a loop at all
-----------------
A repository does not present its breaks one at a time. ``__root__`` aborts
collection, and the ``regex=`` underneath it is invisible until that is fixed --
not deprioritised, *invisible*, because pytest never got far enough to import
the module that contains it. So the loop's shape is forced: fix one break, look
again, and let the next one be discovered rather than predicted.

What it will not do
-------------------
Nothing here retries, and nothing here guesses. A failure that does not narrow
to exactly one rule stops the loop with a sentence saying so, and every stop is
a member of :class:`Stop` rather than a message. The point is that "bumpsmith
could not finish" is never a shrug: the report names which of them happened,
and a person reading it knows whether to write a rule, fix their pytest
invocation, or upgrade a dependency. How many of them there are is not written
down here -- the enum below is the count, and a number repeated in prose beside
it is one that goes stale the next time a member is added.

The runner and the tree
-----------------------
:func:`migrate` takes a :class:`~bumpsmith.run.Runner` rather than running
pytest itself, which is what lets the suite execute somewhere safer than this
process. It carries a requirement the protocol cannot state: **the runner has to
execute against the same tree the edits are written to.** ``LocalRunner``
satisfies it by construction. ``SandboxRunner`` does not -- the harness's
sandbox is a different filesystem -- and a loop that edited here and verified
there would keep a change on the strength of a suite that never saw it. That is
the same defect :mod:`bumpsmith.run` exists to prevent, one level up.

So it is checked rather than asked for. Every run reports where it happened, and
a run from anywhere but this machine stops the loop at :attr:`Stop.WRONG_PLACE`
before its result is used for anything. Saying the requirement in this paragraph
was the first version, and a paragraph is not an enforcement: :func:`migrate` is
public and takes the general protocol, so a caller holding a ``SandboxRunner``
never passes the command line's refusal on the way in.

The tree and its configuration
------------------------------
Running against the right tree is not sufficient, because pytest does not read
its settings from the tree it runs in -- it walks upward for the first file that
counts as an inifile. A repository with no pytest configuration of its own
inherits whatever it happens to sit beneath, so a subject cloned into a checkout
that configures pytest is measured under settings nobody chose for it. An
outside ``addopts`` that deselects, or a narrowing ``testpaths``, runs fewer
tests than the repository's own suite would, and a suite that should have gone
red goes green with the edits kept. That is ``WRONG_PLACE``'s defect arriving by
a different road, so it gets the same treatment: :attr:`Stop.FOREIGN_CONFIG`,
checked once before the first run. :mod:`bumpsmith.rootdir` does the looking.
"""

from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

from bumpsmith.apply import ApplyError, Attempt, Edit, RevertError, attempt
from bumpsmith.failures import Failure, parse_failures
from bumpsmith.rewrite import Plan, UnsupportedRuleError, plan
from bumpsmith.rootdir import describe, foreign_config, runs_pytest
from bumpsmith.rules import Rule, RuleKind, ScanResult, find_matches, write_rule
from bumpsmith.run import Completed, RunError, Runner, Where

SAME_TREE: frozenset[Where] = frozenset({"local"})
"""Where a run can happen and still be a run against the edited tree.

Today that is one place. :class:`~bumpsmith.run.SandboxRunner` executes in the
harness's sandbox, which does not share a filesystem with this process, and the
harness offers no way to put a file into it -- so the edits cannot be carried
across and a suite there would not be testing them.

This is the enforcement, and it is here rather than in the command line because
:func:`migrate` is public and takes the general ``Runner`` protocol. A caller
holding a ``SandboxRunner`` reaches this function without going near the CLI's
refusal. It tests the fact each run reports rather than the type of the runner,
so a wrapper cannot slip past it and a runner nobody has written yet is covered.

When edits *can* be carried into a sandbox, this is the line that has to change,
deliberately, as part of that work.
"""

_WHERE: dict[Where, str] = {"local": "on this machine", "sandbox": "in the sandbox"}
"""How each place a suite can run reads in a sentence.

Typed against the ``Where`` literal so that a third place added to
:mod:`bumpsmith.run` fails type-checking here rather than raising ``KeyError``
in the one branch that reports success.
"""

DEFAULT_STEP_LIMIT = 6
"""How many times the loop may change the repository before giving up.

Chosen to be larger than any chain observed in the fixtures and small enough
that a rule which matches its own output cannot run away. It is a bound on
*applications*, not on runs: every application is verified by the run that opens
the next step, including the last one, so the loop never leaves an edit on disk
that nothing has tested.
"""


class Stop(Enum):
    """Why the loop ended. Every exit from it is one of these.

    An enum rather than a message because the caller sometimes has to act on the
    answer -- ``NOT_RUN`` means fix the invocation and try again, ``NO_REWRITER``
    means the rule is the useful output and a human takes it from here -- and
    matching on prose is how that goes wrong quietly.
    """

    GREEN = "green"
    """The suite passed. This is the only value that keeps anything."""

    NOT_RUN = "not-run"
    """The suite could not be run, so there is no result to reason about.

    Distinct from a red suite, and the distinction is the whole of
    :mod:`bumpsmith.run`. A missing interpreter and a failing test are not two
    grades of the same thing.
    """

    NOT_A_BREAK = "not-a-break"
    """The run failed, but not from a migration break.

    An interrupted session or a misinvoked pytest. Reported separately because
    the fix is to the command, not to the code, and a loop that wrote a rule for
    a timeout would be confidently wrong.
    """

    NOTHING_PARSED = "nothing-parsed"
    """The suite failed in a layout this parser could not read."""

    NO_RULE = "no-rule"
    """The failure does not narrow to exactly one transformation."""

    DEPENDENCY = "dependency"
    """The break is real and no edit to this repository removes it."""

    NO_REWRITER = "no-rewriter"
    """The rule is known and nobody has written the rewriter for it yet."""

    NOTHING_TO_APPLY = "nothing-to-apply"
    """The rule matched nothing, or nothing that changes when rewritten."""

    NOT_APPLIED = "not-applied"
    """The edits were refused before anything was written to disk."""

    STEP_LIMIT = "step-limit"
    """The cap was reached and the suite was still red."""

    WRONG_PLACE = "wrong-place"
    """The suite ran somewhere other than the tree being edited.

    The loop writes its edits to ``root`` on this machine, so a run that
    happened anywhere else did not observe them, and a zero from it says
    nothing about the edits. Refused rather than trusted, because the failure it
    would otherwise produce is the worst one available: edits kept on the
    strength of a suite that never saw them.
    """

    FOREIGN_CONFIG = "foreign-config"
    """The suite would be configured from outside the tree being edited.

    pytest resolves its settings by walking up from the directory it runs in, so
    a repository that configures nothing itself is governed by whatever it sits
    beneath. Refused for the same reason as :attr:`WRONG_PLACE`: an outside
    setting that narrows what runs makes a green suite mean less than it says,
    and the loop keeps edits on exactly that signal. The remedy is one file --
    the repository configuring itself -- and the message names what would have
    governed it instead.
    """


class Outcome(Enum):
    """What became of the repository. Not the same question as :class:`Stop`.

    ``Stop`` says why the loop ended; this says what is on disk afterwards. They
    are kept apart because a caller usually wants one of them and would have to
    reconstruct it from the other -- and because the two most different results
    the loop can produce, "fixed it" and "changed nothing", share a ``Stop``.
    """

    ALREADY_GREEN = "already-green"
    """The suite passed before anything was changed."""

    MIGRATED = "migrated"
    """Edits were applied, the suite went green, and the edits were kept."""

    REVERTED = "reverted"
    """Edits were applied, the suite did not go green, and they were taken back."""

    UNTOUCHED = "untouched"
    """The suite was red and nothing was ever applied."""


@dataclass(frozen=True, slots=True)
class Step:
    """One pass of the loop: a run, and what was decided about it.

    Every field after ``run`` is filled in only as far as that step got, so a
    step that stopped at ``NO_RULE`` carries the failure it read and no rule.
    The ``None``s are the record of where it stopped, which is why they are not
    defaulted away into empty tuples.
    """

    number: int
    run: Completed
    failure: Failure | None = None
    rule: Rule | None = None
    scan: ScanResult | None = None
    plan: Plan | None = None
    applied: bool = False
    """Whether these edits reached the disk.

    Recorded rather than derived from ``plan``, and the difference is not
    academic: :func:`bumpsmith.apply.attempt` can refuse a plan outright, and a
    plan that was refused is a change the tree never saw. Deriving this from the
    plan's contents was the first version, and the exhaustive test below caught
    it reporting "1 change, taken back" for a run that had changed nothing. A
    plan is what was intended; only the apply knows what happened.
    """

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail.

        Every key that counts something names where the count came from, and
        that is a fix rather than a style. ``files`` used to mean "files the
        plan edits", and a reader who joined it to ``sites`` -- which comes from
        the *scan* -- got a sentence describing neither: a file whose every
        match was skipped produces no edit, so it vanished from a count offered
        as the rule's reach. The page did exactly that (finding 72). A scan
        number and a plan number can no longer be confused for one another
        because their names no longer let them.

        ``unreadable`` carries the reason as well as the path for the same kind
        of reason. :class:`~bumpsmith.rules.Unreadable` has always held both,
        this dropped the half that says *why*, and "the report names the file"
        is a much weaker promise than the one the class makes.
        """
        return {
            "step": self.number,
            "returncode": self.run.returncode,
            "where": self.run.where,
            "break_class": None if self.failure is None else self.failure.break_class.name,
            "message": None if self.failure is None else self.failure.message,
            "culprit": None
            if self.failure is None or self.failure.culprit is None
            else str(self.failure.culprit),
            "rule": None if self.rule is None else self.rule.summary,
            "sites": None if self.scan is None else self.scan.count,
            # Paired with `sites`, so counted over the same thing. A use lives in
            # the file that imported the name, so this never differs today -- it
            # is written this way so it still cannot differ later.
            "match_files": None
            if self.scan is None
            else len({match.path for match in self.scan.sites}),
            # Reported separately because they are not sites: nothing rewrites
            # them, and a person still has to deal with every one.
            "uses": []
            if self.scan is None
            else [
                {"path": str(u.path), "line": u.line, "excerpt": u.excerpt} for u in self.scan.uses
            ],
            "scan_complete": None if self.scan is None else self.scan.is_complete,
            "unreadable": []
            if self.scan is None
            else [{"path": str(u.path), "reason": u.reason} for u in self.scan.unreadable],
            "rewritten": None if self.plan is None else self.plan.rewritten,
            "edit_files": None if self.plan is None else len(self.plan.edits),
            "skipped": [] if self.plan is None else [str(s) for s in self.plan.skipped],
            "applied": self.applied,
        }


@dataclass(frozen=True, slots=True)
class Migration:
    """Everything one run of the loop did, and what it left behind.

    Only three things are stored. :attr:`outcome`, :attr:`applied` and
    :attr:`kept` are derived from them, because a report that stores a
    conclusion alongside the evidence for it can end up disagreeing with itself,
    and this is the object somebody reads to find out whether their working tree
    was changed.
    """

    steps: tuple[Step, ...]
    stop: Stop
    reason: str

    @property
    def applied(self) -> int:
        """How many steps wrote to disk."""
        return sum(1 for step in self.steps if step.applied)

    @property
    def outcome(self) -> Outcome:
        """What became of the repository."""
        if self.stop is Stop.GREEN:
            return Outcome.MIGRATED if self.applied else Outcome.ALREADY_GREEN
        return Outcome.REVERTED if self.applied else Outcome.UNTOUCHED

    @property
    def complete(self) -> bool:
        """Whether every site the rules matched was accounted for.

        False when a candidate file could not be read or parsed, or when the
        rewriter matched a site and then declined to change it. Either way some
        v1 code the rule named is still there.

        Kept separate from :attr:`outcome` rather than folded into it, and the
        loop does *not* refuse to apply an incomplete plan. A suite that goes
        green is real evidence about the tests that exist, and refusing to help
        a repository because one vendored file will not parse would be worse
        than helping it and saying so. But "the suite passes" and "the migration
        is finished" are different claims, and a report that ran them together
        would let the first quietly stand in for the second.
        """
        for step in self.steps:
            if step.scan is not None and not step.scan.is_complete:
                return False
            if step.plan is not None and not step.plan.is_complete:
                return False
        return True

    @property
    def kept(self) -> bool:
        """Whether the edits are still on disk.

        True for exactly one outcome. A caller may treat this as the answer to
        "did my working tree change", because the loop keeps nothing by any
        other route.
        """
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
            "steps": [step.as_dict() for step in self.steps],
        }


def _sites(count: int) -> str:
    return "site" if count == 1 else "sites"


def _writes(planned: Plan) -> tuple[Edit, ...]:
    """The edits in ``planned`` that change the file they name.

    :func:`bumpsmith.apply.attempt` drops the others, so anything that counts or
    reports applications has to drop them here too or it will disagree with the
    disk. A rule can match a site already in its target state -- fixture C is
    entirely made of them -- and rewriting it produces an edit that is real,
    correct, and writes nothing.
    """
    return tuple(edit for edit in planned.edits if edit.changes_anything)


@dataclass(frozen=True, slots=True)
class _Setup:
    """The inputs that do not change between steps."""

    root: Path
    runner: Runner
    command: tuple[str, ...]
    project_packages: frozenset[str]
    step_limit: int


@dataclass(frozen=True, slots=True)
class _Stopped:
    """A step that produced a reason to end rather than edits to apply."""

    stop: Stop
    reason: str


def migrate(
    root: Path,
    runner: Runner,
    command: Sequence[str],
    *,
    project_packages: frozenset[str] = frozenset(),
    step_limit: int = DEFAULT_STEP_LIMIT,
) -> Migration:
    """Migrate the repository at ``root`` until its suite is green, or stop saying why.

    Args:
        root: The repository to change. Every edit is made inside it, and
            :func:`bumpsmith.apply.attempt` refuses any that would land outside.
        runner: Where the suite runs. It must execute against ``root`` itself;
            see the module docstring for what goes wrong when it does not.
        command: The argv that runs the suite, never a shell string.
        project_packages: Top-level package names this repository owns. Used
            only to tell its own missing module from an unmigrated third-party
            one. Omitting it makes that distinction unavailable, which is
            reported as an unclassified break rather than guessed.
        step_limit: How many times the loop may change the repository.

    Returns:
        A :class:`Migration` describing every step and what became of the tree.
        Ordinary failure is a return value here, not an exception: "the suite
        still does not pass" is a result the caller has to read either way.

    Raises:
        ValueError: if ``step_limit`` is negative.
        RevertError: if edits were applied and could not be taken back. This one
            is not turned into a stop reason, because it means the working tree
            is in a state nobody chose and a caller that treated it as an
            ordinary outcome would carry on against a repository it no longer
            understands.
    """
    if step_limit < 0:
        raise ValueError(f"step_limit cannot be negative; got {step_limit}")

    # Before the first run, not after it. A refusal that arrives once the suite
    # has already produced a verdict has to argue with a number somebody can
    # see, and the whole point is that the number should never have been
    # produced. Nothing has been applied at this line, so there is nothing to
    # take back and no step to record.
    if runs_pytest(command):
        outside = foreign_config(root, command)
        if outside is not None:
            return Migration(
                steps=(),
                stop=Stop.FOREIGN_CONFIG,
                reason=(
                    f"the suite at {root} would be configured from outside the tree "
                    f"being edited, by {describe(outside)}; give the repository its own "
                    f"pytest configuration so its suite is measured by its own rules"
                ),
            )

    setup = _Setup(
        root=root,
        runner=runner,
        command=tuple(command),
        project_packages=project_packages,
        step_limit=step_limit,
    )
    steps: list[Step] = []
    attempts: list[Attempt] = []

    with ExitStack() as stack:
        stopped = _peel(setup, stack, steps, attempts)
        migration = Migration(steps=tuple(steps), stop=stopped.stop, reason=stopped.reason)
        # The only call to keep() in the package outside its own tests, and the
        # only place the loop can leave a repository changed. It is reached only
        # through `outcome`, so the disk and the report cannot disagree about
        # whether anything was kept.
        if migration.outcome is Outcome.MIGRATED:
            for session in attempts:
                session.keep()
    return migration


def _peel(
    setup: _Setup,
    stack: ExitStack,
    steps: list[Step],
    attempts: list[Attempt],
) -> _Stopped:
    """Run the loop, appending to ``steps`` and ``attempts`` as it goes.

    Split out from :func:`migrate` so that every way of ending is a ``return``
    at the point it is decided, while the keep-or-revert decision stays in one
    place that all of them pass through.
    """
    while True:
        try:
            result = setup.runner.run(setup.command, setup.root)
        except RunError as exc:
            # Not a red suite -- an absence of evidence. Nothing applied so far
            # has been verified, and the stack is about to take it all back.
            return _Stopped(Stop.NOT_RUN, f"the suite could not be run: {exc}")

        number = len(steps) + 1
        if result.where not in SAME_TREE:
            steps.append(Step(number=number, run=result))
            return _Stopped(
                Stop.WRONG_PLACE,
                f"the suite ran {_WHERE.get(result.where, result.where)}, which is not "
                f"where the edits are written; a result from there cannot verify them",
            )

        if result.returncode == 0:
            steps.append(Step(number=number, run=result))
            return _Stopped(Stop.GREEN, f"the suite passed {_WHERE[result.where]}")

        if len(attempts) >= setup.step_limit:
            steps.append(Step(number=number, run=result))
            return _Stopped(
                Stop.STEP_LIMIT,
                f"the suite was still failing after {setup.step_limit} "
                f"{'change' if setup.step_limit == 1 else 'changes'}",
            )

        step, decision = _analyse(setup, number, result)
        if isinstance(decision, _Stopped):
            steps.append(step)
            return decision

        try:
            attempts.append(stack.enter_context(attempt(decision, setup.root)))
        except RevertError:
            # A failed application that could not undo itself. Already the worst
            # thing this package can report, and already classified by the layer
            # that knows; re-describing it as a tidy stop reason would hide it.
            raise
        except ApplyError as exc:
            steps.append(step)
            return _Stopped(Stop.NOT_APPLIED, f"the edits were refused: {exc}")

        # Recorded here and nowhere else: this is the only line in the package
        # after which the repository is different from how it was found.
        steps.append(replace(step, applied=True))


def _analyse(
    setup: _Setup, number: int, result: Completed
) -> tuple[Step, _Stopped | tuple[Edit, ...]]:
    """Work out what one failing run means, and either stop or produce edits.

    Returns the step as far as it got either way, so a stop is recorded with the
    evidence that produced it rather than as a bare reason.
    """
    step = Step(number=number, run=result)

    failures = parse_failures(
        result.output,
        returncode=result.returncode,
        project_packages=setup.project_packages,
    )
    if not failures:
        return step, _Stopped(
            Stop.NOTHING_PARSED,
            f"the suite exited {result.returncode} and printed nothing this parser could read",
        )

    # The first is the one to fix. pytest may report several, but a chain is
    # discovered rather than predicted: fixing this one changes what the next
    # run can even see, so planning against the rest would plan against a
    # repository that is about to stop existing.
    failure = failures[0]
    step = Step(number=number, run=result, failure=failure)

    if not failure.shape.is_migration_break:
        return step, _Stopped(
            Stop.NOT_A_BREAK,
            f"the run ended as {failure.shape.value}, which is a problem with the "
            f"invocation rather than with the code being migrated",
        )

    rule = write_rule(failure)
    if rule is None:
        return step, _Stopped(
            Stop.NO_RULE,
            f"the failure classified as {failure.break_class.name}, which does not narrow "
            f"to one rule; a rule naming the wrong transformation is worse than none",
        )
    step = Step(number=number, run=result, failure=failure, rule=rule)

    if rule.kind is RuleKind.DEPENDENCY:
        return step, _Stopped(Stop.DEPENDENCY, rule.rationale)

    scan = find_matches(rule, setup.root)
    step = Step(number=number, run=result, failure=failure, rule=rule, scan=scan)

    try:
        planned = plan(rule, scan)
    except UnsupportedRuleError as exc:
        return step, _Stopped(Stop.NO_REWRITER, str(exc))
    step = Step(number=number, run=result, failure=failure, rule=rule, scan=scan, plan=planned)

    writes = _writes(planned)
    if not writes:
        return step, _Stopped(
            Stop.NOTHING_TO_APPLY,
            f"the rule matched {scan.count} {_sites(scan.count)}, of which "
            f"{planned.rewritten} could be rewritten and none needed to be",
        )
    return step, writes
