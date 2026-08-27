"""Migrate several repositories at once, each one somewhere of its own.

A migration is embarrassingly parallel across *subjects* and stubbornly
sequential inside one. Within a repository each break hides behind the one
before it, so the loop cannot look ahead; across repositories nothing is shared
at all -- different trees, different suites, different breaks. This module is
the second half of that sentence and nothing else.

Why the unit is a whole subject
-------------------------------
:mod:`bumpsmith.migrate` refuses to edit here and test there, because the suite
would then answer a question about code the edits never reached. That refusal
decides the shape of this module: fanning out means giving each subject its own
*whole* migration -- clone, edit and run on one filesystem -- not splitting one
migration across several. So a job here is an entire ``bumpsmith`` run, and
this module never sees an edit, a rule or a test result. It sees which subject a
verdict belongs to, and when a verdict never arrived.

That also keeps the transaction out of reach. :mod:`bumpsmith.apply` guarantees
that edits all land or none do; a parallel orchestrator that could interleave
two subjects' edits would be arguing with that guarantee from outside. Here the
guarantee is untouched, because two jobs never share a tree.

What this module refuses to do
------------------------------
**It will not turn a subject it could not reach into a subject with nothing to
migrate.** These are the same number and opposite facts. "Four subjects, none
migrated" is a fine outcome when four suites were already green, and a total
failure when four sandboxes never came up -- and the two collapse the instant
anything counts outcomes rather than attempts. So an attempt holds either a
:class:`Verdict` or an :class:`Unreached`, never both and
never neither, and every figure this module reports is derived from that union
rather than accumulated while the run goes.

It also decides nothing about any migration. It does not retry a red suite, does
not merge results, does not let one subject's outcome inform another's. Each
verdict is produced by the loop running against that subject's own tree; this
module's entire contribution is concurrency and bookkeeping.
"""

from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Protocol, final, runtime_checkable

from bumpsmith.migrate import Outcome

# Four concurrent sandboxes measured 3.57x against the sum of their individual
# times on 27 Aug 2026 -- four distinct TrueForge sessions, each returning its
# own marker. Session creation was ~0.03s; the cost is the turn, not the
# sandbox. The number is a default rather than a limit because the right value
# belongs to whoever is paying for the sandboxes.
DEFAULT_WORKERS = 4

# A whole migration in a cold sandbox: clone, install a baseline, install
# pydantic v2, then peel a chain a break at a time. Fixture B's suite runs in
# seconds and the chain is three breaks deep; the margin is for the sandbox
# coming up and the installs, not for a slow suite.
DEFAULT_TIMEOUT = 1800.0


@runtime_checkable
class Verdict(Protocol):
    """What a job produced: a migration's result, wherever it was reached.

    A protocol rather than :class:`~bumpsmith.migrate.Migration` itself, because
    two different things are legitimately a verdict about a repository and only
    one of them is a ``Migration``. The loop running here produces one of those.
    A loop running in a sandbox produces a report, and
    :class:`bumpsmith.remote.Reported` is what that report may honestly be read
    as -- a summary whose evidence is gone, which is a different object and says
    so in its type.

    One attribute, because this module wants exactly one thing from a verdict:
    what became of the repository. It does not read steps, does not look at a
    stop reason, and does not care which kind it was handed. Widening it later
    would be widening what the orchestrator is allowed to have an opinion about.
    """

    @property
    def outcome(self) -> Outcome:
        """What became of the repository this verdict is about."""
        ...

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail."""
        ...


@runtime_checkable
class Job(Protocol):
    """One subject's entire migration, wherever it runs.

    Deliberately opaque. The orchestrator must not be able to tell a sandbox
    from a local run, because the moment it can, it acquires an opinion about
    which one is trustworthy -- and that opinion belongs in
    :mod:`bumpsmith.run`, which already has it.
    """

    @property
    def subject(self) -> str:
        """What this job migrates. Used only to label the result."""
        ...

    def __call__(self) -> Verdict:
        """Run it. Raising is how a job says the migration did not happen."""
        ...


@final
@dataclass(frozen=True, slots=True)
class Unreached:
    """A subject whose migration did not happen, and why.

    Not an error type and not a failed migration -- the distinction this whole
    module exists to keep. A migration that ran and left the tree red is a
    :class:`Verdict` with a stop reason. This is the other thing: no run, no
    verdict, nothing learned about the subject.
    """

    reason: str

    still_running: bool = False
    """Whether the work may still be going after this was recorded.

    True when a job outlived the deadline. A Python thread cannot be cancelled,
    so the deadline stops *waiting*, not the job -- and a sandbox on the other
    end of it may still be part-way through a migration. Saying so is the
    honest form; a caller that tears down sandboxes needs to know one is
    possibly still live, and a caller that retries needs to know the first
    attempt was never stopped.
    """

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail."""
        return {"reason": self.reason, "still_running": self.still_running}


