"""Run a real test suite inside the harness's sandbox, using only the package.

This is the first half of the hackathon's control-and-safety criterion: does the
agent run its code somewhere safe. The answer has to be demonstrated rather than
asserted, and the demonstration is worth as much as its transport is honest --
so there is no transport here. ``Client`` opens the session, ``SandboxExec``
issues the ``exec``, ``SandboxRunner`` reads the result, and ``parse_failures``
classifies it. Four lines, all of them ``import bumpsmith``.

That is the point of how short it is. Every earlier version of this proof
supplied its own session handling and turn polling in a scratch file, which
demonstrated that a sandbox run was possible, not that *this package* could do
one. Findings 35 and 39 both said so.

Needs a running TrueForge with a sandbox provider configured. See
``proofs/README.md``.
"""

import argparse
import json
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from bumpsmith.failures import BreakClass, parse_failures
from bumpsmith.run import RunError, SandboxRunner
from bumpsmith.trueforge import Client, SandboxExec, TransportError

DEFAULT_MODEL = "bedrock-mantle/qwen-3-coder-480b"

EXPECTED = BreakClass.REGEX_KEYWORD
"""The break this proof builds and therefore the only one it may end green on."""

WORKSPACE = "/tmp/bumpsmith-proof"  # noqa: S108 -- a path in the sandbox, not on this machine

APP = """from pydantic import BaseModel, Field


class User(BaseModel):
    name: str = Field(..., regex="^[a-z]+$")
"""

TEST = """from app import User


def test_user():
    assert User(name="ada").name == "ada"
"""

SETUP = " && ".join(
    [
        f"rm -rf {WORKSPACE}",
        f"mkdir -p {WORKSPACE}",
        f"cd {WORKSPACE}",
        f"printf '%s' {shlex.quote(APP)} > app.py",
        f"printf '%s' {shlex.quote(TEST)} > test_app.py",
        "python -m pip install -q pydantic pytest",
        "echo ready",
    ]
)
"""Build a project with one class-3 break, inside the sandbox.

The sources are shell-quoted with :func:`shlex.quote` rather than escaped by
hand. That is the same quoting :class:`~bumpsmith.run.SandboxRunner` applies to
argv, and it is the reason this file has no backslashes in it: a proof whose
setup step silently wrote the wrong source would be a proof of nothing, and an
earlier version of this script did exactly that.

Written with ``printf`` rather than uploaded because the harness offers no way
to put a file into a sandbox -- there is a download endpoint and no upload. That
limitation is also why ``python -m bumpsmith --sandbox`` refuses: the loop's
edits cannot be carried across, so a suite run there would not be testing them.
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python proofs/sandbox.py",
        description="Run a suite with a pydantic v1 break inside the harness's sandbox.",
    )
    parser.add_argument("--base-url", default=None, help="TrueForge API root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model to run the session as")
    parser.add_argument(
        "--out", type=Path, default=Path("sandbox.json"), help="where to write the evidence"
    )
    args = parser.parse_args(argv)

    client = Client() if args.base_url is None else Client(args.base_url)
    runner = SandboxRunner(SandboxExec(client, args.model))

    try:
        print("setting up the project in the sandbox...", flush=True)
        setup = runner.run(["sh", "-c", SETUP], Path("/tmp"))  # noqa: S108
        print(f"  setup rc={setup.returncode}  {setup.output.strip()[-60:]}", flush=True)

        # A command that ran and failed is a `Completed`, not a `RunError` --
        # that distinction is the whole of `bumpsmith.run` and it is correct.
        # It does mean a failed `pip install` arrives here looking like an
        # ordinary result, and carrying on from one would run pytest against a
        # project that was never built. The nonzero pytest that followed would
        # then be recorded as proof of a pydantic break it had nothing to do
        # with.
        if setup.returncode != 0:
            print(
                f"\nsetup exited {setup.returncode}, so the project was never built and "
                f"anything pytest says next is about something else:\n{setup.output[-800:]}",
                file=sys.stderr,
            )
            return 1

        print("running the suite in the sandbox...", flush=True)
        result = runner.run(["python", "-m", "pytest", "-q"], Path(WORKSPACE))
    except (RunError, TransportError) as exc:
        print(f"\nthe proof did not run: {exc}", file=sys.stderr)
        print(
            "Is TrueForge up, and does it have a sandbox provider? See README.md.", file=sys.stderr
        )
        return 1

    print(f"\nran in the {result.where}: rc={result.returncode}", flush=True)
    print(result.output[:1500], flush=True)

    failures = parse_failures(result.output, returncode=result.returncode)
    print(f"bumpsmith read {len(failures)} failure(s) out of it:", flush=True)
    for failure in failures:
        print(f"  [{failure.break_class.name}] {failure.message or '(no message)'}", flush=True)

    args.out.write_text(
        json.dumps(
            {
                "transport": "bumpsmith.trueforge.Client + SandboxExec",
                "runner": "bumpsmith.run.SandboxRunner",
                "model": args.model,
                "setup": {"returncode": setup.returncode, "output": setup.output},
                "result": {
                    "returncode": result.returncode,
                    "where": result.where,
                    "output": result.output,
                },
                "parsed": [
                    {"break_class": f.break_class.name, "message": f.message} for f in failures
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nevidence written to {args.out}", flush=True)

    # The suite is meant to fail, and to fail of *this*. A green run would mean
    # the break never happened; a red run of some other colour would mean
    # something else went wrong and got recorded as a pydantic migration
    # failure. "Nonzero and something parsed" was the first version of this
    # check and it accepted both.
    if result.returncode == 0:
        print("\nthe suite passed, so the break never happened.", file=sys.stderr)
        return 1
    if not any(failure.break_class is EXPECTED for failure in failures):
        got = ", ".join(f.break_class.name for f in failures) or "nothing"
        print(
            f"\nthe suite failed, but of {got} rather than {EXPECTED.name}. "
            f"That is not the break this proof is about.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
