"""Tests for ``python -m bumpsmith``.

These run the real :class:`~bumpsmith.run.LocalRunner` against a real
subprocess. The subprocess is not pytest -- installing a second pydantic into
this environment to break it on purpose would be a strange thing to ask of
anybody running the suite -- but it is faithful in the way that matters: it
reads the file under migration and fails while the break is in it, exactly as
pytest would. A stand-in that returned a scripted answer regardless of the tree
would pass just as happily on a version that never applied the edit.
"""

import argparse
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

from bumpsmith import __main__ as cli
from bumpsmith import publish
from bumpsmith.apply import RevertError
from bumpsmith.gate import NotApprovedError, Request
from bumpsmith.migrate import Migration, Outcome, Step, Stop
from bumpsmith.run import Completed

DATA = Path(__file__).parent / "data"

ACCOUNT = (
    "from pydantic import BaseModel, Field\n"
    "\n"
    "\n"
    "class Account(BaseModel):\n"
    '    sort_code: str = Field(..., regex=r"^\\d{2}-\\d{2}-\\d{2}$")\n'
)

_FAKE_SUITE = """
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
if "regex=" in source:
    sys.stdout.write(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
    raise SystemExit(2)
sys.stdout.write("1 passed in 0.01s\\n")
raise SystemExit(0)
"""
"""A suite that fails while the break is present and passes once it is not.

The whole point of the loop is that the second run is a real observation of the
edited tree. A stand-in that ignored the tree would make every test here pass
against a loop that applied nothing.
"""

_ALWAYS_RED = """
import pathlib
import sys

sys.stdout.write(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(2)
"""


def _repo(root: Path) -> Path:
    package = root / "mypkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(ACCOUNT, encoding="utf-8")
    return root


def _honest_suite(root: Path) -> list[str]:
    """The suite command, behind the `--` that keeps its flags out of argparse's hands."""
    return [
        "--",
        sys.executable,
        "-c",
        _FAKE_SUITE,
        str(root / "mypkg" / "__init__.py"),
        str(DATA / "field-regex-broken.txt"),
    ]


def _always_red(output: Path) -> list[str]:
    return ["--", sys.executable, "-c", _ALWAYS_RED, str(output)]


# --------------------------------------------------------------------------
# It refuses before it does anything
# --------------------------------------------------------------------------


def test_a_suites_own_flags_are_explained_rather_than_just_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The mistake everyone makes once, answered where they make it."""
    with pytest.raises(SystemExit) as raised:
        cli.main(["/tmp", "python", "-m", "pytest", "-q"])  # noqa: S108

    assert raised.value.code == 2
    message = capsys.readouterr().err
    assert "unrecognized arguments" in message
    assert "put `--` in front of it" in message


def test_help_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])
    assert raised.value.code == 0


def test_a_path_that_is_not_a_directory_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main([str(tmp_path / "nowhere")]) == 2
    assert "is not a directory" in capsys.readouterr().err


def test_a_negative_step_count_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main([str(tmp_path), "--steps", "-1"]) == 2
    assert "cannot be negative" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-1", "inf", "-inf", "nan"])
def test_a_timeout_that_is_not_a_number_of_seconds_is_refused(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`inf` and `nan` both parse as floats and neither is <= 0.

    `inf` would silently remove the per-run cap this flag exists to set, and
    `nan` compares false against everything, so `subprocess`'s own timeout check
    never fires either. A flag whose whole purpose is a bound has to refuse the
    values that are not one.
    """
    # Written as one token: argparse reads a bare `-inf` as a flag, not a value.
    assert cli.main([str(tmp_path), f"--timeout={value}"]) == 2
    assert "positive, finite" in capsys.readouterr().err


