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

    ``tool`` and ``origin`` are what will run: the tool's own name on the server
    it lives on, after any unwrapping. ``called_as`` is the name the model used,
    which is the same string almost always and is not the identity -- see
    :func:`describe`. ``via`` names the wrapper the call arrived through, or is
    empty for one the model made directly; it is kept because "the agent called
    this tool" and "the agent asked the harness to go and find this tool" are
    different stories about the same run.

    ``arguments`` is never rewritten. When the call arrived wrapped, this is still
    the wrapper's argument string -- the text the harness itself parses -- because
    a description that re-encoded it would be showing a human one string while the
    harness acts on another.
    """

    tool_call_id: str
    thread_id: str
    tool: str
    origin: str
    called_as: str
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
    called_as = _string(function, "name", UnreadableCallError, where)

    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        # The wire format defines this as a JSON-encoded *string*. Something else
        # here means the event is not the event this code was written against,
        # and re-encoding it would be inventing the text a human then approves.
        raise UnreadableCallError(
            f"the arguments for {called_as} arrived as {type(arguments).__name__}, "
            "not the JSON string the wire format defines"
        )

    info = hit.get("tool_info")
    if not isinstance(info, Mapping):
        raise UnreadableCallError(
            f"{called_as} came with no tool_info, so what it runs is unstated"
        )
    # The tool's own name where it lives. This, not the model-facing name, is the
    # identity: the harness derives the model-facing one by sanitising this and
    # appending an ordinal on collision, so the same alias can belong to a
    # different tool after a server is added.
    tool = _string(info, "name", UnreadableCallError, f"the tool_info of {where}")
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
        # The model named the inner tool itself, in the arguments, so there is no
        # alias left to record once it is unwrapped.
        via, tool, origin = _unwrap(arguments)
        called_as = tool

    return ToolCall(
        tool_call_id=pending.tool_call_id,
        thread_id=question.thread_id,
        tool=tool,
        origin=origin,
        called_as=called_as,
        arguments=arguments,
        via=via,
    )


def _unwrap(arguments: str) -> tuple[str, str, str]:
    """Read the real tool out of a ``call_tool`` call: ``(via, tool, origin)``.

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
    return WRAPPER_TOOL, inner, f"mcp:{server}"


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

    ``detail`` carries the arguments verbatim, exactly as the model wrote them:
    normalising them would mean the text somebody approved and the text that runs
    are two different strings, which is the whole failure this module exists to
    avoid.

    The fingerprint therefore covers ``tool_call_id`` as well, which makes an
    approval good for one call and not for the identical call next to it. That is
    deliberate -- "run this command" twice is two decisions, and a fingerprint
    that collapsed them would let one yes stand for both.

    ``action`` names the tool as it exists on the server it runs on, unwrapped,
    and not the name the model used. Those differ more often than they look like
    they would: the harness builds the model-facing name by replacing every
    character outside ``[a-zA-Z0-9_-]``, truncating to 64, and **appending an
    ordinal when two servers publish the same name**. So the model-facing name is
    assigned partly by which servers happen to be registered, and a policy keyed
    to it is a policy that can come to mean a different tool after an unrelated
    server is added. The pair that does not move is the tool's own name and the
    server it is on, and that is what ``action`` and ``origin`` carry.
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
        "thread": call.thread_id,
        "tool_call_id": call.tool_call_id,
        "arguments": call.arguments,
    }
    # Both of the following are recorded only when there is something to record.
    # A line that says "not wrapped" or "no alias" on every ordinary call is a
    # line that stops being read, and these two have to be read.
    through = ""
    if call.via:
        detail["via"] = call.via
        through = f", reached through the harness's {call.via}"
    alias = ""
    if call.called_as != call.tool:
        detail["called_as"] = call.called_as
        alias = f", which the model called {call.called_as}"
    return Request(
        action=f"harness.tool_call:{call.tool}",
        summary=(
            f"run {call.tool} from {call.origin} on thread {call.thread_id}"
            f"{alias}{through} ({shown}); the values are in the detail, "
            "not in this line"
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
    """What was decided about one call, and on the strength of what request.

    Carries the thread and the asking event as well as the call id, because a
    call id alone does not identify a question -- see :class:`ApprovalBridge`.
    """

    tool_call_id: str
    thread_id: str
    source_event_id: str
    status: Status
    reason: str
    request: Request


@dataclass(frozen=True, slots=True)
class _Decided:
    """A decision, the event that carries it, and whether that event got out.

    The two are separate on purpose. A decision is made once; delivering it can
    fail and be retried. Collapsing them means a failed send looks like a
    question that was never answered, and the retry asks again -- which is how a
    refusal turns into an approval because a socket closed.
    """

    answer: Answer
    event: Mapping[str, object]
    delivered: bool


@final
class ApprovalBridge:
    """The harness's question, the gate's answer.

    Decisions are remembered, keyed by the thread, the call id **and** the event
    that asked. Events are read by polling, so the same ``tool.approval_required``
    arrives on every look; a bridge that decided afresh each time would ask a
    human the same question repeatedly and send an approval for a call already
    resolved.

    The key is all three parts because a tool call id is issued by the model, not
    by anything that guarantees it. Two different pending calls sharing one id are
    two questions, and answering the second with the first's answer would leave a
    real call paused with nothing in the record to say why. When that happens the
    second is denied rather than decided: the harness addresses a decision by
    thread and call id, so an approval meant for one of them could release the
    other, and only a refusal is safe to send into that ambiguity.
    """

    def __init__(self, gate: Gate, channel: Channel) -> None:
        self._gate = gate
        self._channel = channel
        self._decided: dict[tuple[str, str, str], _Decided] = {}
        self._first_asked: dict[tuple[str, str], str] = {}

    @property
    def answered(self) -> tuple[Answer, ...]:
        """Every decision this bridge has made, in the order it made them.

        A decision appears here as soon as it is made, whether or not the event
        carrying it reached the harness.
        """
        return tuple(decided.answer for decided in self._decided.values())

    def answer(
        self,
        event: Mapping[str, object],
        events: Iterable[Mapping[str, object]],
    ) -> tuple[Answer, ...]:
        """Decide every call in ``event``, reading ``events`` to find out what they are.

        ``events`` should be the events of the turn that raised the question. It
        is materialised once, so a generator that would be consumed by the first
        call is safe to pass.

        A :class:`Channel` that fails raises through. The decision is kept, and
        the next look re-sends *that* decision rather than making a new one.
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
        key = (question.thread_id, pending.tool_call_id, pending.source_event_id)
        already = self._decided.get(key)
        if already is not None:
            if not already.delivered:
                return self._deliver(key, already)
            return Answer(
                tool_call_id=pending.tool_call_id,
                thread_id=question.thread_id,
                source_event_id=pending.source_event_id,
                status="repeated",
                reason=f"already {already.answer.status}: {already.answer.reason}",
                request=already.answer.request,
            )

        asked_by = self._first_asked.get((question.thread_id, pending.tool_call_id))
        if asked_by is not None and asked_by != pending.source_event_id:
            problem = (
                f"{pending.tool_call_id} on thread {question.thread_id} was already "
                f"decided for the message {asked_by}, and this one points at "
                f"{pending.source_event_id}; one id, two questions"
            )
            return self._refuse(key, question, pending, problem)

        try:
            call = read_call(question, pending, seen)
        except UnreadableCallError as exc:
            return self._refuse(key, question, pending, str(exc))

        request = describe(call)
        answer = Answer(
            tool_call_id=pending.tool_call_id,
            thread_id=question.thread_id,
            source_event_id=pending.source_event_id,
            status="allowed",
            reason="approved",
            request=request,
        )
        event = allow_event(question.thread_id, pending.tool_call_id)
        try:
            self._gate.run(request, partial(self._channel.send, event))
        except NotApprovedError as exc:
            # Already recorded by the gate; this only has to reach the harness.
            return self._deny(key, question, pending, request, exc.reason)
        except Exception:
            # Approved, and then the delivery failed. Recording it is what stops
            # the retry from asking again and getting a different answer.
            self._remember(key, answer, event, delivered=False)
            raise
        self._remember(key, answer, event, delivered=True)
        return answer

    def _refuse(
        self,
        key: tuple[str, str, str],
        question: Question,
        pending: PendingCall,
        problem: str,
    ) -> Answer:
        """Deny without asking, for a call nobody could put in front of an approver."""
        request = _unreadable_request(question, pending, problem)
        self._gate.refuse(request, problem)
        return self._deny(key, question, pending, request, problem)

    def _deny(
        self,
        key: tuple[str, str, str],
        question: Question,
        pending: PendingCall,
        request: Request,
        reason: str,
    ) -> Answer:
        answer = Answer(
            tool_call_id=pending.tool_call_id,
            thread_id=question.thread_id,
            source_event_id=pending.source_event_id,
            status="denied",
            reason=reason,
            request=request,
        )
        event = deny_event(question.thread_id, pending.tool_call_id, f"{DENIED_BY}{reason}")
        self._remember(key, answer, event, delivered=False)
        self._channel.send(event)
        self._remember(key, answer, event, delivered=True)
        return answer

    def _deliver(self, key: tuple[str, str, str], decided: _Decided) -> Answer:
        """Send a decision already made. Never asks anybody anything."""
        self._channel.send(decided.event)
        self._remember(key, decided.answer, decided.event, delivered=True)
        return decided.answer

    def _remember(
        self,
        key: tuple[str, str, str],
        answer: Answer,
        event: Mapping[str, object],
        *,
        delivered: bool,
    ) -> None:
        self._decided[key] = _Decided(answer=answer, event=event, delivered=delivered)
        self._first_asked.setdefault((answer.thread_id, answer.tool_call_id), key[2])
