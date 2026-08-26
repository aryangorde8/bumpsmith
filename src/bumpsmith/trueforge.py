"""Talk to the harness, and decide nothing.

Two modules in this package take their transport as a protocol.
:mod:`bumpsmith.harness` reads an approval question and hands back an answer
through a :class:`~bumpsmith.harness.Channel`; :mod:`bumpsmith.run` reads what a
sandbox command did through an :class:`~bumpsmith.run.Exec`. Both were written
that way so a decision can be tested against a recorded event stream with no
socket in the way. Neither could be used by installing the package, because
nothing implemented either protocol. This module is the missing half, and it is
deliberately the *only* place in the package that opens one.

The split is not decoration. Everything here is allowed to be wrong about the
network -- a retry, a timeout, a body that arrived empty -- and nothing here is
allowed to be wrong about what an event means. It parses no approval, classifies
no failure, and makes no decision that changes what runs. When it cannot get an
answer it says which kind of not-knowing it has, and something above decides
what that is worth.

What it will not do
-------------------
It will not report a command as never having started when it might have.
TrueForge starts a turn and answers in milliseconds; the work happens
afterwards, and the only way to see it is to poll. So a request that was
accepted and then lost -- a read timeout, a poll that ran out, a turn that ended
without the tool result appearing -- is a command that *may* have run to
completion, and :mod:`bumpsmith.run` is told exactly that. Reporting it as
never-ran would be the more convenient answer and a false one: it invites a
retry of something that already happened.
"""

import http.client
import json
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, final

from bumpsmith.run import NeverRanError, TimedOutError

DEFAULT_BASE_URL = "http://localhost:8790/api/v1"

# The harness answers a POST to /turns in milliseconds and does the work after,
# so every read below is a poll. These are the numbers the probes settled on
# against TrueForge 0.1.4.
DEFAULT_HTTP_TIMEOUT = 120.0
DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_POLL_LIMIT = 300.0

TURN_EVENTS_EMPTY_RETRIES = 90

SANDBOX_EXEC_TOOL = "exec"
USER_MESSAGE = "user.message"
TOOL_RESPONSE = "tool.response"
MODEL_MESSAGE = "model.message"


