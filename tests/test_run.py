"""Tests for where the suite runs.

The important test in here is :func:`test_no_bad_answer_ever_becomes_a_result`.
Every other test checks one rejection; that one asserts the property the module
exists for, over every malformed shape at once -- that nothing which is not a
completed run can leave this module as a :class:`Completed`. Spot-checking the
rejections one at a time would pass just as happily on a version that grew a
new field and quietly let it through.

The :class:`LocalRunner` tests start real subprocesses rather than patching
:mod:`subprocess`. A test that asserts a mock was called with ``timeout=`` shows
that the argument was passed, not that a hung command is survivable.
"""

import dataclasses
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from bumpsmith.run import (
    Completed,
    Exec,
    LocalRunner,
    NeverRanError,
    RunError,
    Runner,
    SandboxRunner,
    TimedOutError,
    read_exec_json,
)

PY = sys.executable


def _ok(exit_code: int = 0, result: str = "") -> dict[str, Any]:
    """The shape TrueForge returns for a command that ran."""
    return {"success": True, "response": {"exitCode": exit_code, "result": result}}


_UNSET = object()


class _Exec:
    """Records what it was asked to run and replays a prepared answer.

    The sentinel matters: `None` is one of the malformed answers under test, so
    a default of `answer=None` would substitute a *valid* result for the case
    that exists to check the invalid one. It did, and
    `test_no_bad_answer_ever_becomes_a_result` is what noticed.
    """

    def __init__(self, answer: object = _UNSET, raises: Exception | None = None) -> None:
        self.answer = _ok() if answer is _UNSET else answer
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    def __call__(self, command: str, cwd: str) -> Any:
        self.calls.append((command, cwd))
        if self.raises is not None:
            raise self.raises
        return self.answer


# --------------------------------------------------------------------------
# The protocol
# --------------------------------------------------------------------------


def test_both_runners_satisfy_the_protocol() -> None:
    local: Runner = LocalRunner()
    sandbox: Runner = SandboxRunner(_Exec())
    assert local is not None
    assert sandbox is not None


def test_a_completed_run_cannot_be_edited_afterwards() -> None:
    completed = Completed(returncode=0, output="fine", where="local")
    with pytest.raises(dataclasses.FrozenInstanceError):
        completed.returncode = 1  # type: ignore[misc]


# --------------------------------------------------------------------------
# LocalRunner -- real processes
# --------------------------------------------------------------------------


def test_local_reports_a_zero_status(tmp_path: Path) -> None:
    result = LocalRunner().run([PY, "-c", "print('hello')"], tmp_path)
    assert result.returncode == 0
    assert "hello" in result.output
    assert result.where == "local"


def test_local_reports_a_non_zero_status_without_raising(tmp_path: Path) -> None:
    # The pytest case: a failing suite is the signal, not an error.
    result = LocalRunner().run([PY, "-c", "raise SystemExit(1)"], tmp_path)
    assert result.returncode == 1


def test_local_keeps_stdout_and_stderr_in_the_order_they_were_written(tmp_path: Path) -> None:
    script = (
        "import sys\n"
        "print('first', flush=True)\n"
        "print('second', file=sys.stderr, flush=True)\n"
        "print('third', flush=True)\n"
    )
    output = LocalRunner().run([PY, "-c", script], tmp_path).output
    assert output.index("first") < output.index("second") < output.index("third")


def test_local_runs_in_the_directory_it_was_given(tmp_path: Path) -> None:
    result = LocalRunner().run([PY, "-c", "import os; print(os.getcwd())"], tmp_path)
    assert str(tmp_path.resolve()) in result.output


def test_a_missing_binary_never_ran(tmp_path: Path) -> None:
    with pytest.raises(NeverRanError):
        LocalRunner().run(["bumpsmith-no-such-binary", "--version"], tmp_path)


def test_an_unreadable_directory_never_ran(tmp_path: Path) -> None:
    with pytest.raises(NeverRanError):
        LocalRunner().run([PY, "-c", "pass"], tmp_path / "does-not-exist")


