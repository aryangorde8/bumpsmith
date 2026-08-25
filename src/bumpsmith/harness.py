"""Answer the harness's approval question with the gate that guards our own effects.

TrueForge stops a tool call it was told needs approval, emits
``tool.approval_required``, and waits. The turn does not move again until a
``user.tool_approval`` event arrives naming that call. Whatever sends that event
is the thing deciding what the agent may do, so it should be the same thing that
decides everything else -- :class:`bumpsmith.gate.Gate`. This module is the join:
it turns the harness's question into a :class:`~bumpsmith.gate.Request`, and the
gate's answer into the event the harness is waiting for.

What the question leaves out
----------------------------
``tool.approval_required`` carries ``{id, source_event_id}`` per call and nothing
else. No tool name, no arguments, no server. The name and the arguments are in
the ``model.message`` that ``source_event_id`` points at, and reading it is the
client's job. A client that answers on the id alone approves something it never
read, and it will do that as confidently for ``rm -rf /`` as for ``ls``.

So: **a call that cannot be read is denied.** Not skipped, not logged and left
pending -- denied, with the reason, in the same event a considered refusal would
have used. A call whose asking message is missing, is on another thread, or does
not contain that call is a call nobody can describe, and this module will not be
the reason it ran.

The name in the event is not always the name that runs
------------------------------------------------------
Tools the harness has not put in the model's context are called through its own
``call_tool`` wrapper, whose arguments carry the real server and tool::

    {"mcp_server": "github", "tool_name": "create_pull_request", "input": {...}}

The harness resolves that wrapper before deciding whether to pause -- the pause is
earned by the *inner* tool's annotations -- but the event it hands the client still
carries the wrapper's identity: ``truefoundry-system`` / ``call_tool``. A client
that reports what ``tool_info`` says therefore describes the wrong tool, and does
it identically for every deferred call on the machine. This module unwraps it, so
what is approved is named as what will run. The measurement that found this is in
``REVIEW-LOG.md``; it did not come from reading the schema, which is consistent
with itself on this point.

Deciding is not transport
-------------------------
Nothing here opens a socket. Events come in as mappings and go out through
:class:`Channel`, so the decisions can be tested against recorded events rather
than against a live agent, and so that the module cannot quietly acquire a
retry-until-it-works loop around an approval.

What this cannot check
----------------------
Reading the ``model.message`` establishes what the model *asked* for. It does not
establish what the harness will *run*: between the approval and the execution sits
the harness's own dispatch, which this process does not own. The gap is narrow and
it is not nothing, which is the honest reason bumpsmith also guards its own
irreversible effects in-process (:mod:`bumpsmith.gate`) instead of trusting that
every dangerous thing will arrive here first.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from types import MappingProxyType
from typing import Literal, Protocol, final

from bumpsmith.gate import Gate, NotApprovedError, Request

#: The event the harness emits when it has paused one or more tool calls.
APPROVAL_REQUIRED = "tool.approval_required"
#: The event the harness waits for before it will move again.
USER_TOOL_APPROVAL = "user.tool_approval"
#: The event type that holds what the model actually asked for.
MODEL_MESSAGE = "model.message"

#: The harness's own wrapper for calling a tool it had not put in the model's
#: context. Its arguments name the server and the tool that will really run.
WRAPPER_TOOL = "call_tool"
#: What `tool_info.type` says for a tool the harness itself provides.
SYSTEM_ORIGIN = "truefoundry-system"
#: What the harness fills in for a server it could not identify. A call carrying
#: this is a call with no attribution, whatever the field says.
UNATTRIBUTED = "unknown"

#: Prefixed to every reason sent back, so a refusal in the agent's transcript
#: says which layer refused. A trail that records "denied" without saying by whom
#: is one somebody has to reconstruct later from timestamps.
DENIED_BY = "bumpsmith: "


class HarnessError(Exception):
    """Something arrived from the harness that this module will not act on."""


class MalformedEventError(HarnessError):
    """The event is not the approval question it claims to be."""


class UnreadableCallError(HarnessError):
    """A pending call could not be read back to what it would run."""


@dataclass(frozen=True, slots=True)
class PendingCall:
    """One entry of ``tool_calls`` -- an id, and where to go and read about it."""

    tool_call_id: str
    source_event_id: str


@dataclass(frozen=True, slots=True)
class Question:
    """A parsed ``tool.approval_required``.

    ``calls`` may be empty. An approval event that names nothing is odd but it is
    not malformed, and inventing an error for it would mean this module decides
    what the harness is allowed to ask.
    """

    event_id: str
    thread_id: str
    calls: tuple[PendingCall, ...]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A pending call, read back from the message that asked for it.

    ``tool``, ``origin`` and ``declared_tool`` describe what will run, after any
    unwrapping. ``via`` names the wrapper it arrived through, or is empty for a
    call the model made directly; it is kept because "the agent called this tool"
    and "the agent asked the harness to go and find this tool" are different
    stories about the same run.

    ``arguments`` is never rewritten. When the call arrived wrapped, this is still
    the wrapper's argument string -- the text the harness itself parses -- because
    a description that re-encoded it would be showing a human one string while the
    harness acts on another.
    """

    tool_call_id: str
    thread_id: str
    tool: str
    origin: str
    declared_tool: str
    arguments: str
    via: str = ""