@final
@dataclass(frozen=True, slots=True)
class Attempt:
    """What became of one subject. Exactly one of two things, never both.

    ``result`` is a union rather than two optional fields, because two fields
    can be set at once and then something has to decide which one wins. The
    union cannot be in that state, so nothing has to decide.
    """

    subject: str
    result: Verdict | Unreached

    @property
    def ran(self) -> bool:
        """Whether a migration happened at all.

        Asks whether the result is an :class:`Unreached` rather than whether it
        is a verdict, and the direction is deliberate. ``Unreached`` is this
        module's own type and has exactly one meaning; "a verdict" is anything
        satisfying a protocol, and testing for *that* means a result of a kind
        this module has not met yet reads as a subject nobody reached. The
        failure would be silent and in the safe-looking direction, which is the
        one thing this module exists to refuse.
        """
        return not isinstance(self.result, Unreached)

    @property
    def verdict(self) -> Verdict | None:
        """What the migration concluded, or ``None`` if nobody reached the subject."""
        return None if isinstance(self.result, Unreached) else self.result

    @property
    def outcome(self) -> Outcome | None:
        """What became of the tree, or ``None`` when nothing ran.

        ``None`` rather than a fourth ``Outcome`` member on purpose:
        :class:`~bumpsmith.migrate.Outcome` answers "what became of the
        repository", and for a subject nobody reached the answer is not a
        state of the repository at all.
        """
        verdict = self.verdict
        return None if verdict is None else verdict.outcome

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail."""
        return {
            "subject": self.subject,
            "ran": self.ran,
            "result": self.result.as_dict(),
        }


@final
@dataclass(frozen=True, slots=True)
class Fanout:
    """Every attempt, in the order the jobs were given.

    Ordered by input rather than by completion so that two runs over the same
    subjects produce the same report. Completion order is a property of how
    busy the sandboxes were, and putting it in the output would make the
    document differ run to run for a reason nobody cares about.

    Every count below is derived. Nothing here is incremented as results
    arrive, because a counter and a list can disagree and then the summary is
    the thing that gets quoted.
    """

    attempts: tuple[Attempt, ...]

    @property
    def reached(self) -> tuple[Attempt, ...]:
        """The subjects a migration actually ran against."""
        return tuple(a for a in self.attempts if a.ran)

    @property
    def unreached(self) -> tuple[Attempt, ...]:
        """The subjects nothing is known about."""
        return tuple(a for a in self.attempts if not a.ran)

    @property
    def complete(self) -> bool:
        """Whether every subject produced a verdict.

        The gate on reading any figure below as a statement about the whole
        set. False means at least one subject is missing, and the counts
        describe the ones that ran and no others.
        """
        return not self.unreached

    def counting(self, outcome: Outcome) -> int:
        """How many subjects ended in ``outcome``.

        Only ever counts subjects that ran. A caller wanting to know how many
        did *not* end in an outcome has to consult :attr:`unreached` as well,
        which is the point: there is no arithmetic here that turns a subject
        nobody reached into a subject that came out a particular way.

        The filter is deliberately redundant. An unreached attempt's
        :attr:`Attempt.outcome` is already ``None``, so iterating every attempt
        would give the same answer today -- breaking it changes no test, which
        is how it was found. It stays because it states the rule at the place
        the rule matters instead of inheriting it from another class's
        behaviour, and ``test_every_unreached_attempt_has_no_outcome`` pins the
        behaviour it would otherwise be silently relying on.
        """
        return sum(1 for a in self.reached if a.outcome is outcome)

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail.

        ``complete`` travels beside the counts rather than being left for the
        reader to work out from two lengths, because this payload is read by a
        renderer, and finding 72 was a renderer answering a question with the
        nearest number it had.
        """
        return {
            "subjects": len(self.attempts),
            "reached": len(self.reached),
            "unreached": len(self.unreached),
            "complete": self.complete,
            "outcomes": {o.value: self.counting(o) for o in Outcome},
            "attempts": [a.as_dict() for a in self.attempts],
        }


def _labelled(jobs: Sequence[Job]) -> None:
    """Refuse a job set that cannot produce a readable report.

    Checked before anything is started rather than while results come back: a
    duplicate subject is a mistake in the caller's list, and finding it after
    four sandboxes have been paid for helps nobody.
    """
    seen: set[str] = set()
    for job in jobs:
        name = job.subject
        if not name:
            raise ValueError("every job needs a subject; one was empty")
        if name in seen:
            raise ValueError(
                f"two jobs claim the subject {name!r}; results could not be told apart"
            )
        seen.add(name)