def test_a_hung_command_times_out_and_says_so(tmp_path: Path) -> None:
    with pytest.raises(TimedOutError):
        LocalRunner(timeout=0.2).run([PY, "-c", "import time; time.sleep(30)"], tmp_path)


def test_a_timeout_is_not_a_never_ran(tmp_path: Path) -> None:
    # Both are refusals, and a caller deciding whether to retry needs the
    # difference: one machine did nothing, the other may have done everything.
    with pytest.raises(TimedOutError) as caught:
        LocalRunner(timeout=0.2).run([PY, "-c", "import time; time.sleep(30)"], tmp_path)
    assert not isinstance(caught.value, NeverRanError)


def test_an_empty_command_never_ran(tmp_path: Path) -> None:
    with pytest.raises(NeverRanError):
        LocalRunner().run([], tmp_path)


# --------------------------------------------------------------------------
# SandboxRunner -- the contract
# --------------------------------------------------------------------------


def test_the_sandbox_reports_a_zero_status(tmp_path: Path) -> None:
    result = SandboxRunner(_Exec(_ok(0, "2 passed"))).run([PY, "-m", "pytest"], tmp_path)
    assert result == Completed(returncode=0, output="2 passed", where="sandbox")


def test_a_failing_suite_in_the_sandbox_is_a_result_not_an_error(tmp_path: Path) -> None:
    # `success: true` with a non-zero exitCode is TrueForge saying the command
    # ran and failed. For pytest that is the entire point of running it.
    result = SandboxRunner(_Exec(_ok(1, "1 failed"))).run([PY, "-m", "pytest"], tmp_path)
    assert result.returncode == 1
    assert result.output == "1 failed"


def test_an_unreachable_sandbox_never_ran(tmp_path: Path) -> None:
    answer = {"success": False, "error": "sandbox unavailable"}
    with pytest.raises(NeverRanError, match="sandbox unavailable"):
        SandboxRunner(_Exec(answer)).run([PY, "-m", "pytest"], tmp_path)


def test_a_refusal_with_no_reason_still_refuses(tmp_path: Path) -> None:
    with pytest.raises(NeverRanError, match="no reason given"):
        SandboxRunner(_Exec({"success": False})).run([PY, "-m", "pytest"], tmp_path)


def test_a_transport_that_raises_never_ran(tmp_path: Path) -> None:
    exec_ = _Exec(raises=ConnectionError("no session"))
    with pytest.raises(NeverRanError, match="could not be reached"):
        SandboxRunner(exec_).run([PY, "-m", "pytest"], tmp_path)


def test_a_command_that_wrote_nothing_is_not_a_refusal(tmp_path: Path) -> None:
    answer = {"success": True, "response": {"exitCode": 0}}
    assert SandboxRunner(_Exec(answer)).run([PY, "-c", "pass"], tmp_path).output == ""


def test_the_sandbox_is_told_where_to_run(tmp_path: Path) -> None:
    exec_ = _Exec()
    SandboxRunner(exec_).run([PY, "-c", "pass"], tmp_path)
    assert exec_.calls[0][1] == str(tmp_path)


# --------------------------------------------------------------------------
# One argv, two executions, no shell either side
# --------------------------------------------------------------------------


def test_a_path_with_a_space_stays_one_argument(tmp_path: Path) -> None:
    exec_ = _Exec()
    SandboxRunner(exec_).run(["pytest", "tests/a b.py"], tmp_path)
    assert exec_.calls[0][0] == "pytest 'tests/a b.py'"


def test_a_quote_in_an_argument_is_escaped(tmp_path: Path) -> None:
    exec_ = _Exec()
    SandboxRunner(exec_).run(["echo", "it's"], tmp_path)
    # The same single-quote idiom TrueForge's own shellEscape uses.
    assert exec_.calls[0][0] == "echo 'it'\"'\"'s'"


