"""Propose the migration as a pull request, and open it only if a human says yes.

This is the noun in the project's own description of itself -- *turns a failing
pydantic v1→v2 migration into a reviewed pull request* -- and until now the tool
did not have it. What it had was the refusal: :mod:`bumpsmith.gate` proves that
``open_pull_request`` is denied, and :mod:`bumpsmith.harness` proves the denial
travels back through a live harness with the tool never called. That is a real
guarantee and it is the wrong half to have alone. A gate with nothing behind it
guards a door into an empty room.

The dangerous part is not opening a pull request
------------------------------------------------
It is opening one *somewhere nobody chose*. A migration runs against a clone of
somebody else's repository, so its ``origin`` is **their** repository. Every
convenience this module could offer -- default to ``origin``, infer the base
branch, push and see what happens -- points the irreversible action at the one
destination it must never reach. That is not a hypothetical: it is the ordinary
result of writing the obvious code.

So the destination is never inferred:

* the remote is **named by the caller**, and there is no default;
* the name is **resolved to a URL** before anybody is asked, and the URL is what
  the approval request shows -- ``origin`` tells a reviewer nothing, and
  ``https://github.com/someone-else/their-project`` tells them everything;
* the URL is part of the request's fingerprint, so an approval granted for one
  destination cannot open a pull request against another. That binding already
  existed in :class:`~bumpsmith.gate.Gate`; this module's job is to put the fact
  that matters *inside* the thing being bound.

Only a run whose edits survived
-------------------------------
:func:`propose` refuses anything but :attr:`~bumpsmith.migrate.Outcome.MIGRATED`.
A reverted run has nothing on disk -- that is what reverted means -- and a
proposal built from one would offer a branch of no changes. An untouched or
already-green run has nothing to offer either. The refusal names which of them
it was, because "there is nothing to open" is a different message from "the
suite never went green".

Only the files the migration wrote
----------------------------------
The commit stages the migration's own paths, explicitly, one by one. Never
``git add -A`` and never ``git commit -a``. A development checkout accumulates --
this repository has a review log with two findings in it about exactly that --
and a repository being migrated is a working directory somebody else may have
been working in. Sweeping the tree would put their uncommitted work in a pull
request under this tool's name, and it would look like the tool's own change.

What runs before the gate, and what runs after
----------------------------------------------
Before: reads only. ``git remote get-url``, ``git rev-parse``, ``git status``.
Nothing that writes, nothing that leaves the machine.

After: the branch, the commit, the push, the pull request -- in that order, each
through :class:`~bumpsmith.run.Runner`, which will not turn a command that never
ran into a command that succeeded. The push is the irreversible one and it is
what the summary leads with, because a pull request can be closed and a branch
on somebody's remote is already there.
"""

from dataclasses import dataclass
from pathlib import Path

from bumpsmith.gate import Gate, Request
from bumpsmith.migrate import Migration, Outcome
from bumpsmith.run import Completed, RunError, Runner

DEFAULT_BRANCH = "bumpsmith/pydantic-v2"
"""Deterministic on purpose.

A name with a timestamp in it makes every re-run a new branch and a new pull
request, which is how a migration tool becomes a way to produce forty pull
requests. Re-running with the same name pushes to the same branch, and the
remote decides whether that is a fast-forward -- which is the right place for
that decision.
"""

ACTION = "open_pull_request"
"""The action name the gate and the harness already know.

Chosen to match `proofs/deny.py` and the MCP stub it drives, so the thing that
was proven refusable is the thing this opens. A different name here would mean
the proof and the feature were about two different actions.
"""


class PublishError(Exception):
    """Something stopped a pull request being proposed or opened."""


class NothingToPublishError(PublishError):
    """The run left nothing a pull request could carry."""


class GitError(PublishError):
    """A git command ran and said no."""