def _verdict(
    *,
    finished_by_deadline: bool,
    recorded: Verdict | Unreached | None,
    cancelled: bool,
    timeout: float,
) -> Verdict | Unreached:
    """What one job's attempt holds, decided at the deadline and not after it.

    ``finished_by_deadline`` is membership of the ``done`` set
    :func:`concurrent.futures.wait` returned -- a fact about the instant the
    deadline passed. ``recorded`` is what the shared results hold *now*, which
    for a job that finished late is a genuine migration that nobody waited for.

    The first decides; the second only supplies the value. Reading ``recorded``
    first was the original, and it accepted a verdict that arrived after the
    deadline whenever the bookkeeping between the two took long enough -- which
    makes the timeout nondeterministic exactly at its boundary, in a module
    whose report is supposed to be the same for the same subjects twice.

    Pulled out as a function because the window it is about is microseconds
    wide and cannot be provoked reliably from outside. A rule that cannot be
    raced can still be stated and checked, and this is that rule.
    """
    if finished_by_deadline and recorded is not None:
        return recorded
    return Unreached(
        reason=f"did not finish within {timeout:g}s",
        # A future that was cancelled never began, so nothing is left running
        # for it. One that is merely unfinished is still going.
        still_running=not cancelled,
    )


def _assemble(
    jobs: Sequence[Job],
    futures: Sequence[concurrent.futures.Future[None]],
    done: AbstractSet[concurrent.futures.Future[None]],
    recorded: Mapping[int, Verdict | Unreached],
    timeout: float,
) -> Fanout:
    """Turn what the pool did into one report, in the order the jobs were given.

    Separate from :func:`fan_out` so that the wiring can be checked with futures
    a test built itself. :func:`_verdict` states the rule; this is the half that
    has to hand it the right arguments, and getting *that* wrong looks identical
    from outside -- the deadline tests never populate a recorded result for a
    job that missed the deadline, so a call site ignoring ``done`` entirely
    passed all of them. A guarantee spelled across two places needs both halves
    tested, which is the shape finding 55 named.
    """
    return Fanout(
        attempts=tuple(
            Attempt(
                subject=job.subject,
                result=_verdict(
                    finished_by_deadline=futures[index] in done,
                    recorded=recorded.get(index),
                    cancelled=futures[index].cancelled(),
                    timeout=timeout,
                ),
            )
            for index, job in enumerate(jobs)
        )
    )


def fan_out(
    jobs: Sequence[Job],
    *,
    workers: int = DEFAULT_WORKERS,
    timeout: float = DEFAULT_TIMEOUT,
) -> Fanout:
    """Run every job concurrently and report what each one did.

    Args:
        jobs: The subjects to migrate. Each is run exactly once; none is
            retried, because a migration that half-happened is not a thing to
            repeat blindly and this module cannot tell whether it did.
        workers: How many run at a time. The rest queue.
        timeout: How long to wait for *all* of them, in seconds.

    Returns:
        A :class:`Fanout` with one :class:`Attempt` per job, in the order the
        jobs were given. Ordinary failure is a return value: a job that raised
        is an :class:`Unreached` in the result, not an exception out of here,
        because one unreachable sandbox is not a reason to throw away three
        migrations that worked.

    Raises:
        ValueError: if ``workers`` is not positive, if ``timeout`` is not
            positive, or if the jobs do not have distinct non-empty subjects.
    """
    if workers < 1:
        raise ValueError(f"workers must be at least 1; got {workers}")
    if timeout <= 0:
        raise ValueError(f"timeout must be positive; got {timeout}")
    _labelled(jobs)

    if not jobs:
        return Fanout(attempts=())

    results: dict[int, Verdict | Unreached] = {}
    lock = threading.Lock()

    def one(index: int, job: Job) -> None:
        try:
            migration = job()
        except BaseException as exc:
            # Every exception, not just the expected ones. A job is somebody
            # else's whole migration and the exceptions it can raise are not
            # this module's to enumerate; an unexpected one escaping here would
            # take down the thread and leave the subject with no attempt at
            # all, which reads as a bug in the orchestrator rather than as the
            # subject having failed. `Unreached` is the safe direction: it
            # claims nothing about the tree.
            outcome: Verdict | Unreached = Unreached(reason=f"{type(exc).__name__}: {exc}")
        else:
            outcome = migration
        with lock:
            results[index] = outcome

    # Deliberately not `with`. `ThreadPoolExecutor.__exit__` calls
    # `shutdown(wait=True)`, which blocks until every worker has finished --
    # including the one the deadline just gave up on. Written that way first,
    # and the deadline was decorative: the test for it took as long as the job
    # it was supposed to abandon. A timeout that only stops *waiting* has to
    # stop waiting everywhere, so the shutdown is explicit and does not wait.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    try:
        futures = [pool.submit(one, i, job) for i, job in enumerate(jobs)]
        # `done` is the deadline, and it is a set decided *by* `wait` at the
        # moment it gave up -- not a question asked afterwards. Everything below
        # reads membership of it rather than the shared results, because those
        # keep being written to by threads nobody is waiting for any more.
        done, _ = concurrent.futures.wait(futures, timeout=timeout)
    finally:
        # `cancel_futures` drops the ones that never started. A thread already
        # running cannot be cancelled and keeps going; that is what
        # `Unreached.still_running` is for.
        pool.shutdown(wait=False, cancel_futures=True)

    with lock:
        recorded_by_index = dict(results)

    return _assemble(jobs, futures, done, recorded_by_index, timeout)
