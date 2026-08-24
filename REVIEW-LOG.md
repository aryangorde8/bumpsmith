# Review log

Every finding automated review has raised on this repository, and what happened
to each one.

This file exists because the pull requests alone do not answer the question a
reader actually has. A finding that was fixed and a finding that nobody read
look identical once the thread is resolved — both show as closed. The
difference is the reasoning, and the reasoning is spread across five pull
requests, or it is here.

It also exists because it caught something. Six findings in, working from
memory, the count was wrong: a third finding on #4 had been missed entirely and
was sitting unaddressed on `main`. Nothing was tracking them. That is what this
file is for, and it is why row 5 below says what it says rather than quietly not
existing.

Findings are recorded whether they were accepted, rejected, or partly both.

| # | PR | Finding | Disposition | Where |
|---|----|---------|-------------|-------|
| 1 | [#2](https://github.com/aryangorde8/bumpsmith/pull/2) | Unverified `.pr_agent.toml` key name | **Rejected** — the file already carried the citation | — |
| 2 | [#3](https://github.com/aryangorde8/bumpsmith/pull/3) | Unpinned GitHub Actions tags | **Fixed**, and further than asked | [`6d32305`](https://github.com/aryangorde8/bumpsmith/commit/6d32305) |
| 3 | [#4](https://github.com/aryangorde8/bumpsmith/pull/4) | Drops additional pytest errors | **Fixed** | [`0612109`](https://github.com/aryangorde8/bumpsmith/commit/0612109) |
| 4 | [#4](https://github.com/aryangorde8/bumpsmith/pull/4) | Exit code 2 mis-mapped | **Fixed** — it was right about the design | [`0612109`](https://github.com/aryangorde8/bumpsmith/commit/0612109) |
| 5 | [#4](https://github.com/aryangorde8/bumpsmith/pull/4) | Malformed multi-error fixture | **Fixed late** — missed at merge, found by audit | [#6](https://github.com/aryangorde8/bumpsmith/pull/6) |
| 6 | [#5](https://github.com/aryangorde8/bumpsmith/pull/5) | Fetch-by-SHA often rejected | **Concern accepted, remedy rejected** | [`e8f1bc7`](https://github.com/aryangorde8/bumpsmith/commit/e8f1bc7) |
| 7 | [#5](https://github.com/aryangorde8/bumpsmith/pull/5) | Duplicate ids cause failures | **Fixed** | [`e8f1bc7`](https://github.com/aryangorde8/bumpsmith/commit/e8f1bc7) |
| 8 | [#7](https://github.com/aryangorde8/bumpsmith/pull/7) | Non-clickable doc references | **Fixed** | this PR |
| 9 | [#7](https://github.com/aryangorde8/bumpsmith/pull/7) | Hardcoded GitHub PR URLs | **Premise accepted, remedy rejected** | this PR |
| 10 | [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | Import scope misresolved | **Fixed** — a real false positive, reproduced | this PR |
| 11 | [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | `pydantic.v1` matched as v2 | **Fixed** — a real false positive, reproduced | this PR |
| 12 | [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | Unstable match ordering | **Fixed** | this PR |
| 13 | [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | Ignores PEP 263 source encoding | **Fixed** | this PR |
| 14 | [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | Eager file list sorting | **Accepted on the measurement, not on the framing** | this PR |

---

## 1 · Unverified `.pr_agent.toml` key name — rejected

The finding argued that `expand_evidence` and `show_context_used` might sit
under the wrong section, would then silently no-op, and cited the PR
description's own admission that the configuration was unverified.

The PR description did say that. The file did not: `.pr_agent.toml` shipped in
that same commit with a link to Qodo's configuration reference and both
documented defaults written next to the keys. The finding read the prose and
not the file it was about.

Both features the keys name have been visibly active in every review since —
evidence blocks are expanded, context sources are listed. That is consistent
with the keys being honoured; it does not prove it, because the same output
could be default behaviour, and establishing causation would cost a review cycle
to observe the difference. Not worth it for a setting whose failure mode is
cosmetic.

## 2 · Unpinned GitHub Actions tags — fixed, further than asked

Actions were pinned to commit SHAs. The finding suggested pinning the `v5` and
`v6` tags that were in use; they were pinned at **v7.0.1 and v7.0.0** instead,
because freezing a version that is two majors stale is not an improvement — it
just makes the staleness permanent.

Pinning without an update path trades supply-chain risk for staleness risk, so
Dependabot was added in the same commit. That was an optional recommendation in
the review, taken because it is what makes the pin maintainable rather than
merely correct.

## 3 · Drops additional pytest errors — fixed

`parse_failures` promised one `Failure` per distinct error in its docstring and
returned a single-element list. `REVIEW.md` states that *partial failure in a
batch must be reported per item*, which is what made this a violation of the
project's own standard rather than a missing nicety.

Fixed by splitting output on collection banners with a trailer boundary, so a
block cannot inherit its neighbour's documentation link.

## 4 · Exit code 2 mis-mapped — fixed, and it was right about the design

This one landed on the central design claim. The parser dispatched on pytest's
return code first, and read `2` as a collection error. pytest documents `2` as
*interrupted*, which is a different thing that can happen for unrelated reasons.

`from_returncode` was replaced with `detect(returncode, output)`: the return code
narrows, and one text marker disambiguates. `4` got the same treatment, since a
broken `conftest` also produces it. The return code is still read first — it is
just no longer asked a question it cannot answer.

## 5 · Malformed multi-error fixture — fixed late

**This finding was missed when #4 merged.** It arrived about half an hour after
the first two on that PR, the fixes for those were already in flight, and
nothing was tracking the set. It surfaced during an audit of the review threads
and is fixed in [#6](https://github.com/aryangorde8/bumpsmith/pull/6).

The finding is half right, and the accurate half is worth having. It said the
test helper's substring splicing could stop the test exercising the trailer
trimming. Measured: it does not — the trimming path was exercised throughout.
The real defect is fidelity. `tests/data/README.md` promises those recordings
are verbatim, and a helper that assembles them into lines pytest cannot emit
breaks that promise.

Measuring it found two impossibilities the finding did not mention: the composed
output carried two `Interrupted:` lines, one of them mid-run followed by a
further collection error, and two `ERRORS` headers. pytest prints each once.

## 6 · Fetch-by-SHA often rejected — concern accepted, remedy rejected

The mechanism is real: whether a server serves an object it never advertised is
controlled by `uploadpack.allowAnySHA1InWant`, which vanilla git defaults to
false.

The conclusion did not survive testing. All four fixtures fetch by SHA from
GitHub at depth 1 — verified cold, twice. Locally, git 2.53 served a non-tip
reachable SHA with all three `uploadpack.allow*SHA1InWant` set explicitly to
`false`; the documented default could not be reproduced at all. So this is
portability to other hosts, not a broken workflow.

The suggested fix — a `ref` field in the manifest plus a bounded deepen loop —
was not taken. **A ref is a moving pointer**, and putting one in the manifest
reintroduces exactly the mutability that pinning to a SHA exists to remove: a
renamed or deleted branch would break the manifest while the SHA stayed
perfectly valid.

Taken instead: fall back to an ordinary fetch of every branch and tag when the
single-commit fetch is refused. No new manifest field. `HEAD` is still verified
against the pinned SHA afterwards, so the fallback can only change how many
bytes it takes to reach the commit, never which commit you end up on.

## 7 · Duplicate ids cause failures — fixed

`fixtures B B` cloned `B`, then reported that the destination was not empty — a
clone failure for what is a typo, reported after half the work was done.

Repeated ids are now refused as a usage error before anything is cloned. Of the
two options offered, the stricter one: silently de-duplicating would hide the
typo, and refusing matches how the manifest already treats an unrecognised key.

Reproducing it turned up something separate — failures were printing before
successes, because a piped stdout is block-buffered and stderr is not. Fixed in
the same commit.

## 8 · Non-clickable doc references — fixed

The README named `REVIEW.md` and `REVIEW-LOG.md` as code spans while the pull
request claimed they were "linked from the README". The text contradicted
itself. They are links now.

## 9 · Hardcoded GitHub PR URLs — premise accepted, remedy rejected

Raised against this file, which is the right place to raise it: a long-lived
record should not rot. The suggested fix was relative links — `../../pull/5`,
which GitHub resolves correctly from a blob view.

Not taken, for a reason specific to what this file is. A review log records
events that happened in **one** repository. Relative links resolve against
wherever the reader is: in a fork, `../../pull/5` points at that fork's pull
request 5, which is either missing or an unrelated change. A link that silently
points at the wrong artifact is worse than one that breaks loudly, and this file
exists precisely to stop findings being confused with each other.

The stated risk is also partly covered already — GitHub redirects old URLs after
a rename or transfer, so the absolute links survive the two most likely cases.

The optional half of the suggestion was taken: commit SHAs are now links too,
which is the navigation this table was actually missing.

## 10 · Import scope misresolved — fixed

The worst of the nine so far, because it broke the guarantee the pull request
made loudest. `_pydantic_names` walked the whole tree, so a `from pydantic
import validator` *inside a function* overruled a module-level `from
mylib.decorators import validator`, and an unrelated decorator was matched as
pydantic's.

Reproduced before fixing: one file, one match, where the correct answer is zero.

Import collection now stops at function bodies. `try`/`except ImportError` and
`if TYPE_CHECKING:` are deliberately *not* skipped — an import wrapped in either
is still a module-level binding, and skipping them would have traded this false
positive for a false negative. There is a test for each direction.

## 11 · `pydantic.v1` matched as v2 — fixed

`pydantic.v1` is v2's bundled copy of the old API. Code importing from it kept v1
behaviour on purpose, so the v2 signature change does not apply to it, and
counting those sites inflates the number with things that are not broken.

Also reproduced first: `from pydantic.v1 import validator` matched, and should
not have.

Being on the compatibility shim is a finding of its own. It is just not this one.

## 12 · Unstable match ordering — fixed

`ast.walk` is documented to yield "in no specified order". CPython happens to be
deterministic, which is exactly why this would have gone unnoticed until it did
not. The match list is read in a pull request diff, so two runs over the same
tree have to produce the same order or the diff is noise. Sorted by path and
line.

## 13 · Ignores PEP 263 source encoding — fixed

A Python file may declare its own encoding via a BOM or a `# coding:` cookie.
Reading everything as UTF-8 marked such a file unreadable, which undercounted
matches *and* reported the scan incomplete — for a file Python itself parses
without complaint. Now read with `tokenize.open`, which is how Python reads it.

## 14 · Eager file list sorting — accepted on the measurement, not the framing

`REVIEW.md` says a speculative performance concern without a measurement is not
a finding, so this was measured rather than argued.

The stated risk — a large memory spike — is not real at any plausible scale; a
few thousand `Path` objects is nothing. What is real is the wasted descent:
walking into a virtualenv only to discard every file inside it is work with a
known-zero yield.

On a tree carrying 8,000 vendored files beside 50 real ones:

| | before | after |
|---|---|---|
| whole scan | 0.364s | **0.005s** |

Taken, with directory-level pruning. The suggestion was right; the reason given
for it was not the reason it holds.

---

## How this stays honest

- A finding is recorded when it is raised, not when it is resolved.
- Rejections are recorded with the reason, in the same detail as fixes. A log
  that only lists what was fixed is a list of compliments.
- Where a finding was tested rather than assumed, the log says what was measured.
- Pull requests are merged with `--merge`, never `--squash`. Each carries a "here
  is the work" commit and a "here is what review changed" commit, and squashing
  would destroy the evidence that the second one exists.
