"""Run the test suite somewhere, and never guess what happened.

The migration loop turns on one question: after an edit, does the suite pass?
Everything else -- the rule, the matches, the plan -- is a proposal until a test
run answers it. That makes the test run the point where a wrong answer is most
expensive, because a wrong answer here does not raise. It gets believed.

The command runs against a repository that was just edited by a tool, in a
project nobody in this process wrote. :mod:`bumpsmith.apply` guarantees the edit
can be taken back; it cannot make the code safe to execute. That is what the
sandbox is for, and it is why the choice of where to run is a seam rather than a
detail: the same argv goes to a subprocess on a developer's machine or to
Daytona through the harness, and the caller reads one result type either way.

What this module refuses to do
------------------------------
It will not turn "the command did not run" into a test result. The two are easy
to collapse -- both are unhappy, both have an error string -- and collapsing them
is silent. A sandbox that cannot be reached would parse as a run that found no
failures, :func:`bumpsmith.failures.parse_failures` would report nothing to fix,
and the attempt would be kept because the suite looked green. The tree would
then hold an edit that was never tested and is recorded as verified.

So :class:`Completed` is only ever built from a command that ran to completion
and returned a status. Anything else raises: the sandbox was unreachable, the
binary was missing, the run timed out with the outcome still unknown. A caller
that wants to treat those as failures is free to catch them, but it has to say
so, in code a reviewer can see.
"""

import contextlib
import json
import os
import shlex
import signal
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, final

# `chain.py` used 600s against fixture B, whose suite runs in seconds. The margin
# is for a cold sandbox, not for a slow suite -- a suite that genuinely needs ten
# minutes has a problem this tool is not going to fix.
DEFAULT_TIMEOUT = 600.0

Where = Literal["local", "sandbox"]

# Process groups are POSIX. `start_new_session=True` is rejected outright on
# Windows, so the isolation degrades there rather than the runner failing to
# start -- a timeout still kills the command, just not what it spawned.
_POSIX = os.name == "posix"


class RunError(Exception):
    """The command did not produce a result anybody may reason about."""


class NeverRanError(RunError):
    """The command was never executed.

    An unreachable sandbox, a missing interpreter, a refused connection. The
    working tree is untouched by anything this run did, because it did nothing.
    """


class TimedOutError(RunError):
    """The command ran and the outcome is unknown.

    Deliberately not a :class:`NeverRanError`. Something did execute, possibly
    most of the suite, and the process was killed before it said how it went.
    Nothing may be concluded about the edit from that, which is the same
    practical answer as never having run -- but it is a different fact, and a
    caller deciding whether to retry needs to be able to tell them apart.
    """


@dataclass(frozen=True, slots=True)
class Completed:
    """A command that ran and returned a status.

    ``output`` is stdout and stderr as one stream, in the order they were
    written, because that is the order pytest's own layout depends on and
    :mod:`bumpsmith.failures` parses that layout. Splitting them and rejoining
    later reorders the interleaving and loses error context from its traceback.

    ``where`` is carried so the review trail can say where a result came from.
    A suite that passed on a developer's laptop and a suite that passed in the
    sandbox are the same ``returncode`` and different evidence.
    """

    returncode: int
    output: str
    where: Where


class Runner(Protocol):
    """Somewhere a command can run.

    ``command`` is argv, never a shell string. Both implementations take the
    same list and neither lets a shell near it, so a path containing a space
    means one argument in both places rather than one locally and two in the
    sandbox.
    """

    def run(self, command: Sequence[str], cwd: Path) -> Completed: ...


# Long enough for a killed process tree to be reaped, short enough that a
# process which ignores SIGKILL (uninterruptible IO) does not hang the caller.
_REAP_TIMEOUT = 10.0

# Between SIGTERM and SIGKILL. A test runner that catches SIGTERM usually wants
# it to remove a temporary directory or stop a container; leaving those behind
# is the same kind of mess as leaving the processes behind.
_GRACE = 2.0


