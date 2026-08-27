# bumpsmith

**An agent that migrates a repository from pydantic v1 to v2 and keeps the
change only once the test suite has come back green.**

It runs the suite, reads the break out of the failure, writes the migration rule
that break implies, finds every site the rule applies to, plans the smallest edit
that carries it out, applies that edit as a revertible transaction, and runs the
suite again — repeating until the suite passes or until it hits something it
cannot do, which it then names.

Afterwards, every edit it made is either **kept, with a green run behind it — or
taken back byte for byte.** Never half of each, and never kept on the strength of
a run that did not test them. Most of the design is in service of that.

Two things that guarantee does *not* cover are stated where they happen rather
than buried: the suite it runs is not isolated and leaves its own artefacts, and
if something else edits a file mid-run the revert **refuses** rather than
destroying that work. See [what it does not do](#what-it-does-not-do).

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
| `--html PATH` | also write it as a **self-contained page** — the same report, rendered for a person. No network, no scripts, opens from `file://` |
| `--open-pr REMOTE` | after a green migration, offer to push to this remote and open a pull request. The remote is **named, never inferred**, and nothing is pushed without a typed `yes` — see [below](#stopping-before-anything-irreversible) |
| `--pr-branch NAME` | the branch `--open-pr` pushes (default `bumpsmith/pydantic-v2`) |
| `--pr-base NAME` | the branch to open against (default: whatever the remote's HEAD points at) |
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

**It stopped, said exactly what it could not do, and took every edit back.** All
25 rewritten sites are byte-for-byte what they were: `git diff` is empty and so
is `git status`. A migration that leaves a checkout changed and no better is
worse than one that changes nothing, because somebody then has to work out which
of the two happened.

What an empty `git status` does *not* tell you is that the directory is
untouched. This run left seven `__pycache__/` directories behind, and the fixture
gitignores them — so the check that looked like proof of "byte-for-byte" was only
ever proof of "no tracked file changed". Those are the interpreter's, not
bumpsmith's; nothing here claims to restore them, and `git status --ignored` is
the command that shows them.

The count is from a clean reproduction — fresh clone, fresh fixture, nothing
carried over — because the first version of this paragraph named `.pytest_cache/`
as well. That correction was right and its stated reason was not: it blamed a
directory listing still holding the previous day's residue. The actual reason is
better and more useful. pytest writes its cache at `rootdir`, and `rootdir` for
this fixture is **not the fixture** — `fixtures/B` configures no pytest of its
own, so the search walks upward out of it. `.pytest_cache/` could therefore
never have appeared under `git -C ./fixtures/B`, on that day or any other. It
lands wherever the walk stopped: beside this README before the barrier existed,
and in `fixtures/` now that it does. Verified both times by deleting every
cache, running only the fixture's suite, and finding exactly one.

Being right about a claim and wrong about the mechanism under it is its own
defect, and a quiet one — nothing fails, and the next person to reason from the
stated reason gets a different wrong answer. [Whose settings the suite runs
under](#whose-settings-the-suite-runs-under) is what that mechanism turned out
to be worth.

## The report a person reads

`--html PATH` writes the run as one page: the chain being peeled a break at a
time, what pytest blamed against what the rule actually matched, and what became
of the tree. It is the same report `--json` writes — **built from the same
mapping**, so the two cannot become two descriptions of one run that drift apart.

The page exists because a rule is reviewed before it is agreed to, and the thing
worth reviewing is a ratio. pytest named `models.py:397`; the rule matched
nineteen sites across two files. That is the argument for emitting a rule rather
than a patch, and it is easier to see than to read.

Everything on it — repository paths, pytest's output, exception messages, file
names — originates in a repository this process did not write, so every value is
escaped and placed in a text node, never in an attribute, a script, a style block
or a URL. There is no network access and no JavaScript: one file that opens from
`file://`, which is the only form that can be attached to a review or committed
as evidence.

## When it stops, it says which thing happened

"bumpsmith could not finish" is never a shrug. Every exit from the loop is a
member of a `Stop` enum — an enum rather than a message, because the caller
sometimes has to act on the answer and matching on prose is how that goes wrong
quietly. The table below is the list; this sentence used to say how many there
were, and adding one made it wrong.

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
| `FOREIGN_CONFIG` | the suite would be configured from outside that tree | give the repository its own pytest config — see [below](#whose-settings-the-suite-runs-under) |

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
| [`failures.py`](src/bumpsmith/failures.py) | pytest output → a structured `Failure`. The return code is asked first — it is available before any parsing and cannot be confused by message content — but it is not sufficient alone: a collection failure and a Ctrl-C both exit 2, a broken conftest and a misinvoked pytest both exit 4. It narrows each to two candidates and one marker in the text picks between them, so no pattern is ever right about the layout *and* the content at once. Unrecognised is `UNKNOWN`, never a guess |
| [`rules.py`](src/bumpsmith/rules.py) | `Failure` → `Rule`, and `Rule` + root → every site. Matched over the AST, never over text: `@validator` appears in strings, comments and docs, and a library may define a decorator of its own by that name. Resolves pydantic's names through imports and `as` aliases |
| [`rewrite.py`](src/bumpsmith/rewrite.py) | `Rule` + sites → `Edit`s. **Text replacement at AST positions, never `ast.unparse`** — a file comes back byte-identical apart from the matched sites. Refuses rather than guesses; every match ends as an edit or a `Skipped` carrying a reason |
| [`apply.py`](src/bumpsmith/apply.py) | `attempt(edits, root)` — all of them land or none do, the originals come back byte for byte, and nothing outside the root is touched. **Reverting is the default**; a caller earns a change by saying `keep()` |
| [`gate.py`](src/bumpsmith/gate.py) | nothing irreversible happens except through here. Fail-closed, no bypass, approval bound to a request fingerprint |
| [`run.py`](src/bumpsmith/run.py) | where the suite runs. `LocalRunner` and `SandboxRunner` behind one protocol. Refuses to turn "the command never ran" into a test result |
| [`harness.py`](src/bumpsmith/harness.py) | TrueForge's `tool.approval_required` → the same `Gate`. The event carries only ids, so the asking message is read back; **a call that cannot be read is denied** |
| [`trueforge.py`](src/bumpsmith/trueforge.py) | the transport, and the only place in the package that opens a socket. Decides nothing about what an event means |
| [`sources.py`](src/bumpsmith/sources.py) | one byte-exact reader honouring PEP 263, shared so encoding handling cannot drift between modules |
| [`rootdir.py`](src/bumpsmith/rootdir.py) | which configuration would govern the subject's suite. pytest walks *upward* for it, so a repository that configures nothing inherits whatever it sits beneath — and a verdict from the right tree can still not be about it |
| [`fixtures.py`](src/bumpsmith/fixtures.py) | clones the four fixtures from upstream at pinned SHAs and verifies `HEAD`. No vendored code in this repository |

Two design choices carry more weight than the rest.

**Reverting is the default, not the error path.** A tool that edits a repository
and decides afterwards whether that was a good idea has already done the
irreversible part. In `apply.py` an exception, an early return, or simply
forgetting all land in the same place — the tree exactly as it was. That covers
anything which unwinds the stack, which is what a `finally` block covers and the
limit of what it covers: a `SIGKILL` or a power cut leaves the edits on disk,
because nothing runs afterwards to take them back and there is no journal to
recover from.

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

### Whose settings the suite runs under

Running against the right tree is not enough, because pytest does not take its
settings from the tree it runs in. It walks **upward** for the first file that
counts as an inifile — `pytest.ini`, a `pyproject.toml` with
`[tool.pytest.ini_options]`, a `tox.ini` with `[pytest]`, a `setup.cfg` with
`[tool:pytest]` — and whatever it finds sets `rootdir`, `addopts` and
`testpaths`. A repository that configures nothing itself therefore inherits the
configuration of whatever it happens to sit beneath.

That is not hypothetical. `python -m bumpsmith.fixtures` clones into
`./fixtures/` **inside this checkout**, and this checkout sets
`addopts = "-ra --strict-markers --strict-config"`. Same tree, same interpreter,
same command, on a project with one unregistered marker:

| where the subject sits | what pytest does |
|---|---|
| under a checkout that configures pytest | `1 error`, exit **2** — collection aborted on the marker |
| anywhere else | `1 passed, 1 deselected`, exit **0** — a warning |

Only one of those two directions is loud. A *stricter* outside configuration
turns green into red, which costs a wasted migration attempt against a break
that was never a pydantic break. An outside configuration that **deselects** —
`-m "not slow"`, a narrowing `testpaths`, an `--ignore` — runs fewer tests than
the repository's own suite would, so a suite that should have gone red goes
green and the loop keeps the edits. That is `WRONG_PLACE`'s defect by a
different road, and it gets the same treatment: `Stop.FOREIGN_CONFIG`, checked
once before the first run, never after a verdict exists to argue with.

The check is deliberately blunt. Rather than decide which pytest settings are
dangerous — a list that would be wrong the first time pytest grows an option —
an outside inifile that sets **anything at all** is refused, and one that sets
nothing is allowed through. An empty `[pytest]` section is a real and useful
thing: it counts as an inifile, so it stops the walk, while contributing no
settings. That is how a directory of cloned subjects keeps the host checkout
out of them, and `python -m bumpsmith.fixtures` writes exactly such a barrier
into `fixtures/` when it clones.

Of the four fixtures, three configure pytest themselves and are unaffected;
only B does not, which is why the barrier exists. The refusal names the file and
what it sets, because the remedy is one line in the repository being migrated.

### Stopping before anything irreversible

`--open-pr REMOTE` pushes a branch and opens a pull request, and it goes through
`bumpsmith.gate`, which owns the call rather than warning about it: a denial is
not an error raised afterwards, it is a call that never happens.

**The dangerous part is not opening a pull request. It is opening one somewhere
nobody chose.** A migration runs against a clone of somebody else's repository,
so its `origin` is *their* repository — and every convenience the flag could
offer (default to `origin`, infer the base, push and see) points the
irreversible action at the one destination it must never reach. So the remote is
named by you, resolved to its **push** URL before anybody is asked — `git remote
get-url` answers about *fetching*, and a remote with a `pushurl` sends the branch
somewhere the fetch URL never named — and it is that URL the approval shows, the
fingerprint binds, and `git push` is given. Not the remote's name, which
`git remote set-url` could re-point in between. An approval granted for your fork
cannot be replayed against the upstream it was cloned from. A remote that pushes
to more than one place is refused: one approval cannot mean three destinations.

The prompt requires the whole word `yes`. `y` is a refusal, `n` is a refusal, and
so is a run with no terminal attached — a CI job has nobody in it to say no.

**Nothing but the migration goes out**, and staging the right paths is the
smallest part of that. A pull request is a diff against the base, so a checkout
ahead of it would publish whatever else is there — and the suite went green
against `HEAD`, which makes a pull request against anything else a *different
change from the one that was tested*. So `HEAD` must be the base. Anything
already staged is refused, because `git commit` commits the index. Each file is
checked against what the migration first read, because `git add -- path` stages
that file's uncommitted changes too. And an existing branch is refused rather
than reset.

[`proofs/pull_request.py`](proofs/pull_request.py) runs all four answers against
a real bare git repository and checks what reached it each time. It needs no
harness, no network and no credentials. There is
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
git -C ./fixtures/B diff              # empty — every edit taken back
git -C ./fixtures/B status --ignored  # seven __pycache__/ — the interpreter's, not bumpsmith's
```

[`proofs/`](proofs/README.md) holds the scripts that demonstrate things a test
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
- **It does not open a pull request you did not approve**, and treats every
  answer but the word `yes` as no. It also cannot open one for a run that
  reverted: there is nothing on disk to send.
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
- **It does not restore what the test suite itself writes.** The transaction
  covers the edits bumpsmith planned and nothing else. pytest runs directly in
  the checkout, so `__pycache__/`, a `.pytest_cache/` at whatever it resolves as
  rootdir, and anything a suite's own fixtures write all stay where they landed.
  "Taken back byte for byte" is a claim about bumpsmith's edits, not about the
  directory.
- **It does not survive being killed.** Reverting happens as the stack unwinds,
  so a `SIGKILL`, an `os._exit` or a power cut between applying and reverting
  leaves the edits on disk. There is no on-disk journal and no recovery at the
  next start.
- **It will refuse to revert rather than destroy your work.** If something else
  modifies a file after bumpsmith edited it, that file is left alone and the run
  ends with `RevertError`, a `STOP:` on stderr naming the file, and exit code 2.
  The tree is then in a state nobody chose — which is the one case the two-state
  guarantee above does not hold, and it is loud precisely because it cannot be
  made quiet safely.

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
