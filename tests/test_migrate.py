"""Tests for the loop that is the agent.

The important test here is :func:`test_nothing_is_kept_unless_a_run_came_back_green`.
Every other test checks one stop reason; that one asserts the property the loop
exists for, over every way it can end at once -- that a repository is either
green and changed or byte-for-byte what it was. It also asserts that its own
table covers every member of :class:`Stop`, so a tenth stop reason added without
a case fails the test rather than slipping through untested.

The runs are scripted rather than real. That is deliberate and it is the reverse
of the choice made in ``test_run.py``, which starts real subprocesses: what is
under test here is not whether pytest can be executed but what the loop does
with each answer, including the answers a real pytest is hard to provoke into
giving. The one thing scripting could get wrong -- output that does not classify
the way the test assumes -- is pinned separately by
:func:`test_the_scripted_output_classifies_the_way_these_tests_assume`, because a
test whose premise has silently drifted passes while checking nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from bumpsmith import migrate as migrate_module
from bumpsmith.apply import RevertError
from bumpsmith.failures import BreakClass, Failure, RunShape, parse_failures
from bumpsmith.migrate import (
    DEFAULT_STEP_LIMIT,
    SAME_TREE,
    Migration,
    Outcome,
    Step,
    Stop,
    migrate,
)
from bumpsmith.rewrite import Plan, Skipped
from bumpsmith.run import Completed, NeverRanError, TimedOutError

DATA = Path(__file__).parent / "data"

SUITE = ("pytest", "-q")

# --------------------------------------------------------------------------
# A repository, and the runs a suite in it can produce
# --------------------------------------------------------------------------

ACCOUNT = (
    "from pydantic import BaseModel, Field\n"
    "\n"
    "\n"
    "class Account(BaseModel):\n"
    '    sort_code: str = Field(..., regex=r"^\\d{2}-\\d{2}-\\d{2}$")\n'
)
"""The source `field-regex-broken.txt` was recorded against.

Laid out so the recorded traceback's `mypkg/__init__.py:5` names the line that
is really there. The scan does not read the traceback -- it finds sites by
parsing -- but a test whose recorded failure and whose tree disagree is testing
a repository that could not have produced that output.
"""


def _repo(root: Path) -> Path:
    """A repository with exactly one ``regex=`` site."""
    package = root / "mypkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(ACCOUNT, encoding="utf-8")
    return root


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every file under ``root``, by relative path, as bytes.

    Bytes rather than text: a revert that restored the content but changed the
    line endings or the encoding would compare equal as text and be a defect.
    """
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _collection_error(error_type: str, message: str, *, module: str = "tests/test_it.py") -> str:
    """One error in pytest's collection-error layout.

    The frame, banner and trailer shapes are copied from the recorded runs in
    ``tests/data/``; only the exception line varies. Keeping the surrounding
    layout real is what makes ``RunShape.detect`` see a collection error rather
    than an interrupted session.
    """
    return (
        "==================================== ERRORS ====================================\n"
        f"_________________________ ERROR collecting {module} _________________________\n"
        f"{module}:1: in <module>\n"
        "    from mypkg import Account\n"
        "mypkg/__init__.py:4: in <module>\n"
        "    class Account(BaseModel):\n"
        f"E   {error_type}: {message}\n"
        "=========================== short test summary info ============================\n"
        f"ERROR {module} - {error_type}: {message}\n"
        "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!\n"
        "1 error in 0.10s\n"
    )


REGEX_BROKEN = (DATA / "field-regex-broken.txt").read_text(encoding="utf-8")
"""A real run against a real `Field(regex=...)`. Recorded, not written here."""

ROOT_MODEL_BROKEN = _collection_error(
    "TypeError",
    "To define root models, use `pydantic.RootModel` rather than a field called '__root__'",
)

VALIDATOR_BROKEN = _collection_error(
    "pydantic.errors.PydanticUserError",
    "The `field` and `config` parameters are not available in Pydantic V2, "
    "please use the `info` parameter instead.",
)

NO_REWRITER_BROKEN = (DATA / "F4-broken.txt").read_text(encoding="utf-8")
"""A real run whose break has a rule and no rewriter.

Class 1 used to stand here, and stopped being able to the moment it got one.
This is fixture F4's recorded output: `pydantic.utils:DUNDER_ATTRIBUTES` names a
symbol V2 deleted, which narrows to a rule a person can act on and to no edit
this package will write unasked.
"""

