"""Tests for the join between the harness's approval question and our gate.

The events here are built to the shapes in TrueForge's own wire schema --
``tool.approval_required`` carrying only ``{id, source_event_id}``, and a
``model.message`` whose ``tool_calls`` hold the function name, the JSON-string
arguments and the ``tool_info`` that says where the tool lives. The point of most
of these tests is not that a good event is handled but that a *damaged* one ends
as a deny that reaches the harness, because the failure this module exists to
prevent is a client answering about a call it never read.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

from bumpsmith.gate import Allow, Decision, Deny, Gate, Request
from bumpsmith.harness import (
    DENIED_BY,
    Answer,
    ApprovalBridge,
    MalformedEventError,
    PendingCall,
    UnreadableCallError,
    allow_event,
    deny_event,
    describe,
    read_call,
    read_question,
)

CALL = "call_0001"
ASKED = "evt_model_0001"
QUESTION = "evt_question_0001"


def _tool_call(
    *,
    call_id: str = CALL,
    name: str = "exec",
    arguments: str = '{"command": "rm -rf /srv", "timeout": 30}',
    origin: str = "mcp",
    server: str = "shell-tools",
    declared: str | None = None,
) -> dict[str, object]:
    info: dict[str, object] = {"type": origin, "name": declared if declared else name}
    if origin == "mcp":
        info["server_id"] = "srv_1"
        info["server_name"] = server
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
        "tool_info": info,
    }


def _model_message(
    *,
    event_id: str = ASKED,
    thread_id: str = "main",
    calls: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "type": "model.message",
        "id": event_id,
        "thread_id": thread_id,
        "created_at": "2026-08-26T00:00:00.000Z",
        "content": "I will clear the directory first.",
        "tool_calls": list(calls) if calls is not None else [_tool_call()],
    }


def _question_event(
    *,
    event_id: str = QUESTION,
    thread_id: str = "main",
    refs: Sequence[tuple[str, str]] = ((CALL, ASKED),),
) -> dict[str, object]:
    return {
        "type": "tool.approval_required",
        "id": event_id,
        "created_at": "2026-08-26T00:00:01.000Z",
        "thread_id": thread_id,
        "tool_calls": [{"id": call, "source_event_id": source} for call, source in refs],
    }


class _Approver:
    """Answers however it was built to, and remembers what it was asked."""

    def __init__(self, reply: Callable[[Request], Decision]) -> None:
        self._reply = reply
        self.seen: list[Request] = []

    def decide(self, request: Request) -> Decision:
        self.seen.append(request)
        return self._reply(request)


def _yes(request: Request) -> Decision:
    return Allow(fingerprint=request.fingerprint(), reason="a human said so")


def _no(request: Request) -> Decision:  # noqa: ARG001 -- the signature is the protocol
    return Deny(reason="not that command")


class _Channel:
    """Records what was sent; fails the first ``failures`` sends if asked to."""

    def __init__(self, failures: int = 0) -> None:
        self.sent: list[Mapping[str, object]] = []
        self._failures = failures

    def send(self, event: Mapping[str, object]) -> None:
        self.sent.append(dict(event))
        if self._failures > 0:
            self._failures -= 1
            raise ConnectionError("the harness was not reachable")


def _bridge(
    reply: Callable[[Request], Decision],
) -> tuple[ApprovalBridge, Gate, _Approver, _Channel]:
    approver = _Approver(reply)
    gate = Gate(approver)
    channel = _Channel()
    return ApprovalBridge(gate, channel), gate, approver, channel


# ---------------------------------------------------------------------------
# read_question
# ---------------------------------------------------------------------------


def test_read_question_parses_the_refs() -> None:
    question = read_question(_question_event())
    assert question.event_id == QUESTION
    assert question.thread_id == "main"
    assert question.calls == (PendingCall(tool_call_id=CALL, source_event_id=ASKED),)


def test_read_question_accepts_an_event_naming_nothing() -> None:
    """Odd, but the harness is allowed to ask about nothing; it is not our error."""
    assert read_question(_question_event(refs=())).calls == ()


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda e: e.__setitem__("type", "tool.response_required"), "expected a tool.approval"),
        (lambda e: e.__setitem__("id", ""), "'id'"),
        (lambda e: e.pop("thread_id"), "'thread_id'"),
        (lambda e: e.__setitem__("tool_calls", "call_1"), "no tool_calls list"),
        (lambda e: e.__setitem__("tool_calls", ["call_1"]), "is not an object"),
        (lambda e: e.__setitem__("tool_calls", [{"id": "c"}]), "'source_event_id'"),
    ],
)
def test_read_question_refuses_a_damaged_event(
    mutate: Callable[[dict[str, object]], object], fragment: str
) -> None:
    event = _question_event()
    mutate(event)
    with pytest.raises(MalformedEventError, match=fragment):
        read_question(event)


# ---------------------------------------------------------------------------
# read_call
# ---------------------------------------------------------------------------


def test_read_call_reads_the_message_that_asked() -> None:
    question = read_question(_question_event())
    call = read_call(question, question.calls[0], [_model_message()])
    assert call.tool == "exec"
    assert call.origin == "mcp:shell-tools"
    assert call.thread_id == "main"
    assert call.arguments == '{"command": "rm -rf /srv", "timeout": 30}'


def test_read_call_keeps_both_names_when_a_tool_was_remapped() -> None:
    """The name the model called and the name on the server are different facts."""
    question = read_question(_question_event())
    message = _model_message(calls=[_tool_call(name="shell_exec", declared="exec")])
    call = read_call(question, question.calls[0], [message])
    assert (call.tool, call.declared_tool) == ("shell_exec", "exec")


def test_read_call_reads_a_system_tool() -> None:
    question = read_question(_question_event())
    message = _model_message(calls=[_tool_call(origin="truefoundry-system")])
    assert read_call(question, question.calls[0], [message]).origin == "truefoundry-system"


@pytest.mark.parametrize(
    ("events", "fragment"),
    [
        ([], "is not among the events read"),
        ([_model_message(), _model_message()], "events share the id"),
        (
            [{"type": "tool.response", "id": ASKED, "thread_id": "main"}],
            "not a model.message",
        ),
        ([_model_message(thread_id="agent_1")], "on thread 'agent_1'"),
        ([_model_message(calls=[])], f"did not ask for {CALL}"),
        ([_model_message(calls=[_tool_call(call_id="other")])], f"did not ask for {CALL}"),
        (
            [_model_message(calls=[_tool_call(), _tool_call(arguments='{"command": "ls"}')])],
            "2 times with different content",
        ),
    ],
)
def test_read_call_refuses_what_it_cannot_pin_down(
    events: Sequence[Mapping[str, object]], fragment: str
) -> None:
    question = read_question(_question_event())
    with pytest.raises(UnreadableCallError, match=fragment):
        read_call(question, question.calls[0], events)


@pytest.mark.parametrize(
    ("mutate", "fragment"),
    [
        (lambda c: c.pop("function"), "carries no function"),
        (lambda c: cast("dict[str, object]", c["function"]).__setitem__("name", ""), "'name'"),
        (
            lambda c: cast("dict[str, object]", c["function"]).__setitem__(
                "arguments", {"command": "ls"}
            ),
            "arrived as dict",
        ),
        (lambda c: c.pop("tool_info"), "no tool_info"),
        (lambda c: cast("dict[str, object]", c["tool_info"]).pop("server_name"), "'server_name'"),
        (
            lambda c: cast("dict[str, object]", c["tool_info"]).__setitem__("type", "webhook"),
            "origin this build does not know",
        ),
    ],
)
def test_read_call_refuses_a_damaged_tool_call(
    mutate: Callable[[dict[str, object]], object], fragment: str
) -> None:
    call = _tool_call()
    mutate(call)
    question = read_question(_question_event())
    with pytest.raises(UnreadableCallError, match=fragment):
        read_call(question, question.calls[0], [_model_message(calls=[call])])


# ---------------------------------------------------------------------------
# describe
# ---------------------------------------------------------------------------


def test_describe_carries_the_arguments_verbatim() -> None:
    question = read_question(_question_event())
    raw = '{"command":  "rm -rf /srv" , "timeout":30}'
    message = _model_message(calls=[_tool_call(arguments=raw)])
    request = describe(read_call(question, question.calls[0], [message]))
    assert request.detail["arguments"] == raw
    assert request.action == "harness.tool_call:exec"


def test_describe_names_the_arguments_without_pretending_to_show_them() -> None:
    question = read_question(_question_event())
    request = describe(read_call(question, question.calls[0], [_model_message()]))
    assert "arguments: command, timeout" in request.summary
    assert "the values are in the detail" in request.summary
    assert "rm -rf /srv" not in request.summary


def test_describe_says_so_when_the_arguments_are_not_a_json_object() -> None:
    question = read_question(_question_event())
    message = _model_message(calls=[_tool_call(arguments="not json at all")])
    request = describe(read_call(question, question.calls[0], [message]))
    assert "not a JSON object" in request.summary
    assert request.detail["arguments"] == "not json at all"


def test_two_identical_calls_are_two_decisions() -> None:
    """One yes must not stand for the identical call next to it."""
    question = read_question(_question_event(refs=((CALL, ASKED), ("call_0002", ASKED))))
    message = _model_message(calls=[_tool_call(), _tool_call(call_id="call_0002")])
    first = describe(read_call(question, question.calls[0], [message]))
    second = describe(read_call(question, question.calls[1], [message]))
    assert first.detail["arguments"] == second.detail["arguments"]
    assert first.fingerprint() != second.fingerprint()


# ---------------------------------------------------------------------------
# the events sent back
# ---------------------------------------------------------------------------


def test_allow_event_shape() -> None:
    assert allow_event("main", CALL) == {
        "type": "user.tool_approval",
        "thread_id": "main",
        "tool_call_id": CALL,
        "approval": {"status": "allow"},
    }


def test_deny_event_carries_the_reason_and_omits_an_empty_one() -> None:
    assert deny_event("main", CALL, "no")["approval"] == {"status": "deny", "reason": "no"}
    assert deny_event("main", CALL, "   ")["approval"] == {"status": "deny"}


# ---------------------------------------------------------------------------
# ApprovalBridge
# ---------------------------------------------------------------------------


def test_an_approved_call_is_allowed_once_and_recorded() -> None:
    bridge, gate, approver, channel = _bridge(_yes)
    answers = bridge.answer(_question_event(), [_model_message()])

    assert [a.status for a in answers] == ["allowed"]
    assert channel.sent == [allow_event("main", CALL)]
    assert [r.outcome for r in gate.history] == ["allowed"]
    assert approver.seen[0].detail["tool"] == "exec"


def test_a_refused_call_is_denied_to_the_harness_with_the_reason() -> None:
    bridge, gate, _, channel = _bridge(_no)
    (answer,) = bridge.answer(_question_event(), [_model_message()])

    assert answer.status == "denied"
    assert channel.sent == [deny_event("main", CALL, f"{DENIED_BY}not that command")]
    assert [r.outcome for r in gate.history] == ["denied"]


def test_a_call_that_cannot_be_read_is_denied_without_asking_anybody() -> None:
    """The approver is never shown a request nobody could describe."""
    bridge, gate, approver, channel = _bridge(_yes)
    (answer,) = bridge.answer(_question_event(), [])

    assert answer.status == "denied"
    assert approver.seen == []
    assert len(channel.sent) == 1
    approval = cast("Mapping[str, object]", channel.sent[0]["approval"])
    assert approval["status"] == "deny"
    assert "is not among the events read" in cast("str", approval["reason"])
    assert [r.outcome for r in gate.history] == ["denied"]
    assert gate.history[0].request.action == "harness.tool_call"
    assert "problem" in gate.history[0].request.detail


def test_no_approver_at_all_still_answers_the_harness() -> None:
    """A bridge assembled from nothing configured refuses; it does not hang the turn."""
    channel = _Channel()
    gate = Gate(None)
    (answer,) = ApprovalBridge(gate, channel).answer(_question_event(), [_model_message()])

    assert answer.status == "denied"
    approval = cast("Mapping[str, object]", channel.sent[0]["approval"])
    assert approval["status"] == "deny"
    assert "no approver is configured" in cast("str", approval["reason"])


def test_an_approval_for_a_different_request_does_not_let_this_one_through() -> None:
    """The composed guarantee: a rubber stamp is not an approval of this call."""

    def stamp(request: Request) -> Decision:  # noqa: ARG001 -- the signature is the protocol
        return Allow(fingerprint="0" * 64, reason="looks fine")

    bridge, gate, _, channel = _bridge(stamp)
    (answer,) = bridge.answer(_question_event(), [_model_message()])

    assert answer.status == "denied"
    assert cast("Mapping[str, object]", channel.sent[0]["approval"])["status"] == "deny"
    assert gate.history[0].reason == "the approval was made for a different request"


def test_the_same_question_delivered_twice_is_decided_once() -> None:
    """Events are polled, so the same question arrives again on every look."""
    bridge, gate, approver, channel = _bridge(_yes)
    event, events = _question_event(), [_model_message()]

    first = bridge.answer(event, events)
    second = bridge.answer(event, events)

    assert [a.status for a in first] == ["allowed"]
    assert [a.status for a in second] == ["repeated"]
    assert len(channel.sent) == 1
    assert len(approver.seen) == 1
    assert len(gate.history) == 1


def test_one_bad_call_does_not_take_the_good_one_with_it() -> None:
    bridge, _, _, channel = _bridge(_yes)
    answers = bridge.answer(
        _question_event(refs=((CALL, ASKED), ("call_0002", "evt_missing"))),
        [_model_message()],
    )

    assert [a.status for a in answers] == ["allowed", "denied"]
    assert [cast("Mapping[str, object]", e["approval"])["status"] for e in channel.sent] == [
        "allow",
        "deny",
    ]


def test_an_undelivered_denial_is_not_remembered_as_delivered() -> None:
    """A send that failed left the turn paused; the next look must try again."""
    channel = _Channel(failures=1)
    bridge = ApprovalBridge(Gate(_Approver(_no)), channel)

    with pytest.raises(ConnectionError):
        bridge.answer(_question_event(), [_model_message()])
    assert bridge.answered == {}

    (answer,) = bridge.answer(_question_event(), [_model_message()])
    assert answer.status == "denied"
    assert len(channel.sent) == 2


def test_an_effect_that_failed_after_approval_is_recorded_as_failed() -> None:
    channel = _Channel(failures=1)
    gate = Gate(_Approver(_yes))
    bridge = ApprovalBridge(gate, channel)

    with pytest.raises(ConnectionError):
        bridge.answer(_question_event(), [_model_message()])

    assert [r.outcome for r in gate.history] == ["failed"]
    assert bridge.answered == {}


def test_answered_is_a_snapshot_the_caller_cannot_edit() -> None:
    bridge, _, _, _ = _bridge(_yes)
    bridge.answer(_question_event(), [_model_message()])
    answered = bridge.answered

    assert set(answered) == {CALL}
    with pytest.raises(TypeError):
        cast("dict[str, Answer]", answered)["call_9999"] = answered[CALL]
    assert set(bridge.answered) == {CALL}


def test_a_generator_of_events_is_read_once_for_every_call() -> None:
    """The second call must not find the events already consumed."""
    bridge, _, _, channel = _bridge(_yes)
    message = _model_message(calls=[_tool_call(), _tool_call(call_id="call_0002")])
    answers = bridge.answer(
        _question_event(refs=((CALL, ASKED), ("call_0002", ASKED))),
        (event for event in [message]),
    )

    assert [a.status for a in answers] == ["allowed", "allowed"]
    assert len(channel.sent) == 2


# ---------------------------------------------------------------------------
# the harness's call_tool wrapper
# ---------------------------------------------------------------------------


def _wrapped(arguments: str) -> dict[str, object]:
    """A ``call_tool`` call: a system tool whose arguments name the real one."""
    return _tool_call(name="call_tool", origin="truefoundry-system", arguments=arguments)


WRAPPED_ARGS = json.dumps(
    {
        "mcp_server": "irreversible-things",
        "tool_name": "open_pull_request",
        "input": {"repository": "aryangorde8/bumpsmith", "branch": "wip", "title": "a change"},
    }
)


def test_a_wrapped_call_is_named_as_the_tool_that_will_run() -> None:
    question = read_question(_question_event())
    call = read_call(question, question.calls[0], [_model_message(calls=[_wrapped(WRAPPED_ARGS)])])

    assert (call.tool, call.origin) == ("open_pull_request", "mcp:irreversible-things")
    assert call.via == "call_tool"
    assert call.arguments == WRAPPED_ARGS


def test_a_wrapped_call_shows_the_arguments_the_tool_receives() -> None:
    """The wrapper's own keys are the same three every time and say nothing."""
    question = read_question(_question_event())
    request = describe(
        read_call(question, question.calls[0], [_model_message(calls=[_wrapped(WRAPPED_ARGS)])])
    )

    assert request.action == "harness.tool_call:open_pull_request"
    assert "arguments: branch, repository, title" in request.summary
    assert "mcp_server" not in request.summary
    assert request.detail["via"] == "call_tool"
    assert request.detail["arguments"] == WRAPPED_ARGS