@pytest.mark.parametrize(
    "argument",
    ["$HOME", "`whoami`", "a; rm -rf /", "*", "$(id)", "a\nb"],
)
def test_shell_syntax_in_an_argument_is_never_interpreted(argument: str, tmp_path: Path) -> None:
    # The argument reaches the sandbox quoted, so the shell there sees one
    # literal word. A runner that joined argv with spaces would send these as
    # syntax.
    exec_ = _Exec()
    SandboxRunner(exec_).run(["echo", argument], tmp_path)
    sent = exec_.calls[0][0]
    assert sent.startswith("echo '")
    assert argument in sent


def test_an_empty_command_never_reaches_the_sandbox(tmp_path: Path) -> None:
    exec_ = _Exec()
    with pytest.raises(NeverRanError):
        SandboxRunner(exec_).run([], tmp_path)
    assert exec_.calls == []


# --------------------------------------------------------------------------
# Malformed answers
# --------------------------------------------------------------------------

MALFORMED: list[tuple[str, object]] = [
    ("not an object", ["success", True]),
    ("a bare string", "ok"),
    ("nothing at all", None),
    ("no success field", {"response": {"exitCode": 0, "result": ""}}),
    ("success is null", {"success": None, "response": {"exitCode": 0}}),
    ("success is a string", {"success": "true", "response": {"exitCode": 0}}),
    ("success is 1", {"success": 1, "response": {"exitCode": 0}}),
    ("success without a response", {"success": True}),
    ("response is a string", {"success": True, "response": "done"}),
    ("no exitCode", {"success": True, "response": {"result": "ok"}}),
    ("exitCode is true", {"success": True, "response": {"exitCode": True, "result": ""}}),
    ("exitCode is a string", {"success": True, "response": {"exitCode": "1", "result": ""}}),
    ("exitCode is null", {"success": True, "response": {"exitCode": None}}),
    ("result is a number", {"success": True, "response": {"exitCode": 0, "result": 3}}),
    ("result is a list", {"success": True, "response": {"exitCode": 0, "result": []}}),
]


@pytest.mark.parametrize(("why", "answer"), MALFORMED, ids=[why for why, _ in MALFORMED])
def test_a_malformed_answer_never_ran(why: str, answer: object, tmp_path: Path) -> None:
    assert why
    with pytest.raises(NeverRanError):
        SandboxRunner(_Exec(answer)).run([PY, "-m", "pytest"], tmp_path)


def test_no_bad_answer_ever_becomes_a_result(tmp_path: Path) -> None:
    """The property the module exists for.

    Not one rejection at a time: every shape that is not a completed run, all
    asserted at once to produce no :class:`Completed` at all. The failure this
    guards against is a sandbox outage that parses as a suite with no failures
    -- which would be kept, and recorded as verified.
    """
    bad: list[object] = [answer for _, answer in MALFORMED]
    bad.append({"success": False, "error": "boom"})
    results: list[Completed] = []
    for answer in bad:
        try:
            results.append(SandboxRunner(_Exec(answer)).run([PY, "-m", "pytest"], tmp_path))
        except RunError:
            continue
    assert results == []


def test_a_bool_exit_code_is_not_read_as_a_failing_suite(tmp_path: Path) -> None:
    # `bool` is an `int` in Python. Read loosely, `exitCode: true` is 1, and a
    # green suite would be reported as one that failed.
    answer = {"success": True, "response": {"exitCode": True, "result": "1 passed"}}
    with pytest.raises(NeverRanError, match="not a status"):
        SandboxRunner(_Exec(answer)).run([PY, "-m", "pytest"], tmp_path)


# --------------------------------------------------------------------------
# The result as the tool actually returns it: text holding JSON
# --------------------------------------------------------------------------


def test_a_json_result_reads_the_same_as_a_decoded_one() -> None:
    assert read_exec_json(json.dumps(_ok(1, "1 failed"))) == Completed(
        returncode=1, output="1 failed", where="sandbox"
    )


def test_a_result_that_is_not_json_never_ran() -> None:
    with pytest.raises(NeverRanError, match="not JSON"):
        read_exec_json("Sandbox initialization failed: no provider configured")


