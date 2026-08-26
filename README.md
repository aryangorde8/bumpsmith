# bumpsmith

Entry for the **TrueForge Agent Harness Hackathon**, 24–30 August 2026.

---

## Status: in progress

The build window opened at **08:00 London on 24 August 2026** and closes at
**20:00 London on 30 August**. Everything before the window is tooling only —
license, code review integration, and CI plumbing, committed 19–21 August. Per
hackathon rule 7, no project code or design work predates the start. The commit
history is the record.

A full README with setup steps, a demo video, and a write-up lands before the
deadline.

## Using it

```
pip install -e .
python -m bumpsmith PATH -- <the command that runs its tests>
```

The suite command goes after `--`, because it usually has flags of its own and
`--` is how they get past this command's own parser.

```
python -m bumpsmith ./fixtures/B --package emnify -- ./venv/bin/python -m pytest -q
```

That is the whole agent. It runs the suite, reads the break out of the failure,
writes the migration rule that break implies, finds every site the rule applies
to, plans the smallest edit that carries it out, applies that edit as a
revertible transaction, and runs the suite again — and it keeps the changes only
once a run has come back green.

Here it is against fixture B, a real third-party SDK, unabridged:

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
  rule     Replace a v1 validator's `field` and `config` parameters with v2's `info`
  scan     1 site in 1 file

reverted -- the edits did not make it pass and were taken back
  no rewriter is written for VALIDATOR_FIELD_CONFIG; the rule is still the useful output, but it cannot be applied automatically
  2 changes, taken back
```

Two things in that are the point of the whole project.

**The second break was invisible until the first was fixed.** `__root__` aborts
collection, so pytest never imported the module holding the `constr(regex=...)`
underneath it. Not lower priority — unreachable. That is why this is a loop and
not a pass.

**It stopped, said exactly what it could not do, and left the repository
byte-for-byte as it found it.** `git status` afterwards is empty. A migration
that leaves a checkout changed and no better is worse than one that changes
nothing, because somebody then has to work out which of the two happened. Every
way the loop can end is one of ten named reasons, so "bumpsmith could not finish"
always says *which* thing happened and whether the next move is to write a rule,
fix the pytest invocation, or upgrade a dependency.

Exit status is `0` if the suite ends green, `1` if it does not, and `2` if the
run never got far enough to say. `--json PATH` writes the same report as JSON.
`--steps 0` runs the suite and changes nothing.

### Where the suite runs

`bumpsmith.run` makes that a seam. `LocalRunner` uses a subprocess on this
machine and is the default, which is the honest default for a tool you have just
cloned. `SandboxRunner` runs it in the harness's sandbox, and
[`proofs/sandbox.py`](proofs/sandbox.py) demonstrates a real pytest run in
Daytona through nothing but package code.

`--sandbox` on the command line is parsed and **refused**, with the reason. The
sandbox is a different filesystem, so the loop would write its edits here and
verify them there, against code the edits never reached — and a green result
would keep a change that nothing had tested. That is the defect `bumpsmith.run`
exists to prevent, one level up. Carrying the edits across is the missing piece;
until it is written and reviewed, a flag that quietly did it would be worse than
no flag at all.

### Stopping before anything irreversible

Nothing here opens a pull request yet. When it does, it goes through
`bumpsmith.gate`, which owns the call rather than warning about it: a denial is
not an error raised afterwards, it is a call that never happens. The harness's
own `tool.approval_required` is answered by that same gate, and
[`proofs/deny.py`](proofs/deny.py) proves the refusal against a live TrueForge —
including that the MCP server it would have called reports zero tool calls
served. See [`proofs/`](proofs/README.md).

## The fixtures

bumpsmith is measured against four real repositories rather than against test
doubles, because a pydantic v1-to-v2 migration only breaks in ways that real
code produces. They are **not vendored here**. A vendored copy is a snapshot
whose provenance decays, and the point of a fixture is that somebody else can
obtain exactly the same one:

```
python -m bumpsmith.fixtures            # clone all four into ./fixtures
python -m bumpsmith.fixtures B          # just the smallest one, about a second
python -m bumpsmith.fixtures --list     # what they are, without cloning
```

`fixtures.toml` pins each one to a full 40-character commit SHA and records the
baseline it is expected to produce — the number of tests that pass *before* any
migration is attempted. A fixture whose baseline does not reproduce is not
evidence of anything, so the number is written down rather than remembered.

| id | repository | pydantic | baseline | role |
|----|------------|----------|----------|------|
| A  | `data-mie/dbt-cloud-cli` | 1.10.10 | 31 passed | breaks loudly |
| B  | `emnify/emnify-sdk-python` | 1.10.26 | 24 passed | smallest; the one to develop against |
| C  | `cloudblue/connect-eaas-core` | 2.13.4 | 347 passed | negative control — already v2, must stay green |
| F4 | `cloudblue/connect-eaas-core` | 1.10.26 | 347 passed | the commit C was migrated from |

Pinning to a SHA is only half of it: a tag can be moved and a branch always
moves, so a SHA is the only reference that cannot change underneath us — but a
reference that cannot change is still worth checking, so every clone ends by
comparing `HEAD` against the SHA that was asked for and fails if they differ.
That is the same reasoning the CI workflow applies to its GitHub Actions, which
are pinned to commit SHAs for the same reason.

Fetching one commit by SHA is the cheap path — 11 MB for the largest fixture
instead of a full history nobody reads — but whether a server will serve an
object it never advertised is the server's decision, not ours. GitHub allows it,
so all four fixtures take that path. A host that refuses gets an ordinary fetch
of every branch and tag instead, and the pinned commit is verified the same way
either way.

Cloning never deletes anything. If a destination already holds files the command
refuses and says so; removing a previous clone is a decision for whoever is
running it.

## Review

[`REVIEW.md`](REVIEW.md) is the standard this repository is reviewed against,
by people and by automated review alike. [`REVIEW-LOG.md`](REVIEW-LOG.md) is
what that review has actually produced: every finding raised, and what happened
to it — including the ones that were rejected, with the reasoning, and the one
that was missed.

## AI assistant disclosure

Per hackathon rule 11 — "AI coding assistants are allowed, but their use must be
disclosed" — this project is built with the assistance of AI coding tools.

Per rules 12 and 13, the architecture, technical decisions, and review of all
generated code are the author's own. Every part of the submitted system is
something the author can explain and defend.