def _never_left(exc: BaseException) -> bool:
    """Whether this failure provably happened before the request was written.

    Walks ``__cause__``/``reason`` because :mod:`urllib` wraps the real error in
    a :class:`urllib.error.URLError`. Deliberately a short list: anything not
    recognised is treated as ambiguous, because the cost of being wrong here is
    asymmetric. Calling a sent request "never sent" invites a retry of something
    that already happened; calling an unsent one ambiguous costs a retry nobody
    took.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ConnectionRefusedError | socket.gaierror):
            return True
        reason = getattr(current, "reason", None)
        current = reason if isinstance(reason, BaseException) else current.__cause__
    return False


class TransportError(Exception):
    """The harness could not be reached, or did not answer in a usable way."""


class HTTPError(TransportError):
    """The harness answered with a status that is not a success.

    Carries the code and the body, because the body is where TrueForge explains
    which field of the request it did not like, and a message without it sends
    the reader back to the wire to find out.
    """

    def __init__(self, method: str, path: str, code: int, body: str) -> None:
        super().__init__(f"{method} {path} -> {code}: {body[:500]}")
        self.method = method
        self.path = path
        self.code = code
        self.body = body


class NotSentError(TransportError):
    """The request was never written to a socket.

    The distinction this class exists for is the whole reason
    :mod:`bumpsmith.run` separates "never ran" from "ran, outcome unknown".
    A refused connection or a name that does not resolve happened *before*
    anything reached the harness, so nothing started and a retry is free.
    Every other failure is ambiguous and is treated as though the command may
    have run.
    """


class ProtocolError(TransportError):
    """The harness answered successfully with something this module cannot read.

    Separate from :class:`HTTPError` because it means the two ends disagree
    about the shape rather than about the request -- a version drift, not a bad
    call. Nothing is retried on it.
    """


@dataclass(frozen=True, slots=True)
class Turn:
    """One turn, and the session it belongs to.

    Both ids travel together because every read needs both, and passing them
    separately is how a poll ends up asking one session about another's turn.
    """

    session_id: str
    turn_id: str


def _read_events(payload: object, path: str) -> list[dict[str, object]]:
    """Validate one events response, or say the two ends disagree.

    Every rejection here is a shape a previous version accepted by retrying it
    into an empty list. An empty list is what a caller gets when a turn has no
    events yet, so returning one for "I could not read this" made drift look
    exactly like patience.
    """
    if not isinstance(payload, Mapping):
        raise ProtocolError(f"GET {path} answered with {type(payload).__name__}, not an object")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ProtocolError(f"GET {path} answered without a `data` list")
    events: list[dict[str, object]] = []
    for index, event in enumerate(data):
        if not isinstance(event, dict):
            # Dropping it silently would lose exactly the event that explains
            # why a turn did not do what it was asked.
            raise ProtocolError(
                f"GET {path} returned {type(event).__name__} at data[{index}], not an event"
            )
        events.append(event)
    return events


@final
class Client:
    """The one place in the package that opens a socket.

    ``base_url`` points at a running TrueForge. Everything is stdlib: the
    package declares no runtime dependencies, and a review agent is a poor
    reason to make somebody install an HTTP library to migrate their models.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        http_timeout: float = DEFAULT_HTTP_TIMEOUT,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        poll_limit: float = DEFAULT_POLL_LIMIT,
        sleep: Any = time.sleep,
        now: Any = time.monotonic,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._http_timeout = http_timeout
        self._poll_interval = poll_interval
        self._poll_limit = poll_limit
        # Injected so the polling tests do not spend their runtime sleeping.
        # Not a public knob: a caller supplying these is writing a test.
        self._sleep = sleep
        self._now = now

    # -- the wire ---------------------------------------------------------

    def call(
        self, method: str, path: str, body: object = None, *, timeout: float | None = None
    ) -> object:
        """One request. Raises :class:`TransportError`; never returns a failure.

        ``timeout`` caps this call below the client's own, so a caller working
        to a deadline can stop a single request from outliving it.
        """
        if timeout is not None and timeout <= 0:
            raise TransportError(f"{method} {path} was not attempted: no time left")
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310
            f"{self._base}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            limit = self._http_timeout if timeout is None else min(self._http_timeout, timeout)
            with urllib.request.urlopen(request, timeout=limit) as response:  # noqa: S310
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HTTPError(method, path, exc.code, detail) from exc
        except OSError as exc:
            # `URLError` is an `OSError`, and so is a socket timeout. They do not
            # all mean the same thing: a refused connection proves nothing was
            # received, while a timeout proves only that no answer came back.
            # Callers deciding whether a retry is safe need that difference, so
            # it is drawn here, where the errno still exists.
            if _never_left(exc):
                raise NotSentError(f"{method} {path} was never sent: {exc!r}") from exc
            raise TransportError(f"{method} {path} got no answer: {exc!r}") from exc
        except http.client.HTTPException as exc:
            # `IncompleteRead`, `BadStatusLine` and friends are *not* `OSError`,
            # so without this they escape the hierarchy entirely and are read
            # further up as "never ran". They mean the opposite: the request was
            # written and the response came back damaged, which happens most
            # often while reading a turn back -- after the command was accepted
            # and possibly after it finished.
            raise TransportError(f"{method} {path} answered incompletely: {exc!r}") from exc
        if not raw.strip():
            return None
        try:
            return json.loads(raw)
        except ValueError as exc:
            raise ProtocolError(
                f"{method} {path} answered with something that is not JSON"
            ) from exc

    def _data(self, payload: object, what: str) -> Mapping[str, object]:
        if not isinstance(payload, Mapping):
            raise ProtocolError(f"{what} answered with {type(payload).__name__}, not an object")
        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise ProtocolError(f"{what} answered without a `data` object")
        return data

    # -- sessions and turns ----------------------------------------------

    def create_session(self, spec: Mapping[str, object]) -> str:
        """Start a session and return its id.

        ``spec`` is the *agent spec*, not the whole request body -- the request
        and the response are different shapes here, and wrapping it in one place
        is cheaper than every caller remembering that.
        """
        payload = self.call("POST", "/sessions", {"agent": {"spec": dict(spec)}})
        data = self._data(payload, "POST /sessions")
        session_id = data.get("id")
        if not isinstance(session_id, str) or not session_id:
            raise ProtocolError("the session was created without an id")
        return session_id

    def start_turn(self, session_id: str, events: Sequence[Mapping[str, object]]) -> Turn:
        """Submit turn input and return the turn it started.

        ``input`` is an array even when there is one event, and the call returns
        before the work does.
        """
        payload = self.call(
            "POST",
            f"/sessions/{session_id}/turns",
            {"input": [dict(event) for event in events], "stream": False},
        )
        data = self._data(payload, f"POST /sessions/{session_id}/turns")
        turn_id = data.get("id")
        if not isinstance(turn_id, str) or not turn_id:
            raise ProtocolError("the turn was started without an id")
        return Turn(session_id=session_id, turn_id=turn_id)

    def ask(self, session_id: str, message: str) -> Turn:
        """The ordinary case: one user message, one turn."""
        return self.start_turn(session_id, [{"type": USER_MESSAGE, "content": message}])

    def turn_events(self, turn: Turn, *, deadline: float | None = None) -> list[dict[str, object]]:
        """Every event in a turn so far.

        A live turn answers this with an **empty body** -- not an empty list and
        not an error -- so *that one case* is retried rather than believed. It
        cost an afternoon to find and is the reason this method exists instead
        of a call to :meth:`call`.

        Nothing else is retried. A successful answer whose shape this module
        does not recognise is version drift, and drift does not improve by being
        asked ninety more times; retrying it hid a permanent disagreement inside
        what looked like a slow turn. It raises :class:`ProtocolError` instead.

        An empty *list* is a real answer and is returned as one. A turn that has
        not produced an event yet has genuinely produced no events, and the
        caller looking for one is the one that knows whether to wait.
        """
        path = f"/sessions/{turn.session_id}/turns/{turn.turn_id}/events"
        for attempt in range(TURN_EVENTS_EMPTY_RETRIES):
            remaining = None if deadline is None else deadline - self._now()
            if remaining is not None and remaining <= 0:
                return []
            payload = self.call("GET", path, timeout=remaining)
            if payload is not None:
                return _read_events(payload, path)
            if attempt + 1 < TURN_EVENTS_EMPTY_RETRIES:
                self._sleep(self._poll_interval)
        return []

    def poll(self, turn: Turn) -> Iterator[list[dict[str, object]]]:
        """Yield the turn's events repeatedly until the poll limit runs out.

        A generator rather than a callback so the caller keeps the loop and can
        stop on whatever it was looking for. It does not decide when a turn is
        finished; the thing waiting knows what it is waiting for.
        """
        deadline = self._now() + self._poll_limit
        while self._now() < deadline:
            # Passed down, not merely checked here: `turn_events` can retry an
            # empty body ninety times, each with the full HTTP timeout, and a
            # deadline consulted only between calls is not a deadline. Without
            # this a 300-second limit could block for hours.
            yield self.turn_events(turn, deadline=deadline)
            self._sleep(self._poll_interval)

    def deliver(self, session_id: str, event: Mapping[str, object]) -> None:
        """Deliver one event as turn input to a named session."""
        self.call(
            "POST",
            f"/sessions/{session_id}/turns",
            {"input": [dict(event)], "stream": False},
        )


