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

---

## How this stays honest

- A finding is recorded when it is raised, not when it is resolved.
- Rejections are recorded with the reason, in the same detail as fixes. A log
  that only lists what was fixed is a list of compliments.
- Where a finding was tested rather than assumed, the log says what was measured.
- Pull requests are merged with `--merge`, never `--squash`. Each carries a "here
  is the work" commit and a "here is what review changed" commit, and squashing
  would destroy the evidence that the second one exists.
