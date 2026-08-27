"""Tests for :mod:`bumpsmith.fanout`.

The module has one job worth testing hard: keeping "nothing ran" apart from
"nothing was found". Every other property here is bookkeeping, and bookkeeping
is only interesting because a wrong figure in a summary is the kind of defect
this project has shipped before -- twice in prose, once in a renderer.
"""

import concurrent.futures
import json
import threading
import time
from collections.abc import Callable

import pytest

from bumpsmith.fanout import (
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    Attempt,
    Fanout,
    Job,
    Unreached,
    Verdict,
    _assemble,
    _verdict,
    fan_out,
)
from bumpsmith.migrate import Migration, Outcome, Stop


def _boom() -> Migration:
    """A job that cannot reach its subject."""
    raise ConnectionRefusedError("no sandbox")


def green() -> Migration:
    """A migration that changed nothing because the suite already passed."""
    return Migration(steps=(), stop=Stop.GREEN, reason="already green")


def untouched() -> Migration:
    """A migration that ran, found a red suite, and applied nothing."""
    return Migration(steps=(), stop=Stop.NO_RULE, reason="no rule for this break")


class Fake:
    """A job that does whatever it is told, so the orchestrator is what is tested."""

    def __init__(self, subject: str, action: Callable[[], Migration] | None = None) -> None:
        self._subject = subject
        self._action = action or green

    @property
    def subject(self) -> str:
        return self._subject

    def __call__(self) -> Migration:
        return self._action()


def test_a_fake_job_satisfies_the_protocol() -> None:
    # Otherwise every test below proves things about a shape the real caller
    # cannot supply.
    assert isinstance(Fake("a"), Job)


# -- the distinction the module exists for --------------------------------


def test_four_unreached_subjects_do_not_report_as_four_that_found_nothing() -> None:
    """The whole reason this module has a type instead of a list of migrations.

    Both sets have zero migrated subjects. One is four green repositories; the
    other is four sandboxes that never came up. If any figure in the payload is
    the same for both, that figure is a lie in one of the two cases.
    """

    def boom() -> Migration:
        raise ConnectionRefusedError("no sandbox")

    ran = fan_out([Fake(f"s{i}") for i in range(4)], workers=4)
    lost = fan_out([Fake(f"s{i}", boom) for i in range(4)], workers=4)

    assert ran.counting(Outcome.MIGRATED) == lost.counting(Outcome.MIGRATED) == 0
    # ... and yet nothing else about them matches.
    assert ran.complete is True
    assert lost.complete is False
    assert len(ran.reached) == 4
    assert len(lost.reached) == 0
    assert ran.counting(Outcome.ALREADY_GREEN) == 4
    assert lost.counting(Outcome.ALREADY_GREEN) == 0
    assert ran.as_dict() != lost.as_dict()


def test_an_unreached_subject_is_never_counted_as_an_outcome() -> None:
    def boom() -> Migration:
        raise RuntimeError("gone")

    result = fan_out([Fake("ok"), Fake("bad", boom)], workers=2)
    # Every outcome, so a future member cannot quietly start absorbing them.
    assert sum(result.counting(o) for o in Outcome) == 1
    assert len(result.attempts) == 2


def test_an_unreached_subject_has_no_outcome_rather_than_a_fourth_one() -> None:
    def boom() -> Migration:
        raise RuntimeError("gone")

    (attempt,) = fan_out([Fake("bad", boom)]).attempts
    assert attempt.outcome is None
    assert attempt.verdict is None
    assert attempt.ran is False


def test_a_migration_that_ran_and_reverted_is_reached_not_unreached() -> None:
    """A red suite is a verdict. Only the absence of one is `Unreached`."""
    (attempt,) = fan_out([Fake("red", untouched)]).attempts
    assert attempt.ran is True
    assert attempt.outcome is Outcome.UNTOUCHED


# -- failure is a return value, not an exception ---------------------------


def test_one_failing_job_does_not_lose_the_others() -> None:
    def boom() -> Migration:
        raise OSError("disk")

    result = fan_out([Fake("a"), Fake("b", boom), Fake("c")], workers=3)
    assert [a.ran for a in result.attempts] == [True, False, True]


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionRefusedError("refused"),
        RuntimeError("boom"),
        KeyboardInterrupt(),
        SystemExit(1),
        BaseException("not even an Exception"),
    ],
)
def test_any_exception_becomes_unreached_rather_than_escaping(exc: BaseException) -> None:
    """Including the ones that are not `Exception`.

    A job is somebody else's whole migration. If a `BaseException` escaped the
    worker the subject would have no attempt at all, and the report would be
    short a row without saying so.
    """

    def raise_it() -> Migration:
        raise exc

    (attempt,) = fan_out([Fake("s", raise_it)]).attempts
    assert attempt.ran is False
    assert isinstance(attempt.result, Unreached)
    assert type(exc).__name__ in attempt.result.reason