def test_a_truncated_json_result_never_ran() -> None:
    with pytest.raises(NeverRanError, match="not JSON"):
        read_exec_json('{"success": true, "response": {"exitCode": 0, "resu')


def test_an_error_result_read_from_json_never_ran() -> None:
    with pytest.raises(NeverRanError, match="auth failure"):
        read_exec_json(json.dumps({"success": False, "error": "auth failure"}))


def test_the_command_is_named_in_the_refusal() -> None:
    with pytest.raises(NeverRanError, match="pytest -q"):
        read_exec_json("not json at all", command="pytest -q")


# --------------------------------------------------------------------------
# The two runners agree
# --------------------------------------------------------------------------


def test_the_same_command_reads_the_same_from_both_runners(tmp_path: Path) -> None:
    """Only `where` should differ.

    The seam is worth nothing if a caller has to know which runner it holds.
    """
    script = "import sys; print('out'); sys.exit(3)"
    local = LocalRunner().run([PY, "-c", script], tmp_path)
    sandbox = SandboxRunner(_Exec(_ok(local.returncode, local.output))).run(
        [PY, "-c", script], tmp_path
    )
    assert (local.returncode, local.output.strip()) == (sandbox.returncode, sandbox.output.strip())
    assert (local.where, sandbox.where) == ("local", "sandbox")


def test_an_exec_callable_is_all_the_sandbox_runner_needs(tmp_path: Path) -> None:
    # A plain function satisfies `Exec`; no transport, no session, no harness.
    def answer(command: str, cwd: str) -> dict[str, Any]:
        assert command and cwd
        return _ok(0, "ok")

    exec_: Exec = answer
    assert SandboxRunner(exec_).run(["true"], tmp_path).output == "ok"


# --------------------------------------------------------------------------
# The format as the harness actually sends it
# --------------------------------------------------------------------------

RECORDED = Path(__file__).parent / "data" / "sandbox-exec-regex.json"


def _recorded() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(RECORDED.read_text(encoding="utf-8"))
    return loaded


def test_a_real_sandbox_result_reads_as_a_completed_run() -> None:
    """Against what TrueForge sent, not against what I think it sends.

    Every other sandbox test in this file uses a payload written by the same
    person who wrote the parser, which proves only that the two agree.
    """
    completed = _read_recorded()
    assert completed == Completed(
        returncode=2,
        output=completed.output,
        where="sandbox",
    )
    assert "`regex` is removed" in completed.output


def _read_recorded() -> Completed:
    exec_ = _Exec(_recorded()["result"])
    return SandboxRunner(exec_).run(["python", "-m", "pytest", "-q"], Path("/workspace/demo"))


def test_the_recorded_result_is_the_shape_the_module_documents() -> None:
    result = _recorded()["result"]
    assert result["success"] is True
    assert set(result["response"]) == {"exitCode", "result"}
    # Non-zero and *not* an error: the case the module exists to keep separate.
    assert result["response"]["exitCode"] != 0


def test_a_real_sandbox_result_parses_into_a_failure_bumpsmith_can_classify() -> None:
    """The join, on real output: sandbox -> Completed -> parsed break."""
    from bumpsmith.failures import parse_failures

    completed = _read_recorded()
    failures = parse_failures(completed.output, returncode=completed.returncode)
    assert len(failures) == 1
    assert failures[0].break_class.name == "REGEX_KEYWORD"


def test_the_recorded_result_survives_the_json_round_trip() -> None:
    # The transport hands back text, not an object; both doors reach the same place.
    as_text = json.dumps(_recorded()["result"])
    assert read_exec_json(as_text).returncode == 2


# --------------------------------------------------------------------------
# What a timeout leaves behind
# --------------------------------------------------------------------------


def _still_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # pragma: no cover - exists, not ours
        return True
    return True


