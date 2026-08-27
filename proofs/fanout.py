"""Migrate several repositories at the same time, and tell the failures apart.

What a test suite cannot reach here is *simultaneity*. ``tests/test_fanout.py``
proves the bookkeeping with jobs that do as they are told; this runs the real
loop -- real breaks, real edits, real pytest runs -- against several subjects at
once, and checks that four concurrent migrations reach the same verdicts four
sequential ones would.

The fourth subject is the point of the whole module. It cannot be reached at
all, and the proof fails unless the report keeps that apart from the subject
that was reached and needed nothing. Both contribute zero migrations. Only one
of them is good news.

Needs an interpreter with **pydantic v2 and pytest** on it -- the subjects are
migrated by running their own suites through it, so both are prerequisites and
both are checked before anything is built. This package deliberately depends on
neither. No harness, no network, no credentials.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from bumpsmith.fanout import Attempt, Unreached, fan_out
from bumpsmith.migrate import Migration, Outcome, migrate
from bumpsmith.run import LocalRunner

# Each subject is a whole small project with one real v1 break in it. Kept
# minimal on purpose: the thing being demonstrated is that four migrations run
# at once and come out right, not that the loop can handle a large repository,
# which `fixtures.toml` already covers against real third-party code.
SUBJECTS: dict[str, tuple[str, str, Outcome]] = {
    "regex-keyword": (
        "from pydantic import BaseModel, Field\n\n\n"
        "class User(BaseModel):\n"
        '    name: str = Field(..., regex="^[a-z]+$")\n',
        'import app\n\n\ndef test_user():\n    assert app.User(name="ada").name == "ada"\n',
        Outcome.MIGRATED,
    ),
    "root-model": (
        "from typing import List\n\nfrom pydantic import BaseModel\n\n\n"
        "class Tags(BaseModel):\n"
        "    __root__: List[str]\n",
        "import app\n\n\ndef test_tags():\n    assert app.Tags is not None\n",
        Outcome.MIGRATED,
    ),
    # The negative control, and the reason `Outcome` separates "already green"
    # from "migrated". A run that "fixes" this one is broken.
    "already-v2": (
        "from pydantic import BaseModel, Field\n\n\n"
        "class User(BaseModel):\n"
        '    name: str = Field(..., pattern="^[a-z]+$")\n',
        'import app\n\n\ndef test_user():\n    assert app.User(name="ada").name == "ada"\n',
        Outcome.ALREADY_GREEN,
    ),
}

UNREACHABLE = "sandbox-that-never-came-up"
"""A fourth subject whose migration never starts. Not a failure of this proof."""


class Subject:
    """One project on disk, and the migration that will be run against it."""

    def __init__(self, name: str, root: Path, python: str) -> None:
        self._name = name
        self._root = root
        self._python = python

    @property
    def subject(self) -> str:
        return self._name

    @property
    def root(self) -> Path:
        return self._root

    def __call__(self) -> Migration:
        return migrate(
            self._root,
            LocalRunner(),
            [self._python, "-m", "pytest", "-q"],
            project_packages=frozenset({"app"}),
        )


class Unreachable:
    """A job standing in for a sandbox that never came up.

    Raises the exception a refused connection actually produces, rather than a
    bespoke one, so what the report says about it is what it would say in the
    real case.
    """

    subject = UNREACHABLE

    def __call__(self) -> Migration:
        raise ConnectionRefusedError("[Errno 111] Connection refused")


def build(where: Path, python: str) -> list[Subject]:
    """Write every subject to disk and return a job for each."""
    jobs: list[Subject] = []
    for name, (app, test, _) in SUBJECTS.items():
        root = where / name
        root.mkdir(parents=True)
        (root / "app.py").write_text(app, encoding="utf-8")
        (root / "test_app.py").write_text(test, encoding="utf-8")
        # An empty inifile, so the subject's own suite is governed by the
        # subject. Without it pytest walks upward and the run inherits whatever
        # this proof happens to be sitting beneath -- which is finding 94, and
        # is exactly the confound that would make these results mean nothing.
        (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        jobs.append(Subject(name, root, python))
    return jobs


def check(attempts: Sequence[Attempt], jobs: Sequence[Subject]) -> list[str]:
    """Everything this proof claims, checked one at a time."""
    problems: list[str] = []
    by_name = {a.subject: a for a in attempts}
    roots = {j.subject: j.root for j in jobs}

    for name, (_, _, expected) in SUBJECTS.items():
        attempt = by_name.get(name)
        if attempt is None:
            problems.append(f"{name}: no attempt recorded")
            continue
        if not attempt.ran:
            problems.append(f"{name}: expected a migration, got {attempt.result}")
            continue
        if attempt.outcome is not expected:
            problems.append(f"{name}: expected {expected.value}, got {attempt.outcome}")

    lost = by_name.get(UNREACHABLE)
    if lost is None:
        problems.append(f"{UNREACHABLE}: no attempt recorded")
    elif lost.ran:
        problems.append(f"{UNREACHABLE}: reported a migration it never ran")
    elif not isinstance(lost.result, Unreached):
        problems.append(f"{UNREACHABLE}: expected Unreached, got {type(lost.result).__name__}")
    elif "ConnectionRefusedError" not in lost.result.reason:
        problems.append(f"{UNREACHABLE}: reason does not name the failure: {lost.result.reason!r}")

    # The negative control is not merely reported as untouched -- its file is
    # still the bytes that were written. `ALREADY_GREEN` is a claim about the
    # tree, and this is the tree.
    control = roots.get("already-v2")
    if control is not None:
        on_disk = (control / "app.py").read_text(encoding="utf-8")
        if on_disk != SUBJECTS["already-v2"][0]:
            problems.append("already-v2: the control was edited")

    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="an interpreter with pydantic v2 installed; the suites run under it",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--json", type=Path, help="write the payload here")
    args = parser.parse_args(argv)

    # Both, not just pydantic. Every subject is migrated by running
    # `python -m pytest` through this same interpreter, so an interpreter with
    # pydantic and no pytest fails all four subjects for a reason that has
    # nothing to do with fanning out -- and the proof would report it as
    # migrations that did not work. A missing prerequisite is not a result.
    probe = subprocess.run(  # noqa: S603
        [
            args.python,
            "-c",
            "import pydantic, pytest; print(pydantic.VERSION, pytest.__version__)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        print(
            f"--python needs both pydantic v2 and pytest installed: {probe.stderr.strip()}",
            file=sys.stderr,
        )
        return 2
    version, pytest_version = probe.stdout.split()
    if not version.startswith("2."):
        print(f"--python has pydantic {version}; this proof needs v2", file=sys.stderr)
        return 2

    where = Path(tempfile.mkdtemp(prefix="bumpsmith-fanout-"))
    try:
        jobs = build(where, args.python)
        print(
            f"pydantic {version}, pytest {pytest_version}, "
            f"{len(jobs)} subjects + one unreachable, {args.workers} workers"
        )
        result = fan_out([*jobs, Unreachable()], workers=args.workers)

        for attempt in result.attempts:
            what = attempt.outcome.value if attempt.outcome else f"unreached ({attempt.result})"
            print(f"  {attempt.subject:28s} {what}")
        print(
            f"\nreached {len(result.reached)}/{len(result.attempts)}, "
            f"complete={result.complete}, "
            f"migrated={result.counting(Outcome.MIGRATED)}"
        )

        problems = check(result.attempts, jobs)
        payload = {
            "pydantic": version,
            "pytest": pytest_version,
            "workers": args.workers,
            "fanout": result.as_dict(),
            "problems": problems,
        }
        if args.json:
            args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        if problems:
            print("\nFAILED:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1
        print("\nEvery subject came out as expected, and the one nobody reached says so.")
        return 0
    finally:
        shutil.rmtree(where, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
