"""The pull request is proposed, described, and opened only where somebody said.

The tests here divide the way the module does. One half is about *description*:
a proposal has to say where the code is going in terms a person can act on, and
it has to refuse to exist at all when there is nothing to send. The other half
is about *order*: nothing that writes may run before the gate answers, the
answer is bound to one destination, and the commit stages the migration's files
and no others.

The git commands are scripted. What is under test is not whether git works --
`test_run.py` starts real subprocesses for that -- but which commands are
issued, in which order, and which ones never run at all. A real remote would
make the most important assertion in this file impossible to write: that after a
denial, nothing happened anywhere.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from bumpsmith.apply import Edit
from bumpsmith.failures import BreakClass, Failure, RunShape
from bumpsmith.gate import Allow, Decision, Deny, Gate, NotApprovedError, Request
from bumpsmith.migrate import Migration, Step, Stop
from bumpsmith.publish import (
    ACTION,
    DEFAULT_BRANCH,
    GitError,
    NothingToPublishError,
    Opened,
    Proposal,
    body_for,
    open_pull_request,
    propose,
    request_for,
)
from bumpsmith.rewrite import Plan, Skipped
from bumpsmith.rules import Match, Rule, RuleKind, ScanResult, Unreadable
from bumpsmith.run import Completed, NeverRanError

URL = "https://github.com/aryangorde8/emnify-fork.git"
OTHER = "https://github.com/emnify/emnify-python.git"


class _Git:
    """A scripted git and gh that answers by argv, not by substring.

    The defaults describe the ordinary case `propose` is willing to publish: a
    checkout sitting exactly on the base, nothing staged, and only the
    migration's own file modified. Each keyword moves one of those, so a test
    for one refusal reads as one changed default.

    Dispatch is on the whole command. An earlier version matched keywords
    anywhere in the argv, which was fine while there were four commands and
    would have silently answered `rev-parse HEAD` with the reply meant for
    `rev-parse fork/trunk`.
    """

    ORIGINAL = "regex="

    def __init__(
        self,
        *,
        push_urls: Sequence[str] = (URL,),
        head: str = "aaaa1111",
        base_at: str = "aaaa1111",
        branch_exists: bool = False,
        staged: Sequence[str] = (),
        modified: Sequence[str] = ("emnify/models.py",),
        committed: Mapping[str, str] | None = None,
        modes: Mapping[str, str] | None = None,
        pr: Completed | None = None,
    ) -> None:
        self.calls: list[list[str]] = []
        self.push_urls = list(push_urls)
        self.head = head
        self.base_at = base_at
        self.branch_exists = branch_exists
        self.staged = list(staged)
        self.modified = list(modified)
        # `is not None`, not `or`: an empty mapping is a repository where the
        # target is untracked, which is a case this suite has to be able to
        # express. `or` quietly substituted the default for it.
        self.committed = dict(
            {"emnify/models.py": self.ORIGINAL} if committed is None else committed
        )
        self.modes = dict(modes or {})
        self.pr = pr or _ok("https://github.com/aryangorde8/emnify-fork/pull/7\n")

    def run(self, command: Sequence[str], cwd: Path) -> Completed:  # noqa: ARG002
        argv = list(command)
        self.calls.append(argv)
        if argv[0] == "gh":
            return self.pr
        rest = argv[1:]
        if rest[:3] == ["remote", "get-url", "--push"]:
            return _ok("\n".join(self.push_urls))
        if rest == ["rev-parse", "HEAD"]:
            return _ok(self.head)
        if rest[:1] == ["symbolic-ref"]:
            return _ok("refs/remotes/fork/trunk")
        if rest[:3] == ["rev-parse", "--verify", "--quiet"]:
            return _ok("bbbb2222") if self.branch_exists else _fail()
        if rest[:1] == ["rev-parse"]:
            return _ok(self.base_at)
        if rest == ["diff", "--cached", "--name-only"]:
            return _ok("\n".join(self.staged))
        if rest == ["diff", "--name-only"]:
            return _ok("\n".join(self.modified))
        if rest[:1] == ["show"]:
            name = rest[1].removeprefix("HEAD:")
            return _ok(self.committed[name]) if name in self.committed else _fail(128)
        if rest[:2] == ["ls-tree", "HEAD"]:
            name = rest[-1]
            if name not in self.committed:
                return _ok("")
            return _ok(f"{self.modes.get(name, '100644')} blob 0123456789abcdef\t{name}")
        return _ok()

    @property
    def written(self) -> list[list[str]]:
        """Only the calls that could change something."""
        reads = {"remote", "symbolic-ref", "rev-parse", "status", "diff", "show", "ls-tree"}
        return [call for call in self.calls if not reads & set(call[1:2])]


def _ok(output: str = "") -> Completed:
    return Completed(returncode=0, output=output, where="local")


def _fail(code: int = 1, output: str = "") -> Completed:
    return Completed(returncode=code, output=output, where="local")


class _Answering:
    """`git`, but with one command answered differently.

    For the two cases that are about a command *failing* rather than about the
    repository being in some state. A wrapper rather than another keyword on
    `_Git`, so that `_Git`'s constructor stays a description of a repository and
    not a list of things that can go wrong.
    """

    def __init__(self, git: "_Git", prefix: Sequence[str], answer: Completed) -> None:
        self.git = git
        self.prefix = list(prefix)
        self.answer = answer

    def run(self, command: Sequence[str], cwd: Path) -> Completed:
        argv = list(command)
        if argv[1 : 1 + len(self.prefix)] == self.prefix:
            self.git.calls.append(argv)
            return self.answer
        return self.git.run(command, cwd)


def _git_that_resolves(**kwargs: object) -> _Git:
    return _Git(**kwargs)  # type: ignore[arg-type]


def _step(root: Path, *, applied: bool = True, skipped: bool = False) -> Step:
    path = root / "emnify" / "models.py"
    # On disk, because a migration that applied its edits wrote them there, and
    # the publishability check reads the file rather than the plan's idea of it.
    # Only when the root is real: the body-rendering tests pass a notional path
    # and never reach a check that looks at a filesystem.
    if root.is_dir():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("pattern=", encoding="utf-8")
    rule = Rule(
        break_class=BreakClass.REGEX_KEYWORD,
        kind=RuleKind.SOURCE,
        summary="Rename the `regex=` argument to `pattern=`",
        rationale="pydantic v2 renamed it; `regex=` raises at model construction.",
    )
    return Step(
        number=1,
        run=Completed(returncode=2, output="", where="local"),
        failure=Failure(
            shape=RunShape.COLLECTION_ERROR,
            break_class=BreakClass.REGEX_KEYWORD,
            error_type="TypeError",
            message="constr() got an unexpected keyword argument 'regex'",
            culprit=None,
        ),
        rule=rule,
        scan=ScanResult(
            matches=(
                Match(path=path, line=12, excerpt="regex=..."),
                Match(path=root / "emnify" / "other.py", line=3, excerpt="regex=..."),
            ),
            unreadable=(),
        ),
        plan=Plan(
            edits=(Edit(path=path, before="regex=", after="pattern="),),
            skipped=(Skipped(path=root / "emnify" / "other.py", line=3, reason="reads `field`"),)
            if skipped
            else (),
            rewritten=1,
        ),
        applied=applied,
    )


def _migrated(root: Path, **kwargs: object) -> Migration:
    return Migration(steps=(_step(root, **kwargs),), stop=Stop.GREEN, reason="")  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# There has to be something to send
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stop", "applied", "expected"),
    [
        (Stop.NO_RULE, True, "taken back"),
        (Stop.NO_RULE, False, "nothing was ever applied"),
        (Stop.GREEN, False, "passed before anything was changed"),
    ],
)
def test_a_run_with_nothing_on_disk_is_refused_and_says_which_case_it_was(
    tmp_path: Path, stop: Stop, applied: bool, expected: str
) -> None:
    """ "Nothing to open" is four situations and they need four different answers.

    A reverted run and an already-green run are opposite news. Collapsing them
    into one message tells a user their migration failed when it was never
    needed, or that it was never needed when it failed.
    """
    migration = Migration(steps=(_step(tmp_path, applied=applied),), stop=stop, reason="")
    with pytest.raises(NothingToPublishError, match=expected):
        propose(migration, tmp_path, remote="fork", runner=_git_that_resolves())


def test_a_kept_run_that_changed_no_file_is_still_nothing_to_open(tmp_path: Path) -> None:
    """An edit whose before and after are equal is not a change to send."""
    step = _step(tmp_path)
    unchanged = Plan(
        edits=(Edit(path=tmp_path / "a.py", before="same", after="same"),), skipped=(), rewritten=1
    )
    migration = Migration(steps=(replace(step, plan=unchanged),), stop=Stop.GREEN, reason="")
    with pytest.raises(NothingToPublishError, match="none of them changed a file"):
        propose(migration, tmp_path, remote="fork", runner=_git_that_resolves())


def test_only_files_an_applied_step_wrote_are_staged(tmp_path: Path) -> None:
    """A planned edit that never reached the disk is not a file to commit.

    Staging it would either do nothing or, if somebody else had edited that file
    since, commit *their* change under this tool's name.
    """
    migration = Migration(
        steps=(_step(tmp_path, applied=True), _step(tmp_path, applied=False)),
        stop=Stop.GREEN,
        reason="",
    )
    proposal = propose(migration, tmp_path, remote="fork", runner=_git_that_resolves())
    assert proposal.paths == ("emnify/models.py",)


# --------------------------------------------------------------------------
# The destination is named, resolved, and shown
# --------------------------------------------------------------------------


def test_the_proposal_carries_the_resolved_url_not_the_remote_name(tmp_path: Path) -> None:
    """`origin` tells a reviewer nothing about where their code is going."""
    proposal = propose(_migrated(tmp_path), tmp_path, remote="fork", runner=_git_that_resolves())
    assert proposal.url == URL
    assert proposal.remote == "fork"
    assert proposal.branch == DEFAULT_BRANCH


def test_proposing_changes_nothing_anywhere(tmp_path: Path) -> None:
    """Holding a proposal has never pushed anything. Only reads run here."""
    git = _git_that_resolves()
    propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    assert git.written == [], git.written


def test_the_base_branch_is_asked_for_rather_than_assumed(tmp_path: Path) -> None:
    """`main` is a guess that is wrong on most repositories old enough to need this."""
    proposal = propose(_migrated(tmp_path), tmp_path, remote="fork", runner=_git_that_resolves())
    assert proposal.base == "trunk"


def test_an_unresolvable_base_is_an_error_not_a_guess(tmp_path: Path) -> None:
    git = _Answering(_Git(), ["symbolic-ref"], _ok(""))
    with pytest.raises(GitError, match="could not tell which branch"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_a_remote_that_does_not_exist_is_an_error(tmp_path: Path) -> None:
    git = _Answering(_Git(), ["remote", "get-url"], _fail(2, "No such remote"))
    with pytest.raises(GitError, match="No such remote"):
        propose(_migrated(tmp_path), tmp_path, remote="typo", runner=git)


def test_a_git_that_never_ran_is_not_a_git_that_succeeded(tmp_path: Path) -> None:
    """The failure this exists to prevent: an unresolved remote read as an empty URL.

    `Runner` raises rather than returning a status when a command did not run.
    Swallowing that here would resolve the destination to "" and then show a
    person an empty string as the place their code is going.
    """

    class _NoGit:
        def run(self, command: Sequence[str], cwd: Path) -> Completed:  # noqa: ARG002
            raise NeverRanError("git: command not found")

    with pytest.raises(GitError, match="did not run"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=_NoGit())


# --------------------------------------------------------------------------
# Nothing runs before the gate answers
# --------------------------------------------------------------------------


def _proposal(tmp_path: Path) -> Proposal:
    return propose(_migrated(tmp_path), tmp_path, remote="fork", runner=_git_that_resolves())


class _Says:
    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        self.asked: list[Request] = []

    def decide(self, request: Request) -> Decision:
        self.asked.append(request)
        return self.decision


def test_a_denial_leaves_the_repository_untouched(tmp_path: Path) -> None:
    """The assertion a real remote would make impossible to write."""
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    gate = Gate(_Says(Deny(reason="not this one")))

    with pytest.raises(NotApprovedError):
        open_pull_request(gate, proposal, git)

    assert git.calls == []


def test_no_approver_at_all_still_denies(tmp_path: Path) -> None:
    """`Gate(None)` is `DenyEverything`; the safe end is where an accident lands."""
    git = _git_that_resolves()
    with pytest.raises(NotApprovedError):
        open_pull_request(Gate(None), _proposal(tmp_path), git)
    assert git.calls == []


def test_the_request_shows_the_url_and_leads_with_the_push(tmp_path: Path) -> None:
    """A pull request can be closed. A branch on somebody's remote is already there."""
    request = request_for(_proposal(tmp_path))
    assert request.action == ACTION
    assert request.summary.startswith("push ")
    assert URL in request.summary
    assert request.detail["url"] == URL
    assert request.detail["files"] == "emnify/models.py"