def _string(source: Mapping[str, object], key: str, error: type[HarnessError], where: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise error(f"{where} has no usable {key!r}")
    return value


def read_question(event: Mapping[str, object]) -> Question:
    """Parse a ``tool.approval_required`` event, or refuse to.

    Strict about the shape on purpose. Everything downstream assumes these fields
    exist, and a mapping that half-parses here becomes a confident answer about a
    call nobody identified.
    """
    kind = event.get("type")
    if kind != APPROVAL_REQUIRED:
        raise MalformedEventError(f"expected a {APPROVAL_REQUIRED} event, got {kind!r}")
    event_id = _string(event, "id", MalformedEventError, APPROVAL_REQUIRED)
    thread_id = _string(event, "thread_id", MalformedEventError, APPROVAL_REQUIRED)

    raw = event.get("tool_calls")
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise MalformedEventError(f"{event_id} has no tool_calls list")

    calls: list[PendingCall] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, Mapping):
            raise MalformedEventError(f"tool_calls[{index}] of {event_id} is not an object")
        where = f"tool_calls[{index}] of {event_id}"
        calls.append(
            PendingCall(
                tool_call_id=_string(entry, "id", MalformedEventError, where),
                source_event_id=_string(entry, "source_event_id", MalformedEventError, where),
            )
        )
    return Question(event_id=event_id, thread_id=thread_id, calls=tuple(calls))


