"""Tests for the session-reconnect proof, including that it can fail.

The proof in ``proofs/session_reconnect.py`` makes a claim about a live harness,
so nothing here can check the claim itself. What these tests check is the thing
that would otherwise go unexamined: **whether the proof would notice if the claim
were false.**

A proof that passes against a harness where sessions share one filesystem is not
evidence that a session held; it is a script that prints a reassuring sentence.
So the fake below is built three ways -- sessions with separate sandboxes, one
shared sandbox, and a sandbox that forgets between turns -- and the proof is
required to pass against the first and fail against the other two, naming which
leg failed.

That is the same discipline the rest of this repository uses on its guards: a
control nobody has watched fail is not known to be a control.
"""

import http.server
import json
import re
import shlex
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from session_reconnect import ABSENT, MARKER, main

World = Callable[[str], dict[str, str]]
"""Given a session id, the filesystem that session's sandbox sees."""

_WROTE = re.compile(r"printf '%s' (\S+) > ")


class _Harness:
    """A stand-in TrueForge that models sandboxes as dictionaries.

    It answers on a real socket, like ``tests/test_trueforge.py``'s does, because
    the proof builds its own :class:`~bumpsmith.trueforge.Client` and a fake that
    replaced the transport would not exercise the reconnect at all -- the whole
    claim is about a *new client* reaching an *old session*.
    """

    def __init__(self, world: World) -> None:
        self.world = world
        self.sessions: list[str] = []
        self.turns: dict[str, tuple[str, str]] = {}
        self.commands: list[str] = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _reply(self, payload: object) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else {}
                if self.path.endswith("/sessions"):
                    session = f"sess-{len(outer.sessions) + 1}"
                    outer.sessions.append(session)
                    self._reply({"data": {"id": session}})
                    return
                session = self.path.split("/sessions/")[1].split("/turns")[0]
                turn = f"turn-{len(outer.turns) + 1}"
                outer.turns[turn] = (session, outer._run(session, body))
                self._reply({"data": {"id": turn}})

            def do_GET(self) -> None:
                turn = self.path.split("/turns/")[1].split("/events")[0]
                _, output = outer.turns[turn]
                self._reply(
                    {
                        "data": [
                            {
                                "type": "model.message",
                                "tool_calls": [{"id": "call-1", "tool_info": {"name": "exec"}}],
                            },
                            {
                                "type": "tool.response",
                                "tool_call_id": "call-1",
                                "content": json.dumps(
                                    {
                                        "success": True,
                                        "response": {"exitCode": 0, "result": output},
                                    }
                                ),
                            },
                        ]
                    }
                )

            def log_message(self, *args: Any) -> None:
                pass

        self._server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _run(self, session: str, body: Any) -> str:
        """Interpret the one shell line the proof sends, against a sandbox."""
        message = str(body["input"][0]["content"])
        argv = shlex.split(message.split("\n\n", 1)[1])
        script = argv[2]
        self.commands.append(script)
        files = self.world(session)
        wrote = _WROTE.search(script)
        if wrote is not None:
            files[MARKER] = wrote.group(1)
            return "written"
        return files.get(MARKER, ABSENT)

    def __enter__(self) -> "_Harness":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/api/v1"


def _separate() -> World:
    """What an honest harness does: one sandbox per session, and it persists."""
    worlds: dict[str, dict[str, str]] = {}
    return lambda session: worlds.setdefault(session, {})


def _shared() -> World:
    """Every session sees one filesystem. Leg 3 exists for exactly this."""
    everything: dict[str, str] = {}
    return lambda _session: everything


def _amnesiac() -> World:
    """A sandbox that keeps nothing at all, so even leg 1 cannot set its marker."""
    return lambda _session: {}


LEG_ONE_COMMANDS = 2
"""Leg 1 issues a write and a read; leg 2 and leg 3 issue one read each.

:func:`_forgetful` counts touches to decide when the reconnect happens, so it is
coupled to that number. ``test_the_proof_issues_the_commands_the_fake_assumes``
fails if the proof's shape ever changes, rather than letting these worlds quietly
start modelling something else.
"""


