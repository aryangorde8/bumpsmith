"""Tests for the approval gate.

The important test in here does not use a spy. It runs a real ``git push`` at a
real repository and then asks that repository what it received, because "the
callable was not invoked" and "the remote did not change" are different claims
and only the second one is the guarantee. No test touches the network: the
remote is a bare repository in a temporary directory.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import cast

import pytest

from bumpsmith.gate import (
    Allow,
    Approver,
    Decision,
    Deny,
    DenyEverything,
    Gate,
    NotApprovedError,
    Record,
    Request,
)


def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return completed.stdout.strip()


def _has_object(repo: Path, sha: str) -> bool:
    """Whether ``repo`` holds the commit itself, not merely a reference to it."""
    completed = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],  # noqa: S607
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return completed.returncode == 0


def _remote_and_clone(tmp_path: Path) -> tuple[Path, Path, str]:
    """A bare remote with one commit already on it, and a clone holding a second.

    Returns ``(remote, work, unpushed_sha)``. The remote starts with references
    on it so that "unchanged" is a claim about real content rather than about an
    empty file staying empty.
    """
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git("init", "--quiet", "--bare", "--initial-branch", "main", ".", cwd=remote)

    work = tmp_path / "work"
    work.mkdir()
    _git("init", "--quiet", "--initial-branch", "main", ".", cwd=work)
    _git("config", "user.email", "gate@example.invalid", cwd=work)
    _git("config", "user.name", "Gate Test", cwd=work)
    _git("remote", "add", "origin", str(remote), cwd=work)

    (work / "README.md").write_text("first\n")
    _git("add", "--all", cwd=work)
    _git("commit", "--quiet", "--message", "first", cwd=work)
    _git("push", "--quiet", "origin", "main", cwd=work)

    (work / "README.md").write_text("second\n")
    _git("add", "--all", cwd=work)
    _git("commit", "--quiet", "--message", "second", cwd=work)
    return remote, work, _git("rev-parse", "HEAD", cwd=work)


class _Yes:
    """Approves whatever it is shown, binding the answer to that request."""

    def decide(self, request: Request) -> Decision:
        return Allow(request.fingerprint(), reason="the test said yes")


class _No:
    def decide(self, request: Request) -> Decision:  # noqa: ARG002
        return Deny(reason="the test said no")


class _Raises:
    def decide(self, request: Request) -> Decision:  # noqa: ARG002
        raise RuntimeError("the approver fell over")


class _AllowsSomethingElse:
    """Answers every request with an approval bound to one other request."""

    def __init__(self, other: Request) -> None:
        self._other = other

    def decide(self, request: Request) -> Decision:  # noqa: ARG002
        return Allow(self._other.fingerprint(), reason="approved, but not for this")


class _NotADecision:
    def decide(self, request: Request) -> str:  # noqa: ARG002
        return "sure, go ahead"


class _Spy:
    """An effect that records having been called."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        return "done"


def _push_request(remote: Path, sha: str) -> Request:
    return Request(
        action="push",
        summary=f"push 1 commit to {remote.name}, which cannot be taken back",
        detail={"remote": str(remote), "branch": "main", "commit": sha},
    )


# ---------------------------------------------------------------------------
# The guarantee, against a real remote
# ---------------------------------------------------------------------------


def test_a_denied_push_leaves_the_remote_exactly_as_it_was(tmp_path: Path) -> None:
    remote, work, unpushed = _remote_and_clone(tmp_path)
    before = _git("ls-remote", str(remote), cwd=work)
    gate = Gate(_No())

    with pytest.raises(NotApprovedError):
        gate.run(
            _push_request(remote, unpushed),
            lambda: _git("push", "--quiet", "origin", "main", cwd=work),
        )

    assert _git("ls-remote", str(remote), cwd=work) == before
    assert not _has_object(remote, unpushed), "the denied commit reached the remote anyway"


def test_an_approved_push_reaches_the_remote(tmp_path: Path) -> None:
    """The mirror of the denial test.

    Without this one, a gate that refused everything unconditionally would pass
    the suite.
    """
    remote, work, unpushed = _remote_and_clone(tmp_path)
    before = _git("ls-remote", str(remote), cwd=work)
    gate = Gate(_Yes())

    gate.run(
        _push_request(remote, unpushed),
        lambda: _git("push", "--quiet", "origin", "main", cwd=work),
    )

    after = _git("ls-remote", str(remote), cwd=work)
    assert after != before
    assert unpushed in after
    assert _has_object(remote, unpushed)