def _json_object(text: str) -> dict[str, object] | None:
    """The text parsed as a JSON object, or ``None`` if it is not one."""
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def read_call(
    question: Question,
    pending: PendingCall,
    events: Iterable[Mapping[str, object]],
) -> ToolCall:
    """Resolve ``pending`` back to the call the model asked for.

    Raises :class:`UnreadableCallError` -- with a reason fit to send back -- rather
    than returning anything partial. Every branch below is a way of not knowing
    what would run, and they are all the same answer.
    """
    asking = [
        event
        for event in events
        if isinstance(event, Mapping) and event.get("id") == pending.source_event_id
    ]
    if not asking:
        raise UnreadableCallError(
            f"the message that asked for {pending.tool_call_id} "
            f"({pending.source_event_id}) is not among the events read"
        )
    if len(asking) > 1:
        # Ids are monotonic ULIDs, so this should not happen. If it does, the
        # events being read are not one turn's, and picking either one would be
        # answering about a call from somewhere else.
        raise UnreadableCallError(
            f"{len(asking)} events share the id {pending.source_event_id}, "
            "so there is no telling which one asked"
        )

    source = asking[0]
    kind = source.get("type")
    if kind != MODEL_MESSAGE:
        raise UnreadableCallError(
            f"{pending.source_event_id} is a {kind!r}, not a {MODEL_MESSAGE}, "
            "so it did not ask for a tool call"
        )
    on_thread = source.get("thread_id")
    if on_thread != question.thread_id:
        raise UnreadableCallError(
            f"the message that asked is on thread {on_thread!r}, but the approval "
            f"is for thread {question.thread_id!r}"
        )

    raw = source.get("tool_calls")
    if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
        raise UnreadableCallError(f"{pending.source_event_id} asked for no tool calls at all")
    hits = [
        entry
        for entry in raw
        if isinstance(entry, Mapping) and entry.get("id") == pending.tool_call_id
    ]
    if not hits:
        raise UnreadableCallError(
            f"{pending.source_event_id} did not ask for {pending.tool_call_id}"
        )
    if len(hits) > 1:
        raise UnreadableCallError(
            f"{pending.source_event_id} asked for {pending.tool_call_id} "
            f"{len(hits)} times with different content"
        )

    hit = hits[0]
    where = f"tool call {pending.tool_call_id}"
    function = hit.get("function")
    if not isinstance(function, Mapping):
        raise UnreadableCallError(f"{where} carries no function to run")
    tool = _string(function, "name", UnreadableCallError, where)

    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        # The wire format defines this as a JSON-encoded *string*. Something else
        # here means the event is not the event this code was written against,
        # and re-encoding it would be inventing the text a human then approves.
        raise UnreadableCallError(
            f"the arguments for {tool} arrived as {type(arguments).__name__}, "
            "not the JSON string the wire format defines"
        )

    info = hit.get("tool_info")
    if not isinstance(info, Mapping):
        raise UnreadableCallError(f"{tool} came with no tool_info, so where it runs is unstated")
    declared = _string(info, "name", UnreadableCallError, f"the tool_info of {where}")
    origin_kind = info.get("type")
    if origin_kind == "mcp":
        server = _string(info, "server_name", UnreadableCallError, f"the tool_info of {where}")
        if UNATTRIBUTED in {server, info.get("server_id")}:
            # What the harness fills in for a server it could not resolve -- and
            # also a name somebody could legitimately give a server. Refusing both
            # costs a run; telling them apart is not possible from here, and
            # reporting `mcp:unknown` as an attribution would be inventing one.
            raise UnreadableCallError(
                f"{tool} is attributed to a server named {UNATTRIBUTED!r}, "
                "which is what the harness says when it could not resolve one"
            )
        origin = f"mcp:{server}"
    elif origin_kind == SYSTEM_ORIGIN:
        origin = SYSTEM_ORIGIN
    else:
        # Two servers can publish the same tool name, so an origin this build
        # cannot name is an attribution it cannot make. Denying here costs a
        # retry; guessing costs whichever server was not the one meant.
        raise UnreadableCallError(
            f"{tool} declares an origin this build does not know: {origin_kind!r}"
        )

    via = ""
    if origin == SYSTEM_ORIGIN and tool == WRAPPER_TOOL:
        via, tool, origin, declared = _unwrap(arguments)

    return ToolCall(
        tool_call_id=pending.tool_call_id,
        thread_id=question.thread_id,
        tool=tool,
        origin=origin,
        declared_tool=declared,
        arguments=arguments,
        via=via,
    )


def _unwrap(arguments: str) -> tuple[str, str, str, str]:
    """Read the real tool out of a ``call_tool`` call: ``(via, tool, origin, declared)``.

    The server name here comes from the model's own arguments rather than from the
    harness, which sounds weaker than it is: the harness routes on that same
    string, so it is what runs regardless of who wrote it.
    """
    wrapped = _json_object(arguments)
    server = wrapped.get("mcp_server") if wrapped is not None else None
    inner = wrapped.get("tool_name") if wrapped is not None else None
    if not isinstance(server, str) or not server.strip():
        raise UnreadableCallError(f"{WRAPPER_TOOL} did not say which server it would call")
    if not isinstance(inner, str) or not inner.strip():
        raise UnreadableCallError(f"{WRAPPER_TOOL} did not say which tool it would call")
    return WRAPPER_TOOL, inner, f"mcp:{server}", inner