def _wait_until_gone(pid: int, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _still_alive(pid):
            return True
        time.sleep(0.05)
    return False


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_a_timeout_kills_what_the_command_started(tmp_path: Path) -> None:
    """The finding: a suite is not one process.

    pytest-xdist workers, a fixture that starts a server, anything using
    `subprocess`. Killing only the parent leaves those running against the same
    checkout `bumpsmith.apply` is about to revert.
    """
    pidfile = tmp_path / "child.pid"
    script = (
        "import os, subprocess, sys, time\n"
        f"child = subprocess.Popen([{PY!r}, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(pidfile)!r}, 'w').write(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    with pytest.raises(TimedOutError):
        LocalRunner(timeout=3.0).run([PY, "-c", script], tmp_path)

    assert pidfile.exists(), "the grandchild never started; the test proves nothing"
    child_pid = int(pidfile.read_text())
    assert _wait_until_gone(child_pid), f"pid {child_pid} outlived the timeout"


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_the_command_runs_in_its_own_process_group(tmp_path: Path) -> None:
    # The mechanism the test above depends on, asserted directly so a
    # regression names itself instead of showing up as a flaky orphan.
    result = LocalRunner().run([PY, "-c", "import os; print(os.getpgrp())"], tmp_path)
    assert result.output.strip() != str(os.getpgrp())


# --------------------------------------------------------------------------
# Output that is not text
# --------------------------------------------------------------------------


def test_output_that_is_not_utf8_is_still_a_result(tmp_path: Path) -> None:
    """A project whose output is not valid UTF-8 is an ordinary thing to migrate.

    It must not raise past a contract promising a `Completed` or a `RunError`.
    """
    script = "import sys; sys.stdout.buffer.write(b'before \\xff\\xfe after'); sys.exit(1)"
    result = LocalRunner().run([PY, "-c", script], tmp_path)
    assert result.returncode == 1
    assert "before" in result.output
    assert "after" in result.output


def test_undecodable_bytes_do_not_cost_the_surrounding_output(tmp_path: Path) -> None:
    # `replace` rather than `strict`: losing a byte to U+FFFD costs a character
    # in a diagnostic, and raising costs the run.
    script = (
        "import sys\n"
        "sys.stdout.buffer.write(b'E   assert \\xff failed\\n')\n"
        "sys.stdout.buffer.write(b'1 failed\\n')\n"
    )
    output = LocalRunner().run([PY, "-c", script], tmp_path).output
    assert "assert" in output
    assert "1 failed" in output


def test_output_is_decoded_the_same_way_regardless_of_locale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The encoding is pinned, not taken from the environment, so the same suite
    # reads the same way here and in the sandbox.
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    script = "import sys; sys.stdout.buffer.write('café ✓'.encode('utf-8'))"
    assert "café ✓" in LocalRunner().run([PY, "-c", script], tmp_path).output


# --------------------------------------------------------------------------
# Who gets to say whether the command started
# --------------------------------------------------------------------------


def test_a_transport_timeout_stays_a_timeout(tmp_path: Path) -> None:
    """The finding: only the transport knows whether the command started.

    Rewriting its `TimedOutError` as `NeverRanError` would state the opposite of
    what happened -- and `NeverRanError` promises the working tree is untouched,
    which after a sandbox exec that ran for a minute is simply false.
    """
    exec_ = _Exec(raises=TimedOutError("exec_timeout_ms elapsed"))
    with pytest.raises(TimedOutError):
        SandboxRunner(exec_).run([PY, "-m", "pytest"], tmp_path)


def test_a_transport_that_says_it_never_ran_is_believed(tmp_path: Path) -> None:
    exec_ = _Exec(raises=NeverRanError("no session"))
    with pytest.raises(NeverRanError, match="no session"):
        SandboxRunner(exec_).run([PY, "-m", "pytest"], tmp_path)


def test_an_unclassified_transport_failure_is_read_as_never_ran(tmp_path: Path) -> None:
    # The safe reading of "I do not know" is that it did not start.
    exec_ = _Exec(raises=RuntimeError("socket closed"))
    with pytest.raises(NeverRanError, match="could not be reached"):
        SandboxRunner(exec_).run([PY, "-m", "pytest"], tmp_path)


def test_a_transport_timeout_is_not_reported_as_never_ran(tmp_path: Path) -> None:
    exec_ = _Exec(raises=TimedOutError("gave up mid-flight"))
    with pytest.raises(RunError) as caught:
        SandboxRunner(exec_).run([PY, "-m", "pytest"], tmp_path)
    assert not isinstance(caught.value, NeverRanError)


@pytest.mark.skipif(os.name != "posix", reason="process groups are POSIX")
def test_cleanup_never_signals_the_callers_own_group(tmp_path: Path) -> None:
    """Measured, not theorised.

    With `start_new_session` off the child stays in the runner's group, and
    signalling that group kills the caller -- pytest included. The run ends with
    no output at all, which is why this is asserted directly rather than left to
    the timeout test to notice.
    """
    from bumpsmith.run import _end_process_tree

    process = subprocess.Popen(  # noqa: S603
        [PY, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=False,  # deliberately: the unsafe arrangement
    )
    assert os.getpgid(process.pid) == os.getpgrp(), "setup is wrong; no risk to detect"
    try:
        _end_process_tree(process)
        # Reaching this line at all is half the assertion: the caller is alive.
        # The other half is that the child still died -- degrading to killing one
        # process is the point, refusing to kill anything would not be.
        #
        # `wait` rather than a liveness poll: a killed child is a zombie until
        # someone reaps it, and a zombie answers `kill(pid, 0)` exactly as a
        # running process does.
        assert process.wait(timeout=10) < 0, "the child was not killed by a signal"
    finally:
        if process.poll() is None:  # pragma: no cover - cleanup safety
            process.kill()
            process.wait(timeout=10)


# -- what a refusal is able to say for itself --------------------------------

QUOTA = "Sandbox initialization failed: Total disk limit exceeded. Maximum allowed: 30GiB."


def test_a_refusal_carries_the_reason_the_harness_gave_as_content_blocks() -> None:
    """The real shape, which the string-only reading dropped.

    TrueForge sends `error` as a model turn's content blocks. Read as a string
    it is not one, so this used to raise "no reason given" while holding a
    sentence naming a disk quota. The refusal was right and told nobody why.
    """
    with pytest.raises(NeverRanError, match="disk limit exceeded"):
        read_exec_json(
            json.dumps({"success": False, "error": [{"type": "text", "text": QUOTA}]}), "pytest"
        )


def test_a_result_with_no_success_field_still_reports_what_went_wrong() -> None:
    """A sandbox that never came up answers with an error and no `success`.

    That is the case the harness has the most to say about and the one this
    module used to say the least about -- it named the missing field and
    discarded the explanation sitting beside it. Measured against a live
    quota failure on 27 Aug 2026.
    """
    with pytest.raises(NeverRanError) as caught:
        read_exec_json(json.dumps({"error": [{"type": "text", "text": QUOTA}]}), "pytest")
    assert "disk limit exceeded" in str(caught.value)
    assert "neither true nor false" in str(caught.value), "the shape complaint is still the fact"


def test_a_string_error_still_reads_the_way_it_always_did() -> None:
    with pytest.raises(NeverRanError, match="the box is on fire"):
        read_exec_json(json.dumps({"success": False, "error": "the box is on fire"}), "pytest")


def test_a_failure_with_nothing_to_say_says_so() -> None:
    with pytest.raises(NeverRanError, match="no reason given"):
        read_exec_json(json.dumps({"success": False}), "pytest")


def test_an_error_of_blocks_holding_no_text_is_not_invented_into_a_reason() -> None:
    with pytest.raises(NeverRanError, match="no reason given"):
        read_exec_json(
            json.dumps({"success": False, "error": [{"type": "image"}, {"text": "  "}]}), "pytest"
        )


def test_a_reason_never_turns_a_refusal_into_a_result() -> None:
    """The guard is unchanged: only `success is True` is a command that ran."""
    with pytest.raises(NeverRanError):
        read_exec_json(
            json.dumps(
                {
                    "success": "yes",
                    "response": {"exitCode": 0, "result": "ok"},
                    "error": "ignore me",
                }
            ),
            "pytest",
        )