def test_the_reason_names_the_exception_so_a_reader_can_act_on_it() -> None:
    def boom() -> Migration:
        raise ConnectionRefusedError("localhost:8790 refused")

    (attempt,) = fan_out([Fake("s", boom)]).attempts
    assert isinstance(attempt.result, Unreached)
    assert "ConnectionRefusedError" in attempt.result.reason
    assert "8790" in attempt.result.reason


# -- ordering and concurrency ---------------------------------------------


def test_attempts_come_back_in_job_order_not_completion_order() -> None:
    """Two runs over the same subjects must produce the same document."""

    def slow() -> Migration:
        time.sleep(0.15)
        return green()

    jobs = [Fake("first", slow), Fake("second"), Fake("third")]
    result = fan_out(jobs, workers=3)
    assert [a.subject for a in result.attempts] == ["first", "second", "third"]


def test_jobs_actually_run_at_the_same_time() -> None:
    """Otherwise this module is a loop with extra steps.

    Each job blocks on a barrier that only releases once all of them have
    arrived. Sequential execution cannot get past the first one, so this test
    times out rather than passing slowly if the pool ever becomes serial.
    """
    workers = 4
    barrier = threading.Barrier(workers, timeout=5)

    def wait_for_the_others() -> Migration:
        barrier.wait()
        return green()

    jobs = [Fake(f"s{i}", wait_for_the_others) for i in range(workers)]
    result = fan_out(jobs, workers=workers)
    assert all(a.ran for a in result.attempts)


def test_more_jobs_than_workers_still_all_run() -> None:
    jobs = [Fake(f"s{i}") for i in range(9)]
    result = fan_out(jobs, workers=2)
    assert result.complete
    assert len(result.reached) == 9


# -- the deadline ----------------------------------------------------------


def test_a_job_that_outlives_the_deadline_is_unreached_and_says_it_may_be_running() -> None:
    release = threading.Event()

    def hang() -> Migration:
        release.wait(timeout=10)
        return green()

    try:
        result = fan_out([Fake("hangs", hang), Fake("quick")], workers=2, timeout=0.2)
        hung = result.attempts[0]
        assert hung.ran is False
        assert isinstance(hung.result, Unreached)
        assert "0.2" in hung.result.reason
        # The honest part: the thread was not killed, and a caller tearing down
        # sandboxes has to know one may still be live.
        assert hung.result.still_running is True
        assert result.complete is False
        # The job that did finish is unaffected.
        assert result.attempts[1].ran is True
    finally:
        release.set()


def test_a_job_that_never_started_is_not_reported_as_still_running() -> None:
    """A queued job that the deadline cancelled genuinely is not running."""
    release = threading.Event()

    def hang() -> Migration:
        release.wait(timeout=10)
        return green()

    try:
        # One worker, two jobs: the second cannot have started while the first
        # is still hanging.
        result = fan_out([Fake("hangs", hang), Fake("queued", hang)], workers=1, timeout=0.2)
        queued = result.attempts[1]
        assert isinstance(queued.result, Unreached)
        assert queued.result.still_running is False
    finally:
        release.set()


# -- the deadline decides, and nothing after it ----------------------------


def test_a_result_that_arrived_after_the_deadline_is_not_accepted() -> None:
    """The finding: reading the results first accepted a late verdict.

    The job did finish and its migration is real -- it simply finished after
    the deadline, while the orchestrator was still shutting the pool down.
    Accepting it makes the timeout mean "unless the bookkeeping was slow".
    """
    late_but_real = green()
    verdict = _verdict(
        finished_by_deadline=False,
        recorded=late_but_real,
        cancelled=False,
        timeout=30.0,
    )
    assert verdict is not late_but_real
    assert isinstance(verdict, Unreached)
    assert "30s" in verdict.reason


def test_a_result_that_arrived_before_the_deadline_is_the_verdict() -> None:
    on_time = green()
    assert (
        _verdict(finished_by_deadline=True, recorded=on_time, cancelled=False, timeout=30.0)
        is on_time
    )


def test_finishing_by_the_deadline_with_nothing_recorded_is_still_unreached() -> None:
    """Belt and braces: the two sources must agree before a verdict is taken."""
    verdict = _verdict(finished_by_deadline=True, recorded=None, cancelled=False, timeout=1.0)
    assert isinstance(verdict, Unreached)


