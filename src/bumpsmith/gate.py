"""Stop before the irreversible part.

:mod:`bumpsmith.apply` covers the changes that can be taken back. This module is
for the ones that cannot: a push, a pull request, anything that leaves a mark
somebody else can already see. The rule is not "warn loudly first" but "do not
do it unless a human said to", and the way it is enforced is by owning the call.
An effect handed to :meth:`Gate.run` is a callable the gate holds. A denial is
not an error raised after the fact -- it is a call that never happens.

There is deliberately no bypass. No ``force=True``, no "approve the safe ones
automatically", no environment variable that turns the gate off for a while.
Each of those is a way for the guarantee to be true in the tests and false in
the run that mattered.

The harness has a gate of its own: TrueForge pauses any tool selected by
``@write`` or ``@destructive`` and waits for a ``user.tool_approval`` event.
That selection is resolved from the annotations a tool publishes about itself,
so it stops exactly the tools that admit what they are. This gate sits in the
process that owns the effect, where the question is not what a tool claimed but
what is about to run. The two fail in different directions, which is the reason
to have both rather than to pick one.

What this cannot check
----------------------
The gate compares an approval against the *request*, never against the effect.
Nothing here can tell that a request describing a push to a fork is holding a
callable that pushes upstream; the honesty of that pairing belongs to the caller.
The rule that keeps it honest is to build the request from the same values the
effect will use, inside the operation itself, rather than to describe an action
somewhere above the code that performs it.
"""

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol, TypeVar, final

T = TypeVar("T")


class GateError(Exception):
    """The gate would not run an effect."""