def _exec_result_text(events: Sequence[Mapping[str, object]]) -> str | None:
    """The text of the first ``exec`` tool result in these events.

    Two passes because the two halves live in different events: a
    ``model.message`` says which tool call is the ``exec``, and a
    ``tool.response`` carries what it produced. Matching on the id rather than
    taking the first ``tool.response`` is what keeps this correct in a turn that
    called something else as well.
    """
    wanted: set[str] = set()
    for event in events:
        if event.get("type") != MODEL_MESSAGE:
            continue
        calls = event.get("tool_calls")
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, Mapping):
                continue
            info = call.get("tool_info")
            named = info.get("name") if isinstance(info, Mapping) else None
            if named != SANDBOX_EXEC_TOOL:
                function = call.get("function")
                named = function.get("name") if isinstance(function, Mapping) else None
            if named == SANDBOX_EXEC_TOOL and isinstance(call.get("id"), str):
                wanted.add(str(call["id"]))
    if not wanted:
        return None
    for event in events:
        if event.get("type") != TOOL_RESPONSE or event.get("tool_call_id") not in wanted:
            continue
        content = event.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for part in content:
                if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                    return str(part["text"])
    return None


@final
class SandboxExec:
    """Runs one command in the harness's sandbox. Satisfies :class:`~bumpsmith.run.Exec`.

    There is no endpoint that runs a command in Daytona -- ``exec`` is a tool the
    model calls -- so this asks for a turn and waits for that tool's result to
    appear. The instructions are narrow on purpose: a model free to improve the
    command is a model that can change what was verified.

    Which failure is which is the point of this class. A command whose request
    never left raises :class:`~bumpsmith.run.NeverRanError`; a command whose
    request was accepted and then lost raises
    :class:`~bumpsmith.run.TimedOutError`, because it may have run to
    completion and a caller must not retry it believing otherwise.
    """

    INSTRUCTIONS = (
        "You run shell commands in the sandbox with the exec tool. When the user gives "
        "you a command, call exec exactly once with that command verbatim. Do not modify "
        "it, do not split it, do not ask clarifying questions, and do not run anything "
        "else afterwards. Report the output as you received it."
    )

    def __init__(self, client: Client, model: str, *, session_id: str | None = None) -> None:
        self._client = client
        self._model = model
        self._session_id = session_id

    def session_id(self) -> str:
        """The session, created on first use and reused after.

        One session per runner rather than one per command, so the sandbox is
        created once and the checkout it holds survives between runs.
        """
        if self._session_id is None:
            self._session_id = self._client.create_session(
                {
                    "model": {"name": self._model},
                    "instructions": self.INSTRUCTIONS,
                    "config": {"sandbox": {"enabled": True}, "iteration_limit": 8},
                }
            )
        return self._session_id

    def __call__(self, command: str, cwd: str) -> Mapping[str, object]:
        prompt = f"Run this command in the sandbox, exactly as written, in {cwd}:\n\n{command}"
        try:
            session = self.session_id()
            turn = self._client.ask(session, prompt)
        except NotSentError as exc:
            raise NeverRanError(f"the harness was not reachable: {exc}") from exc
        except HTTPError as exc:
            if 400 <= exc.code < 500:
                # The harness read the request and refused it. Nothing started.
                raise NeverRanError(f"the harness refused the request: {exc}") from exc
            raise TimedOutError(f"the harness failed after accepting the command: {exc}") from exc
        except TransportError as exc:
            # Ambiguous: the POST may have landed. Treated as "may have run".
            raise TimedOutError(f"the command was sent and not answered for: {exc}") from exc
        except Exception as exc:
            # Nothing may reach `run.py` unclassified. Its fallback reads an
            # unknown exception as `NeverRanError`, which is the one answer that
            # is unsafe to be wrong about, so anything unexpected is caught here
            # and read the other way. The asymmetry is the whole point: guessing
            # "may have run" costs a retry nobody took, guessing "never ran"
            # costs a command run twice.
            raise TimedOutError(
                f"the command failed in a way this module cannot classify: {exc!r}"
            ) from exc

        try:
            for events in self._client.poll(turn):
                text = _exec_result_text(events)
                if text is not None:
                    return _decode_result(text)
        except TransportError as exc:
            raise TimedOutError(f"the turn could not be read back: {exc}") from exc

        raise TimedOutError(
            f"the sandbox accepted the command and no exec result appeared in turn {turn.turn_id}"
        )


