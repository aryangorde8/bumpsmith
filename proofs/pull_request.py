"""Approve a pull request at a terminal, and watch a branch reach a real remote.

``proofs/deny.py`` proves the half that refuses: ``open_pull_request`` is denied
through a live harness, and the MCP server is never called. That is the half
worth having first and it is the wrong half to have alone -- a gate is only
interesting if something is behind it, and until :mod:`bumpsmith.publish` there
was nothing.

This is the other half, and it needs no harness, no network, no model and no
credentials. It builds a bare git repository in a temporary directory, gives it
a repository with a real pydantic v1 break in it, and runs
``python -m bumpsmith --open-pr`` against it four times:

===============================  ================================================
what is attached to stdin        what must happen
===============================  ================================================
nothing (``/dev/null``)          refused; the remote gains nothing
a terminal, answering ``n``      refused; the remote gains nothing
a terminal, answering ``y``      refused -- ``y`` is not the word; nothing pushed
a terminal, answering ``yes``    the branch is pushed, and only the migrated file
===============================  ================================================

The third case is the one worth writing down. Requiring the whole word is the
difference between an irreversible action approved by a person and one approved
by a keystroke, and it is the kind of decision that quietly stops being true.

After the approved run this checks what actually landed: one commit, touching
exactly the file the migration wrote, containing exactly the migration's edit.
A tool that pushed the right change plus somebody's unrelated work in progress
would pass every test in this repository and be unusable.

Run it with an interpreter that has pydantic 2 available for the suite it runs::

    python proofs/pull_request.py --out proofs/recorded/pull_request.json
"""

import argparse
import json
import os
import pty
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

BROKEN = """from pydantic import BaseModel, Field


class Account(BaseModel):
    sort_code: str = Field(..., regex=r"^\\d{2}-\\d{2}-\\d{2}$")
"""

MIGRATED = """from pydantic import BaseModel, Field


class Account(BaseModel):
    sort_code: str = Field(..., pattern=r"^\\d{2}-\\d{2}-\\d{2}$")
"""

# A suite that fails while `regex=` is in the source and passes once it is not.
# Stands in for pytest so the proof needs no pydantic and no test framework: what
# is under test here is the approval and the push, not the migration loop, which
# `tests/test_migrate.py` covers exhaustively.
SUITE = """
import pathlib, sys
source = pathlib.Path(sys.argv[1]).read_text()
if "regex=" in source:
    print(pathlib.Path(sys.argv[2]).read_text())
    sys.exit(2)
print("1 passed")
sys.exit(0)
"""


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    answer: str | None
    """What is typed at the prompt. ``None`` means nothing is attached at all."""

    approves: bool
    why: str


CASES = (
    Case(
        name="no terminal",
        answer=None,
        approves=False,
        why=(
            "A CI job, a pipe or a nohup has nobody in it to say no. Fail-closed is "
            "the only safe reading of silence when the action is a push."
        ),
    ),
    Case(
        name="answered n",
        answer="n",
        approves=False,
        why="The ordinary refusal. It must cost the user nothing and leave no trace.",
    ),
    Case(
        name="answered y",
        answer="y",
        approves=False,
        why=(
            "`y` is what a person types when they are not reading. The whole word is "
            "the only thing separating 'I read that' from 'I was pressing return'."
        ),
    ),
    Case(
        name="answered yes",
        answer="yes",
        approves=True,
        why="The one path that may push, and it pushes only the migration's own file.",
    ),
)


def _git(*args: str, cwd: Path) -> str:
    # `git` from PATH: the same git the reader just used to clone this repository.
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _build(root: Path) -> tuple[Path, Path, Path]:
    """A bare remote, a repository with a break in it, and a fake suite."""
    fork = root / "fork.git"
    repo = root / "repo"
    suite = root / "suite.py"

    _git("init", "--bare", "--initial-branch=trunk", str(fork), cwd=root)
    (repo / "mypkg").mkdir(parents=True)
    (repo / "mypkg" / "__init__.py").write_text(BROKEN, encoding="utf-8")
    suite.write_text(SUITE, encoding="utf-8")

    _git("init", "--initial-branch=trunk", cwd=repo)
    _git("config", "user.email", "proof@bumpsmith.invalid", cwd=repo)
    _git("config", "user.name", "bumpsmith proof", cwd=repo)
    _git("add", "-A", cwd=repo)
    _git("commit", "-m", "the repository before anybody migrated it", cwd=repo)
    _git("remote", "add", "fork", str(fork), cwd=repo)
    _git("push", "fork", "trunk", cwd=repo)
    _git("remote", "set-head", "fork", "--auto", cwd=repo)
    return fork, repo, suite


def _branches(fork: Path) -> list[str]:
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=fork)
    return sorted(line for line in out.splitlines() if line)


