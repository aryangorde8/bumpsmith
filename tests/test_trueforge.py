"""Tests for the transport.

Every test here runs against a real HTTP server on a real socket. The module is
almost entirely about what happens when a network misbehaves -- an empty body
mid-turn, a refused connection, a status nobody expected -- and a mocked
`urlopen` would only prove that the arguments were passed. The server is bound
to localhost on a port the kernel picks; no test touches the network.

The important test is `test_nothing_claims_never_ran_unless_it_provably_did_not`.
`bumpsmith.run` promises that a `NeverRanError` means the working tree is
untouched, and this module is the only thing in the package positioned to break
that promise. Every failure mode is asserted at once, not one at a time.
"""

import http.server
import json
import socket
import threading
from collections.abc import Callable, Mapping
from typing import Any, cast

import pytest

from bumpsmith.run import NeverRanError, TimedOutError
from bumpsmith.trueforge import (
    Client,
    HTTPError,
    NotSentError,
    ProtocolError,
    SandboxExec,
    TransportError,
    Turn,
    TurnChannel,
    _exec_result_text,
)

Route = Callable[[str, str], tuple[int, str]]


class _Harness:
    """A stand-in TrueForge. Records what it was asked and replays what it was told."""

    def __init__(self, route: Route, *, short_body: bool = False) -> None:
        self.route = route
        self.short_body = short_body
        self.requests: list[tuple[str, str, Any]] = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                outer.requests.append((self.command, self.path, body))
                status, text = outer.route(self.command, self.path)
                payload = text.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                if outer.short_body:
                    # Promise more than is sent, so `response.read()` raises
                    # `http.client.IncompleteRead` -- a real damaged response
                    # rather than a patched-in exception.
                    self.send_header("Content-Length", str(len(payload) + 64))
                else:
                    self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            # Names fixed by BaseHTTPRequestHandler.
            do_GET = _serve  # noqa: N815
            do_POST = _serve  # noqa: N815

            def log_message(self, *args: Any) -> None:
                pass

        self._server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "_Harness":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v1"


def _client(harness: _Harness, **kwargs: Any) -> Client:
    kwargs.setdefault("sleep", lambda _: None)
    return Client(harness.base_url, **kwargs)


