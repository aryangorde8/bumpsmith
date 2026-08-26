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

import json
import shlex
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
            completed = subprocess.run(  # noqa: S603
                argv,
                cwd=cwd,
                stdout=subprocess.PIPE,
                # One stream, so the interleaving pytest wrote is the
                # interleaving `failures` reads.
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimedOutError(
                f"{argv[0]} was still running after {self._timeout:g}s and was killed"
            ) from exc
        except OSError as exc:
            # Missing binary, unreadable cwd, no permission to execute. The local
            # shape of "the infrastructure never got to the command".
            raise NeverRanError(f"{argv[0]} could not be started: {exc!r}") from exc
        return Completed(
            returncode=completed.returncode,
            output=completed.stdout or "",
            where="local",
        )


class Exec(Protocol):
    """One ``exec`` in the harness's sandbox.

    Named for the tool it stands for. TrueForge exposes the sandbox as a tool
    the agent calls -- there is no endpoint that runs a command in Daytona -- so
    what reaches this module is whatever came back from that tool call, already
    decoded from JSON. Getting it there is the transport's problem and not this
    module's; what the result has to *mean* is this module's problem entirely.
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
        except Exception as exc:
            # The transport failed: no session, no turn, a socket that closed.
            # Nothing ran, and this is the one place that can still say so.
            raise NeverRanError(f"the sandbox could not be reached: {exc!r}") from exc
        return _read_exec_result(raw, line)


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
        error = raw.get("error")
        detail = error if isinstance(error, str) and error.strip() else "no reason given"
        raise NeverRanError(f"the sandbox never ran {command}: {detail}")
    if success is not True:
        raise refuse(f"`success` is {success!r}, which is neither true nor false")

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