def _run(case: Case, repo: Path, suite: Path, failure: Path, python: str) -> str:
    """One migration, with ``case``'s answer typed at the prompt.

    A pseudo-terminal, not a pipe. The approver asks ``sys.stdin.isatty()``
    before it asks anybody anything, so feeding the answer down a pipe would
    exercise the *first* case four times and prove nothing about the other
    three.
    """
    command = [
        python,
        "-m",
        "bumpsmith",
        str(repo),
        "--package",
        "mypkg",
        "--open-pr",
        "fork",
        "--",
        python,
        str(suite),
        str(repo / "mypkg" / "__init__.py"),
        str(failure),
    ]
    if case.answer is None:
        with Path(os.devnull).open() as quiet:
            done = subprocess.run(  # noqa: S603 -- argv, no shell, interpreter named by the caller
                command, stdin=quiet, capture_output=True, text=True, check=False, timeout=300
            )
        return done.stdout + done.stderr

    parent, child = pty.openpty()
    try:
        process = subprocess.Popen(  # noqa: S603 -- as above
            command, stdin=child, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        os.close(child)
        child = -1
        os.write(parent, f"{case.answer}\n".encode())
        output, _ = process.communicate(timeout=300)
        return output
    finally:
        if child != -1:
            os.close(child)
        os.close(parent)


def _reset(repo: Path) -> None:
    _git("checkout", "trunk", cwd=repo)
    _git("reset", "--hard", "trunk", cwd=repo)
    with subprocess.Popen(
        ["git", "branch", "-D", "bumpsmith/pydantic-v2"],  # noqa: S607
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) as dropping:
        dropping.wait(timeout=60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="the interpreter to run with")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "recorded" / "pull_request.json",
        help="where to write the evidence",
    )
    args = parser.parse_args(argv)

    failure = Path(__file__).resolve().parent.parent / "tests" / "data" / "field-regex-broken.txt"
    if not failure.is_file():
        print(f"the recorded failure is missing: {failure}", file=sys.stderr)
        return 2

    root = Path(tempfile.mkdtemp(prefix="bumpsmith-pr-proof-"))
    recorded: list[dict[str, object]] = []
    wrong: list[str] = []
    try:
        fork, repo, suite = _build(root)
        print(f"a bare remote at {fork}\na repository at {repo}\n")

        for case in CASES:
            _reset(repo)
            before = _branches(fork)
            output = _run(case, repo, suite, failure, args.python)
            after = _branches(fork)
            pushed = sorted(set(after) - set(before))

            ok = (pushed == ["bumpsmith/pydantic-v2"]) if case.approves else (pushed == [])
            if not ok:
                wrong.append(case.name)
            print(
                f"{'PASS' if ok else 'FAIL'}  {case.name}: the remote gained {pushed or 'nothing'}"
            )
            recorded.append(
                {
                    "case": case.name,
                    "answered": case.answer,
                    "approval_expected": case.approves,
                    "branches_before": before,
                    "branches_after": after,
                    "pushed": pushed,
                    "as_expected": ok,
                    "why_it_matters": case.why,
                    "output": output.strip().splitlines()[-4:],
                }
            )

        landed = _inspect(fork, repo)
        recorded.append({"case": "what landed", **landed})
        if not landed["as_expected"]:
            wrong.append("what landed")
        print(f"\n{'PASS' if landed['as_expected'] else 'FAIL'}  what landed: {landed['files']}")

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "python": args.python,
                    "conclusion": (
                        "The push happens on `yes` and on nothing else. `y`, `n` and an "
                        "absent terminal are all refusals, and after each of them the "
                        "remote is byte-identical to what it was. The approved push "
                        "carries one commit touching only the file the migration wrote."
                    ),
                    "cases": recorded,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nevidence written to {args.out}", flush=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if wrong:
        print(
            f"\n{len(wrong)} case(s) did not behave as bumpsmith.publish says: {', '.join(wrong)}.",
            file=sys.stderr,
        )
        return 1
    print("\nevery case behaved as bumpsmith.publish says it does.", flush=True)
    return 0


def _inspect(fork: Path, repo: Path) -> dict[str, object]:
    """What the approved push actually put on the remote.

    The assertion that matters is the *narrowness* of it. A tool that pushed the
    right change alongside somebody's work in progress would satisfy every other
    check here, and would be unusable by anybody with a dirty tree -- which is
    everybody.
    """
    files = sorted(
        line
        for line in _git(
            "diff", "--name-only", "trunk..bumpsmith/pydantic-v2", cwd=fork
        ).splitlines()
        if line
    )
    commits = [
        line
        for line in _git(
            "log", "--format=%s", "trunk..bumpsmith/pydantic-v2", cwd=fork
        ).splitlines()
        if line
    ]
    content = _git("show", "bumpsmith/pydantic-v2:mypkg/__init__.py", cwd=fork)
    return {
        "files": files,
        "commits": commits,
        "content_matches_the_migration": content.strip() == MIGRATED.strip(),
        "as_expected": (
            files == ["mypkg/__init__.py"]
            and len(commits) == 1
            and content.strip() == MIGRATED.strip()
        ),
        "why_it_matters": (
            "One commit, one file, exactly the migration's edit. The repository being "
            "migrated is somebody's working directory; a push that swept the tree would "
            "put their uncommitted work in a pull request under this tool's name."
        ),
        "repo": str(repo),
    }


if __name__ == "__main__":
    raise SystemExit(main())