def _argument_names(call: ToolCall) -> tuple[str, ...] | None:
    """The names of the arguments the tool will receive, or ``None`` if unreadable.

    For a wrapped call these are the keys of ``input``, not of the wrapper: the
    wrapper's keys are always ``mcp_server``, ``tool_name`` and ``input``, which
    says nothing about the call anybody is being asked to approve. ``input`` is
    optional in the wrapper's own schema, so its absence is no arguments rather
    than a fault.
    """
    parsed = _json_object(call.arguments)
    if parsed is None:
        return None
    if call.via:
        if "input" not in parsed:
            return ()
        inner = parsed["input"]
        if not isinstance(inner, dict):
            return None
        parsed = inner
    return tuple(sorted(str(key) for key in parsed))


def describe(call: ToolCall) -> Request:
    """The question a human is actually being asked.

    ``action`` names the tool so a policy can match on it. ``detail`` carries the
    arguments verbatim, exactly as the model wrote them: normalising them would
    mean the text somebody approved and the text that runs are two different
    strings, which is the whole failure this module exists to avoid.

    The fingerprint therefore covers ``tool_call_id`` as well, which makes an
    approval good for one call and not for the identical call next to it. That is
    deliberate -- "run this command" twice is two decisions, and a fingerprint
    that collapsed them would let one yes stand for both.

    ``action`` names the unwrapped tool. Naming the wrapper instead would give
    every deferred call on the machine the same action, and a policy written
    against that would be a policy about nothing.
    """
    names = _argument_names(call)
    if names is None:
        shown = f"{len(call.arguments)} bytes of arguments that are not a JSON object"
    elif names:
        shown = "arguments: " + ", ".join(names)
    else:
        shown = "no arguments"
    detail = {
        "tool": call.tool,
        "origin": call.origin,
        "declared_tool": call.declared_tool,
        "thread": call.thread_id,
        "tool_call_id": call.tool_call_id,
        "arguments": call.arguments,
    }
    through = ""
    if call.via:
        # Only when there is one. A key saying "not wrapped" on every direct call
        # is a line that stops being read, and this one has to be read.
        detail["via"] = call.via
        through = f", reached through the harness's {call.via}"
    return Request(
        action=f"harness.tool_call:{call.tool}",
        summary=(
            f"run {call.tool} from {call.origin} on thread {call.thread_id}{through} "
            f"({shown}); the values are in the detail, not in this line"
        ),
        detail=detail,
    )


def _unreadable_request(question: Question, pending: PendingCall, problem: str) -> Request:
    """The request for a call that could not be read.

    ``action`` deliberately carries no tool name: there is none to give. A request
    that guessed one would make the audit trail claim knowledge the refusal was
    caused by not having.
    """
    return Request(
        action="harness.tool_call",
        summary=(
            f"a tool call on thread {question.thread_id} that cannot be read back "
            "to what it would run"
        ),
        detail={
            "tool_call_id": pending.tool_call_id,
            "source_event_id": pending.source_event_id,
            "thread": question.thread_id,
            "problem": problem,
        },
    )


def allow_event(thread_id: str, tool_call_id: str) -> dict[str, object]:
    """The event that lets one paused call proceed."""
    return {
        "type": USER_TOOL_APPROVAL,
        "thread_id": thread_id,
        "tool_call_id": tool_call_id,
        "approval": {"status": "allow"},
    }