def test_a_direct_call_says_nothing_about_a_wrapper() -> None:
    question = read_question(_question_event())
    request = describe(read_call(question, question.calls[0], [_model_message()]))

    assert "via" not in request.detail
    assert "reached through" not in request.summary


def test_a_wrapped_call_with_no_input_has_no_arguments() -> None:
    question = read_question(_question_event())
    arguments = json.dumps({"mcp_server": "s", "tool_name": "ping"})
    request = describe(
        read_call(question, question.calls[0], [_model_message(calls=[_wrapped(arguments)])])
    )

    assert "no arguments" in request.summary


def test_a_wrapped_call_whose_input_is_not_an_object_says_so() -> None:
    question = read_question(_question_event())
    arguments = json.dumps({"mcp_server": "s", "tool_name": "ping", "input": ["one"]})
    request = describe(
        read_call(question, question.calls[0], [_model_message(calls=[_wrapped(arguments)])])
    )

    assert "not a JSON object" in request.summary


@pytest.mark.parametrize(
    ("arguments", "fragment"),
    [
        ("not json", "which server"),
        (json.dumps({"tool_name": "open_pull_request"}), "which server"),
        (json.dumps({"mcp_server": "  "}), "which server"),
        (json.dumps({"mcp_server": "s"}), "which tool"),
        (json.dumps({"mcp_server": "s", "tool_name": ""}), "which tool"),
    ],
)
def test_a_wrapper_that_does_not_say_what_it_would_call_is_unreadable(
    arguments: str, fragment: str
) -> None:
    question = read_question(_question_event())
    with pytest.raises(UnreadableCallError, match=fragment):
        read_call(question, question.calls[0], [_model_message(calls=[_wrapped(arguments)])])