class NotApprovedError(GateError):
    """Nobody approved it, so it did not happen.

    Carries the request rather than only a message, because the caller that has
    to explain the refusal upward usually needs the specifics rather than the
    sentence.
    """

    def __init__(self, request: "Request", reason: str) -> None:
        super().__init__(f"{request.action} was not approved: {reason}")
        self.request = request
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Request:
    """What is about to happen, in the words somebody will decide on.

    ``action`` is the stable name a policy can match on. ``summary`` is the one
    line a human reads before saying yes or no, so it should describe the
    consequence rather than the mechanism. ``detail`` carries the specifics that
    change the answer -- which remote, which branch, how many commits.

    ``detail`` is copied on the way in and exposed read-only. A caller that
    keeps a reference to the dictionary it passed cannot reach in afterwards and
    change what was approved out from under the approval.
    """

    action: str
    summary: str
    detail: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action.strip():
            raise ValueError("an approval request needs an action name")
        if not self.summary.strip():
            raise ValueError("an approval request needs a summary somebody can decide on")
        # Typed loosely on purpose. The annotation above says `str`; nothing at
        # runtime enforces an annotation, and a detail that will not serialise
        # makes `fingerprint` raise. Refusing it here puts the error where the
        # caller still has the context to fix it, and leaves fingerprinting
        # total for every request that exists. A comprehension rather than
        # `dict()` because `dict` is invariant, so the loose annotation is only
        # honoured when the type is inferred against it.
        snapshot: dict[object, object] = {key: value for key, value in self.detail.items()}
        for key, value in snapshot.items():
            if not isinstance(key, str):
                raise TypeError(
                    f"approval detail keys have to be strings; got {type(key).__name__}"
                )
            if not isinstance(value, str):
                raise TypeError(
                    "an approval request describes itself in strings; "
                    f"detail[{key!r}] is {type(value).__name__}"
                )
        object.__setattr__(self, "detail", MappingProxyType(snapshot))

    def fingerprint(self) -> str:
        """A name for exactly this request and no other.

        An :class:`Allow` carries this value, and the gate checks it before
        running anything. That is what stops an approval granted for one action
        from authorising a different one -- including the same action with a
        detail quietly changed in between.

        It binds; it does not authenticate. The value is derived from the
        request and anyone holding the request can compute it, so it proves that
        an approval was about *this* action and nothing more. In-process that is
        the only claim worth making: code able to forge a decision is already
        code able to call the effect directly.

        Every string fingerprints, including one Python built by decoding a
        filename that was never valid UTF-8. Those arrive as surrogates from
        :func:`os.fsdecode`, plain ``utf-8`` refuses them, and a gate that
        cannot name an action cannot guard it.
        """
        canonical = json.dumps(
            {
                "action": self.action,
                "summary": self.summary,
                "detail": dict(sorted(self.detail.items())),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8", "surrogatepass")).hexdigest()


@dataclass(frozen=True, slots=True)
class Allow:
    """Yes -- to the one request whose fingerprint this is."""

    fingerprint: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Deny:
    """No.

    Deliberately asymmetric with :class:`Allow`: a denial carries no
    fingerprint. Binding a decision to a request matters only in the direction
    that lets something happen, and a denial aimed at the wrong request is still
    a denial.
    """

    reason: str = ""


Decision = Allow | Deny


class Approver(Protocol):
    """Something that decides.

    The contract is one-sided on purpose. Returning :class:`Allow` with the
    request's own fingerprint is the only way to let an effect run. Everything
    else has to end as a refusal: returning :class:`Deny`, raising, or waiting
    for an answer that never comes.

    An approver that waits on a human owns its own deadline, because the gate
    cannot interrupt a call that is blocking. A deadline that expires is a
    :class:`Deny`. It is never an :class:`Allow`, and it is never a silent one.
    """

    def decide(self, request: Request) -> Decision: ...


@final
class DenyEverything:
    """The approver you get when there is no approver.

    Exists so that a gate assembled from missing or broken configuration is one
    that stops everything rather than one that stops nothing.
    """

    def decide(self, request: Request) -> Decision:
        return Deny(reason=f"no approver is configured, so {request.action} is not approved")


Outcome = Literal["allowed", "denied", "failed"]


@dataclass(frozen=True, slots=True)
class Record:
    """One decision and what became of it.

    ``failed`` is a separate outcome from ``denied`` because the two say
    opposite things about the gate: a denial is the gate working, and a failure
    after approval is something the gate let through and could not finish.
    """

    request: Request
    outcome: Outcome
    reason: str

    def as_dict(self) -> dict[str, object]:
        """A form that survives :func:`json.dumps`, for the review trail."""
        return {
            "action": self.request.action,
            "summary": self.request.summary,
            "detail": dict(sorted(self.request.detail.items())),
            "outcome": self.outcome,
            "reason": self.reason,
        }


@final
class Gate:
    """Nothing irreversible happens except through here.

    Built with the approver that will answer for it. ``None`` is accepted and
    means :class:`DenyEverything` -- the safe end is the one an accident lands
    on.
    """

    def __init__(self, approver: Approver | None) -> None:
        self._approver: Approver = approver if approver is not None else DenyEverything()
        self._records: list[Record] = []

    @property
    def history(self) -> tuple[Record, ...]:
        """Every decision this gate made, in order.

        Refusals are kept alongside approvals. A gate that recorded only what it
        allowed would describe a system where nothing was ever stopped.
        """
        return tuple(self._records)

    def run(self, request: Request, effect: Callable[[], T]) -> T:
        """Ask about ``request``; call ``effect`` only if the answer was yes.

        Raises :class:`NotApprovedError` without calling ``effect`` if the approver
        refuses, fails, or answers about something else. An exception from
        ``effect`` itself is recorded and re-raised unchanged -- by then the
        thing has been approved, and hiding the failure would be worse than the
        failure.
        """
        # Asked before the approver is, so that a request nobody could describe
        # is refused without bothering anyone. `Request` validates its own
        # detail, which is what makes this total; the guard is a backstop for a
        # request assembled around that validation, and it is here because the
        # alternative is an exception that skips the refusal path and leaves
        # `history` with no record that anything was ever asked.
        try:
            expected = request.fingerprint()
        except Exception as exc:
            raise self._refuse(request, f"the request could not be described: {exc!r}") from exc

        # Typed `object` rather than `Decision`: an approver written elsewhere is
        # not bound by the protocol, and something that is not a decision has to
        # land on the safe side instead of raising from inside the gate.
        try:
            decision: object = self._approver.decide(request)
        except Exception as exc:
            raise self._refuse(request, f"the approver failed: {exc!r}") from exc

        if isinstance(decision, Deny):
            raise self._refuse(request, decision.reason or "denied without a reason")
        if not isinstance(decision, Allow):
            raise self._refuse(
                request,
                f"the approver answered with {type(decision).__name__}, which is not a decision",
            )
        if decision.fingerprint != expected:
            raise self._refuse(request, "the approval was made for a different request")

        try:
            result = effect()
        except Exception as exc:
            self._records.append(Record(request, "failed", f"approved, then failed: {exc!r}"))
            raise
        self._records.append(Record(request, "allowed", decision.reason or "approved"))
        return result

    def _refuse(self, request: Request, reason: str) -> NotApprovedError:
        """Record a refusal and build the exception that carries it.

        Returns rather than raises so that every refusal is a ``raise`` the
        reader can see at the point it happens.
        """
        self._records.append(Record(request, "denied", reason))
        return NotApprovedError(request, reason)