def test_an_approval_for_one_destination_does_not_open_against_another(tmp_path: Path) -> None:
    """The binding, end to end, on the fact that matters most.

    The gate has always bound an approval to a request's fingerprint. This
    asserts the thing that makes that binding worth having here: the resolved
    URL is *inside* the fingerprint, so an approval granted for a fork cannot be
    replayed against the upstream repository it was cloned from.
    """
    approved = _proposal(tmp_path)
    elsewhere = replace(approved, url=OTHER)
    gate = Gate(_Says(Allow(fingerprint=request_for(approved).fingerprint())))
    git = _git_that_resolves()

    with pytest.raises(NotApprovedError, match="different request"):
        open_pull_request(gate, elsewhere, git)

    assert git.calls == []


# --------------------------------------------------------------------------
# What it does once it may
# --------------------------------------------------------------------------


def _allowed(proposal: Proposal) -> Gate:
    return Gate(_Says(Allow(fingerprint=request_for(proposal).fingerprint())))


def test_the_commit_stages_the_migrations_files_and_nothing_else(tmp_path: Path) -> None:
    """Never `-A`, never `-a`, never a glob.

    The repository being migrated is a working directory somebody else may have
    been working in. A pathspec that *can* match more than the migration wrote
    is one that eventually will, and their uncommitted work would go out in a
    pull request under this tool's name.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)

    add = next(call for call in git.calls if call[:2] == ["git", "add"])
    assert add == ["git", "add", "--", "emnify/models.py"]
    for call in git.calls:
        assert "-A" not in call and "--all" not in call, call
        assert call[:3] != ["git", "commit", "-a"], call


def test_the_push_happens_before_the_pull_request_is_asked_for(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)

    # The writes, in order. Reads are excluded deliberately: `_do_open` asks the
    # publishability questions again before it touches anything, so the sequence
    # of *reads* is not what this test is about -- the sequence of changes is.
    order = [call[0] if call[0] == "gh" else call[1] for call in git.written]
    assert order == ["checkout", "add", "commit", "push", "gh"]


def test_the_pull_requests_url_is_reported(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    opened = open_pull_request(_allowed(proposal), proposal, _git_that_resolves())
    assert opened == Opened(
        branch=DEFAULT_BRANCH,
        pushed_to=URL,
        url="https://github.com/aryangorde8/emnify-fork/pull/7",
    )


def test_a_warning_printed_by_gh_is_not_reported_as_the_pull_request(tmp_path: Path) -> None:
    """`gh` prints warnings too, and the last line is not always the address."""
    proposal = _proposal(tmp_path)
    git = _Git(pr=_ok("https://github.com/x/y/pull/3\nWarning: 1 uncommitted change\n"))
    opened = open_pull_request(_allowed(proposal), proposal, git)
    assert opened.url == "https://github.com/x/y/pull/3"


def test_a_push_that_worked_and_a_pull_request_that_did_not_says_both(tmp_path: Path) -> None:
    """The push already happened. Raising would describe a state the repo is not in.

    `gh` may be missing, unauthenticated, or refused by the remote. The branch
    is out there regardless, and a caller told only "it failed" would not know
    that -- or where to go and finish the job by hand.
    """
    proposal = _proposal(tmp_path)
    git = _Git(pr=_fail(4, "gh: not authenticated"))
    opened = open_pull_request(_allowed(proposal), proposal, git)

    assert opened.url == ""
    assert opened.pushed_to == URL
    assert "the branch is pushed" in opened.note
    assert URL in opened.note
    assert ["git", "push", URL, f"HEAD:refs/heads/{DEFAULT_BRANCH}"] in git.calls


def test_the_gate_records_what_it_allowed(tmp_path: Path) -> None:
    """A pull request opened with no record of the approval is an unreviewed one."""
    proposal = _proposal(tmp_path)
    gate = _allowed(proposal)
    open_pull_request(gate, proposal, _git_that_resolves())

    assert [record.outcome for record in gate.history] == ["allowed"]
    assert gate.history[0].request.detail["url"] == URL


# --------------------------------------------------------------------------
# What the reviewer reads
# --------------------------------------------------------------------------


def test_the_body_carries_the_argument_for_each_rule(tmp_path: Path) -> None:
    """A reviewer is being asked to accept a change from a tool they did not write."""
    body = body_for(_migrated(tmp_path))
    assert "Rename the `regex=` argument to `pattern=`" in body
    assert "pydantic v2 renamed it" in body
    assert "constr() got an unexpected keyword argument 'regex'" in body


def test_the_body_states_the_gap_between_one_failure_and_every_site(tmp_path: Path) -> None:
    """The reason this project emits a rule rather than a patch."""
    body = body_for(_migrated(tmp_path))
    assert "The failure named one site" in body
    assert "2 sites across 2 files" in body


def test_the_body_says_when_the_migration_is_not_complete(tmp_path: Path) -> None:
    body = body_for(_migrated(tmp_path, skipped=True))
    assert "not complete" in body
    assert "reads `field`" in body


def test_an_unreadable_file_is_named_in_the_body_too(tmp_path: Path) -> None:
    step = _step(tmp_path)
    scan = ScanResult(
        matches=step.scan.matches if step.scan else (),
        unreadable=(Unreadable(path=tmp_path / "vendor.py", reason="invalid syntax"),),
    )
    migration = Migration(steps=(replace(step, scan=scan),), stop=Stop.GREEN, reason="")
    body = body_for(migration)
    assert "vendor.py" in body
    assert "invalid syntax" in body


def test_the_body_never_claims_the_suite_was_not_run(tmp_path: Path) -> None:
    """The one sentence that would be a lie if the loop's guarantee were wrong."""
    body = body_for(_migrated(tmp_path))
    assert "verified by a run of your own test suite" in body