def test_the_sandbox_flag_is_refused_with_the_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal is the feature.

    Somebody reading this repository will reach for `--sandbox` first, because
    the sandbox is what the harness is for. An unrecognised option teaches them
    nothing; this tells them the sandbox is a different filesystem and what
    would go wrong if the flag pretended otherwise.
    """
    assert cli.main([str(_repo(tmp_path)), "--sandbox"]) == 2
    message = capsys.readouterr().err
    assert "different filesystem" in message
    assert "never reached" in message
    assert "proofs/sandbox.py" in message


def test_the_refusal_happens_before_anything_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--sandbox` on a repository with a break must not migrate it locally instead."""
    root = _repo(tmp_path)
    before = (root / "mypkg" / "__init__.py").read_bytes()

    assert cli.main([str(root), "--sandbox", *_honest_suite(root)]) == 2

    capsys.readouterr()
    assert (root / "mypkg" / "__init__.py").read_bytes() == before


# --------------------------------------------------------------------------
# It runs the loop and says what happened
# --------------------------------------------------------------------------


def test_a_repository_it_can_fix_exits_zero_and_keeps_the_change(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)

    code = cli.main([str(root), *_honest_suite(root)])

    assert code == 0
    out = capsys.readouterr().out
    assert "migrated" in out
    assert "[REGEX_KEYWORD]" in out
    assert "pattern=" in (root / "mypkg" / "__init__.py").read_text(encoding="utf-8")


def test_a_repository_it_cannot_fix_exits_one_and_changes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)
    before = (root / "mypkg" / "__init__.py").read_bytes()

    code = cli.main([str(root), *_always_red(DATA / "field-regex-broken.txt")])

    assert code == 1
    assert "reverted" in capsys.readouterr().out
    assert (root / "mypkg" / "__init__.py").read_bytes() == before