def _decode_result(text: str) -> Mapping[str, object]:
    """The ``exec`` tool returns its result as text holding JSON."""
    try:
        loaded = json.loads(text)
    except ValueError as exc:
        raise TimedOutError(f"the exec result was not JSON: {text[:200]!r}") from exc
    if not isinstance(loaded, Mapping):
        raise TimedOutError(f"the exec result was {type(loaded).__name__}, not an object")
    return loaded


@final
class TurnChannel:
    """Where a decision goes back. Satisfies :class:`~bumpsmith.harness.Channel`.

    Takes the session explicitly, and that is the entire reason this is a class
    rather than a method on :class:`Client`.

    An approval event carries a ``thread_id``, and a ``thread_id`` looks exactly
    like something you could put in the URL. It is not: a thread is a
    conversation *inside* a session, the root one is called ``main``, and
    subagents get their own. Reading the session out of the event produced
    ``POST /sessions/main/turns`` and a 404 -- against a live harness, after the
    unit tests had passed, because the test supplied a ``thread_id`` that looked
    like a session id and so agreed with the bug.

    Requiring the session in the constructor makes that mistake unavailable
    rather than merely documented. The ``thread_id`` still travels in the
    payload, where it belongs and where the harness reads it.
    """

    def __init__(self, client: Client, session_id: str) -> None:
        if not session_id:
            raise ValueError("a channel needs the session to deliver into")
        self._client = client
        self._session_id = session_id
        self.sent: list[Mapping[str, object]] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def send(self, event: Mapping[str, object]) -> None:
        self.sent.append(dict(event))
        self._client.deliver(self._session_id, event)