def _free_port() -> int:
    """A port with nothing on it, for the refused-connection tests."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _fixed(status: int, body: str) -> Route:
    """A harness that answers everything the same way."""

    def route(_method: str, _path: str) -> tuple[int, str]:
        return status, body

    return route


def _ok(payload: object) -> tuple[int, str]:
    return 200, json.dumps(payload)


def _session(_method: str, _path: str) -> tuple[int, str]:
    return _ok({"data": {"id": "sess-1"}})


EXEC_RESULT = {"success": True, "response": {"exitCode": 1, "result": "1 failed"}}


def _events_with_exec(call_id: str = "call-1") -> list[dict[str, object]]:
    return [
        {
            "type": "model.message",
            "tool_calls": [
                {"id": call_id, "tool_info": {"type": "truefoundry-system", "name": "exec"}}
            ],
        },
        {"type": "tool.response", "tool_call_id": call_id, "content": json.dumps(EXEC_RESULT)},
    ]


# --------------------------------------------------------------------------
# The wire
# --------------------------------------------------------------------------


def test_a_session_is_created_with_the_spec_wrapped() -> None:
    with _Harness(_session) as harness:
        assert _client(harness).create_session({"model": {"name": "m"}}) == "sess-1"
        _, path, body = harness.requests[0]
        assert path == "/api/v1/sessions"
        # Request and response are different shapes; the spec goes inside `agent`.
        assert body == {"agent": {"spec": {"model": {"name": "m"}}}}


def test_turn_input_is_an_array_even_for_one_event() -> None:
    with _Harness(_fixed(*_ok({"data": {"id": "turn-1"}}))) as harness:
        turn = _client(harness).ask("sess-1", "go")
        assert turn == Turn(session_id="sess-1", turn_id="turn-1")
        assert harness.requests[0][2]["input"] == [{"type": "user.message", "content": "go"}]


def test_an_empty_body_mid_turn_is_retried_not_believed() -> None:
    """A live turn answers with an empty body, not an empty list and not an error."""
    calls = {"n": 0}

    def route(_m: str, _p: str) -> tuple[int, str]:
        calls["n"] += 1
        if calls["n"] < 3:
            return 200, ""
        return _ok({"data": [{"type": "turn.done"}]})

    with _Harness(route) as harness:
        events = _client(harness).turn_events(Turn("sess-1", "turn-1"))
    assert events == [{"type": "turn.done"}]
    assert calls["n"] == 3


def test_an_empty_body_that_never_fills_gives_up_with_nothing() -> None:
    with _Harness(_fixed(200, "")) as harness:
        assert _client(harness).turn_events(Turn("sess-1", "turn-1")) == []


def test_a_failing_status_carries_the_code_and_the_body() -> None:
    route = _fixed(422, '{"detail":"model.name is required"}')
    with _Harness(route) as harness, pytest.raises(HTTPError) as caught:
        _client(harness).create_session({})
    assert caught.value.code == 422
    # The body is where TrueForge says which field it did not like.
    assert "model.name is required" in caught.value.body


def test_a_success_that_is_not_json_is_a_protocol_error() -> None:
    with _Harness(_fixed(200, "<html>gateway</html>")) as harness, pytest.raises(ProtocolError):
        _client(harness).create_session({})


def test_a_session_without_an_id_is_a_protocol_error() -> None:
    with _Harness(_fixed(*_ok({"data": {}}))) as harness, pytest.raises(ProtocolError):
        _client(harness).create_session({})


def test_a_refused_connection_is_known_never_to_have_been_sent() -> None:
    client = Client(f"http://127.0.0.1:{_free_port()}/api/v1", sleep=lambda _: None)
    with pytest.raises(NotSentError):
        client.create_session({})


def test_a_refused_connection_is_still_a_transport_error() -> None:
    # Callers that do not care about the distinction should not have to know it exists.
    client = Client(f"http://127.0.0.1:{_free_port()}/api/v1", sleep=lambda _: None)
    with pytest.raises(TransportError):
        client.create_session({})


# --------------------------------------------------------------------------
# Sending an answer back
# --------------------------------------------------------------------------


def test_an_event_is_delivered_to_the_session_the_channel_was_given() -> None:
    with _Harness(_fixed(*_ok({"data": {"id": "turn-2"}}))) as harness:
        event = {"type": "user.tool_approval", "thread_id": "main", "tool_call_id": "c1"}
        TurnChannel(_client(harness), "sess-9").send(event)
    _, path, body = harness.requests[0]
    assert path == "/api/v1/sessions/sess-9/turns"
    assert body["input"] == [event]


def test_a_thread_id_is_never_mistaken_for_a_session() -> None:
    """The bug a live harness found after the unit tests passed.

    A thread is a conversation inside a session; the root one is `main`.
    Reading the session out of the event gave `POST /sessions/main/turns` and a
    404 -- and the test that should have caught it supplied a `thread_id` that
    looked like a session id, so it agreed with the bug instead.
    """
    with _Harness(_fixed(*_ok({"data": {"id": "turn-2"}}))) as harness:
        event = {"type": "user.tool_approval", "thread_id": "main", "tool_call_id": "c1"}
        TurnChannel(_client(harness), "sess-real").send(event)
    _, path, body = harness.requests[0]
    assert "/main/" not in path
    assert path == "/api/v1/sessions/sess-real/turns"
    # It still travels in the payload, where the harness reads it.
    assert body["input"][0]["thread_id"] == "main"


def test_a_channel_cannot_be_built_without_a_session() -> None:
    # The mistake is unavailable, not merely documented.
    with _Harness(_session) as harness, pytest.raises(ValueError):
        TurnChannel(_client(harness), "")


def test_the_channel_records_what_it_sent() -> None:
    with _Harness(_fixed(*_ok({"data": {"id": "t"}}))) as harness:
        channel = TurnChannel(_client(harness), "sess-9")
        channel.send({"type": "user.tool_approval", "thread_id": "main"})
    assert len(channel.sent) == 1


def test_the_channel_satisfies_the_bridges_protocol() -> None:
    from bumpsmith.harness import Channel

    with _Harness(_session) as harness:
        channel: Channel = TurnChannel(_client(harness), "sess-9")
    assert channel is not None


# --------------------------------------------------------------------------
# Finding the exec result
# --------------------------------------------------------------------------


def test_the_exec_result_is_matched_by_call_id() -> None:
    events: list[dict[str, object]] = [
        {
            "type": "model.message",
            "tool_calls": [
                {"id": "other", "tool_info": {"name": "get_tool_info"}},
                {"id": "mine", "tool_info": {"name": "exec"}},
            ],
        },
        {"type": "tool.response", "tool_call_id": "other", "content": "not this one"},
        {"type": "tool.response", "tool_call_id": "mine", "content": "this one"},
    ]
    assert _exec_result_text(events) == "this one"


def test_a_turn_with_no_exec_has_no_exec_result() -> None:
    events: list[dict[str, object]] = [
        {"type": "model.message", "tool_calls": [{"id": "a", "tool_info": {"name": "search"}}]},
        {"type": "tool.response", "tool_call_id": "a", "content": "results"},
    ]
    assert _exec_result_text(events) is None


def test_exec_result_content_may_be_a_list_of_parts() -> None:
    events: list[Mapping[str, object]] = [
        {"type": "model.message", "tool_calls": [{"id": "x", "function": {"name": "exec"}}]},
        {"type": "tool.response", "tool_call_id": "x", "content": [{"text": "payload"}]},
    ]
    assert _exec_result_text(events) == "payload"


# --------------------------------------------------------------------------
# SandboxExec -- which failure is which
# --------------------------------------------------------------------------


def _exec_route(events: list[dict[str, object]]) -> Route:
    def route(_method: str, path: str) -> tuple[int, str]:
        if path.endswith("/events"):
            return _ok({"data": events})
        if path.endswith("/turns"):
            return _ok({"data": {"id": "turn-1"}})
        return _ok({"data": {"id": "sess-1"}})

    return route


def test_a_sandbox_command_returns_what_the_tool_reported() -> None:
    with _Harness(_exec_route(_events_with_exec())) as harness:
        result = SandboxExec(_client(harness), "model-x")("pytest -q", "/workspace")
    assert result == EXEC_RESULT


def test_the_session_is_created_once_and_reused() -> None:
    with _Harness(_exec_route(_events_with_exec())) as harness:
        runner = SandboxExec(_client(harness), "model-x")
        runner("pytest -q", "/workspace")
        runner("pytest -q", "/workspace")
    created = [r for r in harness.requests if r[1] == "/api/v1/sessions"]
    assert len(created) == 1, "a new sandbox per command would lose the checkout"


def test_a_refused_harness_never_ran_the_command() -> None:
    client = Client(f"http://127.0.0.1:{_free_port()}/api/v1", sleep=lambda _: None)
    with pytest.raises(NeverRanError):
        SandboxExec(client, "model-x")("pytest -q", "/workspace")


def test_a_rejected_request_never_ran_the_command() -> None:
    # 4xx: the harness read the request and refused it. Nothing started.
    with _Harness(_fixed(400, '{"detail":"bad spec"}')) as harness, pytest.raises(NeverRanError):
        SandboxExec(_client(harness), "model-x")("pytest -q", "/workspace")


def test_a_harness_that_breaks_after_accepting_may_have_run_the_command() -> None:
    def route(_m: str, path: str) -> tuple[int, str]:
        if path.endswith("/turns"):
            return 503, '{"detail":"upstream gone"}'
        return _ok({"data": {"id": "sess-1"}})

    with _Harness(route) as harness, pytest.raises(TimedOutError):
        SandboxExec(_client(harness), "model-x")("pytest -q", "/workspace")


def test_a_turn_that_never_produces_an_exec_result_may_have_run_the_command() -> None:
    """The command was accepted. Nothing here proves it did not run."""
    with _Harness(_exec_route([{"type": "turn.done"}])) as harness:
        client = _client(harness, poll_limit=0.05, poll_interval=0.0)
        with pytest.raises(TimedOutError):
            SandboxExec(client, "model-x")("pytest -q", "/workspace")


def test_an_exec_result_that_is_not_json_may_have_run_the_command() -> None:
    events: list[dict[str, object]] = [
        {"type": "model.message", "tool_calls": [{"id": "c", "tool_info": {"name": "exec"}}]},
        {"type": "tool.response", "tool_call_id": "c", "content": "Sandbox init failed"},
    ]
    with _Harness(_exec_route(events)) as harness, pytest.raises(TimedOutError):
        SandboxExec(_client(harness), "model-x")("pytest -q", "/workspace")


def test_the_command_reaches_the_model_verbatim() -> None:
    with _Harness(_exec_route(_events_with_exec())) as harness:
        SandboxExec(_client(harness), "model-x")("pytest -q 'a b.py'", "/workspace")
    turn = next(r for r in harness.requests if r[1].endswith("/turns"))
    content = turn[2]["input"][0]["content"]
    assert "pytest -q 'a b.py'" in content
    assert "/workspace" in content


# --------------------------------------------------------------------------
# The property this module must not break
# --------------------------------------------------------------------------


def test_nothing_claims_never_ran_unless_it_provably_did_not() -> None:
    """`NeverRanError` promises the working tree is untouched.

    Only two things here can honestly make that promise: a connection that was
    refused, and a request the harness read and rejected. Every other failure
    leaves open that the command ran, and must say so -- reporting it as
    never-ran invites a retry of something that already happened.
    """

    def run_against(route: Route, **kwargs: Any) -> BaseException:
        with _Harness(route) as harness:
            client = _client(harness, **kwargs)
            try:
                SandboxExec(client, "model-x")("pytest -q", "/workspace")
            except BaseException as exc:
                return exc
        raise AssertionError("expected a failure")

    cases = {
        "500 on the turn": (_fixed(500, "{}"), {}),
        "503 on the turn": (_fixed(503, "{}"), {}),
        "no exec in the turn": (
            _exec_route([{"type": "turn.done"}]),
            {"poll_limit": 0.05, "poll_interval": 0.0},
        ),
        "unreadable exec result": (
            _exec_route(
                [
                    {
                        "type": "model.message",
                        "tool_calls": [{"id": "c", "tool_info": {"name": "exec"}}],
                    },
                    {"type": "tool.response", "tool_call_id": "c", "content": "not json"},
                ]
            ),
            {},
        ),
    }
    for why, (route, kwargs) in cases.items():
        raised = run_against(route, **kwargs)
        assert not isinstance(raised, NeverRanError), f"{why} claimed the command never ran"
        assert isinstance(raised, TimedOutError), f"{why} raised {type(raised).__name__}"


# --------------------------------------------------------------------------
# A response that arrives damaged
# --------------------------------------------------------------------------


def test_a_truncated_response_is_a_transport_error_not_an_escape() -> None:
    """`IncompleteRead` is not an `OSError`, so it escaped the hierarchy."""
    route = _fixed(*_ok({"data": {"id": "s"}}))
    with _Harness(route, short_body=True) as harness, pytest.raises(TransportError):
        _client(harness).create_session({})


def test_a_truncated_response_never_claims_the_command_did_not_run() -> None:
    """The finding: a damaged read while polling means the command may have finished.

    Reported as never-ran, a caller retries something that already happened.
    """
    route = _fixed(*_ok({"data": {"id": "s"}}))
    with _Harness(route, short_body=True) as harness, pytest.raises(TimedOutError):
        SandboxExec(_client(harness), "model-x")("pytest -q", "/workspace")


def test_a_truncated_response_survives_the_runner_as_a_timeout() -> None:
    # End to end: the classification has to hold all the way through `run.py`,
    # whose own fallback reads an unknown exception as `NeverRanError`.
    from pathlib import Path

    from bumpsmith.run import SandboxRunner

    with _Harness(_fixed(*_ok({"data": {"id": "s"}})), short_body=True) as harness:
        runner = SandboxRunner(SandboxExec(_client(harness), "model-x"))
        with pytest.raises(TimedOutError):
            runner.run(["python", "-m", "pytest"], Path("/workspace"))


def test_an_unclassifiable_failure_is_read_as_may_have_run() -> None:
    """The safety net. Guessing "never ran" is the one unsafe direction."""

    class Exploding:
        """Not a `Client` subclass -- `Client` is final, and this is not one."""

        def create_session(self, spec: Mapping[str, object]) -> str:
            raise RuntimeError(f"something nobody anticipated ({len(spec)} fields)")

    exploding = cast("Client", Exploding())
    with pytest.raises(TimedOutError):
        SandboxExec(exploding, "model-x")("pytest", "/workspace")


# --------------------------------------------------------------------------
# The poll deadline is a deadline
# --------------------------------------------------------------------------


def _clock() -> tuple[Callable[[], float], Callable[[float], None]]:
    state = {"t": 0.0}

    def now() -> float:
        return state["t"]

    def sleep(seconds: float) -> None:
        state["t"] += seconds

    return now, sleep


def test_event_polling_stops_at_the_deadline_it_was_given() -> None:
    """The finding: 90 retries times a 120s timeout is not bounded by a 300s limit."""
    now, sleep = _clock()
    with _Harness(_fixed(200, "")) as harness:
        client = Client(harness.base_url, sleep=sleep, now=now, poll_interval=1.0)
        events = client.turn_events(Turn("s", "t"), deadline=5.0)
    assert events == []
    # Without the deadline this is TURN_EVENTS_EMPTY_RETRIES requests.
    assert len(harness.requests) <= 6, f"{len(harness.requests)} requests ignored the deadline"


def test_polling_passes_its_deadline_down() -> None:
    now, sleep = _clock()
    with _Harness(_fixed(200, "")) as harness:
        client = Client(harness.base_url, sleep=sleep, now=now, poll_interval=1.0, poll_limit=4.0)
        rounds = list(client.poll(Turn("s", "t")))
    assert rounds  # it did poll
    # A deadline consulted only between rounds would allow 90 requests per round.
    assert len(harness.requests) <= 8, f"{len(harness.requests)} requests outlived poll_limit"


def test_a_call_with_no_time_left_is_not_attempted() -> None:
    with _Harness(_session) as harness, pytest.raises(TransportError, match="no time left"):
        _client(harness).call("GET", "/anything", timeout=0.0)
    assert harness.requests == []


# --------------------------------------------------------------------------
# Drift is not patience
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("why", "body"),
    [
        ("a list instead of an object", "[]"),
        ("an object with no data", '{"ok": true}'),
        ("data is an object", '{"data": {"type": "turn.done"}}'),
        ("data is a string", '{"data": "turn.done"}'),
        ("data is null", '{"data": null}'),
    ],
)
def test_an_unreadable_events_response_says_so(why: str, body: str) -> None:
    """Retrying drift ninety times hid a permanent disagreement inside a slow turn."""
    assert why
    with _Harness(_fixed(200, body)) as harness, pytest.raises(ProtocolError):
        _client(harness).turn_events(Turn("s", "t"))


def test_a_non_event_in_the_list_is_not_silently_dropped() -> None:
    # It would be exactly the event explaining why the turn did nothing.
    route = _fixed(200, '{"data": [{"type": "model.message"}, "oops"]}')
    with _Harness(route) as harness, pytest.raises(ProtocolError):
        _client(harness).turn_events(Turn("s", "t"))


def test_an_unreadable_response_is_not_retried() -> None:
    with _Harness(_fixed(200, '{"data": {}}')) as harness, pytest.raises(ProtocolError):
        _client(harness).turn_events(Turn("s", "t"))
    assert len(harness.requests) == 1, "drift does not improve by being asked again"


def test_a_turn_with_no_events_yet_answers_with_no_events() -> None:
    # An empty list is a real answer; only an empty *body* is the transient case.
    with _Harness(_fixed(200, '{"data": []}')) as harness:
        assert _client(harness).turn_events(Turn("s", "t")) == []
    assert len(harness.requests) == 1
