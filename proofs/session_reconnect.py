"""A session outlives the client that made it, and the sandbox holds its state.

The hackathon's harness criterion asks for "a session that holds together across
reconnects". Until this file, that was the one item in the README's *what the
harness is not doing here yet* list with a seam and no test behind it:
:class:`~bumpsmith.trueforge.SandboxExec` already accepts a ``session_id`` it did
not create, and nothing demonstrated that handing it one reaches the sandbox that
session opened.

Reconnecting is modelled by *throwing the client away*. Leg two builds a new
:class:`~bumpsmith.trueforge.Client` and a new
:class:`~bumpsmith.trueforge.SandboxExec` from nothing but the session id --
every socket, every connection pool and every piece of in-process state from leg
one is gone. That is what a second process holding a stored session id has, and
it is the only version of "reconnect" this package can honestly claim.

Why there is a third leg
------------------------
Legs one and two alone prove nothing. "The marker file is there" is also what you
would see if every sandbox everywhere had that file -- if the path were shared,
if sandboxes were pooled, if the harness ignored the session id and handed back
whatever it had. So leg three opens a **brand-new session** and looks for the
same marker. It has to be **absent**.

Leg three is the whole proof. Without it leg two is an observation; with it, leg
two is a measurement. The marker also carries a nonce, so a marker left behind by
an earlier run of this script cannot be mistaken for this run's.

Needs a running TrueForge with a sandbox provider configured. See
``proofs/README.md``.
"""

import argparse
import json
import secrets
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

from bumpsmith.run import Completed, RunError, SandboxRunner
from bumpsmith.trueforge import Client, SandboxExec, TransportError

DEFAULT_MODEL = "bedrock-mantle/qwen-3-coder-480b"

WORKSPACE = "/tmp/bumpsmith-session"  # noqa: S108 -- a path in the sandbox, not on this machine

MARKER = f"{WORKSPACE}/marker"

ABSENT = "__ABSENT__"
"""What the read prints when the marker is not there.

A missing file is read through ``|| echo`` rather than through the exit status
because the two are not the same question. ``cat`` exits non-zero for a file that
is missing *and* for a directory it may not read, and this proof's whole claim
turns on telling "the session did not carry over" apart from "something else went
wrong". One of those is the control succeeding and the other is the proof being
broken, so they may not arrive as the same value.
"""


def _write(nonce: str) -> list[str]:
    """Put the marker in the sandbox this session opened."""
    return [
        "sh",
        "-c",
        " && ".join(
            [
                f"mkdir -p {shlex.quote(WORKSPACE)}",
                f"printf '%s' {shlex.quote(nonce)} > {shlex.quote(MARKER)}",
                "echo written",
            ]
        ),
    ]


def _read() -> list[str]:
    """Read the marker back, or say it is absent.

    ``printf '%s'`` wrote it without a trailing newline, so a session that held
    returns exactly the nonce and nothing else.
    """
    return ["sh", "-c", f"cat {shlex.quote(MARKER)} 2>/dev/null || echo {ABSENT}"]