@dataclass(frozen=True, slots=True)
class Proposal:
    """A pull request that has not been opened, described well enough to decide on.

    Every field is filled in before anybody is asked, and :attr:`url` is the
    resolved destination rather than the remote's name. A proposal is inert:
    holding one has never changed anything anywhere.
    """

    root: Path
    remote: str
    url: str
    branch: str
    base: str
    title: str
    body: str
    paths: tuple[str, ...]
    """Repository-relative, sorted. Exactly what the migration wrote, and the
    only thing the commit will stage."""


@dataclass(frozen=True, slots=True)
class Opened:
    """What actually happened, including when only part of it did."""

    branch: str
    pushed_to: str
    url: str = ""
    """The pull request's URL. Empty when the branch was pushed and no pull
    request could be opened -- which is a real outcome and not a failure to
    round up, because the push already happened."""

    note: str = ""
    """Why :attr:`url` is empty, when it is."""


def _git(runner: Runner, root: Path, *args: str) -> str:
    """One git command, or an exception. Never a shell.

    :class:`~bumpsmith.run.Runner` is reused rather than a second command seam
    invented, and the reuse is the point: it refuses to turn a command that
    never ran into a command that returned zero. A missing ``git`` binary that
    parsed as success here would resolve a remote to the empty string and put
    that in front of somebody as the place their code is going.
    """
    try:
        result: Completed = runner.run(["git", *args], root)
    except RunError as exc:
        raise GitError(f"`git {' '.join(args)}` did not run: {exc}") from exc
    if result.returncode != 0:
        raise GitError(
            f"`git {' '.join(args)}` exited {result.returncode}: {result.output.strip()}"
        )
    return result.output.strip()


def body_for(migration: Migration) -> str:
    """The pull request body: the rules, their reach, and what was skipped.

    Markdown rather than the HTML page, because this is read in a review
    interface that renders markdown and not in a browser. Same source as both
    other renderings -- the migration itself -- so a fourth description of one
    run is not being invented here.

    The rationale is included in full. A reviewer is being asked to accept a
    change to their own code from a tool they did not write, and the argument
    for each rule is the thing that makes that answerable.
    """
    lines = [
        "Opened by [bumpsmith](https://github.com/aryangorde8/bumpsmith), "
        "a pydantic v1→v2 migration agent.",
        "",
        "**The suite passes with these edits and did not before.** Every edit below was "
        "applied, verified by a run of your own test suite, and kept only because that "
        "run came back green.",
        "",
    ]
    for step in migration.steps:
        if step.rule is None or not step.applied:
            continue
        lines.append(f"### {step.rule.summary}")
        lines.append("")
        if step.failure is not None and step.failure.message:
            lines.append(f"Your suite failed with: `{step.failure.message}`")
            lines.append("")
        if step.scan is not None and step.plan is not None:
            written = step.plan.rewritten
            # Only when there is a gap. A rule matching exactly the one site the
            # failure named has no ratio to point at, and "the failure named one
            # site; the rule matches 1 site across 1 file" is a sentence that
            # takes a reviewer's attention and gives nothing back. Same rule the
            # HTML report applies to its bar, for the same reason.
            if step.scan.count > 1:
                reach = _count(step.scan.count, "site")
                files = _count(len({match.path for match in step.scan.matches}), "file")
                lines.append(
                    f"The failure named one site. The rule matches **{reach} across {files}**, "
                    f"of which {written} {'was' if written == 1 else 'were'} rewritten."
                )
            else:
                lines.append(f"{_count(written, 'site')} rewritten.")
            lines.append("")
        lines.append(step.rule.rationale)
        lines.append("")
        skipped = () if step.plan is None else step.plan.skipped
        if skipped:
            lines.append("Matched and deliberately left alone:")
            lines.extend(f"- {item}" for item in skipped)
            lines.append("")
        unreadable = () if step.scan is None else step.scan.unreadable
        if unreadable:
            lines.append("Could not be read, so not considered:")
            lines.extend(f"- `{item.path}` — {item.reason}" for item in unreadable)
            lines.append("")

    if not migration.complete:
        lines.append(
            "> **This migration is not complete.** At least one site the rules matched was "
            "skipped or could not be read, and is listed above. Some v1 code remains."
        )
        lines.append("")
    lines.append(
        "Every edit is a text replacement at a position the parser reported, never a "
        "reformatting of your file. Nothing else in the tree was touched."
    )
    return "\n".join(lines)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _title_for(migration: Migration) -> str:
    rules = [
        step.rule.summary for step in migration.steps if step.rule is not None and step.applied
    ]
    if len(rules) == 1:
        return f"pydantic v2: {rules[0][0].lower()}{rules[0][1:]}"
    return f"pydantic v2: {_count(len(rules), 'migration rule')} applied, suite green"