def test_a_gate_with_no_approver_stops_a_real_push(tmp_path: Path) -> None:
    """Missing configuration has to fail closed, not open."""
    remote, work, unpushed = _remote_and_clone(tmp_path)
    before = _git("ls-remote", str(remote), cwd=work)

    with pytest.raises(NotApprovedError):
        Gate(None).run(
            _push_request(remote, unpushed),
            lambda: _git("push", "--quiet", "origin", "main", cwd=work),
        )

    assert _git("ls-remote", str(remote), cwd=work) == before
    assert not _has_object(remote, unpushed)


# ---------------------------------------------------------------------------
# Every way of not being approved
# ---------------------------------------------------------------------------


def test_a_denial_does_not_call_the_effect() -> None:
    spy = _Spy()
    with pytest.raises(NotApprovedError):
        Gate(_No()).run(Request("push", "push to main"), spy)
    assert spy.calls == 0


def test_an_approver_that_raises_is_a_denial() -> None:
    spy = _Spy()
    with pytest.raises(NotApprovedError) as caught:
        Gate(_Raises()).run(Request("push", "push to main"), spy)
    assert spy.calls == 0
    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "the approver failed" in caught.value.reason


def test_an_answer_that_is_not_a_decision_is_a_denial() -> None:
    """An approver from outside this package is not held to the protocol.

    Whatever it returns has to end on the safe side rather than raising from
    inside the gate.
    """
    spy = _Spy()
    approver = cast("Approver", _NotADecision())
    with pytest.raises(NotApprovedError) as caught:
        Gate(approver).run(Request("push", "push to main"), spy)
    assert spy.calls == 0
    assert "not a decision" in caught.value.reason


def test_an_approval_for_another_request_does_not_authorise_this_one() -> None:
    approved = Request("push", "push to a fork nobody watches")
    asked = Request("push", "push to the upstream everybody watches")
    spy = _Spy()

    with pytest.raises(NotApprovedError) as caught:
        Gate(_AllowsSomethingElse(approved)).run(asked, spy)

    assert spy.calls == 0
    assert caught.value.reason == "the approval was made for a different request"


def test_a_deny_with_no_reason_still_says_something() -> None:
    with pytest.raises(NotApprovedError) as caught:
        Gate(_No()).run(Request("push", "push to main"), _Spy())
    assert caught.value.reason
    assert caught.value.request.action == "push"


def test_the_default_approver_names_the_action_it_refused() -> None:
    decision = DenyEverything().decide(Request("open_pull_request", "open a PR upstream"))
    assert isinstance(decision, Deny)
    assert "open_pull_request" in decision.reason


# ---------------------------------------------------------------------------
# Approval, and what an approval is bound to
# ---------------------------------------------------------------------------


def test_an_approved_effect_runs_once_and_its_value_comes_back() -> None:
    spy = _Spy()
    assert Gate(_Yes()).run(Request("push", "push to main"), spy) == "done"
    assert spy.calls == 1


def test_a_failure_after_approval_is_re_raised_unchanged() -> None:
    def explode() -> str:
        raise OSError("the remote hung up")

    gate = Gate(_Yes())
    with pytest.raises(OSError, match="hung up"):
        gate.run(Request("push", "push to main"), explode)

    assert [record.outcome for record in gate.history] == ["failed"]


def test_the_fingerprint_separates_requests_that_differ_in_any_part() -> None:
    base = Request("push", "push to main", {"remote": "origin"})
    same = Request("push", "push to main", {"remote": "origin"})
    assert base.fingerprint() == same.fingerprint()

    assert (
        base.fingerprint() != Request("push", "push to main", {"remote": "upstream"}).fingerprint()
    )
    assert (
        base.fingerprint() != Request("push", "push to a fork", {"remote": "origin"}).fingerprint()
    )
    assert (
        base.fingerprint()
        != Request("force_push", "push to main", {"remote": "origin"}).fingerprint()
    )


def test_the_fingerprint_does_not_depend_on_the_order_detail_was_written_in() -> None:
    one = Request("push", "push", {"remote": "origin", "branch": "main"})
    other = Request("push", "push", {"branch": "main", "remote": "origin"})
    assert one.fingerprint() == other.fingerprint()


def test_detail_cannot_be_changed_after_the_request_is_made() -> None:
    """The approval is bound to the fingerprint, so the detail has to hold still.

    A caller keeping its own reference to the dictionary must not be able to
    reach in after the approval and change what was approved.
    """
    supplied = {"remote": "a-fork-nobody-watches"}
    request = Request("push", "push somewhere harmless", supplied)
    fingerprint = request.fingerprint()

    supplied["remote"] = "the-upstream-everybody-watches"

    assert request.detail["remote"] == "a-fork-nobody-watches"
    assert request.fingerprint() == fingerprint
    with pytest.raises(TypeError):
        request.detail["remote"] = "still no"  # type: ignore[index]


def test_a_request_needs_words_a_person_can_decide_on() -> None:
    with pytest.raises(ValueError, match="action name"):
        Request("   ", "push to main")
    with pytest.raises(ValueError, match="summary"):
        Request("push", "  ")