def test_no_gap_is_stated_when_the_rule_matched_only_what_failed() -> None:
    """ "1 site across 1 file" spends a reviewer's attention and returns nothing.

    Found by reading the body of a pull request this actually opened, which is
    also how the HTML report's version of this was found. The same rule applies
    in both places for the same reason.
    """
    root = Path("/repo")
    step = _step(root)
    one = replace(
        step,
        scan=ScanResult(
            matches=(Match(path=root / "a.py", line=1, excerpt="regex="),), unreadable=()
        ),
    )
    body = body_for(Migration(steps=(one,), stop=Stop.GREEN, reason=""))
    assert "The failure named one site" not in body
    assert "1 site rewritten." in body


def test_the_body_counts_in_sentences_a_person_would_write() -> None:
    """`of which 1 were rewritten` shipped to a real remote before this existed."""
    body = body_for(_migrated(Path("/repo")))
    assert "1 was rewritten" in body
    assert "1 were rewritten" not in body


# --------------------------------------------------------------------------
# Where the push actually goes
# --------------------------------------------------------------------------


def test_the_destination_is_the_push_url_not_the_fetch_url(tmp_path: Path) -> None:
    """`git remote get-url` answers about fetching, and the push may go elsewhere.

    A remote carrying a `pushurl` sends the branch somewhere the fetch URL never
    named. Showing the fetch URL in the approval would be showing a destination
    the push was never going to use -- reached through the one git command that
    looks like it answers the question.
    """
    git = _git_that_resolves()
    propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    assert ["git", "remote", "get-url", "--push", "--all", "fork"] in git.calls
    assert ["git", "remote", "get-url", "fork"] not in git.calls