def deny_event(thread_id: str, tool_call_id: str, reason: str) -> dict[str, object]:
    """The event that refuses one paused call.

    The reason is optional in the wire format and always sent here when there is
    one, because the agent is shown it and an agent told only "no" retries the
    same call.
    """
    approval: dict[str, object] = {"status": "deny"}
    if reason.strip():
        approval["reason"] = reason
    return {
        "type": USER_TOOL_APPROVAL,
        "thread_id": thread_id,
        "tool_call_id": tool_call_id,
        "approval": approval,
    }


class Channel(Protocol):
    """Where an answer goes back to the harness.

    One method, and it is the sending one. Reading events is the caller's job:
    a bridge that could fetch as well as send is one that could be given a
    different set of events to read after the decision was made.
    """

    def send(self, event: Mapping[str, object]) -> None: ...


Status = Literal["allowed", "denied", "repeated"]


@dataclass(frozen=True, slots=True)
class Answer:
    """What was decided about one call, and on the strength of what request."""

    tool_call_id: str
    status: Status
    reason: str
    request: Request


@final
class ApprovalBridge:
    """The harness's question, the gate's answer.

    Answers are remembered by ``tool_call_id``. Events are read by polling, so the
    same ``tool.approval_required`` is delivered again every time the client looks
    -- and a bridge that decided afresh each time would ask a human the same
    question repeatedly and send an approval for a call already resolved.
    """

    def __init__(self, gate: Gate, channel: Channel) -> None:
        self._gate = gate
        self._channel = channel
        self._answered: dict[str, Answer] = {}

    @property
    def answered(self) -> Mapping[str, Answer]:
        """Every call this bridge has already decided, by id."""
        return MappingProxyType(dict(self._answered))

    def answer(
        self,
        event: Mapping[str, object],
        events: Iterable[Mapping[str, object]],
    ) -> tuple[Answer, ...]:
        """Decide every call in ``event``, reading ``events`` to find out what they are.

        ``events`` should be the events of the turn that raised the question. It
        is materialised once, so a generator that would be consumed by the first
        call is safe to pass.

        A :class:`Channel` that fails raises through, after the gate has recorded
        what it decided. The answer is not remembered in that case: nothing is
        known to have reached the harness, and the safe reading of an undelivered
        refusal is that it still needs delivering.
        """
        question = read_question(event)
        seen = [item for item in events if isinstance(item, Mapping)]
        return tuple(self._answer_one(question, pending, seen) for pending in question.calls)

    def _answer_one(
        self,
        question: Question,
        pending: PendingCall,
        seen: Sequence[Mapping[str, object]],
    ) -> Answer:
        already = self._answered.get(pending.tool_call_id)
        if already is not None:
            return Answer(
                tool_call_id=pending.tool_call_id,
                status="repeated",
                reason=f"already {already.status}: {already.reason}",
                request=already.request,
            )

        try:
            call = read_call(question, pending, seen)
        except UnreadableCallError as exc:
            problem = str(exc)
            # Refused without asking. Putting an undescribable request in front of
            # an approver is how an approver ends up approving one.
            request = _unreadable_request(question, pending, problem)
            self._gate.refuse(request, problem)
            return self._deny(question, pending, request, problem)

        request = describe(call)
        try:
            self._gate.run(
                request,
                partial(self._channel.send, allow_event(question.thread_id, pending.tool_call_id)),
            )
        except NotApprovedError as exc:
            # Already recorded by the gate; this only has to reach the harness.
            return self._deny(question, pending, request, exc.reason)

        answer = Answer(
            tool_call_id=pending.tool_call_id,
            status="allowed",
            reason="approved",
            request=request,
        )
        self._answered[pending.tool_call_id] = answer
        return answer

    def _deny(
        self,
        question: Question,
        pending: PendingCall,
        request: Request,
        reason: str,
    ) -> Answer:
        self._channel.send(
            deny_event(question.thread_id, pending.tool_call_id, f"{DENIED_BY}{reason}")
        )
        answer = Answer(
            tool_call_id=pending.tool_call_id,
            status="denied",
            reason=reason,
            request=request,
        )
        self._answered[pending.tool_call_id] = answer
        return answer