def _ran(result: Completed, what: str) -> str:
    """The output of a command that had to succeed, or a reason it did not.

    A non-zero exit here is not a failed control -- it is the proof failing to
    run. Reading one as the other is how a broken leg gets recorded as evidence.
    """
    if result.returncode != 0:
        raise RunError(f"{what} exited {result.returncode}: {result.output.strip()[-300:]}")
    return result.output.strip()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python proofs/session_reconnect.py",
        description="Show that a TrueForge session, and its sandbox, outlive the client.",
    )
    parser.add_argument("--base-url", default=None, help="TrueForge API root")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="model to run the session as")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("session_reconnect.json"),
        help="where to write the evidence",
    )
    parser.add_argument(
        "--nonce",
        default=None,
        help="the marker's contents; a fresh random one by default",
    )
    args = parser.parse_args(argv)

    nonce = args.nonce or secrets.token_hex(8)

    def connect() -> Client:
        """A client with nothing carried over from the last one."""
        return Client() if args.base_url is None else Client(args.base_url)

    try:
        # ---- leg 1: open a session and leave something in its sandbox --------
        print("leg 1: opening a session and writing a marker...", flush=True)
        first_exec = SandboxExec(connect(), args.model)
        first = SandboxRunner(first_exec)
        _ran(first.run(_write(nonce), Path("/tmp")), "the write")  # noqa: S108
        established = _ran(first.run(_read(), Path("/tmp")), "the first read")  # noqa: S108
        session = first_exec.session_id()
        print(f"  session {session}", flush=True)
        print(f"  marker  {established}", flush=True)

        # ---- leg 2: throw the client away and come back with the id ----------
        # Nothing from leg 1 crosses this line except the session string. The
        # objects are rebuilt rather than reused precisely so that a connection
        # held open cannot be what makes the next read succeed.
        print("\nleg 2: new client, same session id...", flush=True)
        del first, first_exec
        second_exec = SandboxExec(connect(), args.model, session_id=session)
        second = SandboxRunner(second_exec)
        reconnected = _ran(second.run(_read(), Path("/tmp")), "the read after reconnect")  # noqa: S108
        print(f"  session {second_exec.session_id()}", flush=True)
        print(f"  marker  {reconnected}", flush=True)

        # ---- leg 3: the control -- a new session must not see it -------------
        print("\nleg 3: control, a brand-new session...", flush=True)
        third_exec = SandboxExec(connect(), args.model)
        third = SandboxRunner(third_exec)
        control = _ran(third.run(_read(), Path("/tmp")), "the control read")  # noqa: S108
        fresh = third_exec.session_id()
        print(f"  session {fresh}", flush=True)
        print(f"  marker  {control}", flush=True)
    except (RunError, TransportError) as exc:
        print(f"\nthe proof did not run: {exc}", file=sys.stderr)
        print(
            "Is TrueForge up, and does it have a sandbox provider? See README.md.", file=sys.stderr
        )
        return 1

    args.out.write_text(
        json.dumps(
            {
                "transport": "bumpsmith.trueforge.Client + SandboxExec",
                "runner": "bumpsmith.run.SandboxRunner",
                "model": args.model,
                "nonce": nonce,
                "marker": MARKER,
                "established": {"session": session, "read": established},
                "reconnected": {"session": second_exec.session_id(), "read": reconnected},
                "control": {"session": fresh, "read": control},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nevidence written to {args.out}", flush=True)

    # Every check below has to hold for the sentence in the README to be true,
    # and each one fails differently. They are separate so the output says which.
    if established != nonce:
        print(
            f"\nleg 1 never had the marker: read {established!r}, wrote {nonce!r}. "
            "Nothing after this means anything.",
            file=sys.stderr,
        )
        return 1
    if second_exec.session_id() != session:
        print(
            f"\nleg 2 did not reuse the session: asked for {session}, "
            f"used {second_exec.session_id()}.",
            file=sys.stderr,
        )
        return 1
    if reconnected != nonce:
        print(
            f"\nthe session did not hold: after reconnecting, the marker read "
            f"{reconnected!r} rather than {nonce!r}.",
            file=sys.stderr,
        )
        return 1
    if fresh == session:
        print(
            f"\nthe control is not a control: it got session {fresh}, the same one "
            "leg 2 used, so finding the marker there proves nothing.",
            file=sys.stderr,
        )
        return 1
    if control != ABSENT:
        print(
            f"\nthe control failed: a brand-new session read {control!r} rather than "
            f"{ABSENT}. The marker is reachable from a session that never wrote it, so "
            "leg 2 is not evidence that the session held.",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nthe session held: {session} kept its sandbox across a new client, "
        f"and a fresh session ({fresh}) could not see the marker.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
