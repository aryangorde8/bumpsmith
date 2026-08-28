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

How the read answers
--------------------
Everything above turns on telling three outcomes apart: the marker is there with
known contents, the marker is genuinely not there, and *the question could not be
asked*. Those are three answers, so the read returns three answers. It prints a
fixed prefix -- :data:`PRESENT` or :data:`ABSENT` -- and the marker's bytes go
after the prefix, never in place of it. Absence is therefore a position in the
output rather than a reserved string, and no marker contents can imitate it.

The third outcome is carried by the exit status, under ``set -e``: a marker that
exists and cannot be read is a failed command, not an absent file. Collapsing
those two is how a broken control passes -- an unreadable marker would report as
"a fresh session could not see it", which is the sentence leg three exists to
earn.

Needs a running TrueForge with a sandbox provider. See ``proofs/README.md``.
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

PRESENT = "PRESENT:"
"""Prefix for a marker that was read. Everything after it is the marker's bytes.

The prefix comes first and the payload follows, so the two never compete for the
same position: a marker whose contents are ``ABSENT:`` reads back as
``PRESENT:ABSENT:`` and parses as present. A sentinel *value* would not survive
that -- it would let the marker's own contents answer the question the read was
supposed to answer.
"""

ABSENT = "ABSENT:"
"""The whole answer when the marker is not there. It carries no payload.

Matched exactly rather than by prefix, because absence has nothing to say. An
answer that begins ``ABSENT:`` and continues is not an absent marker; it is a
read this script does not understand, and :func:`_marker` refuses it rather than
guessing.
"""


def _write(nonce: str) -> list[str]:
    """Put the marker in the sandbox this session opened."""
    return [
        "sh",
        "-c",
        " && ".join(
            [
                f"mkdir -p {shlex.quote(WORKSPACE)}",
                f"printf %s {shlex.quote(nonce)} > {shlex.quote(MARKER)}",
                "echo written",
            ]
        ),
    ]


def _read() -> list[str]:
    """Ask whether the marker is there, and say which of three answers it is.

    ``-e`` is deliberately paired with ``-L``: a dangling symlink and a directory
    both take the *present* branch, where ``cat`` fails and ``set -e`` turns the
    read into an error. Testing with ``-f`` instead would report both as absence,
    which is the failure this whole shape exists to prevent -- a control that
    passes because something was broken rather than because nothing was there.

    ``printf %s`` writes the prefix and ``printf %s`` wrote the nonce, so a
    session that held returns exactly the prefix followed by exactly the nonce,
    with nothing added at either end to strip back off.
    """
    path = shlex.quote(MARKER)
    return [
        "sh",
        "-c",
        (
            "set -e; "
            f"if [ -e {path} ] || [ -L {path} ]; "
            f"then printf %s {shlex.quote(PRESENT)}; cat {path}; "
            f"else printf %s {shlex.quote(ABSENT)}; fi"
        ),
    ]


def _ran(result: Completed, what: str) -> str:
    """The output of a command that had to succeed, or a reason it did not.

    A non-zero exit here is not a failed control -- it is the proof failing to
    run. Reading one as the other is how a broken leg gets recorded as evidence.

    The output is returned exactly as it arrived. Only the *error* message
    strips, because that is prose for a human; the marker is data, and a proof
    that normalises its own evidence before comparing it is comparing something
    it did not observe.
    """
    if result.returncode != 0:
        raise RunError(f"{what} exited {result.returncode}: {result.output.strip()[-300:]}")
    return result.output


def _marker(result: Completed, what: str) -> str | None:
    """The marker's contents, or ``None`` if it was genuinely not there.

    Anything that is neither answer raises. A read that came back as something
    this script cannot parse is not evidence of absence -- it is a read that did
    not happen, and the two may not arrive as the same value.
    """
    raw = _ran(result, what)
    if raw.startswith(PRESENT):
        return raw[len(PRESENT) :]
    if raw == ABSENT:
        return None
    raise RunError(f"{what} did not answer in the marker protocol: {raw[:200]!r}")


def _shown(read: str | None) -> str:
    """A marker as a human should see it, with absence named rather than blank."""
    return "absent" if read is None else repr(read)


def _leg(session: str, read: str | None) -> dict[str, object]:
    """One leg's evidence.

    ``present`` is recorded next to ``read`` so the JSON says which of the two
    questions was answered without a reader having to know that ``null`` means
    absence rather than "not recorded".
    """
    return {"session": session, "present": read is not None, "read": read}


def _nonce(value: str) -> str:
    """A marker that is worth writing.

    Only emptiness is refused. Whitespace, newlines and the protocol's own
    prefixes all round-trip intact, which is the point of putting absence in the
    prefix rather than in the contents -- so rejecting them here would be
    guarding against a collision that no longer exists. An empty marker is
    different: it makes leg two's comparison true for any empty file, so it
    proves the file exists and nothing about what survived.
    """
    if not value:
        raise argparse.ArgumentTypeError(
            "the marker needs contents; an empty one is matched by any empty file"
        )
    return value


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
        type=_nonce,
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
        established = _marker(first.run(_read(), Path("/tmp")), "the first read")  # noqa: S108
        session = first_exec.session_id()
        print(f"  session {session}", flush=True)
        print(f"  marker  {_shown(established)}", flush=True)

        # ---- leg 2: throw the client away and come back with the id ----------
        # Nothing from leg 1 crosses this line except the session string. The
        # objects are rebuilt rather than reused precisely so that a connection
        # held open cannot be what makes the next read succeed.
        print("\nleg 2: new client, same session id...", flush=True)
        del first, first_exec
        second_exec = SandboxExec(connect(), args.model, session_id=session)
        second = SandboxRunner(second_exec)
        reconnected = _marker(second.run(_read(), Path("/tmp")), "the read after reconnect")  # noqa: S108
        print(f"  session {second_exec.session_id()}", flush=True)
        print(f"  marker  {_shown(reconnected)}", flush=True)

        # ---- leg 3: the control -- a new session must not see it -------------
        print("\nleg 3: control, a brand-new session...", flush=True)
        third_exec = SandboxExec(connect(), args.model)
        third = SandboxRunner(third_exec)
        control = _marker(third.run(_read(), Path("/tmp")), "the control read")  # noqa: S108
        fresh = third_exec.session_id()
        print(f"  session {fresh}", flush=True)
        print(f"  marker  {_shown(control)}", flush=True)
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
                "established": _leg(session, established),
                "reconnected": _leg(second_exec.session_id(), reconnected),
                "control": _leg(fresh, control),
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
            f"\nleg 1 never had the marker: read {_shown(established)}, wrote {nonce!r}. "
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
            f"{_shown(reconnected)} rather than {nonce!r}.",
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
    if control is not None:
        print(
            f"\nthe control failed: a brand-new session read {_shown(control)} rather than "
            "finding nothing. The marker is reachable from a session that never wrote it, so "
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
