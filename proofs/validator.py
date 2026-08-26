"""Ask a real pydantic v2 which validator signatures it accepts.

The class-1 rewriter deletes ``field`` and ``config`` from a validator's
signature. That is a smaller change than the error message asks for, and the
message is the reason this proof exists:

    The `field` and `config` parameters are not available in Pydantic V2,
    please use the `info` parameter instead.

Read as instructions, that says to rewrite the signature to take ``info``. Under
the ``@validator`` shim it is wrong -- ``info`` belongs to V2's
``@field_validator``, and the shim refuses a parameter by that name outright. A
rewriter that followed the advice in the message would trade one raised error
for another, and every test of it would pass, because the tests and the rewriter
would have been written from the same misreading.

So the rewrite is not derived from the message. It is derived from here: eight
signatures, each built in a subprocess against a real pydantic, with what
happened recorded. :mod:`bumpsmith.rules` states the conclusion in prose and
this is the run behind it.

Unlike the other two proofs this one needs no harness, no network and no model --
only an interpreter with pydantic v2 installed. Point ``--python`` at one.
"""

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# A model with two fields and one validator, with the signature substituted in.
# Built as source and run in a subprocess rather than exec'd here, so that a
# `PydanticUserError` raised at class-construction time is observed the way a
# migrated repository would meet it: at import, before anything runs.
TEMPLATE = """
import json, sys, warnings
warnings.simplefilter("ignore")
import pydantic
from pydantic import BaseModel, {decorator}

try:
    class M(BaseModel):
        x: int
        y: int

        @{decorator}({arguments})
        @classmethod
        def check({signature}):
            return {returns}
except BaseException as exc:
    print(json.dumps({{"stage": "build", "error": type(exc).__name__,
                      "message": str(exc).splitlines()[0]}}))
    sys.exit(0)

try:
    built = M(x=1, y=2)
except BaseException as exc:
    print(json.dumps({{"stage": "call", "error": type(exc).__name__,
                       "message": str(exc).splitlines()[0]}}))
    sys.exit(0)

print(json.dumps({{"stage": "ok", "error": None, "message": repr(built)}}))
"""


@dataclass(frozen=True, slots=True)
class Case:
    """One signature, and what this proof needs to be true of it."""

    name: str
    decorator: str
    arguments: str
    signature: str
    returns: str
    expected: str
    """``ok``, or the exception type the run has to end with."""

    why: str
    """What the rewriter would get wrong if this case came back differently."""


VALIDATOR = "validator"
ROOT = "root_validator"

CASES = (
    Case(
        name="validator with field and config",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v, values, field, config",
        returns="v",
        expected="PydanticUserError",
        why="the break itself; if this passed there would be nothing to migrate",
    ),
    Case(
        name="validator with values only",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v, values",
        returns="v",
        expected="ok",
        why="the shape the rewriter produces, and the whole reason the deletion is enough",
    ),
    Case(
        name="validator with neither",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v",
        returns="v",
        expected="ok",
        why="the shape produced when the site declared no `values` either",
    ),
    Case(
        name="validator with info",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v, info",
        returns="v",
        expected="PydanticUserError",
        why="what the error message tells you to write, and it does not work here",
    ),
    Case(
        name="validator with field alone",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v, field",
        returns="v",
        expected="PydanticUserError",
        why="either parameter alone is the break, so the scan is right to match on either",
    ),
    Case(
        name="validator with config alone",
        decorator=VALIDATOR,
        arguments='"y"',
        signature="cls, v, config",
        returns="v",
        expected="PydanticUserError",
        why="the same, for the other name",
    ),
    Case(
        name="root_validator with field and config",
        decorator=ROOT,
        arguments="skip_on_failure=True",
        signature="cls, values, field, config",
        returns="values",
        expected="TypeError",
        why=(
            "the rule matches `root_validator` too, and it fails differently -- not at "
            "class construction but at call time, with a plain builtin TypeError"
        ),
    ),
    Case(
        name="root_validator with values only",
        decorator=ROOT,
        arguments="skip_on_failure=True",
        signature="cls, values",
        returns="values",
        expected="ok",
        why="the same deletion fixes it, which is why one rewriter covers both decorators",
    ),
)


def _run(python: str, case: Case) -> dict[str, object]:
    """Build one model in a subprocess and report how far it got."""
    source = TEMPLATE.format(
        decorator=case.decorator,
        arguments=case.arguments,
        signature=case.signature,
        returns=case.returns,
    )
    completed = subprocess.run(  # noqa: S603 -- argv, no shell, interpreter named by the caller
        [python, "-c", source],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    line = completed.stdout.strip().splitlines()
    if completed.returncode != 0 or not line:
        return {
            "stage": "no-result",
            "error": None,
            "message": (completed.stderr.strip() or "the interpreter printed nothing")[-300:],
        }
    parsed: dict[str, object] = json.loads(line[-1])
    return parsed


def _version(python: str) -> str | None:
    completed = subprocess.run(  # noqa: S603 -- as above
        [python, "-c", "import pydantic; print(pydantic.VERSION)"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _verdict(case: Case, outcome: dict[str, object]) -> bool:
    """Whether this run says what the rewriter was built on the strength of."""
    if case.expected == "ok":
        return outcome.get("stage") == "ok"
    return outcome.get("error") == case.expected


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="an interpreter with pydantic v2 installed (default: this one)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("validator.json"),
        help="where to write the evidence",
    )
    args = parser.parse_args(argv)

    version = _version(args.python)
    if version is None:
        print(
            f"{args.python} has no importable pydantic, so there is nothing to ask.\n"
            f"Point --python at an interpreter that has pydantic v2 installed.",
            file=sys.stderr,
        )
        return 1
    if not version.startswith("2."):
        print(
            f"{args.python} has pydantic {version}. This proof is about v2's behaviour; "
            f"asking v1 would record the wrong answers confidently.",
            file=sys.stderr,
        )
        return 1

    print(f"asking pydantic {version} at {args.python}\n", flush=True)

    recorded: list[dict[str, object]] = []
    wrong: list[str] = []
    for case in CASES:
        outcome = _run(args.python, case)
        ok = _verdict(case, outcome)
        if not ok:
            wrong.append(case.name)
        got = outcome.get("error") or outcome.get("stage")
        print(f"  {'OK ' if ok else 'NO '} {case.name:38} expected {case.expected:18} got {got}")
        recorded.append(
            {
                "case": case.name,
                "decorator": case.decorator,
                "signature": case.signature,
                "expected": case.expected,
                "outcome": outcome,
                "as_expected": ok,
                "why_it_matters": case.why,
            }
        )

    args.out.write_text(
        json.dumps(
            {
                "python": args.python,
                "pydantic": version,
                "conclusion": (
                    "Removing `field` and `config` is the whole fix. `values` survives; "
                    "`info` is refused under @validator, so the error message's advice "
                    "does not apply to the decorator that raised it."
                ),
                "cases": recorded,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nevidence written to {args.out}", flush=True)

    if wrong:
        print(
            f"\n{len(wrong)} case(s) did not behave as the rewriter assumes: "
            f"{', '.join(wrong)}.\n"
            f"The rewriter is built on these answers, so a change here is a change there.",
            file=sys.stderr,
        )
        return 1

    print("\nevery case behaved as bumpsmith.rules says it does.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