def _forgetful() -> World:
    """The session id is accepted and reaches a *different* sandbox afterwards.

    This is what "the session did not hold" looks like from outside: leg 1 writes
    and reads its marker back happily, and the reconnect lands somewhere else.
    Distinct from :func:`_amnesiac`, where nothing is ever kept and the fault is
    in leg 1 rather than in the session.
    """
    worlds: dict[str, dict[str, str]] = {}
    touches: dict[str, int] = {}

    def world(session: str) -> dict[str, str]:
        touches[session] = touches.get(session, 0) + 1
        if touches[session] > LEG_ONE_COMMANDS:
            return {}
        return worlds.setdefault(session, {})

    return world


@pytest.fixture
def run(tmp_path: Path) -> Iterator[Callable[[World], tuple[int, dict[str, Any], _Harness]]]:
    """Run the proof against a world, and hand back its exit code and evidence."""

    def go(world: World) -> tuple[int, dict[str, Any], _Harness]:
        out = tmp_path / "evidence.json"
        with _Harness(world) as harness:
            code = main(
                [
                    "--base-url",
                    harness.base_url,
                    "--out",
                    str(out),
                    "--nonce",
                    "abc123",
                ]
            )
        written = json.loads(out.read_text()) if out.exists() else {}
        return code, written, harness

    yield go


Run = Callable[[World], tuple[int, dict[str, Any], _Harness]]


def test_the_proof_passes_when_a_session_keeps_its_sandbox(run: Run) -> None:
    """The honest world: three legs, and each one says what it should."""
    code, evidence, _harness = run(_separate())
    assert code == 0
    assert evidence["established"]["read"] == "abc123"
    assert evidence["reconnected"]["read"] == "abc123"
    assert evidence["control"]["read"] == ABSENT


def test_the_proof_issues_the_commands_the_fake_assumes(run: Run) -> None:
    """Four commands, in the order the worlds above are written against.

    :func:`_forgetful` decides where the reconnect starts by counting touches, so
    a proof that grew a fifth command would turn that world into a model of
    something else while every assertion still passed. This is the test that
    fails instead.
    """
    _code, _evidence, harness = run(_separate())
    assert len(harness.commands) == LEG_ONE_COMMANDS + 2
    assert "echo written" in harness.commands[0]
    assert all("cat " in command for command in harness.commands[1:])


def test_the_reconnect_uses_the_session_the_first_leg_opened(run: Run) -> None:
    """Leg 2 must be the *same* session, and leg 3 must not be.

    Without the second half, a control that quietly reused the established
    session would find the marker and the proof would still pass -- which is the
    failure mode leg 3 was added to remove, reappearing inside leg 3.
    """
    _code, evidence, _harness = run(_separate())
    assert evidence["reconnected"]["session"] == evidence["established"]["session"]
    assert evidence["control"]["session"] != evidence["established"]["session"]


def test_a_shared_sandbox_fails_the_control(run: Run, capsys: pytest.CaptureFixture[str]) -> None:
    """If every session sees one filesystem, leg 2 proves nothing and must not pass.

    This is the test that makes the proof a proof. A harness pooling sandboxes
    would let legs 1 and 2 both read the marker back, and the script would print
    that the session held, having demonstrated nothing at all.
    """
    code, evidence, _harness = run(_shared())
    assert code == 1
    assert evidence["control"]["read"] == "abc123"
    assert "the control failed" in capsys.readouterr().err


def test_a_session_that_does_not_hold_fails_the_second_leg(
    run: Run, capsys: pytest.CaptureFixture[str]
) -> None:
    """The claim being false is the case that matters most, and it is caught."""
    code, evidence, _harness = run(_forgetful())
    assert code == 1
    assert evidence["established"]["read"] == "abc123"
    assert evidence["reconnected"]["read"] == ABSENT
    assert "the session did not hold" in capsys.readouterr().err


def test_a_marker_that_never_landed_stops_before_anything_else_is_read(
    run: Run, capsys: pytest.CaptureFixture[str]
) -> None:
    """Leg 1 failing is not the session failing, and the two must not be confused.

    ``_amnesiac`` keeps nothing, so leg 1's own read comes back absent. Reporting
    that as "the session did not hold" would blame the harness for a proof that
    never set its own marker, so leg 1 is checked first and names itself.
    """
    code, _evidence, _harness = run(_amnesiac())
    assert code == 1
    err = capsys.readouterr().err
    assert "leg 1 never had the marker" in err
    assert "the session did not hold" not in err
