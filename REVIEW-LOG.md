# Review log

Every finding raised on this repository — by automated review, or by running the
thing against something real — and what happened to each one.

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
| 15 | [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | Encode errors skip rollback | **Fixed** — reproduced | this PR |
| 16 | [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | Encoding mismatch corrupts restore | **Fixed** | this PR |
| 17 | [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | Symlink edit replaces the link | **Fixed** — reproduced | this PR |
| 18 | [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | CRLF round trip not exact | **Fixed** — reproduced | this PR |
| 19 | [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | Verify/apply race window | **Fixed** | this PR |
| 32 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | Wrapper named instead of the tool — *raised by the live harness* | **Fixed** — reproduced twice, before and after | this PR |
| 33 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | `mcp:unknown` reported as an attribution — *raised by the live harness* | **Fixed** | this PR |
| 34 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | A failed send re-asks, so a refusal can become an approval | **Fixed** — my own test pinned the bug | this PR |
| 35 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | No production path constructs the bridge | **Accepted, deferred to the transport PR** — [#14](https://github.com/aryangorde8/bumpsmith/pull/14) found the same gap for `exec`; both land together | — |
| 36 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | Policy keyed to the model-facing alias, not the tool | **Fixed** — and the reason is worse than the finding said | this PR |
| 37 | [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | A reused call id suppresses a real call | **Fixed** | this PR |
| 38 | [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | A test helper substituted a valid answer for the invalid one under test — *found by another test* | **Fixed** | this PR |
| 39 | [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | Sandbox runner is never wired | **Accepted** — the same gap as 35, from the other side. Deferred to #15 | — |
| 40 | [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | A sandbox timeout is reported as never having run | **Fixed** — the module breaking its own stated guarantee | this PR |
| 41 | [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | A timeout leaves what the command started running | **Fixed** — and the reason is worse than the finding said | this PR |
| 42 | [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | Output that is not UTF-8 escapes the contract | **Fixed** | this PR |
| 43 | [#15](https://github.com/aryangorde8/bumpsmith/pull/15) | A `thread_id` was used as a session id — *raised by the live harness* | **Fixed** — the test agreed with the bug | this PR |
| 44 | [#15](https://github.com/aryangorde8/bumpsmith/pull/15) | A truncated response claims the command never ran | **Fixed** — `IncompleteRead` is not an `OSError` | this PR |
| 45 | [#15](https://github.com/aryangorde8/bumpsmith/pull/15) | The poll deadline is not a deadline | **Fixed** — a 300s limit could block for hours | this PR |
| 46 | [#15](https://github.com/aryangorde8/bumpsmith/pull/15) | Version drift retried ninety times and reported as patience | **Fixed** | this PR |
| 47 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | The report counted a plan that was refused as a change made — *found by its own exhaustive test* | **Fixed** — `applied` is recorded, not derived | this PR |
| 48 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | The deny proof checked a file at a path the two processes never agreed on — *self-found* | **Fixed** — it now asks the server the harness names | this PR |
| 49 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | A missing dependency was reported as an unmigrated one — *found by the clean-clone test* | **Fixed** — the message now says only what it knows | this PR |
| 50 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | Reverting overwrote a file somebody else had changed | **Fixed** — the revert now checks before it writes | this PR |
| 51 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | A suite that never ran exited like a failing one | **Fixed** — and a test was pinning the contradiction | this PR |
| 52 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | An incomplete scan or plan was applied and reported as a migration | **Accepted in part** — still applied, no longer reported as finished | this PR |
| 53 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | The denial proof checked the effect before the agent had finished reacting | **Fixed** — it waits for the session to settle | this PR |
| 54 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | A failed sandbox setup could still be recorded as a successful proof | **Fixed** — setup must succeed and the break must be the right one | this PR |
| 55 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | Cumulative stub state attributed to the current run | **Fixed** — baselined, and nothing is deleted | this PR |
| 56 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | `migrate()` would keep local edits verified in a sandbox | **Fixed** — the loop checks where each run happened | this PR |
| 57 | [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | `inf` and `nan` passed the timeout check | **Fixed** — a bound has to be finite | this PR |
| 58 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | The class-1 rule told you to write `info`, which pydantic refuses — *found by asking pydantic instead of reading its error* | **Fixed** — the rule says remove, and `proofs/validator.py` is the run behind it | this PR |
| 59 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | `BreakClass` said class 3 had no recorded sample, three lines above the class 3 that had two — *self-found* | **Fixed** — and class 2 now has a sample named, with why it still has no classifier | this PR |
| 60 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | The README said the loop ends one of ten ways; there were eleven — *self-found* | **Fixed** — stale since `WRONG_PLACE` landed in #16 | this PR |
| 61 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | The use check could not see `locals()["field"]`, so the deletion looked safe | **Fixed** — a body that can reach its locals by name is refused | this PR |
| 62 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | The proof accepted an exception type without the reason it was claiming | **Fixed** — stage, type and message, all three | this PR |
| 63 | [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | `globals` sat in the dynamic-scope guard, which refused safe sites with a false reason — *self-found re-reading the fix for 61* | **Fixed** — a parameter is a local and the module namespace does not hold one | this PR |
| 64 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | `migrate.py` said the loop names one of *nine* things; there were ten — *self-found, a sibling of 60 that 60 did not look for* | **Fixed** — the number is gone; the enum is the count | this PR |
| 65 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | `proofs/README.md` gave the suite as 448 tests; it was 453 — *self-found* | **Fixed** — the number is gone, and it was never the point of the sentence | this PR |

Rows 20–31 are described in the sections below rather than listed here; they
arrived in groups and the group is the unit that makes sense of them.

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

## 15–19 · Five on the transaction, three of them reproduced

The apply-and-revert module states three guarantees. Review found that **each
one was false in a case the tests did not cover**, which makes this the most
useful round so far.

| the claim | what actually happened |
|---|---|
| the revert is byte for byte | a CRLF file came back **LF** |
| nothing outside the root is touched | a symlink was **destroyed** and its target left unedited |
| all of them land or none do | the first edit **stayed applied** after a later one failed |

Each was reproduced before being fixed.

**18 · CRLF.** `tokenize.open` wraps the file in a TextIOWrapper with universal
newlines, so `\r\n` was read as `\n` and written back as `\n`. The revert changed
the file — in the one operation that has to be exact. The existing
byte-for-byte test passed because it used LF. Reading is raw bytes now, decoded
with the detected encoding, and writing does not translate either.

**17 · Symlink.** The write renames a temporary file over the path, which
replaces a symlink itself rather than what it points at, while the check read
*through* the link. The content verified and the object changed were not the
same thing. Symlinks are refused.

**15 · Rollback bypass.** `UnicodeEncodeError` is a `ValueError` and a bad codec
name raises `LookupError`; neither is an `OSError`, so both escaped the rollback
path. Both are refused up front now, and the handlers cover all three.

**16 · Encoding not verified.** Only the text was compared, so an edit built
with the wrong encoding verified and then wrote different bytes.

**19 · Verify/apply race.** `before` was documented as checked "at the moment of
applying" and was in fact checked in an earlier pass. Each file is now re-read
immediately before it is written, and the documentation says what the code does.

### Two bugs the fixes introduced, caught by their own tests

Worth recording, because the fix is not automatically safer than the defect.

`latin-1` and `iso-8859-1` are one codec, and `detect_encoding` does not always
return the spelling the caller used — so comparing them as strings rejected an
edit **for being written correctly**. Fixed by comparing canonical codec names.
Then the same comparison in the second location was missed, and the just-in-time
check rejected it again. Both now go through one function.

## 20–22 · Three on the approval gate, one of them real

The round where two of three were argued down. Both rejections were tested
before being rejected, because "I disagree" and "I checked" are different claims.

**21 · A refusal that left no trace. Accepted, and the crash was the smaller
half.** `Gate.run` computed the request's fingerprint outside any guard, so a
`detail` value that would not serialise raised `TypeError` instead of
`NotApprovedError`. Reproduced:

```
ESCAPED as TypeError: Object of type object is not JSON serializable
effect called : 0
history       : []   <- the refusal left no trace
```

The effect was correctly never called — fail-closed held. What did not hold was
the trail: **the gate refused something and recorded nothing**, which is the one
failure this project has spent a week punishing elsewhere. `Request` now rejects
a non-string detail where it is written, and the fingerprint call in `run` is
guarded as a backstop that records the refusal.

This is the third instance of the same shape: an exception escaping the path
that was supposed to handle it. Finding 15 was `UnicodeError` slipping past an
`OSError` handler; the surrogate filename bug in this PR was found by looking for
it deliberately; this one was found by review. Worth naming as a class rather
than fixing three times.

**20 · "Bad cast breaks mypy." Rejected — the claim is false.** The finding says
`cast("Approver", ...)` "will fail CI because mypy is configured to type-check
`tests/`". `typing.cast` accepts a string as a forward reference by design.
Tested rather than asserted:

```python
good = cast("Real", object())       # accepted
bad  = cast("NoSuchType", object()) # error: Name "NoSuchType" is not defined
```

mypy flags the second, which proves it is evaluating the string rather than
ignoring it, and accepts the first. CI had already passed on the exact commit
under review. The suggested edit would also move away from ruff's own `TC006`,
which prefers the quoted form.

**22 · "Unbounded history memory growth." Rejected, with the arithmetic.**
Literally true — `_records` has no cap. Measured: **460 bytes per decision**, so
439 MiB needs a million records. Every record is one irreversible outward action
that a human answered a question about. The rate is bounded by human attention,
not by loop speed.

The proposed remedy is worse than the condition. Trimming an audit trail drops
the **oldest denial first** — the record most likely to be the one that matters.
A gate that quietly forgets what it stopped is a gate with no evidence it ever
stopped anything. Export exists already (`Record.as_dict`); a cap does not, and
will not.

## 23–27 · Five on the rewriter, all accepted, all one root cause

The most useful round since the transaction. Five separate findings that are the
same sentence said five ways:

> **`rules.py` resolves names well enough to *count* sites. `rewrite.py` used the
> same answer to *change code*, and those are different questions.**

Reading imports is the right way to count. An import is evidence about the file
whatever block it sits in, and over-counting a site costs a line in a report.
Changing a base class needs the harder question — not what the imports imply, but
what the name still means at the line being edited — and getting that wrong
changes code that was working.

**24 · A rebound base was rewritten. Reproduced exactly as reported.**

```python
from pydantic import BaseModel
from mylib import Other

BaseModel = Other          # rebound: no longer pydantic's


class Items(BaseModel):    # a NON-pydantic class
    __root__: list[int]
```

The rewriter changed `Items`' base to `RootModel`. **That is the
search-and-replace failure this machinery exists to prevent, committed by the
machinery itself** — and the docstring one module over claims name resolution is
"what separates a rule from a search-and-replace".

**25 · An import is not a guarantee the name still means that.** `from pydantic
import RootModel` followed by `RootModel = Other` set `already_imported`, which
skipped the collision check entirely and emitted a class inheriting the
replacement.

**26 · `RootModel, other = pair()` binds `RootModel`.** Binding collection read
only bare `Name` targets, so unpacking went unseen.

**27 · An import under `if TYPE_CHECKING:` binds nothing at runtime**, and one
inside a class body binds an attribute. Either could be selected as the import to
extend, producing a file that raises `NameError` while defining the very class
that had just been rewritten.

**23 · Two declarations on one line: one dropped, both counted.** Sites were keyed
by line rather than grouped by it. Rare enough to be unreachable in ordinary code
and worth fixing anyway, because the failure mode is a file left half-rewritten
and reported as complete.

### The fix, stated once

A name is trusted only when it has **exactly one** module-scope binding and that
binding is the pydantic import it claims to be. **Two bindings is a refusal, not a
tie-break.** Bindings now include unpacking, loops, with-items and except
handlers, and exclude class bodies, which have their own namespace. The import to
extend must be a direct child of the module body.

Verified against real fixture B afterwards: same 19 sites, same 5 sites, still
`complete=True`. Strictness that refused real code would have been a worse bug
than the one it fixed.

## 28–31 · Four on the regex class, all accepted

Two of these are the *same shape as 23–27, in a module the previous round did not
touch*, which is worth stating plainly rather than quietly fixing: getting scope
and binding right is not a thing this project has done once and finished.

**29 · A function parameter was treated as pydantic's. Reproduced.**

```python
from pydantic import constr


def build(constr):                    # a PARAMETER
    return constr(regex=r"^a$")       # matched, and would have been rewritten
```

One module-wide import map was applied to every call in the tree. It is wrong in
both directions — it misses a pydantic import made inside a function, and it
claims a shadowing parameter is pydantic's. The second is the dangerous one, and
it is the same failure as finding 24 wearing different clothes.

Resolution is now scoped: calls are paired with the names actually visible where
they sit. Both directions have tests, including one proving that shadowing inside
a function does not disqualify sites outside it — refusing the whole file would
have been its own bug.

**28 · `removed-kwargs` does not identify one break.** Measured against pydantic
2.12.5: `const` and `unique_items` raise the same slug.

```
const          -> PydanticUserError  code='removed-kwargs'
unique_items   -> PydanticUserError  code='removed-kwargs'
```

Classifying on the slug alone would write a regex rule for a `const` failure,
find whatever `regex=` sites happened to exist, rewrite them, and leave the
argument that actually stopped collection untouched. The slug is still checked
first; it is now required to name `regex` as well. **This is the one slug in the
set that is not authoritative on its own**, which the module docstring now says.

**31 · A stdlib-shaped substring is not an interpreter root.** The fix in #12
tested for `/lib/pythonX.Y/` anywhere in the path, so a project holding its own
`lib/python3.13/` directory would have had its frames skipped and reported a
shallower culprit or none. pytest prints project files relative to rootdir, so
the discriminator is not the substring but whether the run had to *leave the
project* to reach the file. Both recorded interpreters still classify correctly.

Worth noting this is a finding against a fix from the same PR — the fix for the
stdlib culprit was itself too broad. Rounds 15–19 recorded the same lesson.

**30 · Two sites on one line, one gone since the scan.** The survivor stood in
for both: two reported rewritten, one written, plan `complete`. That combination
is worse than either half, because it looks like success. Occurrences are matched
to keywords one-to-one now, and any excess is a `Skipped`.

### Knowingly deferred

`_validator_sites` resolves names the same module-wide way and has the same
exposure. It is **not** fixed here, for a stated reason: nothing rewrites that
class yet, so the consequence is a miscounted report rather than changed code. It
is fixed when the validator rewriter lands, which is when it starts to matter.
Recording it so that finding it later is a confirmation rather than a discovery.

## 32–33 · Two the harness raised before the reviewer saw them

Different provenance from everything above, and worth the distinction: these two
were not raised by a reviewer reading a diff. `harness.py` was written from
TrueForge's own wire schema, its tests passed against events built from that
schema, and then it was pointed at the running harness. The harness disagreed.

**32 · The name in the approval event is not the name that runs.** A tool the
harness has not put in the model's context is called through the harness's own
`call_tool` wrapper. The `tool_info` on that call says `truefoundry-system` /
`call_tool`, truthfully. What would actually run is in the *arguments*:

```json
{"mcp_server": "irreversible-things",
 "tool_name": "open_pull_request",
 "input": {"repository": "aryangorde8/bumpsmith", "branch": "...", "title": "..."}}
```

The module believed `tool_info`, so the first live run produced:

```
action   harness.tool_call:call_tool
summary  run call_tool from truefoundry-system on thread main
         (arguments: input, mcp_server, tool_name)
```

Every deferred call on the machine describes itself that way — listing a
directory and opening a pull request are the same sentence. The harness itself
does not work this way: `DeferredTool.toolCallInfo` resolves the wrapper before
approval is decided, so the pause was earned by `open_pull_request`'s
`destructiveHint` while the event reported the wrapper. Reading only `tool_info`
means describing a different tool from the one the harness stopped.

After the fix, the same call on a second live run:

```
action   harness.tool_call:open_pull_request
summary  run open_pull_request from mcp:irreversible-things on thread main,
         reached through the harness's call_tool
         (arguments: branch, repository, title)
```

`arguments` still carries the wrapper's own string untouched — that is the text
the harness parses, and re-encoding it would show a human one string while the
harness acted on another. Only the argument *names* in the summary come from
`input`.

**33 · An attribution that is present, well-formed and worth nothing.** The same
recording holds a call the harness could not resolve to a server:

```json
"tool_info": {"type": "mcp", "name": "open_pull_request",
              "server_id": "unknown", "server_name": "unknown"}
```

`mcp:unknown` reads like a server name. Two servers can publish the same tool
name, so an origin that cannot be trusted is an origin that cannot be reported.
It is now unreadable, and therefore denied. This also refuses a server somebody
deliberately named `unknown`; the two cannot be told apart from here, and
inventing an attribution is the worse failure of the two.

Both live runs, the event stream, and the `tool.response` the harness recorded
are in `tests/data/approval-call-tool.json`, and the module is tested against
that recording rather than only against events written by hand.

## 34–37 · Four on the harness bridge, three fixed here

**34 · A failed send could turn a refusal into an approval.** The highest-value
finding in this round, and the test I wrote for it asserted the wrong thing.

`_deny()` sent the event and *then* remembered the answer, so a `Channel` failure
left nothing remembered. The next poll re-read the same question and asked the
approver again — and an approver with a human or a clock behind it does not have
to answer the same way twice. A transport failure could therefore overturn a
refusal that had already been recorded as `denied` in `gate.history`. The trail
and the action would disagree, which is the worst version of this bug rather than
a variant of it.

My reasoning at the time is in the commit: *"nothing is known to have reached the
harness, and the safe reading of an undelivered refusal is that it still needs
delivering."* That is true about *delivery* and I used it to justify forgetting
the *decision*. They are two pieces of state and I had one.

`test_an_undelivered_denial_is_not_remembered_as_delivered` asserted
`bridge.answered == {}` after the failed send — it pinned the defect in place and
passed. The replacement uses an approver that says no once and yes afterwards, so
the test fails if anything asks twice.

Decisions are now remembered when they are made; delivery is tracked separately;
a retry re-sends the decision already taken and never re-asks. Both directions
are tested, because the rule is about decisions and not about which answer looks
dangerous.

**36 · The alias is not the identity — and it moves.** `describe()` keyed the
policy action to `function.name`, the model-facing name, while `tool_info.name`
is the tool's name on the server that runs it. The finding called this a benign
alias hiding a destructive tool. It is worse than that. From
`packages/trueforge-core/src/core/mcp/toolNames.ts`, the harness derives the
model-facing name by

- replacing every character outside `[a-zA-Z0-9_-]` with `_`,
- truncating to 64 characters, and
- **appending an ordinal (`name1`, `name2`, …) when two servers publish the same
  name.**

So the alias is assigned partly by which servers happen to be registered, and in
what order. A policy keyed to `create_pull_request1` is a policy that can come to
mean a different server's tool after an unrelated connector is added. The pair
that does not move is the tool's own name plus the server it is on, and that is
what `action` and `origin` now carry; the alias is recorded as `called_as` when it
differs, so nothing is hidden.

This is finding 32 again, in the other direction. Twice in two rounds: **the name
that is easiest to reach is not the name that identifies what runs.**

**37 · One id, two questions.** Deduplication was keyed on `tool_call_id` alone,
so a second, distinct pending call reusing that id was returned as `repeated`,
was never read, never gated, never answered — leaving a real call paused with
nothing in the record. Tool call ids come from the model; nothing guarantees
they are unique, least of all across threads.

The key is now the thread, the id **and** the event that asked. A collision on
the first two with a different third is denied rather than decided, because the
harness addresses a decision by thread and call id — an approval meant for one of
two colliding calls could release the other, and only a refusal is safe to send
into that ambiguity. The same id on a *different thread* is a different question
and is decided on its own merits; there is a test for each.

### 35 · No production wiring — accepted, and deferred on purpose

True as stated: this PR ships the deciding and a one-method `Channel`, and
nothing in the package constructs a bridge, polls TrueForge, or sends
`user.tool_approval`. The live proof in the PR body was driven by a script in a
scratch directory, which is exactly the finding's point.

The remedy is not to relax the separation — keeping decisions free of transport
is why they can be tested against a recorded event stream, and why the module
cannot quietly grow a retry loop around an approval. The remedy is the transport
itself: an HTTP client and the poll loop, in the package, rather than bolted onto
this diff. Recorded here so that a reader who checks finds a plan rather than a
gap.

**Amended 26 Aug.** [#14](https://github.com/aryangorde8/bumpsmith/pull/14) was
expected to carry that transport and does not. Building the sandbox seam first
turned up the same gap from the other side — `bumpsmith.run` decides what an
`exec` result *means* and takes the transport as a protocol, exactly as
`harness.py` does for approvals — and both need the same session, turn and poll
machinery. Writing it twice would be the wrong shape, so it is written once, in
the PR after this one, and serves both. The gap now stands against two merged
modules instead of one, which is worse than the original entry claimed and is
the reason to say so here.

---

## 38 · A test that was testing nothing, caught by the test next to it

`bumpsmith.run` exists to keep two things apart: a command that ran and failed,
and a command that never ran. The first is a test result. The second is a
sandbox outage, and reading it as the first would report a suite with no
failures — which would be kept, and recorded as verified.

So the module refuses a long list of malformed answers, and the tests walk that
list. One entry is `None`: the harness said nothing at all. The helper that
replays a prepared answer took it as a default:

```python
def __init__(self, answer: object = None, ...):
    self.answer = answer if answer is not None else _ok()
```

`_ok()` is a *valid* result. The one case written to prove that nothing becomes
a `Completed` was quietly handed something that becomes a `Completed`, and it
had been passing for exactly as long as it existed.

What found it was not review. It was
`test_no_bad_answer_ever_becomes_a_result`, which asserts the property over
every malformed shape at once instead of one `pytest.raises` per case. A
per-case test would have gone green here: `pytest.raises(NeverRanError)` around
a helper that returns a valid answer fails loudly, but only because the
substitution happened to be visible — and the parametrised case that *did*
fail pointed at the payload, not the helper. The aggregate test is what made
the pattern obvious across two failures at once.

Recorded because it is the same shape as finding 34, where my own test held a
real defect in place. Twice now the test has been the thing that was wrong, and
both times what caught it was a second test asserting the guarantee rather than
the mechanism. That is worth more than the fix: a suite where every test checks
one case is a suite that can be wrong in one case, silently.

---

## 39–42 · Four on the runner, three fixed here

### 39 · Never wired — accepted, and the second time

True as stated: nothing in the package constructs an `Exec`, so no real suite
rerun happens in the sandbox. This is finding 35 seen from the other side, and
recording it as a fresh discovery would be dishonest — the PR body said so
before Qodo did.

What is new is that it now stands against **two** merged modules. `run.py` takes
its transport as a protocol for exactly the reason `harness.py` takes a
`Channel`: the decision is testable against a recorded stream, and the module
cannot quietly grow a retry loop around it. That was the right call twice and it
has the same debt twice. The transport is written once, in #15, and serves both.
Two is the limit; a third module taking a transport it does not have would stop
being a design and start being a habit.

### 40 · The module breaking its own guarantee

`bumpsmith.run` exists to keep "ran and failed" apart from "never ran". Its
transport handler was:

```python
except Exception as exc:
    raise NeverRanError(f"the sandbox could not be reached: {exc!r}") from exc
```

`NeverRanError` promises, in its own docstring, that "the working tree is
untouched by anything this run did, because it did nothing." Daytona is
configured with `exec_timeout_ms: 60000`. A command that ran for a minute in the
sandbox and then had its request abandoned would arrive here and be described to
the caller as never having started — a false claim, and one a caller could
retry on, running twice something whose first run had already done everything.

The fix puts the classification where the knowledge is. Only the transport can
tell whether a request was in flight, so a `RunError` it raises now passes
through unchanged, and the `Exec` protocol documents that a transport giving up
mid-flight should raise `TimedOutError`. Everything else is still read as never
having started, because the safe reading of "I do not know" is that it did not.

Worth naming plainly: this is the second time a defect in this project was the
module contradicting a guarantee written in its own docstring. Prose stating a
property is not the property.

### 41 · Worse than reported: cleanup that kills the caller

The finding says a timed-out suite can leave descendants running — true, and it
matters more here than "Medium" suggests, because a surviving pytest worker
writes to the same checkout `bumpsmith.apply` is about to revert. That is the
"tree in a state nobody chose" that `RevertError` exists to prevent, arriving
by a route the transaction cannot see.

Then the fix was measured, and the finding was understating it. Reverting
`start_new_session` and running the new orphan test did not produce a failure.
It produced **no output at all**: the run terminated, and so did the shell around
it. Without its own session the child sits in the *caller's* process group, so
`os.killpg` aimed at "the command's group" is aimed at pytest, the agent, and
everything else sharing it.

So the isolation and the group-kill are not a mechanism plus a precaution. They
are one mechanism, and holding only half of it is not degraded cleanup but a
self-kill. `_end_process_tree` now refuses to signal the caller's own group and
falls back to killing the single process, so the coupling is safe by
construction rather than by whoever edits it next remembering. Both halves are
tested, including one test whose entire assertion is that the process reached
the next line.

### 42 · Output that was never text

`text=True` decodes with the locale's encoding and a strict error policy. A
project printing bytes that are not valid UTF-8 — a test dumping binary, a
traceback naming a file whose name never was text — raised `UnicodeDecodeError`
straight past a contract promising either a `Completed` or a `RunError`.

`gate.py` already reasons about exactly this, down to surrogates arriving from
`os.fsdecode`, so the codebase knew the hazard and this module did not inherit
the knowledge. Output is now captured as bytes and decoded with a pinned
encoding and `errors="replace"`: losing a byte to U+FFFD costs a character in a
diagnostic, and raising costs the run. Pinning it also means the same suite
reads the same way here and in the sandbox, which the locale-dependent version
did not guarantee.

---

## 43 · A thread is not a session, and the test said it was

Found by running the deny proof against a live harness after the unit tests had
passed. `POST /sessions/main/turns` → `404 Session not found: main`.

An approval event carries a `thread_id`, and a `thread_id` looks exactly like
something that belongs in the URL. It is not. A thread is a conversation
*inside* a session — the root one is called `main`, and subagents get their own
— so the session has to come from whoever started it.

`Client.send` read the session out of the event, with a comment explaining that
asking the caller for it again "invites the two disagreeing." That reasoning was
confident and wrong: the two are not two spellings of one thing.

The test did not catch it because the test agreed with it:

```python
event = {"type": "user.tool_approval", "thread_id": "sess-9", ...}
assert path == "/api/v1/sessions/sess-9/turns"
```

A `thread_id` of `sess-9` is not a value the harness produces. The fixture
committed in #13 has carried `"thread_id": "main"` since the day it was
recorded, and nothing read it.

**This is the third time in this project a test has held a defect in place**
(34, 38, and now 43). The pattern is the same each time: the test and the code
were written together, from the same wrong idea, so agreement between them
proved nothing. What broke the tie twice was a property asserted over many
shapes at once, and this time it was a live run — evidence from outside the
author's head, either way.

The fix is not a corrected URL. `Client` no longer implements `Channel` at all;
`TurnChannel(client, session_id)` does, and it cannot be constructed without
being told which session. The mistake is now unavailable rather than documented,
and the `thread_id` still travels in the payload where the harness reads it.

---

## 44–46 · Three on the transport, all fixed

### 44 · The guarantee, escaping through a gap in the type hierarchy

`Client.call` caught `urllib.error.HTTPError` and `OSError`. `response.read()`
can also raise `http.client.IncompleteRead`, and:

```
IncompleteRead -> HTTPException -> Exception          # not an OSError
```

So it escaped `call`, escaped `SandboxExec` (which catches `TransportError`),
and reached `run.py`, whose fallback reads an unknown exception as
`NeverRanError` — the one classification that is unsafe to be wrong about.
Reproduced before fixing:

```
-> NeverRanError: the sandbox could not be reached: IncompleteRead(7 bytes read)
```

A partial read happens most often while reading a *turn* back, which is after
the command was accepted and possibly after it finished. So the answer was not
merely wrong, it was wrong in the direction that invites running an irreversible
command twice.

Two fixes, because one was not enough. `call` now catches
`http.client.HTTPException`. And `SandboxExec` grew a final `except Exception`
that reads anything unclassifiable as `TimedOutError`, so the guarantee no
longer depends on having enumerated every exception `urllib` can raise. The
asymmetry is the argument: guessing "may have run" costs a retry nobody took,
guessing "never ran" costs a command run twice.

This is **recurring shape 1** for the fourth time in this project — an exception
escaping the path meant to handle it. It keeps happening at boundaries where one
library's hierarchy meets another's.

### 45 · A deadline that was only consulted between the waits

```python
deadline = self._now() + self._poll_limit
while self._now() < deadline:
    yield self.turn_events(turn)      # up to 90 requests, 120s timeout each
```

`turn_events` retries an empty body up to ninety times, each with the full HTTP
timeout and a sleep between. Worst case is 90 x (120 + 1) seconds — a little
over three hours — inside a loop whose stated limit is three hundred seconds.
The deadline was real and the thing it was supposed to bound never saw it.

The deadline is now passed down, each request is capped at the time remaining,
and a call with nothing left is refused rather than attempted. Tested with a
fake clock, asserting the request count rather than elapsed time: the fixed
version makes at most six requests where the old one makes ninety.

### 46 · Drift retried until it looked like patience

A live turn answers `GET .../events` with an **empty body**. That is the
documented transient case and the reason the retry exists. But the retry caught
everything: a payload that was a list, an object with no `data`, a `data` that
was not a list, a list of things that were not events. All of them were retried
ninety times and then returned as `[]`.

An empty list is what a caller gets when a turn has not produced an event yet.
So a permanent disagreement about the wire format — a version drift — was
indistinguishable from a slow turn, and would surface much later as a generic
command timeout with nothing pointing at the cause.

Now only `None` is retried. Anything else is validated and raises
`ProtocolError`, including a non-event inside the list, which was previously
dropped by a comprehension — and which would be exactly the event explaining why
a turn did not do what it was asked. An empty `data` list is returned as the
real answer it is.

## 47 · A plan is not an application, and the report said it was

Self-found, by the test written to look for exactly this class of thing. No
reviewer saw it; it did not survive to a pull request.

`bumpsmith.migrate` reports how many steps changed the repository. The first
version derived that from each step's plan:

```python
@property
def applied(self) -> bool:
    return self.plan is not None and bool(_writes(self.plan))
```

Which is a reasonable thing to believe. A plan holds the edits, the edits change
files, so a step with edits changed files. It follows from everything except
what actually happens: `bumpsmith.apply.attempt` verifies a whole edit set
before writing any of it and can refuse the lot — an edit whose file is a
symlink, or has changed since the plan was made, or lives outside the tree. When
it refuses, nothing is written. The plan is unchanged, and it still says two
files.

So a run that touched nothing reported `reverted -- 1 change, taken back`, and
`Outcome` is computed from that same count. The report described a repository
that had been changed and put back, when the repository had never been touched.

The exhaustive test found it. Not one of the tests aimed at `NOT_APPLIED` — the
table-driven one that runs every way the loop can end and asserts, for each, that
the tree is either changed-with-a-green-run or byte-identical. The `NOT_APPLIED`
row asserted `UNTOUCHED` and got `REVERTED`, which is how a property test earns
its length: nobody had thought to check what the *report* said in the case where
the *disk* was obviously fine.

`Step.applied` is now recorded, set on the one line in the package after which a
repository is different from how it was found:

```python
except ApplyError as exc:
    steps.append(step)
    return _Stopped(Stop.NOT_APPLIED, f"the edits were refused: {exc}")

steps.append(replace(step, applied=True))
```

This is shape 3 again — *an answer good enough for reporting, reused for
mutating* — running backwards. There the resolution that could correctly count
sites was used to rewrite them. Here the plan that correctly describes an
intention was used to report an event. Both are one value asked a question it
was never the answer to.

Verified by reverting the fix: the `not-applied` case fails and every other case
still passes, which is the shape of a defect that only one row could see.

---

## 48 · A proof that could check the wrong process

Also self-found, while moving the proof scripts into the repository.

`proofs/deny.py` ends by asserting that the tool it denied never ran, which it
did by checking that `pr-calls.log` did not exist. The file is written by
`mcp_stub.py`, a *separate process*, at a path relative to whatever directory
that process was started in. The two never agreed on it by construction; they
agreed because the same person launched both from the same directory.

A checker looking in the wrong place finds nothing, and finding nothing is what
this one reports as success. It would have passed most confidently in exactly the
situation where it knew least — the same failure mode as finding 46, in a
different costume.

The stub now answers `GET /calls` with what it actually served, and the proof
reads the URL to ask **out of the harness's own MCP manifest**. The server being
questioned is therefore provably the one the harness was configured to call,
rather than one on a port the script guessed. Being unable to reach it is
reported as "nothing is proven" and exits non-zero; it is never reported as "the
tool did not run". The file check is kept as a second, independent signal.

## 49 · "Unmigrated" was a guess wearing a fact's clothes

Found by running the new command from a clean clone, which is the test it was
written to make possible, on the first try.

Fixture B in a fresh environment has no `requests` installed. pytest reported
`ModuleNotFoundError: No module named 'requests'`, `bumpsmith.failures`
classified it `TRANSITIVE_DEPENDENCY` — correctly, since `requests` is not a
package this repository owns — and `write_rule` produced:

> A dependency of this repository is itself unmigrated.

Which is one of two possible readings and the message picked it without saying
so. The module was not unmigrated; it was not installed. Both look identical in
pytest's output, and nothing in the text distinguishes them.

The classification is right and unchanged. What was wrong was the sentence: a
user reading it would go looking for a pydantic-related pin to bump, when the
answer was `pip install requests`. The rule now names both possibilities, says
the message cannot tell them apart, and says the fix is outside this repository
either way — which is the part that is true regardless.

Pre-existing, from the class-6 work in #8. It sat unnoticed because until this
pull request there was no way to run the pipeline that would print it. That is
most of the argument for the pull request.

## 50–57 · Eight on the loop and its proofs

The largest round so far, and the one where the findings are mostly *about the
composition* rather than about a module. That is what a loop is: eight things
that were each individually fine and one of them wrong once they ran together.

Seven accepted outright. One accepted in part, with the reasoning below.

### 50 · The revert checked the door on the way in and not on the way out

`_apply` re-reads every file immediately before writing it and refuses if the
content changed since the plan was made — because the check and the write are
not the same moment, and anything that moved in between would be silently
overwritten. `_restore` wrote `edit.before` back unconditionally.

The asymmetry was invisible while `attempt` was only ever used the way its own
tests use it, inside a `with` block a few milliseconds long. `bumpsmith.migrate`
holds every transaction open across every later run of the suite, so
"between apply and revert" became minutes of a test run executing against the
same checkout. Anything writing to it in that window — a developer, a formatter
on save, a fixture with a bad path — got its work thrown away by a cleanup that
believed it knew what was there.

The revert now re-reads first. A file that no longer holds what the transaction
put there is left alone and named in the `RevertError`. Deleting the file counts
as a change too, so `before` is not resurrected over it. Every other file in the
transaction is still restored.

This is worth saying plainly: **reverting is supposed to cost nothing, and
destroying somebody's work is not nothing.** The module's headline promise was
true about our own edits and false about everyone else's.

### 51 · A suite that never ran exited like a failing one

`main`'s docstring said `2` means the run never got far enough to say. `Stop.NOT_RUN`
is exactly that — a missing interpreter, a timeout, a sandbox that could not be
reached — and it returned `1`, indistinguishable from a red suite.

The whole of `bumpsmith.run` exists to keep those apart, and the process's exit
status is where that distinction most needs to survive: automation that cannot
tell a failing test from an absent one retries the wrong thing.

**The fourth time a test has held a defect in place** (34, 38, 43, and now this).
`test_a_suite_that_cannot_be_started_exits_one_rather_than_pretending` asserted
`1` and was *named* for it, so the contradiction between the docstring and the
code had a test defending the wrong side. `Stop.WRONG_PLACE` (finding 56) exits
`2` for the same reason and is grouped with it.

### 52 · An incomplete migration reported as a finished one — accepted in part

The finding asked the loop to stop before applying whenever `ScanResult.is_complete`
or `Plan.is_complete` is false.

**The premise is accepted and the remedy is not.** Refusing to apply would make
the tool useless on the repositories it is for: one vendored file that will not
parse, or one matched site the rewriter declines, and a migration that would
have worked is refused entirely. A suite that goes green is real evidence about
the tests that exist, and the right response to partial knowledge is not to
throw away the part that worked.

What was genuinely wrong is that the report let "the suite passes" stand in for
"the migration is finished". Those are different claims and only one of them was
being made. `Migration.complete` is now a property beside `outcome`, false when
any candidate file went unread or any matched site went unchanged, and the
command prints `NOT COMPLETE` above the step detail that says which. The JSON
carries it too.

Same family as finding 34 and finding 46: not a wrong answer, an answer to a
question nobody asked, standing where the answer to a different one belonged.

### 53 · "Not yet" reported as "never"

The deny proof delivered the refusal and immediately asked the MCP server
whether its tool had run. Delivering an event is not the harness having finished
with it — the denial *starts* asynchronous work rather than concluding it.

Checking there answers "has the tool run yet", and the script reported it as
"the tool never ran".

The harness's own record shows how much was being missed. The denial creates a
second turn; in it the refusal comes back as a `tool.response` carrying the
error, the model reads it, and then — the good part — it abandons the tool
entirely and calls `ask_user_question` instead:

> The pull request could not be opened automatically due to requiring human
> approval for irreversible actions. How would you like to proceed?

The proof exited before any of that existed. It now waits for the session to go
quiet — two consecutive passes that add no turn and leave none in progress,
bounded, with a message rather than a false clean bill if the bound is hit — and
records the turns in the evidence. The demonstration got strictly stronger for
being made honest: it now shows not only that the tool did not run, but that the
agent stopped trying and went to find a human.

### 54 · A failed setup recorded as a successful proof

`sandbox.py` built its project and ran pytest without checking that the build
had worked. A `Completed` with a nonzero status is not a `RunError` — that
distinction is correct and is the whole of `bumpsmith.run` — so a failed
`pip install` arrived looking like an ordinary result and got carried past.

The exit check was `returncode != 0 and failures`, which any broken sandbox
satisfies. A missing pytest, an empty workspace, a network failure: all of them
produce a nonzero status and something the parser will classify, and all of them
would have been filed as proof of a pydantic `regex=` break.

Setup must now succeed, and the parsed failure must be `REGEX_KEYWORD` — the
break the script builds and therefore the only one it may end green on.

### 55 · Cumulative state read as this run's

The stub keeps every call it has served, for its whole lifetime, and appends to
its log forever. The proof read both as though they described the run that had
just happened, so a long-lived stub or one previous experiment would report a
failure that did not occur.

This one fails safe — it cries wolf rather than missing one — which is why it is
Medium and the two above are High. It is still wrong. Both signals are now
baselined before the session is created and compared afterwards, and the
baseline is printed when it is nonzero. Nothing is deleted to tidy it up:
clearing the evidence is how a real call gets lost.

### 56 · The guard was at one entrance and the building had two

`python -m bumpsmith --sandbox` refuses, with a paragraph explaining that the
sandbox is a different filesystem and a suite run there would not be testing the
local edits. That paragraph is right and the refusal was in the wrong place.

`migrate()` is public, takes the general `Runner` protocol, and a caller holding
a `SandboxRunner` reaches it without going anywhere near the command line. The
module docstring stated the requirement — *the runner has to execute against the
same tree* — and nothing enforced it. **Prose stating a property is not the
property**, which this log has already written down once, about a different
module, in finding 44.

The loop now checks `Completed.where` against `SAME_TREE` on every run. It tests
the fact each run reports rather than the type of the runner, so a wrapper
cannot slip past and a runner nobody has written yet is covered — and it is
checked on *every* run, so a runner that reported honestly while the suite was
red and conveniently the moment it went green is caught too. That case has its
own test, because it is the one the check exists for.

`Completed.where` was added in #14 so the review trail could say where a result
came from. Using it to enforce the invariant rather than to narrate it is what
it should always have been for.

### 57 · A bound that accepted infinity

`--timeout` rejected anything `<= 0`. `float("inf")` and `float("nan")` both
parse and neither is `<= 0`. `inf` silently removes the per-run cap the flag
exists to set; `nan` compares false against everything, so `subprocess`'s own
timeout never fires either. Both are now refused as invocation errors, which is
what they are.

---

## 58 · The error message named a fix that does not work

The class-1 rule has said this since #8:

> Replace a v1 validator's `field` and `config` parameters with v2's `info`

It reads like a summary of what pydantic itself prints, because it is one:

> The `field` and `config` parameters are not available in Pydantic V2, please
> use the `info` parameter instead.

Both are wrong about the same thing, and the library is wrong first. `info` is
V2's `@field_validator` parameter. Under the `@validator` shim — which is the
decorator that raised the message — a parameter called `info` is refused
outright, as an unsupported V1 signature. Following the advice in the error
trades one raised error for another.

The migration that works is smaller than the one the message describes: remove
both parameters and leave `values`, which V2 still accepts and which still
carries what it did.

This was found before the rewriter was written, by running eight candidate
signatures against a real pydantic rather than by reading the message and
believing it. Had it been found after, there would have been a rewriter, a green
test suite, and a migration that broke every repository it touched — because the
tests would have been written from the same misreading as the code.

That is now `proofs/validator.py`, and it is a proof rather than a test because
this package has no pydantic to test against and should not acquire one: it
works on source text and never imports the library it migrates. The script exits
non-zero if any of the eight signatures stops behaving as `bumpsmith.rules` says
it does.

**The rewriter's own tests do not re-derive this.** They are built on the
recorded answers. A test that decided for itself what pydantic accepts would be
the same misreading in a second place.

## 59 · A docstring that contradicted the code three lines below it

`BreakClass` opened by saying classes 2 and 3 "exist in that taxonomy but have no
recorded sample, so no classifier is written for them". `REGEX_KEYWORD = 3` is
the next member down, it has a classifier, and its own docstring ends "Both are
recorded samples."

Stale rather than wrong when written — class 3 got its sample in #4 and the
paragraph above it was not revisited. Harmless to the code and not harmless to a
reader, who has to decide which of two adjacent statements to believe.

Corrected, and the correction was worth more than the tidy-up. Class 2 — a field
V1 made optional by implication and V2 requires — turns out to have a recorded
sample now, discovered while checking what fixture B does once class 1 is fixed:
peel classes 4, 3 and 1 and the run stops being a collection error and becomes
five `ValidationError`s. What class 2 still lacks is a *classifier*, for a
different reason than "nobody has seen one": its signature is a `ValidationError`
like any other, and no traceback text distinguishes "V1 would have defaulted
this" from "this input really is missing a field". The docstring now says which
of the two reasons applies, because they call for different work.

## 60 · Eleven reasons, described as ten

`Stop` gained `WRONG_PLACE` in #16, as the fix for finding 56. The README's count
of how many ways the loop can end was not updated with it.

Small, and recorded at the same size as the others because the alternative is a
log that only lists findings flattering to the person keeping it. It is also the
second time in two pull requests that a number stated in prose has drifted from
the code it describes, which is the argument for stating fewer of them.

---

## 61–62 · Two from Qodo, both accepted

Both are the same shape as findings this log already holds, which is the useful
thing about them: the pattern was known and the code was written into it anyway.

### 61 · A read the parser could not see

`_names_used` collects `ast.Name` nodes, and refuses the deletion if `field` or
`config` is among them. A body doing `locals()["field"]` reads the parameter
without producing an `ast.Name` for it, so the check came back clean and the
rewriter wrote the edit. Reproduced before fixing:

```python
@validator("status")
def check(cls, v, field):
    return v if locals()["field"] else None
```

went to `def check(cls, v):` with the body untouched.

What makes it worth the finding rather than the shrug it first invites — nobody
writes that in a pydantic validator — is the direction of the damage. The
original break is an `ImportError` at collection: loud, immediate, every test in
the module. What the rewrite produces is a `KeyError` raised only when that one
validator runs. **Quieter, later, and conditional**, in a repository the tool was
asked to make safer.

The fix is not a cleverer detector. `locals`, `vars`, `globals`, `eval` and
`exec` in a validator's body mean this function cannot answer the question it is
being asked, and the honest answer to a question you cannot answer is to say so.
Asked *before* the use check, because it is a different question: the use check
finds uses, and this one establishes whether finding them is possible at all. A
clean answer from a detector that cannot see is an absence of evidence read as
evidence of absence.

### 62 · The proof checked the type and called it the reason

`_verdict` compared the exception class and nothing else. Four of the eight cases
expect `PydanticUserError`, and **two of them expect it for different reasons** --
that is the entire point of running both. `validator with field and config`
raises it because those parameters are gone; `validator with info` raises it
because the V1 shim will not take an `info` parameter at all. A check on the type
could not tell those apart, so a future pydantic that refused every V1 validator
with one blanket error would satisfy every case while the conclusion the script
exists to support quietly stopped being true.

Same shape as finding 54 on #16, where "nonzero and something parsed" accepted a
sandbox failure that had nothing to do with the break being demonstrated. A proof
that accepts a superset of what it claims is worth less than no proof, because it
reports confidence at exactly the moment it has least.

Now checked three ways -- stage, type, and a fragment of the message -- and the
stage is load-bearing on its own: `root_validator` fails at *call* time where
every `validator` case fails at *build* time, and that difference is one of the
things the rewriter's design rests on.

Demonstrated by breaking the claim rather than the check: pointing the `info`
case at the field/config message passes under the old verdict and fails under the
new one.

---

## 63 · A guard member that could not do the thing it was guarding against

Found re-reading the fix for 61 before merging it, which is the only reason it
is here rather than in somebody else's review.

`_DYNAMIC_SCOPE` held `locals`, `vars`, `globals`, `eval` and `exec` — names
whose presence means a parameter's uses cannot be read off the tree. Four of
those can reach a local by name. `globals` cannot: a parameter is a local, and
the module namespace does not hold it. Checked rather than reasoned about:

```
globals sees it      False
locals sees it       True
vars() sees it       True
eval reaches it      True
```

The cost is not a wrong rewrite — it is a refusal, which is the safe direction.
What makes it a finding is the *reason* attached to the refusal:

> `check` calls `globals`, so what it reads cannot be settled by reading it; a
> parameter removed here could still be reached by name at runtime

Which is not true of `globals`. A guard is allowed to cost a false refusal only
when the reason it gives for one is honest; otherwise the log of skipped sites —
the thing a person reads to decide whether to finish the migration by hand —
contains a sentence that will not survive being checked.

The boundary is now pinned from both sides: a test that `globals()` alone does
not stop the rewrite, and one that `exec` still does.

---

## 64–65 · The same stale count, in the two places finding 60 did not look

Finding 60 was "the README says ten ways for the loop to end and there are
eleven". It was fixed by correcting the README. Writing the README's first full
draft turned up the same drift twice more, both older than 60 and neither found
by it:

- `migrate.py`'s own module docstring: *"it names which of nine specific things
  happened"*. `Stop` has eleven members, ten of which are not `GREEN`, so the
  sentence was right when it was written and stale from the moment `WRONG_PLACE`
  landed in #16 — the same commit that made 60 stale, the same day.
- `proofs/README.md`: *"`tests/` does that, 448 times"*. It was 448 when the file
  was written in #17 and 453 by the time #17 merged, because the fixes Qodo
  caused brought five tests with them. **The number went stale inside the pull
  request that introduced it.**

The interesting part is not either defect, which is trivial. It is that fixing 60
did not find them. A finding was closed by correcting the one instance in front
of it, and two siblings a `grep` away stayed. **Fixing an instance is not fixing
a class**, and the log now says so in the one place a reader would check whether
it had been.

### The fix is to state fewer numbers, not to state them more carefully

Both are gone rather than corrected. `migrate.py` sat three lines above the enum
that *is* the count, and `proofs/README.md`'s sentence — "they do not test the
package, `tests/` does that, offline" — carries its whole meaning without a
figure in the middle of it. A number repeated beside its own source is a second
copy of a fact, and the second copy is the one that rots.

Where the number does earn its place, it is now pinned instead of trusted. The
README's count of `Stop` reasons is reader-facing and worth being concrete about,
so `tests/test_docs.py` asserts that the spelled-out number equals `len(Stop)`,
that every `Stop` member appears in the README's table, and that every `Outcome`
member appears in the list beside it. Adding a member without documenting it now
fails the suite, which is the moment the drift costs nothing to fix.

That is this log's recurring shape 6 — *prose stating a property is not the
property* — applied to the prose that had just demonstrated it three times.

**The test caught something on its first run: itself.** The pattern matched a
literal space, the README is hard-wrapped, and the sentence it was looking for
straddles a line ending. It reported the claim as missing rather than as wrong.
Fixed with `\s+`, and noted in the test, because a doc test that silently stops
matching would be worse than no doc test at all — it would pass forever.

---

---

## How this stays honest

- A finding is recorded when it is raised, not when it is resolved.
- Rejections are recorded with the reason, in the same detail as fixes. A log
  that only lists what was fixed is a list of compliments.
- Where a finding was tested rather than assumed, the log says what was measured.
- Pull requests are merged with `--merge`, never `--squash`. Each carries a "here
  is the work" commit and a "here is what review changed" commit, and squashing
  would destroy the evidence that the second one exists.