def test_a_remote_that_pushes_to_several_places_is_refused(tmp_path: Path) -> None:
    """One approval cannot mean three destinations."""
    git = _Git(push_urls=(URL, OTHER))
    with pytest.raises(GitError, match="pushes to 2 places"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_the_push_names_the_url_and_not_the_remote(tmp_path: Path) -> None:
    """A name is an indirection `git remote set-url` can re-point after approval.

    The fingerprint binds the URL, so pushing by name would leave the approved
    destination and the actual one connected by nothing but the assumption that
    the remote had not moved.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)

    push = next(call for call in git.calls if call[:2] == ["git", "push"])
    assert push == ["git", "push", URL, f"HEAD:refs/heads/{DEFAULT_BRANCH}"]
    assert "fork" not in push


def test_the_pull_request_names_the_repository_the_branch_went_to(tmp_path: Path) -> None:
    """Left to itself, `gh` picks a repository from the checkout's own remotes.

    Which, for a migration, is the repository this was cloned from -- somebody
    else's -- and not the fork that was just approved.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)

    gh = next(call for call in git.calls if call[0] == "gh")
    assert gh[:5] == ["gh", "pr", "create", "--repo", "aryangorde8/emnify-fork"]


def test_a_remote_that_is_not_github_gets_a_push_and_no_gh_at_all(tmp_path: Path) -> None:
    """A bare repository is a fine place to push and not a place pull requests exist.

    Running `gh` and reporting its failure would describe something going wrong.
    Nothing went wrong; there is simply nowhere to open one.
    """
    git = _Git(push_urls=("/srv/git/emnify.git",))
    proposal = propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    opened = open_pull_request(_allowed(proposal), proposal, git)

    assert not [call for call in git.calls if call[0] == "gh"]
    assert opened.url == ""
    assert "not a GitHub repository" in opened.note
    assert ["git", "push", "/srv/git/emnify.git", f"HEAD:refs/heads/{DEFAULT_BRANCH}"] in git.calls


# --------------------------------------------------------------------------
# Nothing but the migration goes out
# --------------------------------------------------------------------------


def test_a_checkout_ahead_of_the_base_is_refused(tmp_path: Path) -> None:
    """A pull request is a diff against the base, not a commit.

    Restricting what the commit touches never addressed this -- and the
    deciding argument is not about the other commits at all: the suite went
    green against HEAD, so a pull request against a different base is a
    different change from the one that was tested.
    """
    git = _Git(head="cccc3333", base_at="aaaa1111")
    with pytest.raises(NothingToPublishError, match=r"not at fork/trunk"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_a_branch_that_already_exists_is_refused(tmp_path: Path) -> None:
    """`-B` would reset it, and the default name is reused across runs by design."""
    git = _Git(branch_exists=True)
    with pytest.raises(NothingToPublishError, match="already exists"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_the_branch_is_created_not_reset(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)
    assert ["git", "checkout", "-b", DEFAULT_BRANCH] in git.calls
    assert not [call for call in git.calls if "-B" in call]


def test_anything_already_staged_is_refused(tmp_path: Path) -> None:
    """`git commit` commits the index, whatever pathspec added ours to it."""
    git = _Git(staged=("docs/notes.md",))
    with pytest.raises(NothingToPublishError, match="already something staged"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_an_unrelated_modified_file_is_refused(tmp_path: Path) -> None:
    git = _Git(modified=("emnify/models.py", "emnify/unrelated.py"))
    with pytest.raises(NothingToPublishError, match=r"emnify/unrelated\.py"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_a_file_that_was_already_edited_before_the_migration_is_refused(tmp_path: Path) -> None:
    """`git add -- path` stages that file's whole current contents.

    Which is the migration's edit *plus* whatever was uncommitted in it
    already. Staging the right path does not make the right change.
    """
    git = _Git(committed={"emnify/models.py": "somebody was halfway through this"})
    with pytest.raises(NothingToPublishError, match="already differed from the last commit"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)


def test_the_commit_is_only_the_migrations_paths(tmp_path: Path) -> None:
    """`--only`, so what is committed is the pathspec rather than the index."""
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    open_pull_request(_allowed(proposal), proposal, git)

    commit = next(call for call in git.calls if call[:2] == ["git", "commit"])
    assert commit[2] == "--only"
    assert commit[-2:] == ["--", "emnify/models.py"]


# --------------------------------------------------------------------------
# 124-127 -- what the follow-up review found, and what now catches it
# --------------------------------------------------------------------------


def test_a_target_git_has_never_seen_is_refused(tmp_path: Path) -> None:
    """Finding 124.

    The scan walks Python files, not *tracked* Python files, so a migration
    reaches an untracked one -- and `git add` on it stages the whole body. The
    old check read `git show HEAD:path`, got nothing, and treated the absence of
    a committed version as the absence of anything to check.
    """
    git = _git_that_resolves(committed={})
    with pytest.raises(NothingToPublishError, match="never seen it"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    assert git.written == [], git.written


def test_a_trailing_newline_change_is_not_called_no_change(tmp_path: Path) -> None:
    """Finding 125.

    The comparison stripped trailing newlines from both sides, so a newline a
    user added or removed before the run was "unchanged" and went out with the
    migration. Contents are a format whose whitespace is the content -- the same
    lesson as finding 91, one function along.
    """
    git = _git_that_resolves(committed={"emnify/models.py": _Git.ORIGINAL + "\n"})
    with pytest.raises(NothingToPublishError, match="already differed"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    assert git.written == [], git.written


def test_a_mode_change_is_refused_even_when_the_text_matches(tmp_path: Path) -> None:
    """Finding 126.

    The check compared blob text and never the mode, so a pre-existing
    executable bit rode out with the migration -- from a rewriter that goes out
    of its way to preserve permissions rather than set them.
    """
    git = _git_that_resolves(modes={"emnify/models.py": "100755"})
    with pytest.raises(NothingToPublishError, match="non-executable"):
        propose(_migrated(tmp_path), tmp_path, remote="fork", runner=git)
    assert git.written == [], git.written


def test_a_target_removed_after_the_run_is_refused(tmp_path: Path) -> None:
    """The migration wrote it, so its absence is somebody else's doing."""
    migration = _migrated(tmp_path)
    (tmp_path / "emnify" / "models.py").unlink()
    git = _git_that_resolves()
    with pytest.raises(NothingToPublishError, match="not there any more"):
        propose(migration, tmp_path, remote="fork", runner=git)
    assert git.written == [], git.written


class _SaysAndDoes:
    """Approves, and runs `action` on the way out -- the approval window."""

    def __init__(self, decision: Decision, action: "Callable[[], object]") -> None:
        self.decision = decision
        self.action = action

    def decide(self, request: Request) -> Decision:  # noqa: ARG002
        self.action()
        return self.decision


class _SaysAndMovesTheTree:
    """Approves, and changes the repository on the way out.

    This is the only way to exercise the window: the checks run, a human is
    asked, and the world moves while they are deciding. Nothing else in the
    suite holds the prompt open.
    """

    def __init__(self, decision: Decision, git: "_Git", committed: str) -> None:
        self.decision = decision
        self.git = git
        self.committed = committed

    def decide(self, request: Request) -> Decision:  # noqa: ARG002
        self.git.committed["emnify/models.py"] = self.committed
        return self.decision


def test_the_tree_moving_while_a_human_decides_is_refused(tmp_path: Path) -> None:
    """Finding 127, and the reason this module runs its checks twice.

    `propose` validated HEAD, the index and every target, and then the program
    blocked on somebody typing `yes`. Nothing revalidated afterwards, so every
    guarantee the gate offered was about a repository that had since had the
    longest interval in the program to change.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    gate = Gate(
        _SaysAndMovesTheTree(
            Allow(fingerprint=request_for(proposal).fingerprint()),
            git,
            "somebody else's work",
        )
    )

    with pytest.raises(NothingToPublishError, match="already differed"):
        open_pull_request(gate, proposal, git)
    # The point is not the exception. It is that the approval was granted and
    # still nothing was branched, staged, committed or pushed.
    assert git.written == [], git.written


def test_an_unmoved_tree_still_publishes_after_the_approval(tmp_path: Path) -> None:
    """The no-op control for the test above.

    Revalidation that refused everything would pass that test just as well.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    opened = open_pull_request(_allowed(proposal), proposal, git)
    assert opened.branch == proposal.branch
    written = [call[1] for call in git.written if call[0] == "git"]
    assert written == ["checkout", "add", "commit", "push"], written


def test_the_proposals_paths_come_from_its_targets(tmp_path: Path) -> None:
    """Derived, not stored beside them: two copies is two chances to disagree."""
    proposal = _proposal(tmp_path)
    assert proposal.paths == tuple(target[0] for target in proposal.targets)
    assert proposal.paths == ("emnify/models.py",)


def test_a_target_edited_while_a_human_decides_is_refused(tmp_path: Path) -> None:
    """Finding 129, and the half of the window the first fix left open.

    Revalidating against `before` answers "is somebody else's work in the way".
    It does not answer "is ours still there" -- HEAD is unchanged either way, so
    a target edited while the prompt waits passes every question that was being
    asked and is then staged as this migration's output.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    target = tmp_path / "emnify" / "models.py"
    gate = Gate(
        _SaysAndDoes(
            Allow(fingerprint=request_for(proposal).fingerprint()),
            lambda: target.write_text("somebody else typed this", encoding="utf-8"),
        )
    )

    with pytest.raises(NothingToPublishError, match="no longer holds"):
        open_pull_request(gate, proposal, git)
    assert git.written == [], git.written


def test_a_target_replaced_by_a_symlink_is_refused(tmp_path: Path) -> None:
    """`is_file()` follows the link and answers about a different file."""
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    target = tmp_path / "emnify" / "models.py"
    decoy = tmp_path / "decoy.py"
    decoy.write_text("pattern=", encoding="utf-8")

    def _swap() -> None:
        target.unlink()
        target.symlink_to(decoy)

    gate = Gate(_SaysAndDoes(Allow(fingerprint=request_for(proposal).fingerprint()), _swap))
    with pytest.raises(NothingToPublishError, match="symlink"):
        open_pull_request(gate, proposal, git)
    assert git.written == [], git.written


def test_a_target_that_cannot_be_read_back_is_refused_not_raised(tmp_path: Path) -> None:
    """Finding 130.

    `OSError` and `UnicodeError` are not `PublishError`, and the CLI catches
    only the latter -- so a target made unreadable, or rewritten with bytes that
    are not its encoding, left this module past the one handler meant for it.
    Shape 1 in this project's own list, for the fifth time, in a check added two
    commits earlier to close a different hole.
    """
    proposal = _proposal(tmp_path)
    git = _git_that_resolves()
    target = tmp_path / "emnify" / "models.py"
    gate = Gate(
        _SaysAndDoes(
            Allow(fingerprint=request_for(proposal).fingerprint()),
            lambda: target.write_bytes(b"\xff\xfe not utf-8 at all"),
        )
    )

    with pytest.raises(NothingToPublishError, match="cannot be read back"):
        open_pull_request(gate, proposal, git)
    assert git.written == [], git.written
