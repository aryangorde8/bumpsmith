# Proofs

Scripts that demonstrate something the test suite cannot reach on its own.
One per directory entry ending in `.py`; the count is deliberately not written
down here, because this repository has two review findings about a number
restated in prose and left behind by the thing it counted.

Two of them run against a live TrueForge and cover the halves of the hackathon's
control-and-safety criterion — *does the agent run its code somewhere safe, and
does it stop for a human before anything irreversible.* The others need no harness
at all, but do need a dependency this package deliberately does not have: one asks
a real pydantic v2 which validator signatures it accepts, and one runs several real
migrations at the same time to show that a subject nobody reached is not reported
as a subject with nothing to do.

They are here rather than in `tests/` because each needs something a laptop
running `pytest` does not have, and a test suite that cannot run on a laptop is
not a test suite.

What each one actually proved, on the run recorded in `recorded/`, is at the
bottom of this file.

## What they are not

They do not test the package. `tests/` does that, in full and offline. These
scripts exist for the opposite reason: to catch the things a test cannot, because
the test and the code were written by the same person from the same
understanding. Three of this project's review findings came from live runs and
could not have come from anywhere else — the harness pauses a wrapper rather than
the tool it wraps, `thread_id` is not a session id, and a session id of `"main"`
is a 404. `validator.py` was written after a fourth: the error message pydantic
prints for a class-1 break names a fix that does not work, and a rewriter built
from the message would have been wrong with a full green suite behind it.

The measure of a proof here is how little of it there is. Every one of these
started as a scratch file with its own session handling, turn polling and event
digging, which demonstrated that the thing was *possible*, not that this package
could do it. Findings 35 and 39 both said so. What is left is four lines of
`import bumpsmith` and the arguments.

## Running them

Install the package first (`pip install -e .`) so the imports resolve.
`sandbox.py` and `deny.py` need a TrueForge on `http://localhost:8790`; pass
`--base-url` for anywhere else. `pull_request.py`, `validator.py` and `fanout.py`
need no harness at all — those are the ones a reader without one can run.
`validator.py` wants an interpreter with pydantic v2; `fanout.py` wants pydantic
v2 and pytest, and says so before it starts.

### `sandbox.py` — the suite runs somewhere safe

```
python proofs/sandbox.py
```

Needs a sandbox provider configured in the harness (this project uses Daytona).
It builds a four-line project with a pydantic v1 `regex=` in it, runs pytest
against it **inside the sandbox**, and hands the result to `bumpsmith.failures`.

The suite is *meant* to fail, and to fail of the right thing. A green run would
mean the break never happened; a red run of some other colour would mean
something else went wrong and got filed as a pydantic migration failure. So the
setup step has to succeed before pytest is run at all, and the parsed break has
to be `REGEX_KEYWORD` — the one this script builds — or it exits non-zero.

The setup step writes the project with `printf` because the harness offers a way
to download a file from a sandbox and no way to put one in. That limitation is
also why `python -m bumpsmith --sandbox` refuses — the loop's edits cannot be
carried across, so a suite run there would not be testing them.

### `deny.py` — nothing irreversible happens without a human

```
python proofs/mcp_stub.py        # leave running
python proofs/deny.py
```

`mcp_stub.py` is a one-tool MCP server. Its `open_pull_request` is annotated
`destructiveHint: true`, and TrueForge's default `require_approval_for_tools` is
`["@write", "@destructive"]` — so the harness pauses the call with **no
configuration added to make it do so**. Nothing here arranges the thing it then
demonstrates.

The stub has to be registered with the harness before this works, and `deny.py`
checks: if the harness has no server called `irreversible-things`, it prints the
manifest and stops rather than running a session that would pause nothing.
Registering it is a change to your harness's configuration, so it is yours to
make:

```json
{
  "type": "remote",
  "name": "irreversible-things",
  "url": "http://127.0.0.1:8791/mcp",
  "description": "One tool that opens a pull request. Annotated destructive."
}
```

The agent is then asked to open a pull request. It reaches for the tool, the
harness pauses, `bumpsmith.gate` denies — unconditionally, because nobody is
sitting there, and an unattended agent that treats silence as consent has no gate
at all.

Delivering the denial does not end the conversation — it starts the harness
working again. So the script waits for the session to go quiet before it checks
anything: two consecutive passes that add no turn and leave none in progress,
bounded by `--settle`, with a message rather than a false clean bill if the bound
is hit. On the recorded run the agent read the refusal, abandoned the tool, and
called `ask_user_question` instead. Checking before that had happened would have
been asking whether the tool had run *yet*.

