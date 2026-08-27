"""Tests for reading a verdict back out of a report written somewhere else.

The load-bearing test here is
:func:`test_a_reported_verdict_agrees_with_the_migration_it_came_from`. Every
other test checks one refusal; that one takes real
:class:`~bumpsmith.migrate.Migration` objects covering every outcome, writes
each one out the way ``--json`` does, reads it back, and asserts the two agree
on every derived field. It is the only test that would notice the two types
drifting apart, which is the failure this module is most exposed to: they are
written to answer the same questions from different evidence, and nothing else
in the suite compares their answers.

Nothing here talks to a sandbox. What a sandbox does is
:mod:`bumpsmith.trueforge`'s problem and is proven live in
``proofs/sandbox_fanout.py``; what a *report* means is this module's problem
entirely, and it is worth checking against text a test can malform on purpose.
"""

import json
from pathlib import Path

import pytest

from bumpsmith.fanout import Job, Unreached, Verdict, fan_out
from bumpsmith.fixtures import Fixture
from bumpsmith.migrate import Migration, Outcome, Step, Stop
from bumpsmith.remote import (
    READY,
    REPORT_MARKER,
    Recipe,
    Reported,
    ReportError,
    SandboxJob,
    SubjectError,
    jobs_for,
    migrate_script,
    read_report,
    read_run,
    setup_script,
)
from bumpsmith.rewrite import Plan, Skipped
from bumpsmith.rules import Match, ScanResult, Unreadable
from bumpsmith.run import Completed

GREEN = Completed(returncode=0, output="2 passed in 0.10s\n", where="local")

# Paths inside a sandbox, never on this machine -- the same reason
# `bumpsmith.remote` names its own.
SANDBOX_TMP = "/tmp"  # noqa: S108
ELSEWHERE = "/tmp/elsewhere"  # noqa: S108
RED = Completed(returncode=1, output="1 failed in 0.10s\n", where="local")


def _fixture(fixture_id: str, *, pytest_args: tuple[str, ...] = ()) -> Fixture:
    return Fixture(
        id=fixture_id,
        url=f"https://example.invalid/{fixture_id}.git",
        sha="0" * 40,
        pydantic="1.10.26",
        pytest_args=pytest_args,
        expected_passed=24,
        notes="",
    )


B = _fixture("B")
C = _fixture("C", pytest_args=("--ignore=tests/contrib/django",))


def _applied_step(number: int = 1) -> Step:
    """A step that scanned, planned, wrote, and left nothing behind."""
    return Step(
        number=number,
        run=RED,
        scan=ScanResult(
            matches=(Match(path=Path("a.py"), line=1, excerpt="regex="),),
            unreadable=(),
        ),
        plan=Plan(edits=(), skipped=(), rewritten=1),
        applied=True,
    )


def _report_of(migration: Migration) -> str:
    return json.dumps(migration.as_dict())


# -- the agreement between the two types -------------------------------------


def test_a_reported_verdict_agrees_with_the_migration_it_came_from() -> None:
    """Every derived field, over every outcome, on real objects.

    `Reported` exists because a report cannot honestly be rebuilt into a
    `Migration`. That makes drift between them the standing risk, and this is
    the test that fails when it happens rather than when somebody notices.
    """
    migrations = [
        Migration(steps=(), stop=Stop.GREEN, reason="green before anything"),
        Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="green after one edit"),
        Migration(steps=(_applied_step(),), stop=Stop.NO_RULE, reason="unclassified"),
        Migration(steps=(Step(number=1, run=RED),), stop=Stop.NO_RULE, reason="nothing applied"),
        Migration(steps=(), stop=Stop.NOT_RUN, reason="the suite never ran"),
    ]
    seen = set()
    for migration in migrations:
        reported = read_report(_report_of(migration))
        assert reported.outcome is migration.outcome
        assert reported.applied == migration.applied
        assert reported.kept == migration.kept
        assert reported.complete == migration.complete
        assert reported.stop is migration.stop
        assert reported.reason == migration.reason
        assert len(reported.steps) == len(migration.steps)
        seen.add(migration.outcome)
    # A table that stopped covering an outcome would still pass every assertion
    # above while checking one less thing.
    assert seen == set(Outcome)