DEPENDENCY_BROKEN = _collection_error(
    "ModuleNotFoundError",
    "No module named 'someoldsdk'",
)

UNCLASSIFIABLE = _collection_error(
    "AttributeError",
    "'NoneType' object has no attribute 'split'",
)

INTERRUPTED = (
    "collecting ... collected 12 items\n"
    "\n"
    "!!!!!!!!!!!!!!!!!!!!!!!!!! KeyboardInterrupt !!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
    "/work/repo/conftest.py:9: KeyboardInterrupt\n"
)

GREEN = Completed(returncode=0, output="2 passed in 0.10s\n", where="local")


def _red(output: str, returncode: int = 2) -> Completed:
    return Completed(returncode=returncode, output=output, where="local")


def _elsewhere(output: str, returncode: int = 2) -> Completed:
    """A run that happened somewhere other than the tree being edited."""
    return Completed(returncode=returncode, output=output, where="sandbox")


def _parses_nothing(*_args: object, **_kwargs: object) -> list[Failure]:
    """Stand in for a parser that reads a failing run and finds nothing in it."""
    return []


class _Scripted:
    """A runner that replays prepared answers in order.

    Each answer is either a :class:`Completed` to return or an exception to
    raise. Running out is an error rather than a repeat, because a loop that
    iterated more times than the test scripted is a loop the test is no longer
    describing.
    """

    def __init__(self, *answers: Completed | Exception) -> None:
        self.answers = list(answers)
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def run(self, command: Sequence[str], cwd: Path) -> Completed:
        self.calls.append((tuple(command), cwd))
        if not self.answers:
            raise AssertionError("the loop ran the suite more often than the test scripted")
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


# --------------------------------------------------------------------------
# The premise these tests rest on
# --------------------------------------------------------------------------


def test_the_scripted_output_classifies_the_way_these_tests_assume() -> None:
    """Pin what each scripted run means before anything is concluded from it.

    Three findings in this project so far were defects a test was holding in
    place. Every case below assumes a particular classification and asserts a
    stop reason that follows from it; if the parser stopped agreeing, those
    tests would keep passing while checking a different thing entirely.
    """
    expected = [
        (REGEX_BROKEN, 2, RunShape.COLLECTION_ERROR, BreakClass.REGEX_KEYWORD),
        (ROOT_MODEL_BROKEN, 2, RunShape.COLLECTION_ERROR, BreakClass.ROOT_MODEL),
        (VALIDATOR_BROKEN, 2, RunShape.COLLECTION_ERROR, BreakClass.VALIDATOR_FIELD_CONFIG),
        (DEPENDENCY_BROKEN, 2, RunShape.COLLECTION_ERROR, BreakClass.TRANSITIVE_DEPENDENCY),
        (UNCLASSIFIABLE, 2, RunShape.COLLECTION_ERROR, BreakClass.UNKNOWN),
        (INTERRUPTED, 2, RunShape.INTERRUPTED, BreakClass.UNKNOWN),
    ]
    for output, returncode, shape, break_class in expected:
        failures = parse_failures(
            output, returncode=returncode, project_packages=frozenset({"mypkg"})
        )
        assert failures, f"{shape.name}: nothing parsed"
        assert failures[0].shape is shape
        assert failures[0].break_class is break_class

    assert parse_failures(GREEN.output, returncode=0) == []


# --------------------------------------------------------------------------
# The loop, working
# --------------------------------------------------------------------------


