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

Cloning never deletes anything. If a destination already holds files the command
refuses and says so; removing a previous clone is a decision for whoever is
running it.

## AI assistant disclosure

Per hackathon rule 11 — "AI coding assistants are allowed, but their use must be
disclosed" — this project is built with the assistance of AI coding tools.

Per rules 12 and 13, the architecture, technical decisions, and review of all
generated code are the author's own. Every part of the submitted system is
something the author can explain and defend.