def _decode(raw: bytes | None) -> str:
    """Text from whatever the process actually wrote.

    Bytes are captured and decoded here rather than by ``text=True`` for two
    reasons. The encoding is pinned instead of taken from the locale, so the
    same suite reads the same way on a developer's machine and in the sandbox.
    And the error policy is ``replace``: a project whose output is not valid
    UTF-8 -- a test printing binary, a traceback naming a file whose name never
    was text -- is an ordinary thing to migrate, and it must not raise past a
    contract that promises a :class:`Completed` or a :class:`RunError`. Losing a
    byte to U+FFFD costs a character in a diagnostic; raising here costs the run.
    """
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def _end_process_tree(process: "subprocess.Popen[bytes]") -> None:
    """Stop the timed-out command and everything it started.

    Signals the process group, which is why :class:`LocalRunner` puts the child
    in one. Every failure here is ignored on purpose: the group is already gone,
    or it is not ours to signal, and neither changes the answer the caller is
    about to get. What must not happen is an exception from cleanup replacing
    :class:`TimedOutError` with something that does not say what went wrong.

    It will not signal the caller's own group under any circumstances. See the
    guard below for why that is not a theoretical concern.
    """
    if not _POSIX:
        process.kill()
        return
    try:
        group = os.getpgid(process.pid)
    except OSError:  # already reaped
        return
    if group == os.getpgrp():
        # The child is in *our* group, so it never got one of its own. Signalling
        # here would kill this process and everything sharing its group -- the
        # test runner, the agent, whatever started it. Measured, not theorised:
        # with `start_new_session` off, this function takes the caller down with
        # it and the run ends with no output at all.
        #
        # The isolation and the group-kill are one mechanism, and this is the
        # half that makes losing the other half survivable rather than fatal.
        process.kill()
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(group, sig)
        except OSError:
            return
        if sig is signal.SIGTERM:
            try:
                process.wait(timeout=_GRACE)
            except subprocess.TimeoutExpired:
                continue
            return


