# bumpsmith

**An agent that migrates a repository from pydantic v1 to v2 and keeps the
change only once the test suite has come back green.**

It runs the suite, reads the break out of the failure, writes the migration rule
that break implies, finds every site the rule applies to, plans the smallest edit
that carries it out, applies that edit as a revertible transaction, and runs the
suite again — repeating until the suite passes or until it hits something it
cannot do, which it then names.

Afterwards a repository is in one of exactly two states: **changed, with a green
run behind the change — or byte-for-byte what it was.** There is no third state,
and most of the design is in service of that.

---

## Exit code 0 is not a migration

pydantic's own codemod, `bump-pydantic`, has been free since 2023 and does the
mechanical bulk well. Measured on 22 August 2026 against three real repositories
pinned at the commits in [`fixtures.toml`](fixtures.toml), with
`bump-pydantic==0.8.0` and `pydantic==2.13.4`:

| | A `dbt-cloud-cli` | B `emnify-sdk-python` | F4 `connect-eaas-core` |
|---|---|---|---|
| baseline on pydantic 1.x | 31 passed | 24 passed | 347 passed |
| after upgrading pydantic | collection error | collection error | collection error |
| `bump-pydantic` exit code | **0** | **0** | **0** |
| files rewritten | 12 | 3 | 3 |
| lines changed | 53+ / 49− | 324+ / 323− | 65+ / 65− |
| `TODO[pydantic]` markers left | 1 | 1 | **0** |
| **tests recovered** | **0** | **0** | **0** |
| suite afterwards | same error | same error | same error |

**18 files rewritten, 442 insertions, 437 deletions, zero tests recovered, three
suites out of three still red — and it exited 0 every time.**

This is not a complaint about the tool. Its README does not claim to be a
complete migration and the `TODO[pydantic]` mechanism is deliberate: it is
designed to do the bulk and hand back what needs judgement. The honest statement
of the gap is narrower and more useful than "it's broken":

> The codemod does the mechanical bulk, exits 0 whether or not the result works,
> and leaves residue — visibly on some break classes, silently on others. The
> residue is where the suite stays red, and finding it requires running the
> tests.

Running the tests is the step a one-shot transformer cannot take. B is the
sharpest illustration: 324 lines rewritten, zero tests recovered, and the error
moved from `models.py:397` to `models.py:398` — the file changed enough to shift
the failure, not enough to fix it. F4 is the worst case, because there the
residue is *silent*: `from pydantic.utils import DUNDER_ATTRIBUTES` is a removed
internal, and no marker was left behind pointing at it.

To reproduce: clone a fixture at its pinned SHA with `python -m
bumpsmith.fixtures`, install its baseline dependencies and confirm the baseline
count, install `pydantic==2.13.4`, run `bump-pydantic` 0.8.0 over the package
directory, and run the suite again.

## Install

Python 3.13 or newer. **No runtime dependencies** — everything the agent does at
run time is standard library. `REVIEW.md` asks that every added dependency earn
its place, and so far none has needed to.

```bash
pip install -e .
```

The dev extra adds the three tools the checks run — `ruff`, `mypy`, `pytest`,
each pinned to an exact version so a green run here and a green run in CI mean
the same thing:

```bash
pip install -e ".[dev]"
```

Note that pydantic itself is **not** a dependency of either. bumpsmith reads
pytest's output rather than importing the library it migrates, which is what lets
it run against a repository pinned to a pydantic it does not share. Claims about
pydantic's own behaviour are settled by [`proofs/`](proofs/README.md) instead —
by running a real one and recording what it did.

## Using it

```bash
python -m bumpsmith PATH -- <the command that runs its tests>
```

The suite command goes after `--`, because it usually has flags of its own and
`--` is how they get past this command's own parser.

```bash
python -m bumpsmith ./fixtures/B --package emnify -- ./venv/bin/python -m pytest -q
```