@pytest.mark.parametrize(
    ("cancelled", "still_running"),
    [(True, False), (False, True)],
)
def test_only_a_job_that_never_started_is_reported_as_not_running(
    cancelled: bool, still_running: bool
) -> None:
    verdict = _verdict(finished_by_deadline=False, recorded=None, cancelled=cancelled, timeout=1.0)
    assert isinstance(verdict, Unreached)
    assert verdict.still_running is still_running


def test_the_deadline_rule_holds_for_every_combination() -> None:
    """A verdict is taken in exactly one of the four cases."""
    migration = green()
    taken = {
        (by_deadline, recorded is not None): _verdict(
            finished_by_deadline=by_deadline,
            recorded=recorded,
            cancelled=False,
            timeout=1.0,
        )
        is migration
        for by_deadline in (True, False)
        for recorded in (migration, None)
    }
    assert taken == {
        (True, True): True,
        (True, False): False,
        (False, True): False,
        (False, False): False,
    }


# -- the call site's half of the same rule ---------------------------------


def _future() -> "concurrent.futures.Future[None]":
    return concurrent.futures.Future()


def test_a_late_result_is_refused_even_though_the_pool_recorded_it() -> None:
    """`_verdict` states the rule; this checks it is handed the right arguments.

    Built from futures a test made itself, because the window is microseconds
    wide in a real run and cannot be provoked from outside. The second job
    finished -- its migration is sitting in the recorded results -- but it was
    not in the `done` set the deadline produced, so its verdict arrived too
    late to count.

    Without this, a call site ignoring `done` entirely passes every other test
    in this file: the deadline tests use a job that is still blocked, so it
    never records anything and the flag never decides anything.
    """
    on_time, late = _future(), _future()
    result = _assemble(
        [Fake("on-time"), Fake("late")],
        [on_time, late],
        {on_time},
        {0: green(), 1: green()},
        30.0,
    )
    assert result.attempts[0].ran is True
    assert result.attempts[1].ran is False
    assert result.complete is False


def test_assemble_keeps_job_order() -> None:
    a, b, c = _future(), _future(), _future()
    result = _assemble(
        [Fake("first"), Fake("second"), Fake("third")],
        [a, b, c],
        {a, b, c},
        {0: green(), 1: green(), 2: green()},
        30.0,
    )
    assert [x.subject for x in result.attempts] == ["first", "second", "third"]


def test_assemble_reports_a_cancelled_future_as_not_running() -> None:
    queued = _future()
    assert queued.cancel()
    result = _assemble([Fake("queued")], [queued], set(), {}, 30.0)
    (attempt,) = result.attempts
    assert isinstance(attempt.result, Unreached)
    assert attempt.result.still_running is False


# -- refusals --------------------------------------------------------------


def test_two_jobs_with_the_same_subject_are_refused_before_anything_runs() -> None:
    ran: list[str] = []

    def record() -> Migration:
        ran.append("x")
        return green()

    with pytest.raises(ValueError, match="could not be told apart"):
        fan_out([Fake("same", record), Fake("same", record)])
    # Refused *before*, not after four sandboxes were paid for.
    assert ran == []


def test_an_empty_subject_is_refused() -> None:
    with pytest.raises(ValueError, match="subject"):
        fan_out([Fake("")])


@pytest.mark.parametrize("workers", [0, -1])
def test_workers_must_be_positive(workers: int) -> None:
    # Matched on this module's own wording, not on "workers". `ThreadPoolExecutor`
    # rejects the same values with "max_workers must be greater than 0", which
    # the looser pattern also matched -- so the first version of this test
    # passed with the guard deleted. Fifth instance of a test provoking a
    # different failure from the one it names.
    with pytest.raises(ValueError, match="workers must be at least 1"):
        fan_out([Fake("a")], workers=workers)


@pytest.mark.parametrize("workers", [0, -1])
def test_workers_are_checked_even_when_there_is_nothing_to_run(workers: int) -> None:
    """Where the guard is the only thing standing between a caller and a wrong answer.

    With no jobs the pool is never built, so `ThreadPoolExecutor` never gets to
    object. Without this module's own check, an impossible worker count returns
    an empty result as though it had been asked to do nothing.
    """
    with pytest.raises(ValueError, match="workers must be at least 1"):
        fan_out([], workers=workers)