def test_a_break_is_read_fixed_and_kept_when_the_suite_goes_green(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    runner = _Scripted(_red(REGEX_BROKEN), GREEN)

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.GREEN
    assert result.outcome is Outcome.MIGRATED
    assert result.kept
    assert result.applied == 1
    assert "pattern=" in (root / "mypkg" / "__init__.py").read_text(encoding="utf-8")
    assert "regex=" not in (root / "mypkg" / "__init__.py").read_text(encoding="utf-8")


def test_the_runner_is_asked_for_the_command_and_the_root_it_was_given(tmp_path: Path) -> None:
    """The loop does not decide where or what to run; it passes both through."""
    root = _repo(tmp_path)
    runner = _Scripted(GREEN)

    migrate(root, runner, ["a-suite", "--flag"])

    assert runner.calls == [(("a-suite", "--flag"), root)]


def test_a_green_suite_is_left_alone(tmp_path: Path) -> None:
    """Nothing to migrate is not the same as nothing happened."""
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(GREEN)

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.GREEN
    assert result.outcome is Outcome.ALREADY_GREEN
    assert not result.kept
    assert result.applied == 0
    assert len(runner.calls) == 1
    assert _snapshot(root) == before


def test_a_chain_is_peeled_one_break_at_a_time(tmp_path: Path) -> None:
    """The second break is only visible once the first is fixed.

    This is why the loop exists at all rather than a single pass: while
    ``__root__`` aborts collection, the ``regex=`` under it is not lower
    priority, it is unreachable.
    """
    root = tmp_path
    package = root / "mypkg"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from pydantic import BaseModel, Field\n"
        "\n"
        "\n"
        "class Tags(BaseModel):\n"
        "    __root__: list[str]\n"
        "\n"
        "\n"
        "class Account(BaseModel):\n"
        '    sort_code: str = Field(..., regex=r"^\\d+$")\n',
        encoding="utf-8",
    )
    runner = _Scripted(_red(ROOT_MODEL_BROKEN), _red(REGEX_BROKEN), GREEN)

    result = migrate(root, runner, SUITE)

    assert result.outcome is Outcome.MIGRATED
    assert result.applied == 2
    assert [step.rule.break_class for step in result.steps if step.rule is not None] == [
        BreakClass.ROOT_MODEL,
        BreakClass.REGEX_KEYWORD,
    ]
    after = (package / "__init__.py").read_text(encoding="utf-8")
    assert "RootModel" in after
    assert "pattern=" in after
    assert "__root__" not in after
    assert "regex=" not in after


def test_every_step_records_what_it_saw_and_what_it_decided(tmp_path: Path) -> None:
    """The report is the review trail, so it carries evidence and not a verdict."""
    root = _repo(tmp_path)
    result = migrate(root, _Scripted(_red(REGEX_BROKEN), GREEN), SUITE)

    first, second = result.steps
    assert first.number == 1
    assert first.failure is not None
    assert first.failure.break_class is BreakClass.REGEX_KEYWORD
    assert first.rule is not None
    assert first.scan is not None
    assert first.scan.count == 1
    assert first.plan is not None
    assert first.plan.rewritten == 1
    assert first.applied

    assert second.number == 2
    assert second.run.returncode == 0
    assert second.failure is None
    assert not second.applied


# --------------------------------------------------------------------------
# Each way of stopping
# --------------------------------------------------------------------------


def test_a_suite_that_could_not_be_run_is_not_a_red_suite(tmp_path: Path) -> None:
    """An absence of evidence never becomes evidence of a failure."""
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(NeverRanError("pytest could not be started"))

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.NOT_RUN
    assert result.outcome is Outcome.UNTOUCHED
    assert result.steps == ()
    assert _snapshot(root) == before


def test_a_suite_that_stops_being_runnable_after_an_edit_takes_the_edit_back(
    tmp_path: Path,
) -> None:
    """The dangerous case: something was changed, and then nothing could check it."""
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(_red(REGEX_BROKEN), NeverRanError("the sandbox could not be reached"))

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.NOT_RUN
    assert result.outcome is Outcome.REVERTED
    assert result.applied == 1
    assert not result.kept
    assert _snapshot(root) == before


def test_a_timeout_after_an_edit_takes_the_edit_back(tmp_path: Path) -> None:
    """A suite killed for running too long said nothing about whether it passes."""
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(_red(REGEX_BROKEN), TimedOutError("pytest was still running after 600s"))

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.NOT_RUN
    assert result.outcome is Outcome.REVERTED
    assert _snapshot(root) == before


def test_a_run_that_is_not_a_migration_break_is_reported_as_such(tmp_path: Path) -> None:
    """An interrupted session is a problem with the invocation, not with the code."""
    root = _repo(tmp_path)
    result = migrate(root, _Scripted(_red(INTERRUPTED)), SUITE)

    assert result.stop is Stop.NOT_A_BREAK
    assert result.outcome is Outcome.UNTOUCHED
    assert "invocation" in result.reason