| flag | what it does |
|---|---|
| `--package NAME` | a top-level package this repository owns; repeatable. Used only to tell its own missing module from an unmigrated third-party one. Omitting it makes that distinction unavailable, which is reported rather than guessed |
| `--steps N` | how many times the repository may be changed (default 6). The cap is on *applications*, not on runs, so every edit is still verified by a suite run |
| `--timeout SECONDS` | seconds allowed for each run of the suite (default 600) |
| `--json PATH` | also write the full report there, as JSON |
| `--sandbox` | parsed and **refused**, with the reason — see [below](#where-the-suite-runs) |

Exit status is `0` if the suite ends green, `1` if it does not, and `2` if the
run never got far enough to say. `--steps 0` runs the suite and changes nothing.

## One run, verbatim

Against fixture B, a real third-party SDK. Only the two header lines echoing the
path and the suite command are cut; nothing else is.

```
step 1  rc=2  (local)
  break    [ROOT_MODEL] To define root models, use `pydantic.RootModel` rather than a field called '__root__'
  at       emnify/modules/api/models.py:397
  rule     Replace a `__root__` field with pydantic.RootModel
  scan     19 sites in 2 files
  plan     19 sites across 2 files
  applied

step 2  rc=2  (local)
  break    [REGEX_KEYWORD] constr() got an unexpected keyword argument 'regex'
  at       emnify/modules/api/models.py:640
  rule     Rename the `regex=` argument to `pattern=`
  scan     5 sites in 1 file
  plan     5 sites across 1 file
  applied

step 3  rc=2  (local)
  break    [VALIDATOR_FIELD_CONFIG] The `field` and `config` parameters are not available in Pydantic V2, please use the `info` parameter instead.
  at       emnify/modules/device/models.py:25
  rule     Remove a v1 validator's `field` and `config` parameters
  scan     1 site in 1 file
  plan     1 site across 1 file
  applied

step 4  rc=1  (local)
  break    [UNKNOWN] 1 validation error for RetrieveDevice
  at       emnify/modules/device/manager.py:286

reverted -- the edits did not make it pass and were taken back
  the failure classified as UNKNOWN, which does not narrow to one rule; a rule naming the wrong transformation is worse than none
  3 changes, taken back
```

Four things in that are the point of the whole project.

**Each break was invisible until the one above it was fixed.** `__root__` aborts
collection, so pytest never imported the module holding the `constr(regex=...)`
underneath it, and neither of those ever reached the validator below *them*. Not
lower priority — unreachable. That is why this is a loop and not a pass, and it
is also why running the suite is load-bearing rather than a final check: the
suite is the only thing that reveals break *n+1*.

**Each failing test named one site; the rules found twenty-five.** pytest reported
`models.py:397`, one line in one file. The rule that failure implies matches **19
sites across 2 files** — and the gap between those two numbers is the part a human
wants before agreeing to anything. bumpsmith emits a **rule**, not a patch. A
patch says "change line 397"; a rule says "wherever a field is called `__root__`,
that is this break, and here is every place it occurs." Across the three steps
the run reported three sites and edited twenty-five.

**The run changed shape at step 4.** The first three are `rc=2`: collection
failed, so no test ran at all. The fourth is `rc=1` — the package now imports, 24
tests run, and 19 of them pass. The remaining break is a different kind of thing,
a `ValidationError` from a field V1 made optional by implication, and this run
says so by declining to name a rule for it rather than by guessing one.

**It stopped, said exactly what it could not do, and left the repository
byte-for-byte as it found it.** `git status` afterwards is empty. A migration
that leaves a checkout changed and no better is worse than one that changes
nothing, because somebody then has to work out which of the two happened.

## When it stops, it says which thing happened

"bumpsmith could not finish" is never a shrug. Every exit from the loop is one of
eleven members of a `Stop` enum — an enum rather than a message, because the
caller sometimes has to act on the answer and matching on prose is how that goes
wrong quietly.

| `Stop` | meaning | what to do about it |
|---|---|---|
| `GREEN` | the suite passed | nothing; this is the only value that keeps anything |
| `NOT_RUN` | the suite could not be run at all | fix the invocation — this is not a red suite |
| `NOT_A_BREAK` | it failed, but not from a migration break | fix the command, not the code |
| `NOTHING_PARSED` | it failed in a layout this parser cannot read | file the output; the parser needs the sample |
| `NO_RULE` | the failure does not narrow to exactly one transformation | a human decides |
| `DEPENDENCY` | the break is real and no edit to *this* repository removes it | upgrade the dependency |
| `NO_REWRITER` | the rule is known; nobody has written the rewriter yet | the rule is the useful output — take it from there |
| `NOTHING_TO_APPLY` | the rule matched nothing, or nothing that changes when rewritten | check the rule against the tree |
| `NOT_APPLIED` | the edits were refused before anything was written to disk | read the refusal; it names the site |
| `STEP_LIMIT` | the cap was reached and the suite was still red | raise `--steps`, or look at what it kept hitting |
| `WRONG_PLACE` | the suite ran somewhere other than the tree being edited | see [below](#where-the-suite-runs) |

`Stop` says why the loop ended. A separate `Outcome` says what is on disk —
`ALREADY_GREEN`, `MIGRATED`, `REVERTED`, `UNTOUCHED`. They are kept apart because
a caller usually wants one of them and would otherwise have to reconstruct it
from the other, and because the two most different results the loop can produce —
"fixed it" and "changed nothing" — share a `Stop`.

## The break taxonomy

Six classes, numbered by the project's own taxonomy. Three have rewriters; the
rest classify and stop, which is a useful result on its own.

| # | class | what it is | rewriter |
|---|---|---|---|
| 1 | `VALIDATOR_FIELD_CONFIG` | `@validator` taking `field` or `config` | ✅ |
| 2 | *(absent)* | a field V1 made optional by implication and V2 requires | — |
| 3 | `REGEX_KEYWORD` | `regex=`, which V2 renamed to `pattern=` | ✅ |
| 4 | `ROOT_MODEL` | a field named `__root__` | ✅ |
| 5 | `REMOVED_INTERNAL` | an import of a pydantic internal V2 deleted | — |
| 6 | `TRANSITIVE_DEPENDENCY` | a dependency is itself unmigrated | n/a — no edit here fixes it |

**Class 2 is deliberately absent**, and the reason is worth stating because it is
the same reason the loop declines to name a rule at step 4 above. It has a
recorded sample. What it does not have is a *classifier*: the signature is a
`ValidationError` like any other, and no traceback text separates "V1 would have
defaulted this" from "this input really is missing a field". A pattern authored
against an ambiguous signature would misfile real failures while looking like
coverage. Defining the member and guessing is worse than leaving it out.

**Class 1 is the case where pydantic's own error message is wrong.** It says:

> The `field` and `config` parameters are not available in Pydantic V2, please
> use the `info` parameter instead.

Read as instructions, that says to rewrite the signature to take `info`. Under
the `@validator` shim it is wrong — `info` belongs to V2's `@field_validator`,
and the shim refuses a parameter by that name outright. The migration that works
is to *remove* both parameters; `values` still works and still carries what it
did. That is a fact about somebody else's library, so it is checked against
somebody else's library:
[`proofs/validator.py`](proofs/validator.py) builds eight validator signatures
against a real pydantic and exits non-zero if any of them stops behaving the way
`bumpsmith.rules` says it does. A rewriter built from the error message would
have been wrong with a full green suite behind it, because the tests and the code
would have been written from the same misreading.

## How it is put together

Everything is in [`src/bumpsmith/`](src/bumpsmith). Each module states one
guarantee and is tested against that guarantee rather than against its
implementation.

| module | what it guarantees |
|---|---|
| [`migrate.py`](src/bumpsmith/migrate.py) | **the loop — this is the agent.** Edits from every step are held open together and kept only at the end, only once a run has come back green |
| [`failures.py`](src/bumpsmith/failures.py) | pytest output → a structured `Failure`. Dispatches on the return code, not the text, because pytest emits three materially different layouts and the return code names which one you have before parsing begins |
| [`rules.py`](src/bumpsmith/rules.py) | `Failure` → `Rule`, and `Rule` + root → every site. Matched over the AST, never over text: `@validator` appears in strings, comments and docs, and a library may define a decorator of its own by that name. Resolves pydantic's names through imports and `as` aliases |
| [`rewrite.py`](src/bumpsmith/rewrite.py) | `Rule` + sites → `Edit`s. **Text replacement at AST positions, never `ast.unparse`** — a file comes back byte-identical apart from the matched sites. Refuses rather than guesses; every match ends as an edit or a `Skipped` carrying a reason |
| [`apply.py`](src/bumpsmith/apply.py) | `attempt(edits, root)` — all of them land or none do, the originals come back byte for byte, and nothing outside the root is touched. **Reverting is the default**; a caller earns a change by saying `keep()` |
| [`gate.py`](src/bumpsmith/gate.py) | nothing irreversible happens except through here. Fail-closed, no bypass, approval bound to a request fingerprint |
| [`run.py`](src/bumpsmith/run.py) | where the suite runs. `LocalRunner` and `SandboxRunner` behind one protocol. Refuses to turn "the command never ran" into a test result |
| [`harness.py`](src/bumpsmith/harness.py) | TrueForge's `tool.approval_required` → the same `Gate`. The event carries only ids, so the asking message is read back; **a call that cannot be read is denied** |
| [`trueforge.py`](src/bumpsmith/trueforge.py) | the transport, and the only place in the package that opens a socket. Decides nothing about what an event means |
| [`sources.py`](src/bumpsmith/sources.py) | one byte-exact reader honouring PEP 263, shared so encoding handling cannot drift between modules |
| [`fixtures.py`](src/bumpsmith/fixtures.py) | clones the four fixtures from upstream at pinned SHAs and verifies `HEAD`. No vendored code in this repository |

Two design choices carry more weight than the rest.

**Reverting is the default, not the error path.** A tool that edits a repository
and decides afterwards whether that was a good idea has already done the
irreversible part. In `apply.py` an exception, a crash, or simply forgetting all
land in the same place — the tree exactly as it was.

**Edits are text replacements at positions the tree reported.** The obvious way
to rewrite Python with the standard library is to modify the tree and hand it to
`ast.unparse`, and what comes back has every comment gone, every string requoted
and every line rewrapped. The migration would be correct and the diff would be
unreadable, which for a tool whose output a person has to approve is the same as
being wrong.

### Where the suite runs

`bumpsmith.run` makes that a seam. `LocalRunner` uses a subprocess on this
machine and is the default, which is the honest default for a tool you have just
cloned. `SandboxRunner` runs it in the harness's sandbox, and
[`proofs/sandbox.py`](proofs/sandbox.py) demonstrates a real pytest run in
Daytona through nothing but package code.

`--sandbox` on the command line is parsed and **refused**, with the reason. The
sandbox is a different filesystem, so the loop would write its edits here and
verify them there, against code the edits never reached — and a green result
would keep a change that nothing had tested. Carrying the edits across is the
missing piece; until it is written and reviewed, a flag that quietly did it would
be worse than no flag at all.

The refusal is not only in the command. `migrate()` is a public function taking
any `Runner`, so it checks where each run actually happened and stops at
`Stop.WRONG_PLACE` before using a result that came from somewhere the edits are
not — including a runner that reports honestly while the suite is red and
conveniently the moment it goes green. Stating the requirement in a docstring was
the first version of this, and a docstring is not an enforcement.

### Stopping before anything irreversible

Nothing here opens a pull request yet. When it does, it goes through
`bumpsmith.gate`, which owns the call rather than warning about it: a denial is
not an error raised afterwards, it is a call that never happens. There is
deliberately no bypass — no `force=True`, no "approve the safe ones
automatically", no environment variable that turns it off for a while. Each of
those is a way for the guarantee to be true in the tests and false in the run
that mattered.

The harness's own `tool.approval_required` is answered by that same gate, and
[`proofs/deny.py`](proofs/deny.py) proves the refusal against a live TrueForge —
including that the MCP server it would have called reports zero tool calls
served. The claim is about the effect, not the paperwork.

## Verifying it yourself

The suite runs offline, with no harness and no network:

```bash
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
mypy
```

`mypy` runs strict over `src`, `tests` and `proofs`. `ruff` selects the rule
groups [`REVIEW.md`](REVIEW.md) asks for in prose, so the linter and the written
standard say the same thing and a reviewer never has to arbitrate between them.

Then run it against a real repository end to end:

```bash
python -m bumpsmith.fixtures B
python -m bumpsmith ./fixtures/B --package emnify -- /path/to/a/pydantic2/python -m pytest -q
git -C ./fixtures/B status    # empty
```

[`proofs/`](proofs/README.md) holds three scripts that demonstrate things a test
suite on a laptop cannot reach, plus the verbatim output of each from 26 August
2026. [`proofs/validator.py`](proofs/validator.py) is the one that needs no
harness — only an interpreter with pydantic v2 on it.

## The fixtures

bumpsmith is measured against four real repositories rather than against test
doubles, because a pydantic v1-to-v2 migration only breaks in ways that real code
produces. They are **not vendored here**. A vendored copy is a snapshot whose
provenance decays, and the point of a fixture is that somebody else can obtain
exactly the same one:

```bash
python -m bumpsmith.fixtures            # clone all four into ./fixtures
python -m bumpsmith.fixtures B          # just the smallest one, about a second
python -m bumpsmith.fixtures --list     # what they are, without cloning
```

[`fixtures.toml`](fixtures.toml) pins each one to a full 40-character commit SHA
and records the baseline it is expected to produce — the number of tests that
pass *before* any migration is attempted. A fixture whose baseline does not
reproduce is not evidence of anything, so the number is written down rather than
remembered.

| id | repository | pydantic | baseline | role |
|----|------------|----------|----------|------|
| A  | `data-mie/dbt-cloud-cli` | 1.10.10 | 31 passed | breaks loudly |
| B  | `emnify/emnify-sdk-python` | 1.10.26 | 24 passed | smallest; the one to develop against |
| C  | `cloudblue/connect-eaas-core` | 2.13.4 | 347 passed | negative control — already v2, must stay green |
| F4 | `cloudblue/connect-eaas-core` | 1.10.26 | 347 passed | the commit C was migrated from |

**C is the one that matters most**, because it is the one where doing nothing is
the correct answer. It is already on v2, and an agent that "fixes" it is broken.
Measured 24 August 2026: the rules for classes 1, 3 and 4 match **zero sites**
across its 347 tests. A false positive there would be worse than any missed
migration, because the migrations this tool declines are visible in its report
and a wrong edit to working code is not.

Pinning to a SHA is only half of it: a tag can be moved and a branch always
moves, so a SHA is the only reference that cannot change underneath us — but a
reference that cannot change is still worth checking, so every clone ends by
comparing `HEAD` against the SHA that was asked for and fails if they differ.
That is the same reasoning the CI workflow applies to its GitHub Actions, which
are pinned to commit SHAs for the same reason.

Fetching one commit by SHA is the cheap path — 11 MB for the largest fixture
instead of a full history nobody reads — but whether a server will serve an
object it never advertised is the server's decision, not ours. GitHub allows it,
so all four fixtures take that path. A host that refuses gets an ordinary fetch of
every branch and tag instead, and the pinned commit is verified the same way
either way.

Cloning never deletes anything. If a destination already holds files the command
refuses and says so; removing a previous clone is a decision for whoever is
running it.

## What it does not do

Stated plainly, because a tool that is vague about its edges is asking you to
find them yourself.

- **It does not migrate class 2 or class 5.** It classifies class 5 and stops;
  class 2 it does not classify at all, for the reason given above.
- **It does not open pull requests yet.** The gate that will guard that call
  exists and its denial is proven; the call itself is not written.
- **It does not run the suite in a sandbox while editing locally**, and refuses
  to pretend otherwise. See `--sandbox`.
- **It does not retry, and it does not guess.** A failure that does not narrow to
  exactly one rule stops the loop.
- **It does not make fixture B green.** Peeling three breaks takes B from a
  collection error to 24 tests collected and 19 passing, and then it stops. What
  remains is a class-2 break and, behind that, a break that is not a rewrite at
  all but a design decision about model coercion. Anything else would be a claim
  the run does not support.
- **It has no isolation guarantees when run locally.** `LocalRunner` executes a
  test suite from a repository you pointed it at, in a subprocess on your
  machine, and says so rather than implying otherwise.

## Review

This repository's review trail is a deliverable, not a byproduct.

[`REVIEW.md`](REVIEW.md) is the standard it is reviewed against, by people and by
automated review alike — a priority order in which a finding lower on the list
never outranks one above it. [`REVIEW-LOG.md`](REVIEW-LOG.md) is what that review
has actually produced: every finding raised and what happened to it, including
the ones that were **rejected with the measurement that rejected them**, the ones
**deferred with a reason and a link**, and the one that was **missed**.

Nothing there closes silently. A finding closed without a visible disposition is
indistinguishable from one nobody read.

As of 26 August 2026 it holds **65 findings**: 52 raised by automated review, 3
that only a live run against the harness could have raised, and 10 found by the
author before review saw them. The log also names the recurring *shapes* those
findings fall into — a guarantee true only in the cases the tests covered, an
answer good enough for reporting reused for mutating, "I could not tell" reported
as "it did not happen" — because naming a class of mistake is cheaper than
finding it three more times. Two of the entries are that lesson failing: a stale
number was corrected in one file and left standing in two others a `grep` away.

Merges are `--merge`, never `--squash`. Each pull request carries a "here is the
work" commit and a separate "here is what review changed" commit, and squashing
would destroy the evidence that review changed the code.

## Hackathon

Entry for the **TrueForge Agent Harness Hackathon** (WeMakeDevs × TrueFoundry ×
Qodo), 24–30 August 2026. The build window opened at 08:00 London on 24 August
and closes at 20:00 London on 30 August.

Everything committed before the window is tooling only — licence, code-review
integration, and CI plumbing, committed 19–21 August. Per rule 7, no project code
or design work predates the start. The commit history is the record.

## AI assistant disclosure

Per rule 11 — "AI coding assistants are allowed, but their use must be disclosed"
— this project is built with the assistance of AI coding tools.

Per rules 12 and 13, the architecture, technical decisions, and review of all
generated code are the author's own. Every part of the submitted system is
something the author can explain and defend.

## Licence

MIT — see [`LICENSE`](LICENSE). The fixtures are third-party projects under their
own licences and are cloned from upstream, never vendored here.