@pytest.mark.parametrize("field", ["server_name", "server_id"])
def test_a_server_the_harness_could_not_resolve_is_not_an_attribution(field: str) -> None:
    """`unknown` is the harness's filler, and `mcp:unknown` would read as a name."""
    call = _tool_call()
    cast("dict[str, object]", call["tool_info"])[field] = "unknown"
    question = read_question(_question_event())

    with pytest.raises(UnreadableCallError, match="could not resolve one"):
        read_call(question, question.calls[0], [_model_message(calls=[call])])


# ---------------------------------------------------------------------------
# against events the harness really produced
# ---------------------------------------------------------------------------

RECORDED = Path(__file__).parent / "data" / "approval-call-tool.json"
RECORDED_ASKED = "01m0x812624c5jf5wkw9qwzjqt"
RECORDED_UNRESOLVED = "01m0x80xcv0rmj9h5dt19shskc"


def _recorded() -> tuple[dict[str, object], list[dict[str, object]]]:
    payload = json.loads(RECORDED.read_text(encoding="utf-8"))
    return payload["question"], payload["events"]


def test_the_recorded_event_names_the_wrapper_and_not_the_tool() -> None:
    """The fact the unwrapping exists for, pinned against a real recording."""
    _, events = _recorded()
    (asking,) = [event for event in events if event["id"] == RECORDED_ASKED]
    (call,) = cast("Sequence[Mapping[str, object]]", asking["tool_calls"])

    assert cast("Mapping[str, object]", call["function"])["name"] == "call_tool"
    assert call["tool_info"] == {"type": "truefoundry-system", "name": "call_tool"}