def test_a_green_repository_exits_zero_without_touching_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path
    (root / "mypkg").mkdir()
    (root / "mypkg" / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    code = cli.main([str(root), "--", sys.executable, "-c", "raise SystemExit(0)"])

    assert code == 0
    assert "already green" in capsys.readouterr().out


def test_a_suite_that_cannot_be_started_exits_two_rather_than_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing interpreter is not a failing test, and the exit status has to agree.

    This test previously asserted `1` and was named for it. The docstring on
    `main` had said all along that `2` means the run never got far enough to
    say, and `Stop.NOT_RUN` is exactly that -- so the test was pinning the
    contradiction rather than the contract. Automation that cannot tell a red
    suite from an absent one retries the wrong thing.
    """
    code = cli.main([str(_repo(tmp_path)), "definitely-not-a-real-binary"])

    assert code == 2
    out = capsys.readouterr().out
    assert "untouched" in out
    assert "could not be run" in out


def test_every_stop_maps_to_an_exit_status_and_only_three_exist() -> None:
    """Green is 0, no-usable-result is 2, and everything else is a red suite at 1."""
    assert {cli._status(stop) for stop in Stop} == {0, 1, 2}
    assert cli._status(Stop.GREEN) == 0
    assert {stop for stop in Stop if cli._status(stop) == 2} == cli.NO_RESULT
    assert frozenset({Stop.NOT_RUN, Stop.WRONG_PLACE, Stop.FOREIGN_CONFIG}) == cli.NO_RESULT


def test_a_report_says_when_a_kept_migration_is_not_a_finished_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """ "The suite passes" and "the migration is done" are different claims."""
    root = _repo(tmp_path)
    (root / "mypkg" / "unparseable.py").write_text("def (\n", encoding="utf-8")

    code = cli.main([str(root), *_honest_suite(root)])

    assert code == 0
    out = capsys.readouterr().out
    assert "migrated" in out
    assert "NOT COMPLETE" in out
    assert "unparseable.py" in out


def test_the_command_is_taken_after_a_double_dash(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--` is how a suite of your own gets its own flags through argparse."""
    root = _repo(tmp_path)

    code = cli.main([str(root), "--steps", "3", *_honest_suite(root)])

    assert code == 0
    assert "suite       " in capsys.readouterr().out


def test_the_step_limit_reaches_the_loop(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path)

    code = cli.main([str(root), "--steps", "0", *_honest_suite(root)])

    assert code == 1
    assert "untouched" in capsys.readouterr().out
    assert "regex=" in (root / "mypkg" / "__init__.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The written report
# --------------------------------------------------------------------------


def test_the_json_report_carries_the_run_and_the_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path / "repo")
    destination = tmp_path / "evidence.json"

    code = cli.main([str(root), "--json", str(destination), *_honest_suite(root)])

    assert code == 0
    capsys.readouterr()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["repository"] == str(root.resolve())
    assert payload["command"][0] == sys.executable
    assert payload["outcome"] == "migrated"
    assert payload["kept"] is True
    assert payload["steps"][0]["break_class"] == "REGEX_KEYWORD"


def test_json_and_html_may_not_name_the_same_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both would be written, in turn, and the command would exit 0 saying so.

    The JSON asked for would be gone, replaced by HTML, with two successful
    writes reported. Refusing is the only answer that does not require the user
    to notice.
    """
    root = _repo(tmp_path / "repo")
    destination = tmp_path / "report.out"

    code = cli.main(
        [str(root), "--json", str(destination), "--html", str(destination), *_honest_suite(root)]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "--json and --html both name" in captured.err
    assert not destination.exists()
    # Nothing on stdout at all -- not even the `repository` header, which is
    # printed before the loop starts. A bad invocation should cost nothing, and
    # this one would otherwise cost a full migration before failing.
    assert captured.out == ""


def test_two_spellings_of_one_path_are_still_one_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`out.html` and `./out.html` collide; comparing what was typed would miss it."""
    monkeypatch.chdir(tmp_path)
    root = _repo(tmp_path / "repo")

    code = cli.main([str(root), "--json", "report.out", "--html", "./report.out"])

    assert code == 2
    assert "--json and --html both name" in capsys.readouterr().err


def test_an_empty_open_pr_is_answered_rather_than_absorbed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--open-pr "$REMOTE"` with the variable unset asks, and names nowhere.

    A truthiness test reads the empty string as never having asked, so the
    migration runs, exits 0, and silently does not do the thing it was told to.
    Same principle as the colliding report paths: a bad invocation is answered.
    """
    root = _repo(tmp_path / "repo")

    code = cli.main([str(root), "--open-pr", "", *_honest_suite(root)])

    captured = capsys.readouterr()
    assert code == 2
    assert "--open-pr needs the name of a git remote" in captured.err
    assert captured.out == "", "the suite ran before the invocation was checked"


def test_a_pull_request_that_was_asked_for_and_did_not_happen_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The branch is pushed and there is no pull request. That is not a success.

    A caller reading only the exit status would be told it was. 2 rather than 1,
    because 1 means the suite is red and here the suite is green -- what failed
    is the operation.
    """
    proposal = publish.Proposal(
        root=tmp_path,
        remote="fork",
        url="/srv/git/thing.git",
        branch="b",
        base="trunk",
        title="t",
        body="b",
        targets=(("a.py", "before", "after", "utf-8"),),
    )
    opened = publish.Opened(branch="b", pushed_to="/srv/git/thing.git", note="pushed, not opened")

    def _open(gate: object, _proposal: object, _runner: object) -> publish.Opened:  # noqa: ARG001
        return opened

    args = argparse.Namespace(open_pr="fork", pr_branch="b", pr_base="trunk")
    with (
        mock.patch.object(cli, "propose", return_value=proposal),
        mock.patch.object(cli, "open_pull_request", _open),
    ):
        code = cli._publish(mock.Mock(), tmp_path, args, mock.Mock())

    assert code == 2
    assert "pushed, not opened" in capsys.readouterr().out


def test_a_refusal_leaves_the_status_the_suite_earned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Somebody was asked and said no. Making that cost something makes saying no expensive."""
    args = argparse.Namespace(open_pr="fork", pr_branch="b", pr_base="trunk")

    def _refuse(*_args: object, **_kwargs: object) -> object:
        raise NotApprovedError(Request(action="open_pull_request", summary="s"), "said no")

    with (
        mock.patch.object(cli, "propose", return_value=mock.Mock()),
        mock.patch.object(cli, "open_pull_request", _refuse),
    ):
        code = cli._publish(mock.Mock(), tmp_path, args, mock.Mock())

    assert code == 0
    assert "not opened" in capsys.readouterr().out


def test_a_report_that_cannot_be_written_is_an_error_not_a_shrug(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path / "repo")

    code = cli.main(
        [
            str(root),
            "--json",
            str(tmp_path / "no" / "such" / "dir" / "r.json"),
            *_honest_suite(root),
        ]
    )

    assert code == 2
    assert "could not write" in capsys.readouterr().err


def test_a_failed_revert_is_not_reported_as_an_ordinary_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The working tree is in a state nobody chose, and the exit code says so.

    Provoked with a patch because the real trigger is a filesystem that accepts
    a write and then refuses one, which is not something a test should arrange
    for real.
    """

    def _explode(*_args: object, **_kwargs: object) -> Migration:
        raise RevertError("model.py could not be restored")

    monkeypatch.setattr(cli, "migrate", _explode)

    code = cli.main([str(_repo(tmp_path)), "--", sys.executable, "-c", "pass"])

    assert code == 2
    err = capsys.readouterr().err
    assert "could not be taken back" in err
    assert "needs looking at" in err


# --------------------------------------------------------------------------
# The report is built, not printed, so this is what a user sees
# --------------------------------------------------------------------------


def test_the_report_names_the_outcome_and_the_reason() -> None:
    empty = Migration(steps=(), stop=Stop.NOT_RUN, reason="pytest could not be started")
    text = cli.report(empty)

    assert "untouched" in text
    assert "pytest could not be started" in text
    assert "change" not in text, "nothing was applied, so there is no count to report"


def test_every_outcome_has_a_headline() -> None:
    """A new outcome without a line here would raise KeyError mid-report."""
    assert set(cli._HEADLINE) == set(Outcome)


def test_a_run_that_could_not_read_every_file_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unreadable file makes a scan incomplete, and the report must not hide it."""
    root = _repo(tmp_path)
    (root / "mypkg" / "broken.py").write_text("def (\n", encoding="utf-8")

    cli.main([str(root), *_always_red(DATA / "field-regex-broken.txt")])

    out = capsys.readouterr().out
    assert "unreadable" in out
    assert "broken.py" in out


def test_the_json_report_names_unreadable_files_with_their_reasons(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The review trail has to carry both halves, because a second reader needs them.

    The terminal report reads `Unreadable` straight off the object and has
    always printed the reason. `as_dict` serialised the path alone, so anything
    downstream of the JSON -- the HTML page, a reviewer, a later tool -- got
    "this file could not be read" with no way to find out why. The class has
    carried both since it was written; only the serialisation dropped one.
    """
    root = _repo(tmp_path)
    (root / "mypkg" / "broken.py").write_text("def (\n", encoding="utf-8")
    destination = tmp_path / "evidence.json"

    cli.main([str(root), "--json", str(destination), *_always_red(DATA / "field-regex-broken.txt")])
    capsys.readouterr()

    payload = json.loads(destination.read_text(encoding="utf-8"))
    unreadable = [entry for step in payload["steps"] for entry in step["unreadable"]]
    assert unreadable, "the run read a file it could not parse and the report does not say so"
    assert all(entry["path"] and entry["reason"] for entry in unreadable), unreadable
    assert any("broken.py" in entry["path"] for entry in unreadable)


def test_the_default_command_is_this_interpreter() -> None:
    """`python` would resolve against PATH; the interpreter running us will not move."""
    assert cli.DEFAULT_COMMAND[0] == sys.executable
    assert "pytest" in cli.DEFAULT_COMMAND


def test_a_completed_run_is_rendered_with_where_it_ran() -> None:
    """A pass on a laptop and a pass in a sandbox are the same code and different evidence."""
    step = Step(number=1, run=Completed(returncode=0, output="", where="sandbox"))
    assert "(sandbox)" in "\n".join(cli._describe_step(step))