# ---------------------------------------------------------------------------
# The trail
# ---------------------------------------------------------------------------


def test_the_history_keeps_refusals_next_to_approvals() -> None:
    gate = Gate(_No())
    for _ in range(2):
        with pytest.raises(NotApprovedError):
            gate.run(Request("push", "push to main"), _Spy())

    assert [record.outcome for record in gate.history] == ["denied", "denied"]
    assert all(record.reason for record in gate.history)


def test_the_history_is_a_snapshot_the_caller_cannot_edit() -> None:
    gate = Gate(_Yes())
    gate.run(Request("push", "push to main"), _Spy())
    history = gate.history
    gate.run(Request("push", "push again"), _Spy())
    assert len(history) == 1
    assert len(gate.history) == 2


def test_a_record_survives_being_written_out() -> None:
    record = Record(
        Request("push", "push 1 commit to origin", {"branch": "main"}),
        "denied",
        "the reviewer said no",
    )
    written = json.loads(json.dumps(record.as_dict()))
    assert written == {
        "action": "push",
        "summary": "push 1 commit to origin",
        "detail": {"branch": "main"},
        "outcome": "denied",
        "reason": "the reviewer said no",
    }


def test_every_run_asks_again() -> None:
    """An approval covers one run, not a request that comes back later.

    There is no token to keep, so this is the property that replaces one: the
    same request run twice is two decisions.
    """

    class _Counting:
        def __init__(self) -> None:
            self.asked = 0

        def decide(self, request: Request) -> Decision:
            self.asked += 1
            return Allow(request.fingerprint())

    approver = _Counting()
    gate = Gate(approver)
    request = Request("push", "push to main")

    gate.run(request, _Spy())
    gate.run(request, _Spy())

    assert approver.asked == 2
    assert [record.outcome for record in gate.history] == ["allowed", "allowed"]


def test_a_filename_that_was_never_valid_utf8_can_still_be_fingerprinted() -> None:
    """Real trees hold names that are not valid UTF-8.

    Python hands those back from `os.fsdecode` as surrogates, and a gate that
    raises while describing an action is a gate that cannot guard it.
    """
    undecodable = os.fsdecode(b"models_\xff.py")
    request = Request("push", f"push a change to {undecodable}", {"path": undecodable})

    assert request.fingerprint() == request.fingerprint()
    assert request.fingerprint() != Request("push", "push a change to models.py").fingerprint()
    assert Gate(_Yes()).run(request, _Spy()) == "done"


def test_a_detail_that_is_not_strings_is_refused_where_it_is_written() -> None:
    """A request that cannot be described is stopped at the request.

    The annotation says `str` and nothing at runtime enforces an annotation, so
    the check is real rather than decorative.
    """
    with pytest.raises(TypeError, match="describes itself in strings"):
        Request("push", "push to main", {"commits": 3})  # type: ignore[dict-item]
    with pytest.raises(TypeError, match="keys have to be strings"):
        Request("push", "push to main", {7: "main"})  # type: ignore[dict-item]


def test_a_request_that_cannot_be_described_is_a_recorded_refusal() -> None:
    """The backstop behind that validation, and the reason it is worth having.

    Reached here by assembling a request around its own `__post_init__`. What
    matters is not the exception type but the trail: a refusal that raises
    something else leaves `history` claiming nothing was ever asked.
    """
    request = Request("push", "push to main")
    object.__setattr__(request, "detail", {"commits": object()})
    spy = _Spy()
    gate = Gate(_Yes())

    with pytest.raises(NotApprovedError) as caught:
        gate.run(request, spy)

    assert spy.calls == 0
    assert "could not be described" in caught.value.reason
    assert [record.outcome for record in gate.history] == ["denied"]


def test_refuse_records_a_denial_without_asking_anybody() -> None:
    """A caller that already knows the answer is no still owes the trail a record."""

    class _Counting:
        def __init__(self) -> None:
            self.asked = 0

        def decide(self, request: Request) -> Decision:
            self.asked += 1
            return Allow(request.fingerprint())

    approver = _Counting()
    gate = Gate(approver)
    request = Request(action="push", summary="push to origin")

    error = gate.refuse(request, "the request could not be described")

    assert approver.asked == 0
    assert isinstance(error, NotApprovedError)
    assert error.request is request
    assert [(r.outcome, r.reason) for r in gate.history] == [
        ("denied", "the request could not be described")
    ]


def test_there_is_no_allow_counterpart_to_refuse() -> None:
    """Recording an approval nobody gave would be the bypass this module denies having.

    Written as a test rather than left to the docstring because the tempting
    addition is a one-line method, and the reason not to add it lives here.
    """
    assert not hasattr(Gate, "allow")
    assert not hasattr(Gate, "approve")