def test_an_incomplete_scan_survives_the_round_trip() -> None:
    step = Step(
        number=1,
        run=RED,
        scan=ScanResult(
            matches=(),
            unreadable=(Unreadable(path=Path("vendored.py"), reason="invalid syntax"),),
        ),
    )
    migration = Migration(steps=(step,), stop=Stop.NO_RULE, reason="stopped")
    assert not migration.complete
    assert not read_report(_report_of(migration)).complete


def test_an_incomplete_plan_survives_the_round_trip() -> None:
    step = Step(
        number=1,
        run=GREEN,
        plan=Plan(
            edits=(),
            skipped=(Skipped(path=Path("a.py"), line=3, reason="shadowed by a parameter"),),
            rewritten=0,
        ),
    )
    migration = Migration(steps=(step,), stop=Stop.GREEN, reason="green")
    assert not migration.complete
    assert not read_report(_report_of(migration)).complete


# -- the report as a checksum on itself --------------------------------------


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("outcome", "migrated"),
        ("applied", 4),
        ("kept", True),
        ("complete", False),
    ],
)
def test_a_report_that_disagrees_with_its_own_steps_is_refused(key: str, value: object) -> None:
    """The stated summary is checked against the steps, not preferred to them.

    Each of these is a single edited field in an otherwise perfect report -- the
    shape a truncated write, a hand-fixed file, or a version drift actually
    takes. Read trustingly, every one of them changes what the verdict says
    about somebody's repository.
    """
    body = json.loads(_report_of(Migration(steps=(), stop=Stop.GREEN, reason="green")))
    assert body[key] != value, "the test must actually change the field it names"
    body[key] = value
    with pytest.raises(ReportError, match="disagrees with itself"):
        read_report(json.dumps(body))


def test_a_report_that_agrees_with_itself_is_accepted() -> None:
    """The control for the four tests above.

    A check written slightly too eagerly would refuse every report, and each of
    those tests would pass just as loudly.
    """
    assert read_report(_report_of(Migration(steps=(), stop=Stop.GREEN, reason="g"))).kept is False


