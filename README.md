# bumpsmith

**An agent that rewrites the pydantic v1 breaks a test suite reports, keeps the
edits only once that suite has come back green, and names whatever it could not
do.**

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

**Four real runs are published at
[aryangorde.com/bumpsmith](https://aryangorde.com/bumpsmith/)** —
three real third-party repositories and one small fixture, rendered from the same
JSON `--json` writes. Three of the four end *without* a migration, which is the
part worth looking at: one reverts three applied edits after meeting a failure it
cannot classify, one finds a site and refuses to rewrite it, and one classifies a
break it has no rewriter for and says so. See
[the recorded runs](#the-recorded-runs).

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
or a URL. The page's two varying attributes are computed rather than quoted: a
CSS class taken from a closed set of outcomes, and a bar width that is an
integer. That distinction is not pedantry — this sentence was false until
[finding 183](REVIEW-LOG.md), because the outcome was being interpolated into a
`class`, escaped and inert but there, and no test disagreed. There is no network
access and no JavaScript: one file that opens from `file://`, which is the only
form that can be attached to a review or committed as evidence.

## The recorded runs

Four runs are published at
**[aryangorde.com/bumpsmith](https://aryangorde.com/bumpsmith/)**,
each one the page above rendered from a real run:

| Run | Repository | Ends |
| --- | --- | --- |
| Three real breaks, then a stop | [emnify-sdk-python](https://github.com/emnify/emnify-sdk-python) | `reverted` |
| One site found, and deliberately not rewritten | [dbt-cloud-cli](https://github.com/data-mie/dbt-cloud-cli) | `untouched` |
| A break with no rewriter, said out loud | [connect-eaas-core](https://github.com/cloudblue/connect-eaas-core) | `untouched` |
| A migration that is kept | a small fixture | `migrated` |

Three of the four end without a migration, and that is the reason they are the
four. A migration tool that always edits something is not reporting what it
found.

The site is built by [`pages/build_site.py`](pages/build_site.py) from the
payloads committed in [`pages/runs/`](pages/runs), which are verbatim `--json`
output with exactly one mechanical substitution — the capturing machine's
absolute path, replaced with a stable name.
[`pages/runs.toml`](pages/runs.toml) records that swap for every run, along with
the commit each was captured against and what each is supposed to demonstrate;
[`tests/test_pages.py`](tests/test_pages.py) asserts that claim against the
payload, so a regenerated run that no longer shows what its blurb says fails the
suite rather than going up as a nicer story than the truth.

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

Eight classes, numbered by the project's own taxonomy. Five have rewriters; the
rest classify and stop, which is a useful result on its own.

| # | class | what it is | rewriter |
|---|---|---|---|
| 1 | `VALIDATOR_FIELD_CONFIG` | `@validator` taking `field` or `config` | ✅ |
| 2 | *(absent)* | a field V1 made optional by implication and V2 requires | — |
| 3 | `REGEX_KEYWORD` | `regex=`, which V2 renamed to `pattern=` | ✅ |
| 4 | `ROOT_MODEL` | a field named `__root__` | ✅ |
| 5 | `REMOVED_INTERNAL` | an import of a pydantic internal V2 deleted | — |
| 6 | `TRANSITIVE_DEPENDENCY` | a dependency is itself unmigrated | n/a — no edit here fixes it |
| 7 | `ITEMS_KEYWORD` | `min_items=`/`max_items=` on a constrained collection | ✅ |
| 8 | `ROOT_VALIDATOR_SKIP` | `@root_validator` with v1's default, which v2 refuses | ✅ |

**Class 8 is the one where the migration is not a rename.** v1 ran a root
validator whether or not field validation had failed. v2 removed that behaviour
rather than renaming it, and refuses to construct the validator without being
told so: `pre=False` — the default — with no `skip_on_failure=True` is a hard
error. So the rewrite adopts the only semantics v2 offers, and the validator no
longer runs when a field above it failed. That is a real behaviour change and
saying otherwise would be wrong.

It is written anyway, for the reason class 1 is: the alternative is code that
does not import at all, and this loop only keeps a migration whose suite ended
green. `pre=True` is untouched — it was legal in v1 and is legal in v2, and in
the repository this was measured against six of the seven uses are that form.
A decorator whose `pre` or `skip_on_failure` arrives through a variable or a
`**kwargs` is reported as a site and left alone, because whether v2 already
accepts it is not a question the source answers.

**Class 7 is the one where the same keyword is broken in one place and merely
deprecated in another.** `conlist(int, min_items=1)` raises a `TypeError` from
Python's argument binding, because v2's `conlist` has no such parameter. But
`Field(min_items=1)` still works in v2 — it renames the argument itself and
emits a deprecation warning. So the rule is scoped to `conlist`, `conset` and
`confrozenset`, and deliberately excludes `Field`: a rule written against the
keyword alone would report sites that are not broken and rewrite code that runs
today. Class 3 draws the same distinction in the opposite direction, where
`Field` is the one that raises — which is why neither rule can be derived from
the argument name.

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
| [`publish.py`](src/bumpsmith/publish.py) | the one irreversible effect the tool has — opening a pull request — and the destination is **never inferred**. The remote is named by the caller, resolved to a *push* URL before anybody is asked, and that URL is what the approval shows and what the fingerprint binds. A migration runs against a clone of somebody else's repository, so every convenience here points the irreversible action at the one destination it must never reach |
| [`run.py`](src/bumpsmith/run.py) | where the suite runs. `LocalRunner` and `SandboxRunner` behind one protocol. Refuses to turn "the command never ran" into a test result |
| [`remote.py`](src/bumpsmith/remote.py) | runs the **whole loop** inside the harness's sandbox — clone, edit, re-run, revert — by installing this package there, so editing and testing land on one filesystem again. Hands back a `Reported`, not a `Migration`, because a summary that survived the sandbox is not the run and should not be typed as one |
| [`fanout.py`](src/bumpsmith/fanout.py) | several subjects migrated at once, each in a tree of its own. **A subject it could not reach is never counted as a subject with nothing to migrate** — the same number, opposite facts. Every figure is derived from the attempts rather than accumulated as the run goes |
| [`harness.py`](src/bumpsmith/harness.py) | TrueForge's `tool.approval_required` → the same `Gate`. The event carries only ids, so the asking message is read back; **a call that cannot be read is denied** |
| [`trueforge.py`](src/bumpsmith/trueforge.py) | the transport, and the only place in the package that opens a socket. Decides nothing about what an event means |
| [`report.py`](src/bumpsmith/report.py) | one run, two renderings. `--html` is built from the same payload `--json` writes and from nothing else, so the page a person reads and the file a machine parses cannot drift into two descriptions of one run |
| [`sources.py`](src/bumpsmith/sources.py) | one byte-exact reader honouring PEP 263, shared so encoding handling cannot drift between modules |
| [`rootdir.py`](src/bumpsmith/rootdir.py) | which configuration would govern the subject's suite. pytest walks *upward* for it, so a repository that configures nothing inherits whatever it sits beneath — and a verdict from the right tree can still not be about it |
| [`fixtures.py`](src/bumpsmith/fixtures.py) | clones the four fixtures from upstream at pinned SHAs and verifies `HEAD`. No vendored code in this repository |
| [`__main__.py`](src/bumpsmith/__main__.py) | the command line — `python -m bumpsmith PATH -- <suite>`. It parses, refuses `--sandbox` with the reason above, and renders what came back. It holds no migration logic at all, which is what lets `migrate()` be driven by a caller that never touches `argparse` — and is why the guarantees that matter are enforced there rather than here |
| [`__init__.py`](src/bumpsmith/__init__.py) | the package's public surface, deliberately almost empty. **Nothing is re-exported**: `bumpsmith.migrate` is both a module and the function inside it, and binding one name to both would make `from bumpsmith import migrate` mean different things depending on import order |

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
would keep a change that nothing had tested.

The way past that was not to carry the edits across. It was to stop splitting.
[`remote.py`](src/bumpsmith/remote.py) installs this package *into* the sandbox
and runs the entire loop there — clone, read the failure, write the rule, edit,
re-run the suite, keep it only if green — so editing and testing land on one
filesystem again, just not this one. The loop does not know it is in a sandbox,
and `LocalRunner` is the correct runner there, because the tree really is local
to the process running it.
[`proofs/sandbox_fanout.py`](proofs/sandbox_fanout.py) does that to two real
third-party repositories at once, each in a Daytona sandbox of its own, and its
output is recorded in [`proofs/recorded/`](proofs/recorded).

So the missing piece is no longer the mechanism. It is a command-line route to
it, and until that exists the flag refuses rather than quietly doing the split
version.

The refusal is not only in the command. `migrate()` is a public function taking
any `Runner`, so it checks where each run actually happened and stops at
`Stop.WRONG_PLACE` before using a result that came from somewhere the edits are
not — including a runner that reports honestly while the suite is red and
conveniently the moment it goes green. Stating the requirement in a docstring was
the first version of this, and a docstring is not an enforcement.

### Whose settings the suite runs under

Running against the right tree is not enough, because pytest does not take its
settings from the tree it runs in. It walks **upward** for the first file that
counts as an inifile, and whatever it finds sets `rootdir`, `addopts` and
`testpaths`. A repository that configures nothing itself therefore inherits the
configuration of whatever it happens to sit beneath.

Seven filenames count, in this order, and the rules are not uniform:

| file | counts when | notes |
|---|---|---|
| `pytest.toml` | always, even empty | pytest 9 |
| `.pytest.toml` | always, even empty | pytest 9 |
| `pytest.ini` | always, even empty | |
| `.pytest.ini` | always, even empty | pytest 9 |
| `pyproject.toml` | `[tool.pytest.ini_options]` is present — **or** `[tool.pytest]` holds something | an empty `[tool.pytest]` is walked past; an empty `ini_options` is not |
| `tox.ini` | `[pytest]` is present | |
| `setup.cfg` | `[tool:pytest]` is present | |

That table was measured against the pinned pytest, not read off a page.
`pytest --collect-only -v` prints `configfile:` and names every file it ignored,
so it will tell you which of several it picked. The first version of this check
knew only `pytest.ini` and would walk straight past a repository that configured
itself in any of the other three dedicated names — refusing it for a
configuration that was not governing it.

`pytest -c FILE` replaces discovery outright: pytest reads that file and puts
`rootdir` beside it, wherever it is. So the check reads the argv too, and judges
the named file instead of walking.

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
nothing is allowed through. An empty `pytest.ini` is a real and useful thing: it
counts as configuration, so it stops the walk, while contributing no settings.
That is how a directory of cloned subjects keeps the host checkout out of them,
and `python -m bumpsmith.fixtures` writes exactly such a barrier into
`fixtures/` when it clones. It must be a **file** — pytest reads configuration
from files, so a directory of that name stops nothing, and a guard that only
asked whether the path existed would report a barrier that was not there.

Only a command that recognisably runs pytest is checked at all: pytest as the
program, or `-m pytest` given to an interpreter. `make pytest` is an ordinary
way to spell a suite command and is left alone, as are `tox` and `uv run` — the
refusal is about pytest's discovery, and one nobody could act on would be worse
than none.

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

## No model decides the rewrite

There is no model inference anywhere in the migration loop. bumpsmith runs the
suite, reads the failure text the suite actually printed, matches it against a
closed set of eight break classes, resolves the affected names in the scope they
are read in, and rewrites those sites. Every one of those steps is deterministic,
and every one of them is tested.

That is a decision rather than an omission, and the reason is the argument this
README opens with. A model asked to transform code will produce a
transformation. What it will rarely do is say *I do not recognise this failure* —
it will write something plausible, the file will still import, the suite may even
pass, and the wrong edit will sit in a diff nobody reads line by line. The
failure this tool exists to prevent is exactly a change that looks finished and
is not, so the rewrite path is the last place to put a component whose
characteristic failure is confident invention. Where the tool cannot narrow a
failure to one rule it stops and reverts, and that is only a meaningful promise
if nothing in the path is willing to guess on its behalf.

What the harness *is* for is the next section: running the suite somewhere safe,
stopping for a person before anything irreversible happens, reaching a real tool
over MCP, and holding a session together while it does. Those are the jobs where
the harness does the work rather than sitting underneath a thin wrapper.

## Where TrueForge fits

The harness is not sitting underneath this project as a model call. Six things
it does here, each with the code that does it and a run that was recorded:

| what the harness does | where | the run |
|---|---|---|
| **Runs the suite somewhere safe.** `SandboxRunner` sends the pytest invocation to the harness's sandbox and reads the result back through the `Exec` protocol | [`run.py`](src/bumpsmith/run.py), [`trueforge.py`](src/bumpsmith/trueforge.py) | [`sandbox.py`](proofs/sandbox.py) — a real Daytona run, come back `rc=2` and classified by `failures.py` as `REGEX_KEYWORD` |
| **Runs the whole agent there.** The package installs into the sandbox, so the loop clones, edits, re-runs and reverts on one filesystem | [`remote.py`](src/bumpsmith/remote.py) | [`sandbox_fanout.py`](proofs/sandbox_fanout.py) — two real third-party repositories, **44.3s wall clock** |
| **Stops for a person.** `tool.approval_required` is answered by the same gate that guards this tool's own effects, and a call that cannot be read is denied | [`harness.py`](src/bumpsmith/harness.py), [`gate.py`](src/bumpsmith/gate.py) | [`deny.py`](proofs/deny.py) — paused, denied, and the MCP server reports **0 tool calls served** |
| **Reaches a real tool over MCP.** The tool is registered with the harness and annotated `destructiveHint`; TrueForge's own default `require_approval_for_tools` selects it with no configuration from us at all | [`mcp_stub.py`](proofs/mcp_stub.py) | the same run, checked against the server the harness would have called rather than one this repository chose |
| **Keeps a session across a reconnect.** `SandboxExec` will adopt a `session_id` it did not create, so a second process holding a stored id reaches the sandbox that session opened, not a fresh one | [`trueforge.py`](src/bumpsmith/trueforge.py) | [`session_reconnect.py`](proofs/session_reconnect.py) — one session read its marker back after the client was **thrown away**; a brand-new session found nothing |
| **Hands work out in parallel.** Several subjects migrated at once, each in a tree — or a sandbox — of its own | [`fanout.py`](src/bumpsmith/fanout.py) | [`fanout.py`](proofs/fanout.py) — **1.85s at one worker, 0.87s at four**, each number from the recording that holds it |

Every one of those has its output committed verbatim in
[`proofs/recorded/`](proofs/recorded), session and turn ids kept, because a judge
without a harness cannot run the ones that need one and a claim nobody can check
is worth what it costs to make. [`proofs/README.md`](proofs/README.md) says what
each needs and what each costs.

**`session_reconnect.py` has a control, and the control has been watched fail.**
It would print *"the session held"* against a harness that pooled its sandboxes,
so `tests/test_session_reconnect.py` runs the script against stand-in harnesses
that share one sandbox, forget one, keep nothing at all, and fail the read
outright, and requires it to fail against every one of them — naming the leg
that failed. Two ways that control could have passed while proving nothing — a
marker whose contents impersonated absence, and a read that reported its own
errors as absence — were Qodo findings on
[#39](https://github.com/aryangorde8/bumpsmith/pull/39), both reproduced before
they were accepted.

**What the harness is not doing here yet.** A README that lists only the wins is
the document this project's review log exists to catch.

- The MCP tool that has been exercised end to end is one whose entire purpose is
  to be **refused**. Nothing here has yet had the harness call an MCP tool and
  then use what came back.
- The fan-out is this package's own concurrency over whole migrations. TrueForge
  has subagent threads of its own — `harness.py` reads their `thread_id`s, and
  learned to, because reading one as a session id produced a live 404 — but no
  work is handed to them.

## Verifying it yourself

The suite runs offline, with no harness and no network:

```bash
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
mypy
```

The site is built and checked offline too:

```bash
python pages/build_site.py --out pages/_site   # renders the recorded runs
```

`mypy` runs strict over `src`, `tests`, `proofs` and `pages`. `ruff` selects the rule
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

As of 29 August 2026 it holds **185 findings**: 137 raised by automated review, 4
that only a live run against the harness could have raised, and 44 the author
found rather than review. "Automated review" is two sources now, not one: Qodo on
every pull request, and a single outside audit of `main` that raised the last
three — logged as its own batch, because a column that quietly changes what it
counts is the same defect as a number that quietly goes stale. **The total** is not maintained by hand —
`tests/test_docs.py` reads the log's own table and fails if this sentence and
that table disagree, and separately fails if the three parts do not sum to it,
because this paragraph has been the stale number twice already.

**The split between those three is maintained by hand, and is not checked.** It
could be, and deliberately is not: the log marks a finding's provenance in prose,
and only when it is *not* Qodo's — a row with no marker is a row nobody marked,
which is not the same fact as a row Qodo raised. A test inferring the first from
the second would be the log's own ninth shape, reading an absence as evidence,
and it would be most confident about exactly the rows nobody had thought about.
So the arithmetic is guarded, the totals are guarded, and the classification is a
claim by the author. This paragraph used to say the whole sentence was checked;
review pointed out that it was not.

The log also names the recurring *shapes* those
findings fall into — a guarantee true only in the cases the tests covered, an
answer good enough for reporting reused for mutating, "I could not tell" reported
as "it did not happen" — because naming a class of mistake is cheaper than
finding it three more times. Two of the entries are that lesson failing: a stale
number was corrected in one file and left standing in two others a `grep` away.

Merges are `--merge`, never `--squash`. Each pull request carries a "here is the
work" commit and a separate "here is what review changed" commit, and squashing
would destroy the evidence that review changed the code.

## Qodo Code Review Evidence

Every substantive change here went through a pull request that Qodo reviewed
before it merged. Nothing was pushed to `main` directly, and no branch was
squashed, so the review and the response to it both survive in the history.

**Representative pull request:
[#20 — *The pull request the pitch promises, and only where somebody said*](https://github.com/aryangorde8/bumpsmith/pull/20).**
Qodo raised **eleven findings** on it in its first pass, every one in `publish.py` — the module whose
opening paragraphs argue for never inferring where a pull request is sent, and
which then inferred it in three separate places. It found that `git remote get-url`
returns the **fetch** URL while `git push` uses `pushurl`, so the approval named a
destination the push would not use; that the gate fingerprinted the URL while the
push used the mutable remote *name*; and that `gh pr create` was passed no `--repo`,
so it would have opened the pull request against the repository the migration was
cloned from — somebody else's. All eleven were fixed in a second commit on the same
branch, which is what the `--merge` policy exists to preserve.

**The follow-up review, and what it cost.** Qodo posts one review per pull request
and does not re-review after a push, so a follow-up has to be asked for:
`/agentic_review`, commented on the pull request. Run against #20 on 27 August it
re-reviewed the final commit `c7f5d75` — and raised **four more findings**, on code
that had been merged for a day. Three of them are the same shape as the original
eleven: the publishability check compares blob *text*, so an untracked file, a
trailing-newline change and a mode change each pass a guard whose whole claim is
that nothing but the migration goes out. The fourth is worse and is about the gate:
`propose()` validates HEAD, the index and the targets *before* the blocking
approval prompt, and nothing revalidates them after it. That is a window with a
human in it.

All four are fixed, each with a guard that was verified by breaking it. Two more
things surfaced on the way: `_git_or_none` strips its output, so the contents
comparison had never seen the bytes it compared; and the test fake's
`dict(committed or {...})` meant a test describing an *untracked* target was
handed a default map with the file present, so the case could not be written at
all. The point of keeping this paragraph is that the follow-up review is not a
formality — it found real defects in merged code, which is the argument for
requiring one.

**Two rounds against the final code:
[#32](https://github.com/aryangorde8/bumpsmith/pull/32) and
[#33](https://github.com/aryangorde8/bumpsmith/pull/33)**, the last two merges.
Qodo raised **nine** findings between them on its first pass. Three on #32 were
one defect wearing three faces: every rule resolved names against a single
file-wide import map, so a `conlist` shadowed in a class body, bound by a
comprehension, or imported inside a class was still read as pydantic's. The same
map was behind an already-merged rule and a third that review never mentioned —
fixed at the root, for all four consumers, which is finding 139's lesson applied.
The worst was on #33: `@root_validator(skip_on_failure=False)` was handed a
*second* `skip_on_failure=True` rather than having the first one changed. That
one is worth saying plainly, because `ast.parse` accepts a repeated keyword
argument and `compile` does not — so the tool's own re-parse could not see it,
and the migration would have written a file that does not import.

Asked for a second review against the fix, Qodo returned **five more findings,
every one of them inside the first round's own fix**: a walrus rebinding it did
not count, a nested class handed its enclosing class's namespace, sequential
class-body binding — raised on both pull requests, from opposite directions —
and `global`/`nonlocal` misread as shadowing. All fourteen are fixed, each
reproduced before it was accepted; Qodo marked the first round's threads resolved
on the re-review. The pair is the clearest evidence in this repository that a
follow-up review is not a formality: the second round found real defects in code
whose only purpose was to fix the first.

**Four rounds on one resolver:
[#35](https://github.com/aryangorde8/bumpsmith/pull/35).** The scope walk #32
and #33 rebuilt turned out never to have traversed **PEP 695 type parameters**,
so `class C[T: conlist(str, min_items=1)]` lost a site that the `ast.walk` it
replaced had found. The fix for that raised two findings on the next review, the
fix for those raised one more, and the fix for that one raised another — four
rounds, each against the previous round's own change, and each one real. The
middle pair fail in the direction that costs the most: the type parameter names
were subtracted while walking the bases and then the class body was started from
the *unfiltered* map, so `class C[conlist]` shadowed the import above the body
and nowhere inside it. The tool would have reported a call that is not
pydantic's and rewritten code that has nothing to do with the migration.

Half of one report is recorded as **rejected**, and that half is why this
paragraph is here rather than a line in the log. The third round offered
`nonlocal` as the case analogous to `global`; Python refuses it outright —
`nonlocal binding not allowed for type parameter` — so the code being described
cannot be written and there is no test to write for it. The `global` half was
right, and its fix came out *wider* than the report: an ordinary class-body
shadow with no type parameter anywhere was wrong in exactly the same way and is
fixed by the same change, which is the tell that the defect was the missing
model rather than the type-parameter code. Both halves are answered in the
thread on the pull request as well as in the log.

**Three rounds on the code that publishes this evidence:
[#36](https://github.com/aryangorde8/bumpsmith/pull/36).** Qodo raised **four
findings** on the first pass — three in the generator and one on the manifest it
reads, none anywhere near the migration loop. The worst was not subtle: `build()` recursively removed whatever
path `--out` named before recreating it, so `--out .` typed once would have
destroyed the repository rather than failed. Reproduced before it was accepted —
a directory holding `source.py` came back holding five HTML files and no
`source.py`.

The second review returned **two more, and both were inside the first round's
own fixes.** The guard added for the `rmtree` writes a `.bumpsmith-site` marker
and refuses a directory that has none — but `Path.is_file()` follows symlinks,
so a link named `.bumpsmith-site` pointing at any regular file anywhere
satisfied it, and the guard written to stop `rmtree` reaching a directory it did
not create handed over exactly such a directory. The slug pattern added to stop
a run escaping the output directory accepts `index`, so a run named that
overwrites the gallery's own page and leaves a site whose only entry point is
the page that replaced it. Both are one shape — **a guard asking a question
whose answer it does not control** — and naming the shape is what the log is
for. The third review came back with nothing.

**The whole trail, as of the merge of #37.** Thirty-seven pull requests; Qodo
reviewed every one; thirty-two raised at least one inline finding, **129 in
total**. Every finding is in [`REVIEW-LOG.md`](REVIEW-LOG.md) with what happened
to it and why.

**Two numbers in this README were both 129, and they never checked each other.**
One is threads on GitHub, anchored to #37's merge and counted by the loop below;
the other is rows in a file, attributed to automated review by hand in a split
this README already says is not verified. They have since come apart — the three
findings Qodo raised on #39 took the second past it, and it has kept moving,
while the first, being anchored, stayed where it was. That is what a coincidence does and a
reconciliation does not, and it is why reading the match as a cross-check would
have been the log's recurring **shape 3**: an answer good enough for one question
reused to settle a stronger one. The paragraph is kept, rather than deleted with
the coincidence, because a reader who saw those two numbers agree is owed the
reason they no longer do.

The trail sentence is anchored to a named merge on purpose. The log's total
cannot go stale — a test reads [`REVIEW-LOG.md`](REVIEW-LOG.md)'s own table and
fails when the README and the table disagree — but these numbers live on GitHub,
not in the repository, and the first version of that sentence went stale the
moment the next pull request merged. A count with no date is a claim about now,
and it was wrong about now within a day, twice. Anchored, it ages instead of
lying.

Re-deriving it is one loop, anchored to the same merge the sentence is, and it
prints the sentence:

```
repo=aryangorde8/bumpsmith
cutoff=$(gh api repos/$repo/pulls/37 --jq .merged_at)
for n in $(gh api --paginate "repos/$repo/pulls?state=closed&per_page=100" \
           | jq -s --arg c "$cutoff" \
               'add | map(select(.merged_at != null and .merged_at <= $c)) | .[].number'); do
  f=$(gh api --paginate repos/$repo/pulls/$n/comments \
      | jq -s 'add | map(select(.user.login | startswith("qodo"))
                       | select(.in_reply_to_id == null)) | length')
  cov=$(gh api --paginate repos/$repo/issues/$n/comments \
        | jq -s 'add | map(select(.user.login | startswith("qodo"))) | length')
  echo "$n $f $cov"
done | awk '{ prs++; findings += $2; if ($2 > 0) withf++; if ($2 + $3 > 0) reviewed++ }
            END { printf "%d pull requests, %d reviewed by Qodo, %d with at least one inline finding, %d findings\n",
                         prs, reviewed, withf, findings }'
```

```
37 pull requests, 37 reviewed by Qodo, 32 with at least one inline finding, 129 findings
```

Five details in there were each raised as a finding on the version of this
paragraph that lacked them, and they are five coats on one mistake.

**It asks twice per pull request.** Five of the thirty-seven have zero inline
findings, and zero from `/pulls/N/comments` is the same answer for *Qodo
reviewed this and found nothing* as for *Qodo never reviewed this* — opposite
facts, and the sentence above asserts the first for all thirty-seven. That five
was four through two earlier re-anchorings, which is finding 164's whole point:
a figure that survives a change it should have moved with reads as confirmation
and is nothing of the kind. Coverage
comes from `/issues/N/comments`, where Qodo posts a summary either way.
Collapsing the two is `REVIEW-LOG.md`'s ninth shape, *"I could not tell"
reported as "it did not happen"*.

**Both queries paginate, and both filter with `jq -s` rather than `--jq`.**
GitHub returns thirty comments a page, so a summary on page two came back as
zero — the same false *never reviewed*, reintroduced by the fix for it. And
`--paginate --jq '… | length'` evaluates the filter once per page and prints a
count for each, so a two-page thread prints `30` then `4` rather than `34`: a
different number that looks exactly like the right one.

**It loops.** The claim is an aggregate over thirty-seven pull requests, and a
command that answers for one of them is not a procedure for checking it.

**It stops where the sentence stops.** Anchoring the claim to a merge and then
checking it against *everything merged since* is two halves that disagree: the
moment the next pull request lands, the loop returns a larger number and appears
to refute a sentence that is still true. The cutoff is #37's own `merged_at`, and
the filter is on **merge time** rather than pull request number, because those
are not the same order.

**It enumerates the whole history rather than a recent window.** `gh pr list
--limit 200` returns the *most recent* two hundred and then the cutoff is applied
to those, so once two hundred more pull requests have merged the anchored set
falls out of the window and the loop reports a smaller total — silently, and
about a claim written to be permanent. Paginating `pulls?state=closed` and
dropping the unmerged ones has no window at all.

A test that ran this in CI was considered and rejected: it would fail when the
network is down and pass when a cache is stale — wrong in both directions, and
reassuringly wrong in the second.

**A second representative pull request, for the loop rather than the depth.**
[#30 — *The README understated the project*](https://github.com/aryangorde8/bumpsmith/pull/30)
is smaller than #20 and shows the whole cycle inside one pull request. Three
findings were self-found by reading this README cold against the criteria it is
judged on: a stale claim that survived the pull request which fixed its twin
elsewhere, a module table listing twelve of eighteen files, and the counts above.
Qodo then raised two findings **on the fix** — the completeness guard filtered
`__*.py` while the sentence it defends says *everything*, so it enforced a
narrower claim than the README makes; and the helper returned a set, so neither
check could see a duplicate row. Both were fixed, and fixing the first turned up
a third map of the package inside `__init__.py` listing nine of eighteen. The
follow-up `/agentic_review` then found that the uniqueness check had been added
to one of the two tables that make the claim, and the second `/agentic_review`
against `026d73c` came back **Bugs (0)** with every finding marked ✓ Resolved.
Six findings, three rounds, and the defect the pull request is *about* recurred
twice inside its own fix.

**What was intentionally dismissed.** Three findings were rejected rather than
fixed, each with the measurement that rejected it rather than an opinion. The
substantive one is
[finding 20](https://github.com/aryangorde8/bumpsmith/pull/10#discussion_r3846315678) (High): Qodo held
that `cast("Approver", ...)` would fail CI because mypy type-checks `tests/`.
`typing.cast` takes a string as a forward reference by design, mypy flags only an
*undefined* one, and CI had already passed on the commit under review — so the
claim was tested rather than argued, and declined. The other two were a citation Qodo
could not see in the file it was reading, and an unbounded-growth claim answered
with the arithmetic — 460 bytes a decision, a million records for 439 MiB, at a
rate bounded by human attention — where the remedy was worse than the condition,
because trimming an audit trail drops the oldest denial first.

## Hackathon

Entry for the **TrueForge Agent Harness Hackathon** (WeMakeDevs × TrueFoundry ×
Qodo), 24–30 August 2026. The build window opened at 08:00 London on 24 August
and closes at 20:00 London on 30 August.

Everything committed before the window is tooling only — licence, code-review
integration, and CI plumbing, committed 19–21 August. The rules require that "the
coding and design work itself has to happen between the 8:00 AM London start on
August 24 and the deadline"; no project code or design work predates the start,
and the commit history is the record.

## AI assistant disclosure

"AI coding assistants are allowed, but their use must be disclosed" — this
project is built with the assistance of AI coding tools.

The rules also require that participants "understand the submitted code and be
able to explain the agent, the project architecture, and the technical decisions
behind it". The architecture, the technical decisions, and the review of all
generated code are the author's own; every part of the submitted system is
something the author can explain and defend.

## Licence

MIT — see [`LICENSE`](LICENSE). The fixtures are third-party projects under their
own licences and are cloned from upstream, never vendored here.