**The claim is about the effect, not the paperwork.** A refusal recorded next to
an action that happened anyway is worse than no refusal, so the script finishes
by asking whether the tool ran, twice and in two ways:

- `GET /calls` on the stub, at the URL read out of *the harness's own manifest* —
  so the server being questioned is provably the one the harness would have
  called, not another copy on a port the script guessed.
- `pr-calls.log`, which the stub appends to on every invocation.

Both signals are cumulative — the stub keeps every call it has ever served — so
both are baselined before the session is created and compared afterwards. Nothing
is deleted to tidy that up: clearing the evidence is how a real call gets lost.

Being unable to ask is never reported as "it did not run". A proof that turned an
unreachable server into a clean bill of health would pass most reliably when it
was least entitled to.

### `pull_request.py` — the other half of the gate

```bash
python proofs/pull_request.py
```

`deny.py` proves the half that refuses. This proves the half that does not, and
it is the half that had nothing behind it until `bumpsmith.publish` was written:
a gate is only interesting if something is on the other side of the door.

It builds a **bare git repository in a temporary directory** — a real remote that
nobody owns — gives it a repository with a real pydantic v1 break, and runs
`python -m bumpsmith --open-pr` against it four times, checking what reached the
remote after each:

| answered | at | must happen |
|---|---|---|
| nothing | `/dev/null` | refused; the remote gains nothing |
| `n` | a pty | refused; the remote gains nothing |
| `y` | a pty | **refused** — `y` is not the word |
| `yes` | a pty | pushed, and only the migrated file |

Each row is checked three ways, not one. **Every ref on the remote is compared by
name *and by object***, because a refusal that rewrote `trunk` changes no name
and the conclusion being recorded is that nothing happened. **The exit status is
checked**, because "no new branch appeared" is also satisfied by a crash before
the prompt was ever printed. And the approved run exits **2**, not 0: the remote
here is a bare repository, so there is nowhere to open a pull request, and one
that was asked for and did not happen is not a success.

A pseudo-terminal rather than a pipe, deliberately: the approver asks
`sys.stdin.isatty()` before it asks anybody anything, so feeding the answer down
a pipe would exercise the first case four times and prove nothing about the
other three.

The last check is the narrow one. After the approved push it reads back the
branch: one commit, touching exactly `mypkg/__init__.py`, containing exactly the
migration's edit. A tool that pushed the right change *alongside somebody's work
in progress* would satisfy every other check here and be unusable by anyone with
a dirty tree — which is everyone.

Needs no harness, no network, no model and no credentials. With `validator.py`
it is the second proof a reader can run having only cloned the repository.

### `validator.py` — the fix is not what the error message says

```
python proofs/validator.py --python /path/to/a/venv/bin/python
```

Needs an interpreter with pydantic v2 installed, and nothing else. It builds
eight one-model modules, each with a differently shaped validator, runs each in
its own subprocess, and records how far it got.

It exists because of one sentence pydantic prints:

> The `field` and `config` parameters are not available in Pydantic V2, please
> use the `info` parameter instead.

Read as instructions that says to rewrite the signature to take `info`. Under
the `@validator` shim it is wrong — `info` belongs to V2's `@field_validator`,
and the shim refuses a parameter by that name as an unsupported V1 signature.
The migration that works is to *remove* both parameters; `values` is still
accepted and still carries what it did.

That is a fact about somebody else's library, so it is checked against somebody
else's library rather than asserted in a docstring. The script exits non-zero if
any of the eight stops behaving the way `bumpsmith.rules` says it does — the
rewriter is built on these answers, so a change here is a change there.

### `fanout.py` — several migrations at once, and one that never happened

```
python proofs/fanout.py --python /path/to/a/venv/bin/python
```

Needs an interpreter with **pydantic v2 and pytest** on it — the subjects are
migrated by running their own suites through it, so both are prerequisites and
both are checked up front, before anything is built. No harness, no network, no
credentials. It writes three small projects with real v1 breaks in them, plus
a fourth subject that cannot be reached at all, and migrates them concurrently
through `bumpsmith.fanout.fan_out`.

`tests/test_fanout.py` proves the bookkeeping with jobs that do as they are told.
What a test suite cannot reach is *simultaneity*: this runs the real loop — real
breaks, real edits, real pytest runs — against several subjects at once, and
checks that four concurrent migrations reach the verdicts four sequential ones
would. Measured on the recorded run: **2.1s at one worker, 1.1s at four.**

The fourth subject is the point of the module. It raises the exception a refused
connection actually produces, and the proof fails unless the report keeps it
apart from the subject that was reached and needed nothing. Both contribute zero
migrations; only one of them is good news.