@final
class LocalRunner:
    """Runs the command in a subprocess on this machine.

    Honest about what it is: no isolation at all. It exists because it is what
    the loop did before there was a choice, because the tests for the loop need
    something that does not require a harness, and because a developer running
    the tool on their own checkout has already accepted this risk. It is not the
    default anywhere a sandbox is configured.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def run(self, command: Sequence[str], cwd: Path) -> Completed:
        argv = list(command)
        if not argv:
            raise NeverRanError("there is no command to run")
        try:
            process = subprocess.Popen(  # noqa: S603
                argv,
                cwd=cwd,
                stdout=subprocess.PIPE,
                # One stream, so the interleaving pytest wrote is the
                # interleaving `failures` reads.
                stderr=subprocess.STDOUT,
                # Its own process group, so a timeout can kill the whole tree
                # rather than the one process this module can see. A suite is
                # not one process: pytest-xdist workers, a fixture that starts a
                # server, anything using `subprocess` itself. Killing only the
                # parent leaves those running -- against the same checkout
                # `bumpsmith.apply` is about to revert, which is how a tree ends
                # up in a state nobody chose.
                start_new_session=_POSIX,
            )
        except OSError as exc:
            # Missing binary, unreadable cwd, no permission to execute. The local
            # shape of "the infrastructure never got to the command".
            raise NeverRanError(f"{argv[0]} could not be started: {exc!r}") from exc

        try:
            raw, _ = process.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            _end_process_tree(process)
            # Reap, and take whatever was written before the end. It is
            # discarded with the exception, but leaving the pipe unread leaks
            # the descriptor and can block the dying children on a full buffer.
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.communicate(timeout=_REAP_TIMEOUT)
            raise TimedOutError(
                f"{argv[0]} was still running after {self._timeout:g}s and was killed"
            ) from None

        return Completed(
            returncode=process.returncode,
            output=_decode(raw),
            where="local",
        )


class Exec(Protocol):
    """One ``exec`` in the harness's sandbox.

    Named for the tool it stands for. TrueForge exposes the sandbox as a tool
    the agent calls -- there is no endpoint that runs a command in Daytona -- so
    what reaches this module is whatever came back from that tool call, already
    decoded from JSON. Getting it there is the transport's problem and not this
    module's; what the result has to *mean* is this module's problem entirely.

    One thing is the transport's to say, because nothing above it can know:
    whether a failed call left the command running. An implementation that gives
    up on a request already in flight -- a read timeout, a cancelled turn, the
    sandbox's own ``exec_timeout_ms`` -- should raise :class:`TimedOutError`,
    and it will reach the caller unchanged. Anything else is read as never
    having started.
    """

    def __call__(self, command: str, cwd: str) -> Mapping[str, object]: ...


@final
class SandboxRunner:
    """Runs the command in the harness's sandbox and reads the answer strictly.

    The result shape it accepts is TrueForge's, unchanged::

        {"success": true,  "response": {"exitCode": 1, "result": "..."}}
        {"success": false, "error": "..."}

    The first is a command that ran. A non-zero ``exitCode`` there is not an
    error -- for pytest it is the normal case and the entire signal. The second
    is a command that never ran, and it becomes :class:`NeverRanError` rather
    than a failing test result. Every rejection below exists so that a malformed
    or surprising answer lands on that side too, because the alternative is a
    :class:`Completed` built from something the sandbox did not actually say.
    """

    def __init__(self, exec_: Exec) -> None:
        self._exec = exec_

    def run(self, command: Sequence[str], cwd: Path) -> Completed:
        argv = list(command)
        if not argv:
            raise NeverRanError("there is no command to run")
        # The sandbox takes a shell string; the caller gave argv. Quoting here
        # rather than asking callers for a string is what keeps the two runners
        # honest about meaning the same thing: `shlex.quote` is the same
        # single-quote escaping TrueForge's own `shellEscape` applies, so no
        # element is ever re-split or expanded on the way in.
        line = " ".join(shlex.quote(part) for part in argv)
        try:
            raw = self._exec(command=line, cwd=str(cwd))
        except RunError:
            # Already classified, by the only layer that can tell the difference.
            # A transport that timed out knows the command started; rewriting
            # that as `NeverRanError` would state the opposite, and a caller
            # retrying on the strength of it could run a command twice whose
            # first run had already done everything.
            raise
        except Exception as exc:
            # No session, no turn, a socket that closed before the request went
            # out. Nothing this module can see says the command started, and the
            # safe reading of "I do not know" is that it did not.
            raise NeverRanError(f"the sandbox could not be reached: {exc!r}") from exc
        return _read_exec_result(raw, line)


def _reason(raw: Mapping[str, object]) -> str | None:
    """What the harness said went wrong, however it chose to say it.

    TrueForge's ``error`` is sometimes a string and sometimes the content-block
    list a model turn carries::

        {"error": [{"type": "text", "text": "Total disk limit exceeded..."}]}

    Only the string form was written for, so the block form fell through to
    "no reason given" -- and a result carrying no ``success`` field never
    consulted ``error`` at all. Both were refusals that threw away the sentence
    explaining them, which makes a refusal correct and useless at once: the
    caller is told the shape was wrong instead of that the sandbox ran out of
    disk.

    Found on 27 Aug 2026 by a fan-out that exhausted a Daytona quota, reported
    as ``success`` being ``None``. Nothing about which results are *accepted*
    changes here; only what a rejected one is able to say for itself.
    """
    error = raw.get("error")
    if isinstance(error, str):
        return error.strip() or None
    if isinstance(error, Sequence) and not isinstance(error, str | bytes):
        said = [
            block["text"].strip()
            for block in error
            if isinstance(block, Mapping)
            and isinstance(block.get("text"), str)
            and block["text"].strip()
        ]
        if said:
            return " ".join(said)
    return None


def _read_exec_result(raw: object, command: str) -> Completed:
    """Turn one ``exec`` result into a :class:`Completed`, or refuse to.

    Split out from :class:`SandboxRunner` because it is the part worth testing
    against recorded harness output, with no transport in the way.
    """

    def refuse(why: str) -> NeverRanError:
        return NeverRanError(f"the sandbox did not say what happened to {command}: {why}")

    if not isinstance(raw, Mapping):
        raise refuse(f"the result is {type(raw).__name__}, not an object")

    success = raw.get("success")
    # `is True` rather than truthiness. A string, a 1, or a present-but-null
    # field all mean the answer was not the one documented, and reading a
    # truthy value as success is how a malformed result becomes a test verdict.
    if success is False:
        raise NeverRanError(f"the sandbox never ran {command}: {_reason(raw) or 'no reason given'}")
    if success is not True:
        # The reason is repeated here rather than only above, because a result
        # with no `success` at all is exactly the shape a failure *before* the
        # command takes -- the sandbox never came up, so nothing got as far as
        # reporting on it. That is the case where the harness has the most to
        # say and this module used to say the least.
        said = _reason(raw)
        detail = f"`success` is {success!r}, which is neither true nor false"
        raise refuse(f"{detail}, and it said: {said}" if said else detail)

    response = raw.get("response")
    if not isinstance(response, Mapping):
        raise refuse("it reported success without a `response`")

    code = response.get("exitCode")
    # `bool` is an `int` in Python, so an `exitCode` of `true` would otherwise
    # arrive as 1 and read as a suite that failed. It is not a status.
    if isinstance(code, bool) or not isinstance(code, int):
        raise refuse(f"`exitCode` is {code!r}, which is not a status")

    result = response.get("result")
    if result is None:
        # A command that wrote nothing is ordinary; a missing field is not the
        # same thing, but both leave nothing to parse and neither is a lie.
        result = ""
    if not isinstance(result, str):
        raise refuse(f"`result` is {type(result).__name__}, not text")

    return Completed(returncode=code, output=result, where="sandbox")


def read_exec_json(text: str, command: str = "the command") -> Completed:
    """Read an ``exec`` tool result that is still a JSON string.

    The sandbox tool returns its result as text containing JSON, so a transport
    that hands back the tool call's content verbatim has a string rather than an
    object. Offered here so that decoding it is not each caller's problem, and
    so a truncated or non-JSON body refuses in the same way everything else in
    this module refuses.
    """
    try:
        raw = json.loads(text)
    except ValueError as exc:
        raise NeverRanError(
            f"the sandbox did not say what happened to {command}: the result is not JSON ({exc!r})"
        ) from exc
    return _read_exec_result(raw, command)