@pytest.mark.parametrize("timeout", [0.0, -1.0])
def test_timeout_must_be_positive(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        fan_out([Fake("a")], timeout=timeout)


@pytest.mark.parametrize("timeout", [0.0, -1.0])
def test_timeout_is_checked_even_when_there_is_nothing_to_run(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        fan_out([], timeout=timeout)


def test_no_jobs_is_an_empty_result_not_an_error() -> None:
    result = fan_out([])
    assert result.attempts == ()
    assert result.complete is True
    assert result.counting(Outcome.MIGRATED) == 0


# -- the payload -----------------------------------------------------------


def test_the_payload_survives_json_dumps() -> None:
    def boom() -> Migration:
        raise RuntimeError("nope")

    result = fan_out([Fake("a"), Fake("b", boom)], workers=2)
    text = json.dumps(result.as_dict())
    back = json.loads(text)
    assert back["subjects"] == 2
    assert back["reached"] == 1
    assert back["unreached"] == 1
    assert back["complete"] is False


def test_the_payload_carries_completeness_beside_the_counts() -> None:
    """Finding 72's shape: a renderer reaching for the nearest number.

    A page showing "1 migrated of 4" without `complete` would be describing a
    different run from the one that happened.
    """

    def boom() -> Migration:
        raise RuntimeError("nope")

    payload = fan_out([Fake("a"), Fake("b", boom)], workers=2).as_dict()
    assert "complete" in payload
    assert payload["complete"] is False
    outcomes = payload["outcomes"]
    assert isinstance(outcomes, dict)
    assert sum(outcomes.values()) == payload["reached"]


def test_the_payload_names_every_outcome_even_at_zero() -> None:
    """So a renderer never has to decide what a missing key means."""
    payload = fan_out([Fake("a")]).as_dict()
    outcomes = payload["outcomes"]
    assert isinstance(outcomes, dict)
    assert set(outcomes) == {o.value for o in Outcome}


# -- the counts are derived, not accumulated -------------------------------


def test_counts_are_derived_from_the_attempts_they_describe() -> None:
    """Built by hand so the counts cannot have been produced by the run."""
    attempts = (
        Attempt("a", green()),
        Attempt("b", untouched()),
        Attempt("c", Unreached(reason="no sandbox")),
    )
    result = Fanout(attempts=attempts)
    assert result.counting(Outcome.ALREADY_GREEN) == 1
    assert result.counting(Outcome.UNTOUCHED) == 1
    assert len(result.unreached) == 1
    assert result.complete is False


def test_reached_and_unreached_partition_the_attempts() -> None:
    attempts = (
        Attempt("a", green()),
        Attempt("b", Unreached(reason="x")),
        Attempt("c", untouched()),
    )
    result = Fanout(attempts=attempts)
    assert len(result.reached) + len(result.unreached) == len(attempts)
    assert set(result.reached).isdisjoint(result.unreached)


def test_every_unreached_attempt_has_no_outcome() -> None:
    """The property `counting()`'s filter leans on.

    `counting` iterates `reached` rather than `attempts`. Today that filter
    changes no answer, because an unreached attempt's `outcome` is `None` and
    `None` is never an `Outcome` member -- the two spellings agree. It is kept
    because it states the rule explicitly rather than relying on that
    coincidence, and this test pins the coincidence so that if `outcome` ever
    stops being `None` here, the filter is already load-bearing and correct.
    """
    result = fan_out([Fake("a", _boom), Fake("b", _boom)], workers=2)
    assert len(result.unreached) == 2
    for attempt in result.unreached:
        assert attempt.outcome is None
    assert sum(result.counting(o) for o in Outcome) == 0


def test_the_defaults_are_the_measured_ones() -> None:
    """Pins the numbers the module docstring argues for."""
    assert DEFAULT_WORKERS == 4
    assert DEFAULT_TIMEOUT == 1800.0


def test_a_result_of_an_unfamiliar_kind_is_not_called_a_subject_nobody_reached() -> None:
    """`ran` asks whether the result is an `Unreached`, not whether it is a `Verdict`.

    The two answers agree for both types this module has met, which is why this
    needed writing on purpose: swapping one for the other passed all 713 tests.
    They disagree for a job that hands back something else -- a future verdict
    type, a stub, a mistake -- and the protocol version answers "nobody reached
    this subject", which is a fact nobody established, in the exact direction
    this module exists to refuse. Asking about `Unreached` instead says the
    subject *was* reached and lets the missing attribute be loud, because a
    result that cannot say what became of the repository is a bug in the job,
    not evidence that the sandbox never came up.
    """

    class NotAVerdict:
        """Reached the subject; cannot say what became of it."""

        def as_dict(self) -> dict[str, object]:
            return {"what": "something a later version returns"}

    assert not isinstance(NotAVerdict(), Verdict)
    assert not isinstance(NotAVerdict(), Unreached)

    class Odd:
        subject = "B"

        def __call__(self) -> Verdict:
            return NotAVerdict()  # type: ignore[return-value]

    (attempt,) = fan_out([Odd()]).attempts
    assert attempt.ran, "a subject that was reached must not be recorded as unreached"
    assert isinstance(attempt.result, NotAVerdict)
    with pytest.raises(AttributeError):
        _ = attempt.outcome