def _paths_of(migration: Migration, root: Path) -> tuple[str, ...]:
    """Every file the migration wrote, repository-relative and sorted.

    Taken from the plans of steps that were *applied*. A planned edit that never
    reached the disk is not a file to stage, and staging it would either do
    nothing or -- worse, if somebody else had since edited it -- commit their
    change as this tool's.
    """
    paths: set[str] = set()
    for step in migration.steps:
        if not step.applied or step.plan is None:
            continue
        for edit in step.plan.edits:
            if not edit.changes_anything:
                continue
            try:
                paths.add(edit.path.resolve().relative_to(root.resolve()).as_posix())
            except ValueError as exc:  # pragma: no cover - a plan outside its own root
                raise PublishError(
                    f"{edit.path} is outside {root}; refusing to stage a file the "
                    "migration should never have been able to write"
                ) from exc
    return tuple(sorted(paths))


def propose(
    migration: Migration,
    root: Path,
    *,
    remote: str,
    runner: Runner,
    branch: str = DEFAULT_BRANCH,
    base: str = "",
) -> Proposal:
    """Describe the pull request this run would open. Changes nothing.

    Args:
        migration: the finished run. Must have kept its edits.
        root: the repository those edits are in.
        remote: the git remote to push to, **by name, with no default**. It is
            resolved to a URL here so the approval can show where the code is
            actually going.
        runner: how git commands are run. Only reads are run from this function.
        branch: the branch to push. Deterministic by default; see
            :data:`DEFAULT_BRANCH`.
        base: the branch to open against. Resolved from the remote's HEAD when
            empty, and a failure to resolve it is an error rather than a guess
            at ``main``.

    Raises:
        NothingToPublishError: the run kept no edits, and says which case it was.
        GitError: a git command failed, including a remote that does not exist.
    """
    if migration.outcome is not Outcome.MIGRATED:
        raise NothingToPublishError(_why_nothing(migration.outcome))
    paths = _paths_of(migration, root)
    if not paths:
        raise NothingToPublishError(
            "the run reports edits were kept, but none of them changed a file. "
            "There is nothing to put in a pull request."
        )

    url = _git(runner, root, "remote", "get-url", remote)
    if not url:
        raise GitError(f"the remote {remote!r} resolved to an empty URL")
    if not base:
        base = _default_base(runner, root, remote)

    return Proposal(
        root=root,
        remote=remote,
        url=url,
        branch=branch,
        base=base,
        title=_title_for(migration),
        body=body_for(migration),
        paths=paths,
    )


def _why_nothing(outcome: Outcome) -> str:
    """Name the case. "Nothing to open" is four different situations."""
    return {
        Outcome.REVERTED: (
            "the edits did not make the suite pass and were taken back, so the tree "
            "holds nothing to open a pull request with"
        ),
        Outcome.UNTOUCHED: "nothing was ever applied, so there is nothing to open",
        Outcome.ALREADY_GREEN: (
            "the suite passed before anything was changed; there is no migration to propose"
        ),
    }.get(outcome, f"the run ended {outcome.value}, which left nothing to open")