def test_a_failure_that_does_not_narrow_to_one_rule_stops(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = migrate(root, _Scripted(_red(UNCLASSIFIABLE)), SUITE)

    assert result.stop is Stop.NO_RULE
    assert result.outcome is Outcome.UNTOUCHED


def test_a_break_no_edit_here_can_fix_stops_and_says_why(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    result = migrate(
        root,
        _Scripted(_red(DEPENDENCY_BROKEN)),
        SUITE,
        project_packages=frozenset({"mypkg"}),
    )

    assert result.stop is Stop.DEPENDENCY
    assert result.outcome is Outcome.UNTOUCHED
    assert "not in this repository's source" in result.reason
    assert "outside this repository" in result.reason
    # The message says which module, and says only what the message can support:
    # a missing import is either uninstalled or unmigrated, and pytest's text
    # does not distinguish them.
    assert "someoldsdk" in result.reason
    assert "installed" in result.reason


def test_a_rule_with_no_rewriter_stops_with_the_rule_as_the_output(tmp_path: Path) -> None:
    """Naming the break is useful even when carrying it out automatically is not."""
    root = _repo(tmp_path)
    result = migrate(root, _Scripted(_red(NO_REWRITER_BROKEN)), SUITE)

    assert result.stop is Stop.NO_REWRITER
    assert result.outcome is Outcome.UNTOUCHED
    step = result.steps[0]
    assert step.rule is not None
    assert step.rule.break_class is BreakClass.REMOVED_INTERNAL
    assert "DUNDER_ATTRIBUTES" in step.rule.summary


def test_a_rule_that_matches_nothing_stops_rather_than_looping(tmp_path: Path) -> None:
    """The break is real, the rule is right, and this repository has no such site."""
    root = _repo(tmp_path)
    result = migrate(root, _Scripted(_red(ROOT_MODEL_BROKEN)), SUITE)

    assert result.stop is Stop.NOTHING_TO_APPLY
    assert result.outcome is Outcome.UNTOUCHED
    step = result.steps[0]
    assert step.scan is not None
    assert step.scan.count == 0


def test_edits_refused_before_they_are_written_stop_the_loop(tmp_path: Path) -> None:
    """`attempt` refuses unsafe edits; the loop reports that instead of forcing them."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "account.py").write_text(ACCOUNT, encoding="utf-8")
    root = tmp_path / "repo"
    (root / "mypkg").mkdir(parents=True)
    (root / "mypkg" / "__init__.py").symlink_to(outside / "account.py")

    result = migrate(root, _Scripted(_red(REGEX_BROKEN)), SUITE)

    assert result.stop is Stop.NOT_APPLIED
    assert result.outcome is Outcome.UNTOUCHED
    assert (outside / "account.py").read_text(encoding="utf-8") == ACCOUNT


def test_the_step_limit_is_a_bound_on_changes_not_on_runs(tmp_path: Path) -> None:
    """The last change is verified like every other one, then given up on."""
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(_red(REGEX_BROKEN), _red(REGEX_BROKEN))

    result = migrate(root, runner, SUITE, step_limit=1)

    assert result.stop is Stop.STEP_LIMIT
    assert result.outcome is Outcome.REVERTED
    assert len(runner.calls) == 2, "the one change made was still verified by a run"
    assert result.applied == 1
    assert _snapshot(root) == before


def test_a_step_limit_of_zero_runs_the_suite_and_changes_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = _snapshot(root)

    result = migrate(root, _Scripted(_red(REGEX_BROKEN)), SUITE, step_limit=0)

    assert result.stop is Stop.STEP_LIMIT
    assert result.outcome is Outcome.UNTOUCHED
    assert _snapshot(root) == before


def test_a_negative_step_limit_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        migrate(_repo(tmp_path), _Scripted(GREEN), SUITE, step_limit=-1)


def test_an_empty_parse_stops_instead_of_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A guard, and it is labelled as one.

    `parse_failures` cannot currently return an empty list for a failing run --
    every layout yields at least one block. The loop reads `failures[0]`
    regardless, so the guard is what stands between a future change there and an
    `IndexError` here. Reaching it needs the monkeypatch, and that is the honest
    way to test a branch whose real trigger does not exist yet.
    """
    root = _repo(tmp_path)
    before = _snapshot(root)
    monkeypatch.setattr(migrate_module, "parse_failures", _parses_nothing)

    result = migrate(root, _Scripted(_red(REGEX_BROKEN)), SUITE)

    assert result.stop is Stop.NOTHING_PARSED
    assert result.outcome is Outcome.UNTOUCHED
    assert _snapshot(root) == before


def test_a_suite_that_ran_somewhere_else_cannot_verify_anything(tmp_path: Path) -> None:
    """`migrate` is public and takes any `Runner`; the CLI's refusal is not a guard.

    A `SandboxRunner` executes in the harness's sandbox, which is a different
    filesystem. A caller holding one reaches this function without going near
    the command line, and a zero from it would keep edits the suite never saw.
    """
    root = _repo(tmp_path)
    before = _snapshot(root)

    result = migrate(root, _Scripted(_elsewhere(REGEX_BROKEN)), SUITE)

    assert result.stop is Stop.WRONG_PLACE
    assert result.outcome is Outcome.UNTOUCHED
    assert "not where the edits are written" in result.reason
    assert _snapshot(root) == before


def test_a_green_run_from_somewhere_else_never_keeps_the_edits(tmp_path: Path) -> None:
    """The dangerous shape: local while it is red, elsewhere the moment it is green.

    This is the one the check exists for. A runner that reported honestly until
    the answer became convenient would, without it, get two edits kept on the
    strength of a suite in another filesystem.
    """
    root = _repo(tmp_path)
    before = _snapshot(root)
    runner = _Scripted(
        _red(REGEX_BROKEN),
        Completed(returncode=0, output="1 passed\n", where="sandbox"),
    )

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.WRONG_PLACE
    assert result.outcome is Outcome.REVERTED
    assert not result.kept
    assert _snapshot(root) == before


def test_the_check_is_on_what_the_run_reports_not_on_the_runner() -> None:
    """A wrapper cannot get past it, because it is not looking at types.

    `SAME_TREE` holds values of `Completed.where`, not runner classes. When
    edits can be carried into a sandbox, this set is the line that changes.
    """
    assert frozenset({"local"}) == SAME_TREE


class _Meddling:
    """A runner that changes a file while the suite is supposedly running.

    Not contrived. The loop holds every transaction open across every later run
    of the suite, so "between apply and revert" is minutes of a test run against
    the same checkout -- and anything writing to it in that window (a developer,
    a formatter on save, a fixture with a bad path) lands exactly here.
    """

    def __init__(self, path: Path, text: str, *answers: Completed, meddle_on: int = 2) -> None:
        self.path = path
        self.text = text
        self.answers = list(answers)
        self.meddle_on = meddle_on
        self.calls = 0

    def run(self, command: Sequence[str], cwd: Path) -> Completed:  # noqa: ARG002
        self.calls += 1
        if self.calls == self.meddle_on:
            self.path.write_text(self.text, encoding="utf-8")
        return self.answers.pop(0)


def test_a_suite_that_edits_the_tree_does_not_get_its_work_thrown_away(
    tmp_path: Path,
) -> None:
    """The revert refuses rather than overwriting, and the loop lets that out.

    `RevertError` is the one failure `migrate` does not turn into a stop reason.
    A caller told "reverted" would carry on against a checkout it no longer
    understands; this has to reach them as an exception.
    """
    root = _repo(tmp_path)
    source = root / "mypkg" / "__init__.py"
    theirs = "# somebody else was editing this\n"
    runner = _Meddling(source, theirs, _red(REGEX_BROKEN), _red(UNCLASSIFIABLE))

    with pytest.raises(RevertError, match="changed after this edit was applied"):
        migrate(root, runner, SUITE)

    assert source.read_text(encoding="utf-8") == theirs


class _Littering:
    """A runner that writes files of its own, the way a real test suite does.

    Not a contrivance either: pytest creates ``.pytest_cache/`` at the rootdir
    and a ``__pycache__/`` beside every module it imports, and a suite with
    fixtures may write a great deal more. ``LocalRunner`` executes in the
    checkout with no isolation, so all of it lands in the tree being migrated.
    """

    def __init__(self, root: Path, *answers: Completed) -> None:
        self.root = root
        self.answers = list(answers)

    def run(self, command: Sequence[str], cwd: Path) -> Completed:  # noqa: ARG002
        cache = self.root / ".pytest_cache"
        cache.mkdir(exist_ok=True)
        (cache / "CACHEDIR.TAG").write_text("Signature: pytest\n", encoding="utf-8")
        pycache = self.root / "mypkg" / "__pycache__"
        pycache.mkdir(exist_ok=True)
        (pycache / "__init__.cpython-313.pyc").write_bytes(b"\xcb\r\r\n")
        return self.answers.pop(0)


def test_what_the_suite_writes_is_outside_the_transaction(tmp_path: Path) -> None:
    """The guarantee is about bumpsmith's edits. It is not about the directory.

    ``attempt`` restores the paths it planned and nothing else, so a reverted
    run leaves the suite's own artefacts exactly where the suite put them. That
    is the intended boundary rather than a leak -- restoring files this process
    never wrote would be a tool deleting somebody's test output -- but it is a
    boundary, and it is the one the README is obliged to describe accurately.

    Pinned here because describing it in prose is what kept going wrong. The
    byte-for-byte claim has been false three times now: in #9 for CRLF,
    symlinks and partial rollback, in #16 for a revert that overwrote somebody
    else's work, and in #18 for exactly this -- the artefacts were invisible to
    `git status` because the fixture gitignores them, so the check cited as
    proof could not see what it was cited for.

    If tree-wide snapshotting is ever added, this test fails, and whoever adds
    it has to change the claim in the same commit.
    """
    root = _repo(tmp_path)
    source = root / "mypkg" / "__init__.py"
    before = source.read_bytes()
    runner = _Littering(root, _red(REGEX_BROKEN), _red(UNCLASSIFIABLE))

    migration = migrate(root, runner, SUITE)

    assert migration.outcome is Outcome.REVERTED
    # Every edit bumpsmith made: taken back, byte for byte.
    assert source.read_bytes() == before
    # Everything the suite wrote: still there, because it was never ours to take.
    assert (root / ".pytest_cache" / "CACHEDIR.TAG").read_text(encoding="utf-8") == (
        "Signature: pytest\n"
    )
    assert (root / "mypkg" / "__pycache__" / "__init__.cpython-313.pyc").is_file()


# --------------------------------------------------------------------------
# Complete is not the same question as green
# --------------------------------------------------------------------------


def test_a_migration_that_could_not_read_a_file_says_so(tmp_path: Path) -> None:
    """A green suite is evidence about the tests that exist, not about the tree."""
    root = _repo(tmp_path)
    (root / "mypkg" / "unparseable.py").write_text("def (\n", encoding="utf-8")

    result = migrate(root, _Scripted(_red(REGEX_BROKEN), GREEN), SUITE)

    assert result.outcome is Outcome.MIGRATED
    assert result.kept
    assert not result.complete, "one candidate file was never read"
    assert result.as_dict()["complete"] is False


def test_a_migration_that_read_everything_is_complete(tmp_path: Path) -> None:
    result = migrate(_repo(tmp_path), _Scripted(_red(REGEX_BROKEN), GREEN), SUITE)

    assert result.complete
    assert result.as_dict()["complete"] is True


def test_a_skipped_site_makes_a_migration_incomplete() -> None:
    """The rewriter matching a site and then declining it is the other half.

    Constructed rather than provoked: which sites the rewriter declines is
    `bumpsmith.rewrite`'s business and is pinned there. What is under test here
    is that `Migration` does not report a plan with a hole in it as finished.
    """
    step = Step(
        number=1,
        run=GREEN,
        plan=Plan(
            edits=(),
            skipped=(Skipped(path=Path("a.py"), line=3, reason="shadowed by a parameter"),),
            rewritten=0,
        ),
    )
    assert not Migration(steps=(step,), stop=Stop.GREEN, reason="green").complete


def test_a_migration_with_nothing_to_say_is_complete() -> None:
    """No scans and no plans is not an incomplete migration; it is no migration."""
    assert Migration(steps=(), stop=Stop.NOT_RUN, reason="nothing ran").complete


# --------------------------------------------------------------------------
# The property all of it exists for
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Case:
    """One way the loop can end, and how to make it end that way."""

    stop: Stop
    answers: tuple[Completed | Exception, ...]
    packages: frozenset[str] = frozenset()
    step_limit: int = DEFAULT_STEP_LIMIT
    symlinked: bool = False
    """Lay the repository out so `attempt` refuses the edits."""

    nothing_parses: bool = False
    """Patch the parser to return nothing, which it cannot currently do."""

    foreign_config: bool = False
    """Put a pytest configuration in the directory *above* the repository."""

    expect: Outcome = Outcome.UNTOUCHED


CASES = (
    _Case(Stop.GREEN, (GREEN,), expect=Outcome.ALREADY_GREEN),
    _Case(Stop.GREEN, (_red(REGEX_BROKEN), GREEN), expect=Outcome.MIGRATED),
    _Case(Stop.NOT_RUN, (NeverRanError("nothing started"),)),
    _Case(
        Stop.NOT_RUN,
        (_red(REGEX_BROKEN), TimedOutError("still running")),
        expect=Outcome.REVERTED,
    ),
    _Case(Stop.NOT_A_BREAK, (_red(INTERRUPTED),)),
    _Case(Stop.NOTHING_PARSED, (_red(REGEX_BROKEN),), nothing_parses=True),
    _Case(Stop.NO_RULE, (_red(UNCLASSIFIABLE),)),
    _Case(Stop.DEPENDENCY, (_red(DEPENDENCY_BROKEN),), packages=frozenset({"mypkg"})),
    _Case(Stop.NO_REWRITER, (_red(NO_REWRITER_BROKEN),)),
    _Case(Stop.NOTHING_TO_APPLY, (_red(ROOT_MODEL_BROKEN),)),
    _Case(Stop.NOT_APPLIED, (_red(REGEX_BROKEN),), symlinked=True),
    _Case(
        Stop.STEP_LIMIT,
        (_red(REGEX_BROKEN), _red(REGEX_BROKEN)),
        step_limit=1,
        expect=Outcome.REVERTED,
    ),
    _Case(Stop.WRONG_PLACE, (_elsewhere(REGEX_BROKEN),)),
    # A green answer is scripted and deliberately never reached: the refusal
    # happens before the suite is run, so the runner is not consulted at all.
    _Case(Stop.FOREIGN_CONFIG, (GREEN,), foreign_config=True),
)


def test_the_cases_cover_every_way_the_loop_can_end() -> None:
    """Adding a stop reason without a case fails here rather than silently."""
    assert {case.stop for case in CASES} == set(Stop)


def test_every_outcome_is_reachable() -> None:
    """The same, for what becomes of the repository."""
    assert {case.expect for case in CASES} == set(Outcome)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.stop.value}-{case.expect.value}")
def test_nothing_is_kept_unless_a_run_came_back_green(
    case: _Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The property the loop exists for, over every way it can end.

    Whatever happened, the repository afterwards is one of two things: changed,
    with a run that returned zero as the reason it was changed; or exactly what
    it was. There is no third state, and in particular no "we improved it a bit
    and could not tell". Checking the interesting stops one at a time would pass
    just as happily on a version that grew a new one and let it keep.
    """
    if case.symlinked:
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "account.py").write_text(ACCOUNT, encoding="utf-8")
        root = tmp_path / "repo"
        (root / "mypkg").mkdir(parents=True)
        (root / "mypkg" / "__init__.py").symlink_to(outside / "account.py")
    else:
        root = _repo(tmp_path / "repo")
    if case.nothing_parses:
        monkeypatch.setattr(migrate_module, "parse_failures", _parses_nothing)
    if case.foreign_config:
        (root.parent / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
        )

    before = _snapshot(root)
    result = migrate(
        root,
        _Scripted(*case.answers),
        SUITE,
        project_packages=case.packages,
        step_limit=case.step_limit,
    )

    assert result.stop is case.stop
    assert result.outcome is case.expect

    if result.outcome is Outcome.MIGRATED:
        assert result.kept
        assert result.steps[-1].run.returncode == 0, "kept on the strength of a green run"
        assert _snapshot(root) != before
        return

    assert not result.kept
    assert _snapshot(root) == before


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def test_a_foreign_configuration_is_refused_before_the_suite_is_ever_run(
    tmp_path: Path,
) -> None:
    """Not after a verdict exists to argue with.

    A green answer is scripted and the runner records every call it receives, so
    "the refusal came first" is checked against an empty call list rather than
    inferred from the outcome. Refusing after the run would produce the same
    `Stop` and the same untouched tree, and would have already spent whatever
    the suite costs on a number nobody may use.
    """
    root = _repo(tmp_path / "repo")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
    )
    runner = _Scripted(GREEN)

    result = migrate(root, runner, SUITE)

    assert result.stop is Stop.FOREIGN_CONFIG
    assert runner.calls == [], "the suite was run before the configuration was checked"
    assert result.steps == ()
    assert str(tmp_path / "pyproject.toml") in result.reason
    assert "addopts" in result.reason


def test_a_command_that_is_not_recognisably_pytest_is_left_alone(tmp_path: Path) -> None:
    """The check is about pytest's rootdir algorithm and claims nothing wider.

    A tox run or a make target sits under the same foreign configuration and is
    not governed by it, so refusing would be a refusal nobody could act on. The
    cost of the narrow reading is a check that does not happen; the cost of the
    wide one is a tool that cannot be used.
    """
    root = _repo(tmp_path / "repo")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
    )

    result = migrate(root, _Scripted(GREEN), ("make", "test"))

    assert result.stop is Stop.GREEN


@pytest.mark.parametrize(
    "command",
    [
        ("pytest", "-q"),
        ("py.test", "-q"),
        ("/somewhere/else/bin/pytest",),
        ("python", "-m", "pytest"),
        ("./venv/bin/python", "-m", "pytest", "-q"),
    ],
)
def test_the_usual_ways_of_spelling_a_pytest_run_are_all_recognised(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    """Each of these is how somebody actually writes it on a command line."""
    root = _repo(tmp_path / "repo")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
    )

    assert migrate(root, _Scripted(GREEN), command).stop is Stop.FOREIGN_CONFIG


def test_the_report_is_derived_from_the_steps_rather_than_stored(tmp_path: Path) -> None:
    """`outcome`, `applied` and `kept` cannot disagree with the steps they come from."""
    result = migrate(_repo(tmp_path), _Scripted(_red(REGEX_BROKEN), GREEN), SUITE)

    assert result.applied == sum(1 for step in result.steps if step.applied)
    assert result.kept is (result.outcome is Outcome.MIGRATED)


def test_a_step_that_wrote_nothing_does_not_claim_to_have_applied(tmp_path: Path) -> None:
    """A rule can match a site already in its target state.

    `attempt` drops edits that change nothing, so a step whose every edit was a
    no-op wrote nothing. Counting it would report a change the tree never saw --
    and the count is what decides whether the outcome reads `migrated`.
    """
    root = tmp_path
    package = root / "mypkg"
    package.mkdir()
    already_fixed = (
        "from pydantic import BaseModel, Field\n"
        "\n"
        "\n"
        "class Account(BaseModel):\n"
        '    sort_code: str = Field(..., pattern=r"^\\d+$")\n'
    )
    (package / "__init__.py").write_text(already_fixed, encoding="utf-8")

    result = migrate(root, _Scripted(_red(REGEX_BROKEN)), SUITE)

    assert result.stop is Stop.NOTHING_TO_APPLY
    assert result.applied == 0
    assert result.outcome is Outcome.UNTOUCHED
    assert (package / "__init__.py").read_text(encoding="utf-8") == already_fixed


def test_the_report_survives_json(tmp_path: Path) -> None:
    """`as_dict` is the review trail's shape, so it has to serialise."""
    import json

    result = migrate(_repo(tmp_path), _Scripted(_red(REGEX_BROKEN), GREEN), SUITE)
    payload = json.loads(json.dumps(result.as_dict()))

    assert payload["outcome"] == "migrated"
    assert payload["stop"] == "green"
    assert payload["kept"] is True
    assert payload["applied"] == 1
    assert [step["step"] for step in payload["steps"]] == [1, 2]
    assert payload["steps"][0]["break_class"] == "REGEX_KEYWORD"
    assert payload["steps"][0]["applied"] is True


def test_a_step_reports_only_as_far_as_it_got(tmp_path: Path) -> None:
    """The `None`s are the record of where the loop stopped, not missing data."""
    result = migrate(_repo(tmp_path), _Scripted(_red(UNCLASSIFIABLE)), SUITE)

    step = result.steps[0]
    assert step.failure is not None
    assert step.rule is None
    assert step.scan is None
    assert step.plan is None
    assert step.as_dict()["rule"] is None
    assert step.as_dict()["sites"] is None


def test_a_migration_is_frozen(tmp_path: Path) -> None:
    """The report is evidence; nothing downstream gets to edit it."""
    import dataclasses

    result = migrate(_repo(tmp_path), _Scripted(GREEN), SUITE)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.stop = Stop.GREEN  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.steps[0].number = 9  # type: ignore[misc]


def test_a_migration_with_no_steps_reads_as_untouched() -> None:
    """Constructible without the loop, because the CLI has to render one."""
    empty = Migration(steps=(), stop=Stop.NOT_RUN, reason="nothing ran")
    assert empty.applied == 0
    assert empty.outcome is Outcome.UNTOUCHED
    assert not empty.kept
    assert empty.as_dict()["steps"] == []


def test_a_step_with_no_plan_has_not_applied() -> None:
    step = Step(number=1, run=GREEN)
    assert not step.applied