def test_a_summary_a_report_does_not_state_is_not_invented() -> None:
    """A report missing an optional summary field is read from its steps."""
    body = json.loads(_report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g")))
    for key in ("outcome", "applied", "kept", "complete"):
        del body[key]
    reported = read_report(json.dumps(body))
    assert reported.outcome is Outcome.MIGRATED
    assert reported.applied == 1
    assert reported.kept is True


def test_a_step_whose_scan_flag_contradicts_its_unreadable_list_is_refused() -> None:
    body = json.loads(_report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g")))
    body["steps"][0]["scan_complete"] = False  # while `unreadable` stays empty
    with pytest.raises(ReportError, match="disagrees with itself"):
        read_report(json.dumps(body))


def test_a_step_that_never_scanned_may_not_claim_a_scan_result() -> None:
    body = json.loads(
        _report_of(Migration(steps=(Step(number=1, run=RED),), stop=Stop.NO_RULE, reason="r"))
    )
    assert body["steps"][0]["sites"] is None
    body["steps"][0]["scan_complete"] = True
    with pytest.raises(ReportError, match="did not scan"):
        read_report(json.dumps(body))


# -- refusing what cannot be read --------------------------------------------


def test_text_that_is_not_json_is_refused() -> None:
    with pytest.raises(ReportError, match="not JSON"):
        read_report("the sandbox printed this instead")


def test_a_truncated_report_is_refused_rather_than_read_as_far_as_it_goes() -> None:
    whole = _report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g"))
    with pytest.raises(ReportError, match="not JSON"):
        read_report(whole[: len(whole) // 2])


def test_a_json_list_is_not_a_report() -> None:
    with pytest.raises(ReportError, match="not an object"):
        read_report("[]")


@pytest.mark.parametrize("key", ["stop", "reason", "steps"])
def test_a_report_missing_something_it_stores_is_refused(key: str) -> None:
    body = json.loads(_report_of(Migration(steps=(), stop=Stop.GREEN, reason="g")))
    del body[key]
    with pytest.raises(ReportError, match=f"no {key!r}"):
        read_report(json.dumps(body))


def test_a_stop_reason_this_package_does_not_have_is_refused() -> None:
    """Version drift, not a migration. A near-enough member would be a guess."""
    body = json.loads(_report_of(Migration(steps=(), stop=Stop.GREEN, reason="g")))
    body["stop"] = "green-ish"
    with pytest.raises(ReportError, match="not a stop reason"):
        read_report(json.dumps(body))


def test_an_applied_flag_that_is_not_a_boolean_is_refused() -> None:
    """`applied` decides whether a tree was written to. It is not coerced."""
    body = json.loads(_report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g")))
    body["steps"][0]["applied"] = "yes"
    with pytest.raises(ReportError, match="not true or false"):
        read_report(json.dumps(body))


def test_a_step_that_is_not_an_object_is_refused() -> None:
    body = json.loads(_report_of(Migration(steps=(), stop=Stop.GREEN, reason="g")))
    body["steps"] = ["step one"]
    with pytest.raises(ReportError, match="not an object"):
        read_report(json.dumps(body))


def test_a_step_without_a_number_is_refused() -> None:
    body = json.loads(_report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g")))
    del body["steps"][0]["step"]
    with pytest.raises(ReportError, match="not a number"):
        read_report(json.dumps(body))


# -- pulling the report out of what the command printed ----------------------


def _printed(report: str, *, rc: int = 0, log: str = "step 1 rc=2\n") -> Completed:
    return Completed(returncode=rc, output=f"{log}{REPORT_MARKER}\n{report}", where="sandbox")


def test_a_run_that_printed_no_report_is_refused() -> None:
    """No marker, no report. The measurement this rule comes from read a field
    off a payload it had not checked and called four empty sandboxes a success.
    """
    ran = Completed(returncode=2, output="Traceback...\nboom\n", where="sandbox")
    with pytest.raises(ReportError, match="printed no report"):
        read_run(ran, "B")


def test_a_run_whose_report_is_empty_is_refused() -> None:
    ran = Completed(returncode=0, output=f"log\n{REPORT_MARKER}\n   \n", where="sandbox")
    with pytest.raises(ReportError, match="report is empty"):
        read_run(ran, "B")


def test_a_nonzero_exit_with_a_report_is_a_verdict_and_not_a_failure() -> None:
    """The distinction the whole module turns on.

    A loop that peeled three breaks and reverted exits non-zero, and that is a
    complete verdict about a repository. Treating the exit code as the
    discriminator would throw it away and report the subject as unreached --
    turning "we tried and it did not go green" into "we never looked".
    """
    migration = Migration(steps=(_applied_step(),), stop=Stop.NO_RULE, reason="unclassified")
    reported = read_run(_printed(_report_of(migration), rc=1), "B")
    assert reported.outcome is Outcome.REVERTED
    assert reported.kept is False


def test_the_subject_is_named_when_a_report_will_not_read() -> None:
    """A fan-out over four subjects produces four of these; an unattributed one
    sends the reader to find out which sandbox it came from."""
    with pytest.raises(ReportError, match="C:"):
        read_run(_printed("{not json"), "C")


# -- the scripts -------------------------------------------------------------


def test_the_workspace_is_cleared_before_anything_reads_it() -> None:
    """A leftover report from a previous attempt would parse perfectly."""
    script = setup_script(Recipe(fixture=B), manifest="m.toml")
    assert script.startswith("rm -rf ")
    assert script.index("rm -rf ") < script.index("git clone")


def test_setup_stops_at_the_first_step_that_fails() -> None:
    """`&&` throughout: a failed clone must not be followed by a successful
    install reporting a workspace with no repository in it."""
    script = setup_script(Recipe(fixture=B), manifest="m.toml")
    assert ";" not in script
    assert script.endswith(f"echo {READY}")


def test_the_suite_command_comes_from_the_manifest_and_is_not_written_here() -> None:
    """C's arguments are its own. A plausible invocation guessed here would
    produce failures belonging to the invocation, classified as breaks."""
    script = migrate_script(Recipe(fixture=C))
    assert "--ignore=tests/contrib/django" in script
    assert "--ignore" not in migrate_script(Recipe(fixture=B))


def test_the_migration_is_not_run_through_a_pipe() -> None:
    """A pipeline reports its last stage's status, so `bumpsmith | tail` reports
    `tail` -- which succeeds whatever happened upstream. The probe that shaped
    this module printed a zero for a run that had failed outright, for exactly
    that reason.
    """
    script = migrate_script(Recipe(fixture=B))
    start = script.index("python -m bumpsmith")
    end = script.index("echo RC=$?")
    assert start < end
    assert "|" not in script[start:end]


def test_a_recipe_without_a_package_does_not_pass_the_flag() -> None:
    assert "--package" not in migrate_script(Recipe(fixture=B))
    assert "--package emnify" in migrate_script(Recipe(fixture=B, package="emnify"))


def test_a_suite_argument_containing_a_space_stays_one_argument() -> None:
    """`-k "not slow"` re-split by the shell would select different tests, and
    the loop would classify whatever they did as breaks."""
    script = migrate_script(Recipe(fixture=_fixture("B", pytest_args=("-k", "not slow"))))
    assert "'not slow'" in script


def test_extra_requirements_are_installed_and_an_empty_list_installs_nothing() -> None:
    with_extras = setup_script(Recipe(fixture=B, install=("pydantic>=2", "vcrpy")), manifest="m")
    assert "'pydantic>=2' vcrpy" in with_extras
    plain = setup_script(Recipe(fixture=B), manifest="m")
    assert plain.count("python -m pip install") == with_extras.count("python -m pip install") - 1


# -- the shapes the orchestrator needs ---------------------------------------


def test_a_reported_verdict_is_a_verdict() -> None:
    assert isinstance(Reported(steps=(), stop=Stop.GREEN, reason="g"), Verdict)


def test_a_migration_is_still_a_verdict() -> None:
    """The protocol was widened for `Reported`; it must not have narrowed away
    from the type it was extracted from."""
    assert isinstance(Migration(steps=(), stop=Stop.GREEN, reason="g"), Verdict)


def test_a_sandbox_job_is_a_job() -> None:
    job = SandboxJob(Recipe(fixture=B), manifest="m.toml")
    assert isinstance(job, Job)
    assert job.subject == "B"


def test_one_job_per_recipe_in_the_order_given() -> None:
    jobs = jobs_for([Recipe(fixture=B), Recipe(fixture=C)], manifest="m.toml")
    assert [job.subject for job in jobs] == ["B", "C"]


def test_a_subject_that_could_not_be_prepared_is_unreached_not_migrated() -> None:
    """The refusal this module exists for, checked through the orchestrator.

    A sandbox that never came up must not arrive as a repository with nothing
    to migrate. Those are the same number and opposite facts.
    """

    class Broken:
        subject = "B"

        def __call__(self) -> Reported:
            raise SubjectError("B was never prepared: the sandbox could not be reached")

    (attempt,) = fan_out([Broken()]).attempts
    assert not attempt.ran
    assert attempt.outcome is None
    assert isinstance(attempt.result, Unreached)
    assert fan_out([Broken()]).counting(Outcome.ALREADY_GREEN) == 0


def test_a_v1_subject_is_installed_without_its_own_dependencies() -> None:
    """The flag that keeps the break in place.

    A project written for pydantic v1 pins pydantic below 2 in its metadata.
    Installing that list after moving the environment to v2 moves it back, the
    suite passes, and the loop truthfully reports a repository with nothing to
    migrate -- having migrated nothing, for a reason nobody would see.
    """
    script = setup_script(Recipe(fixture=B, install=("pydantic>=2",)), manifest="m")
    assert "--no-deps -e " in script
    assert script.index("pydantic>=2") < script.index("--no-deps")


def test_a_v2_subject_may_have_its_dependencies_installed() -> None:
    """Fixture C's baseline of 347 does not reproduce without them."""
    script = setup_script(Recipe(fixture=C, with_dependencies=True), manifest="m")
    assert "--no-deps" not in script
    assert "pip install -q -e " in script


# -- what a report may not claim about a phase that never ran ----------------


def test_a_step_that_never_scanned_may_not_list_unreadable_files() -> None:
    """The shape that parsed cleanly and reported **complete**.

    `is_complete` asks about a scan, so a step claiming there was no scan is
    never incomplete -- and an `unreadable` list beside `sites: null` is a
    contradiction that used to resolve in the reassuring direction. The producer
    never writes that pair; this reader exists for text nobody here produced.
    """
    body = json.loads(
        _report_of(Migration(steps=(Step(number=1, run=RED),), stop=Stop.NO_RULE, reason="r"))
    )
    assert body["steps"][0]["sites"] is None
    body["steps"][0]["unreadable"] = [{"path": "vendored.py", "reason": "invalid syntax"}]
    with pytest.raises(ReportError, match="did not scan"):
        read_report(json.dumps(body))


def test_a_step_that_never_planned_may_not_list_skipped_sites() -> None:
    body = json.loads(
        _report_of(Migration(steps=(Step(number=1, run=RED),), stop=Stop.NO_RULE, reason="r"))
    )
    assert body["steps"][0]["rewritten"] is None
    body["steps"][0]["skipped"] = ["a.py:3"]
    with pytest.raises(ReportError, match="did not plan"):
        read_report(json.dumps(body))


@pytest.mark.parametrize("key", ["sites", "rewritten"])
@pytest.mark.parametrize("value", ["one", True, 1.5])
def test_a_phase_count_that_is_not_a_count_is_refused(key: str, value: object) -> None:
    """ "Not null" is a weaker claim than "a number", and `bool` is an `int`."""
    body = json.loads(_report_of(Migration(steps=(_applied_step(),), stop=Stop.GREEN, reason="g")))
    body["steps"][0][key] = value
    with pytest.raises(ReportError, match="neither a count nor null"):
        read_report(json.dumps(body))


# -- reaching the sandbox a job actually used --------------------------------


def test_a_job_that_has_not_run_has_no_sandbox_to_ask() -> None:
    """Refused rather than answered from a session opened on the spot.

    A fresh `SandboxExec` is a fresh session and therefore a fresh, empty
    sandbox. Asking one of those whether the subject changed gets a confident
    answer from a filesystem that never held the subject.
    """
    job = SandboxJob(Recipe(fixture=C), manifest="m.toml")
    assert job.session_id() is None
    with pytest.raises(SubjectError, match="no sandbox of its own"):
        job.exec_in_its_sandbox("git status --porcelain", SANDBOX_TMP)


def test_a_job_reports_where_it_works_so_a_caller_need_not_guess() -> None:
    job = SandboxJob(Recipe(fixture=C), manifest="m.toml", workspace=ELSEWHERE)
    assert job.workspace == ELSEWHERE
    assert ELSEWHERE in setup_script(Recipe(fixture=C), manifest="m", workspace=ELSEWHERE)
