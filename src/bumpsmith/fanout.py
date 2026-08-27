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
:class:`~bumpsmith.migrate.Migration` or an :class:`Unreached`, never both and
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
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, final, runtime_checkable

from bumpsmith.migrate import Migration, Outcome

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

    def __call__(self) -> Migration:
        """Run it. Raising is how a job says the migration did not happen."""
        ...


@final
@dataclass(frozen=True, slots=True)
class Unreached:
    """A subject whose migration did not happen, and why.

    Not an error type and not a failed migration -- the distinction this whole
    module exists to keep. A migration that ran and left the tree red is a
    :class:`~bumpsmith.migrate.Migration` with a stop reason. This is the other
    thing: no run, no verdict, nothing learned about the subject.
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
    result: Migration | Unreached

    @property
    def ran(self) -> bool:
        """Whether a migration happened at all."""
        return isinstance(self.result, Migration)

    @property
    def migration(self) -> Migration | None:
        """The migration, or ``None`` if the subject was never reached."""
        return self.result if isinstance(self.result, Migration) else None

    @property
    def outcome(self) -> Outcome | None:
        """What became of the tree, or ``None`` when nothing ran.

        ``None`` rather than a fourth ``Outcome`` member on purpose:
        :class:`~bumpsmith.migrate.Outcome` answers "what became of the
        repository", and for a subject nobody reached the answer is not a
        state of the repository at all.
        """
        migration = self.migration
        return None if migration is None else migration.outcome

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

    results: dict[int, Migration | Unreached] = {}
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
            outcome: Migration | Unreached = Unreached(reason=f"{type(exc).__name__}: {exc}")
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
        concurrent.futures.wait(futures, timeout=timeout)
    finally:
        # `cancel_futures` drops the ones that never started. A thread already
        # running cannot be cancelled and keeps going; that is what
        # `Unreached.still_running` is for.
        pool.shutdown(wait=False, cancel_futures=True)

    # Snapshot once, under the lock. A job finishing between the deadline and
    # this line would otherwise appear in some figures and not others. Reading
    # it as unreached is the safe direction: nobody waited for that verdict, so
    # nothing here claims it.
    with lock:
        recorded_by_index = dict(results)

    attempts: list[Attempt] = []
    for index, job in enumerate(jobs):
        recorded = recorded_by_index.get(index)
        if recorded is None:
            started = futures[index].cancelled() is False
            recorded = Unreached(
                reason=f"did not finish within {timeout:g}s",
                # A future that was cancelled never began, so nothing is left
                # running for it. One that is merely unfinished is still going.
                still_running=started,
            )
        attempts.append(Attempt(subject=job.subject, result=recorded))
    return Fanout(attempts=tuple(attempts))