def test_a_real_paused_call_is_read_back_to_what_it_would_have_done() -> None:
    bridge, gate, approver, channel = _bridge(_no)
    question_event, events = _recorded()

    (answer,) = bridge.answer(question_event, events)

    assert answer.status == "denied"
    assert answer.request.action == "harness.tool_call:open_pull_request"
    assert answer.request.detail["origin"] == "mcp:irreversible-things"
    assert answer.request.detail["via"] == "call_tool"
    assert "arguments: branch, repository, title" in answer.request.summary
    assert approver.seen[0].detail["tool"] == "open_pull_request"
    assert channel.sent[0]["tool_call_id"] == "call_2bd2ef15af4b4203b789a730"
    assert [r.outcome for r in gate.history] == ["denied"]


def test_the_recorded_unresolved_server_is_refused() -> None:
    """The same run also holds a call the harness could not attribute to a server."""
    _, events = _recorded()
    (asking,) = [event for event in events if event["id"] == RECORDED_UNRESOLVED]
    (call,) = cast("Sequence[Mapping[str, object]]", asking["tool_calls"])
    question = read_question(
        _question_event(refs=((cast("str", call["id"]), RECORDED_UNRESOLVED),))
    )

    with pytest.raises(UnreadableCallError, match="could not resolve one"):
        read_call(question, question.calls[0], events)