The already-v2 subject is the negative control, and it is checked twice — that
the report calls it `already-green`, and that its file on disk is still the bytes
that were written. `ALREADY_GREEN` is a claim about a tree, so the tree is what
settles it.

### `sandbox_fanout.py` — several real repositories, each in a sandbox of its own

```
python proofs/sandbox_fanout.py --subjects B,C
```

Needs a sandbox provider **and** this repository to be public: each sandbox
installs the package from it. This is the one that costs something to run.

`fanout.py` proves the orchestration with projects it writes itself. This proves
the thing that cannot be faked — several *real* third-party repositories being
migrated at the same time, each in its own Daytona sandbox, by a `bumpsmith`
that was installed there and does not know it is in a sandbox. The whole loop
goes across: clone, read the failure, write the rule, edit, re-run the suite,
keep it only if green.

That is possible because nothing is split. `python -m bumpsmith --sandbox` still
refuses, and is still right to — it would edit a checkout here and test it
there. Installing the package *into* the sandbox puts editing and testing back
on one filesystem, just not this one.

Three things make it a proof rather than a demonstration, and the third is the
one that is hard:

- **A negative control.** Fixture C is already on pydantic v2. It has to come
  back `already-green` *and* with `git status` clean **in the sandbox that ran
  it** — a report and a filesystem are two claims, and a loop that edited it and
  reverted perfectly would produce the same report as one that never touched it.
- **An unreachable subject.** One job points at a port nobody is listening on.
  "Four subjects, none migrated" and "four sandboxes, none reached" are the same
  number and opposite facts; the only way to show the report keeps them apart is
  to make one happen.
- **A count nobody accumulated.** Every figure it prints is derived by
  `bumpsmith.fanout` from the attempts. There is no counter in the script that
  could disagree with the report.

Each subject's environment is recorded in the script rather than guessed, and
the script refuses a fixture it has no measured environment for. A plausible
environment produces a red suite about the environment, and the loop classifies
it as a migration break with total sincerity — which is a convincing-looking run
that proves nothing.

**What it costs, which is worth knowing before you run it.** One sandbox per
subject, each holding a clone of this repository, a clone of the fixture, and an
installed dependency tree. Twenty-two of them exhausted a 30 GiB Daytona quota
on 27 Aug 2026 — call it 1.4 GiB apiece — and the failure that followed is worth
describing, because it is the one a reader is most likely to hit.

Sandboxes outlive the sessions that made them. Deleting a TrueForge session does
**not** delete its Daytona sandbox; the provider's own intervals do, and this
project's are auto-stop after 5 idle minutes, auto-archive 60 minutes later.
Between filling the quota and that archiving, every subject comes back
unreached — correctly, and for a reason that has nothing to do with migrations.

The script says so plainly, and only because of finding 118. Before that fix it
reported `` `success` is None, which is neither true nor false `` while holding
Daytona's actual sentence about disk. A proof whose failure mode is illegible is
a proof that costs an afternoon the first time it fails.

## The recorded runs

`recorded/` holds the output of every script, verbatim — the two harness ones
against TrueForge 0.1.4 with `bedrock-mantle/qwen-3-coder-480b` and `validator.py`
against pydantic 2.12.5, all from 26 August 2026, and `fanout.py` against pydantic
2.12.5 from 27 August. They are committed because a judge
without a harness cannot run the first two, and a claim nobody can check is worth
what it costs to make.

| file | what it shows |
|---|---|
| `sandbox.log` / `sandbox.json` | pytest ran in Daytona and came back `rc=2`; `bumpsmith.failures` read it as `[REGEX_KEYWORD] \`regex\` is removed. use \`pattern\` instead` |
| `validator.log` / `validator.json` | pydantic 2.12.5, eight signatures, all eight as documented — `field`/`config` raise, `values` survives, and `info` is refused under `@validator` |
| `fanout.log` / `fanout.json` | four subjects migrated at once against pydantic 2.12.5 — two migrated, one already green and unedited, and one never reached, reported as `unreached` with the reason rather than folded into the zero |
| `deny.log` / `deny.json` | a real `tool.approval_required` on thread `main`, denied through `TurnChannel`; the session then run to rest — 2 turns, both `done` — and the harness's own MCP server reports **0 tool calls served during the run** |

Neither file was edited. They contain no credentials. The repository and branch
names in them are this project's own and are public — the same policy applied to
`tests/data/approval-call-tool.json`.

Session and turn ids are kept. They are the part a reader can hold against a
harness's own event log, and removing them would leave a transcript that could
have been written by hand.