def _default_base(runner: Runner, root: Path, remote: str) -> str:
    """The remote's own default branch, asked for rather than assumed.

    ``main`` is a guess that is wrong on every repository old enough to need a
    pydantic v1 migration, which is most of them. Guessing here opens a pull
    request against a branch that may not exist, or -- worse -- one that does
    and is not the one anybody merges into.
    """
    head = _git(runner, root, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD")
    name = head.rsplit("/", 1)[-1] if head else ""
    if not name:
        raise GitError(
            f"could not tell which branch {remote!r} opens pull requests against. "
            f"Run `git remote set-head {remote} --auto`, or pass the base explicitly."
        )
    return name


def request_for(proposal: Proposal) -> Request:
    """The approval request for ``proposal``.

    The summary leads with the push, not with the pull request. A pull request
    can be closed; a branch on somebody's remote is already on somebody's
    remote, and that is the sentence a person should be reading when they decide.

    Every fact that changes the answer is in ``detail``, which means every one of
    them is in the fingerprint. Swap the URL after approval and the gate refuses
    it as an approval made for a different request -- which it is.
    """
    return Request(
        action=ACTION,
        summary=(
            f"push {proposal.branch} to {proposal.url} and open a pull request "
            f"against {proposal.base}"
        ),
        detail={
            "url": proposal.url,
            "remote": proposal.remote,
            "branch": proposal.branch,
            "base": proposal.base,
            "title": proposal.title,
            "files": ", ".join(proposal.paths),
        },
    )


def open_pull_request(gate: Gate, proposal: Proposal, runner: Runner) -> Opened:
    """Open it, if the gate says yes. Nothing here runs before that answer.

    Raises :class:`~bumpsmith.gate.NotApprovedError` without touching the
    repository if the answer is no. After a yes: branch, stage the migration's
    own paths, commit, push, then open the pull request.

    A failure to open the pull request after a successful push is reported as
    :class:`Opened` with an empty ``url`` and a reason, not as an exception. The
    push happened; raising would describe a state the repository is not in, and
    the caller needs to know the branch is out there either way.
    """
    return gate.run(request_for(proposal), lambda: _do_open(proposal, runner))


def _do_open(proposal: Proposal, runner: Runner) -> Opened:
    root = proposal.root
    _git(runner, root, "checkout", "-B", proposal.branch)
    # `--` and one path at a time. Not `-A`, not `-a`, and not a glob: the tree
    # this runs in may hold work that is not ours, and a pathspec that could
    # match more than the migration wrote is a pathspec that eventually will.
    _git(runner, root, "add", "--", *proposal.paths)
    _git(runner, root, "commit", "-m", proposal.title, "-m", proposal.body)
    _git(runner, root, "push", "--set-upstream", proposal.remote, proposal.branch)

    try:
        out = _gh(
            runner,
            root,
            "pr",
            "create",
            "--base",
            proposal.base,
            "--head",
            proposal.branch,
            "--title",
            proposal.title,
            "--body",
            proposal.body,
        )
    except PublishError as exc:
        return Opened(
            branch=proposal.branch,
            pushed_to=proposal.url,
            note=(
                f"the branch is pushed; the pull request was not opened: {exc}. "
                f"Open it from {proposal.url}."
            ),
        )
    return Opened(branch=proposal.branch, pushed_to=proposal.url, url=_first_url(out))


def _gh(runner: Runner, root: Path, *args: str) -> str:
    try:
        result: Completed = runner.run(["gh", *args], root)
    except RunError as exc:
        raise PublishError(f"`gh {args[0]} {args[1]}` did not run: {exc}") from exc
    if result.returncode != 0:
        raise PublishError(f"`gh {args[0]} {args[1]}` exited {result.returncode}")
    return result.output.strip()


def _first_url(output: str) -> str:
    """`gh pr create` prints the URL on a line of its own, usually the last one.

    Read rather than assumed: gh also prints warnings, and taking the last line
    unconditionally would report a warning as the pull request's address.
    """
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if candidate.startswith("https://"):
            return candidate
    return ""


__all__ = [
    "ACTION",
    "DEFAULT_BRANCH",
    "GitError",
    "NothingToPublishError",
    "Opened",
    "Proposal",
    "PublishError",
    "body_for",
    "open_pull_request",
    "propose",
    "request_for",
]
