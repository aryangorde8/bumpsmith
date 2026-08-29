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

The table of findings names a pull request when a finding was raised on it.
A pull request Qodo reviewed and found nothing on has no row there. That is
correct for a *finding* index and fatal for a *review* index: recording #42 as
finding 186 is how #43 then needs a finding, and #44 after that. **Pull requests
and reviews live in the other table.**

### Pull requests

Every pull request, including this one. Qodo reviewed all of 1–42; the two
count columns are the two queries the README already documents (inline comments
versus coverage comments). The last row is the open pull request that carries
this file. The next pull request replaces that row with the review that landed
and adds itself. An empty review is a row here, not a new finding.

| PR | Qodo | Inline findings | Coverage comments |
|----|------|-----------------|-------------------|
| [#1](https://github.com/aryangorde8/bumpsmith/pull/1) | reviewed | 0 | 1 |
| [#2](https://github.com/aryangorde8/bumpsmith/pull/2) | reviewed | 1 | 2 |
| [#3](https://github.com/aryangorde8/bumpsmith/pull/3) | reviewed | 1 | 2 |
| [#4](https://github.com/aryangorde8/bumpsmith/pull/4) | reviewed | 3 | 3 |
| [#5](https://github.com/aryangorde8/bumpsmith/pull/5) | reviewed | 2 | 2 |
| [#6](https://github.com/aryangorde8/bumpsmith/pull/6) | reviewed | 0 | 2 |
| [#7](https://github.com/aryangorde8/bumpsmith/pull/7) | reviewed | 2 | 2 |
| [#8](https://github.com/aryangorde8/bumpsmith/pull/8) | reviewed | 5 | 2 |
| [#9](https://github.com/aryangorde8/bumpsmith/pull/9) | reviewed | 5 | 2 |
| [#10](https://github.com/aryangorde8/bumpsmith/pull/10) | reviewed | 3 | 2 |
| [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | reviewed | 5 | 2 |
| [#12](https://github.com/aryangorde8/bumpsmith/pull/12) | reviewed | 4 | 2 |
| [#13](https://github.com/aryangorde8/bumpsmith/pull/13) | reviewed | 4 | 2 |
| [#14](https://github.com/aryangorde8/bumpsmith/pull/14) | reviewed | 4 | 2 |
| [#15](https://github.com/aryangorde8/bumpsmith/pull/15) | reviewed | 3 | 2 |
| [#16](https://github.com/aryangorde8/bumpsmith/pull/16) | reviewed | 8 | 2 |
| [#17](https://github.com/aryangorde8/bumpsmith/pull/17) | reviewed | 2 | 2 |
| [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | reviewed | 4 | 2 |
| [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | reviewed | 5 | 2 |
| [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | reviewed | 15 | 3 |
| [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | reviewed | 5 | 2 |
| [#22](https://github.com/aryangorde8/bumpsmith/pull/22) | reviewed | 1 | 2 |
| [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | reviewed | 1 | 2 |
| [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | reviewed | 2 | 2 |
| [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | reviewed | 3 | 2 |
| [#26](https://github.com/aryangorde8/bumpsmith/pull/26) | reviewed | 0 | 2 |
| [#27](https://github.com/aryangorde8/bumpsmith/pull/27) | reviewed | 0 | 2 |
| [#28](https://github.com/aryangorde8/bumpsmith/pull/28) | reviewed | 2 | 4 |
| [#29](https://github.com/aryangorde8/bumpsmith/pull/29) | reviewed | 1 | 3 |
| [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | reviewed | 3 | 4 |
| [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | reviewed | 7 | 8 |
| [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | reviewed | 11 | 3 |
| [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | reviewed | 5 | 3 |
| [#34](https://github.com/aryangorde8/bumpsmith/pull/34) | reviewed | 2 | 3 |
| [#35](https://github.com/aryangorde8/bumpsmith/pull/35) | reviewed | 4 | 5 |
| [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | reviewed | 6 | 4 |
| [#37](https://github.com/aryangorde8/bumpsmith/pull/37) | reviewed | 0 | 2 |
| [#38](https://github.com/aryangorde8/bumpsmith/pull/38) | reviewed | 0 | 3 |
| [#39](https://github.com/aryangorde8/bumpsmith/pull/39) | reviewed | 3 | 3 |
| [#40](https://github.com/aryangorde8/bumpsmith/pull/40) | reviewed | 1 | 3 |
| [#41](https://github.com/aryangorde8/bumpsmith/pull/41) | reviewed | 1 | 2 |
| [#42](https://github.com/aryangorde8/bumpsmith/pull/42) | reviewed | 0 | 2 |
| this PR | this PR | — | — |

### Findings

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
| 20 | [#10](https://github.com/aryangorde8/bumpsmith/pull/10) | `cast("Approver", ...)` "will fail CI because mypy type-checks `tests/`" | **Rejected** — the claim is false and was tested, not argued: `typing.cast` takes a string as a forward reference by design, mypy flags only an undefined one, and CI had already passed on the commit under review | [§20–22](#2022--three-on-the-approval-gate-one-of-them-real) |
| 21 | [#10](https://github.com/aryangorde8/bumpsmith/pull/10) | `Gate.run` computed the fingerprint outside the guard, so a `detail` that would not serialise raised `TypeError` rather than `NotApprovedError` — **the gate refused something and recorded nothing** | **Fixed** — rejected where it is written, with the fingerprint call guarded as a backstop that records the refusal. Fail-closed held; the *trail* did not | [§20–22](#2022--three-on-the-approval-gate-one-of-them-real) |
| 22 | [#10](https://github.com/aryangorde8/bumpsmith/pull/10) | Unbounded history memory growth in `_records` | **Rejected, with the arithmetic** — 460 bytes per decision, so a million records for 439 MiB, and the rate is bounded by human attention. The remedy is worse than the condition: trimming an audit trail drops the **oldest denial first** | [§20–22](#2022--three-on-the-approval-gate-one-of-them-real) |
| 23 | [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | Two declarations on one line: one dropped, both counted | **Fixed** | [§23–27](#2327--five-on-the-rewriter-all-accepted-all-one-root-cause) |
| 24 | [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | A rebound base was rewritten — `BaseModel = Other` then `class Items(BaseModel)` is not pydantic's | **Fixed** — reproduced exactly as reported | [§23–27](#2327--five-on-the-rewriter-all-accepted-all-one-root-cause) |
| 25 | [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | An import is not a guarantee the name still means that: `RootModel = Other` after the import set `already_imported` and skipped the collision check | **Fixed** | [§23–27](#2327--five-on-the-rewriter-all-accepted-all-one-root-cause) |
| 26 | [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | `RootModel, other = pair()` binds `RootModel`, and binding collection missed it | **Fixed** | [§23–27](#2327--five-on-the-rewriter-all-accepted-all-one-root-cause) |
| 27 | [#11](https://github.com/aryangorde8/bumpsmith/pull/11) | An import under `if TYPE_CHECKING:` binds nothing at run time, and one in a class body binds an attribute — either could be chosen as the import to extend, producing a `NameError` in the class just rewritten | **Fixed** | [§23–27](#2327--five-on-the-rewriter-all-accepted-all-one-root-cause) |
| 28 | [#12](https://github.com/aryangorde8/bumpsmith/pull/12) | `removed-kwargs` does not identify one break — measured against pydantic 2.12.5, `const` and `unique_items` raise the same slug | **Fixed** | [§28–31](#2831--four-on-the-regex-class-all-accepted) |
| 29 | [#12](https://github.com/aryangorde8/bumpsmith/pull/12) | A function *parameter* named `constr` was treated as pydantic's, because one module-wide import map was applied to every call in the file | **Fixed** — `calls_in_scope`, whose docstring names this failure. 🔴 **Reintroduced as [106](#106107--the-paragraph-one-function-above-the-mistake) on #22**, in a new function written beside that docstring | [§28–31](#2831--four-on-the-regex-class-all-accepted) |
| 30 | [#12](https://github.com/aryangorde8/bumpsmith/pull/12) | Two sites on one line, one gone since the scan: the survivor stood in for both — two reported rewritten, one written, plan `complete` | **Fixed** — the combination is worse than either half, because it looks like success | [§28–31](#2831--four-on-the-regex-class-all-accepted) |
| 31 | [#12](https://github.com/aryangorde8/bumpsmith/pull/12) | A stdlib-shaped substring is not an interpreter root: `/lib/pythonX.Y/` anywhere in the path meant a project holding its own `lib/python3.13/` had frames skipped | **Fixed** | [§28–31](#2831--four-on-the-regex-class-all-accepted) |
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
| 66 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | "byte-for-byte what it was" excluded everything the *test suite* writes, and `git status` was the wrong check for it | **Fixed** — the guarantee is scoped to bumpsmith's own edits, and the artefacts are named | this PR |
| 67 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | "a crash" reverts the tree — a `finally` block cannot survive `SIGKILL` | **Fixed** — narrowed to stack unwinding, in `apply.py` and the README | this PR |
| 68 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | The README said the parser dispatches on the return code *not* the text; it uses both | **Fixed** — and `failures.py`'s own module docstring said it first | this PR |
| 69 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | The completeness test searched the whole README, so it did not pin the table it advertised | **Fixed** — scoped to the table and the list, plus a stray-row check | this PR |
| 70 | [#18](https://github.com/aryangorde8/bumpsmith/pull/18) | The fix for 66 named an artefact the run had not created — leftovers from the previous day, read as output — *self-found by the cold clone* | **Fixed** — the count is from a clean reproduction | this PR |
| 71 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | The page promised unreadable files "listed with their reason" and rendered neither — and `as_dict` had been dropping the reason since #16 | **Fixed** in the payload and the page; the old shape still renders | this PR |
| 72 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | "19 sites across 2 files" joined the *scan*'s site count to the *plan*'s file count, so a skipped-only file vanished from the rule's reach | **Fixed** — `match_files` and `edit_files` cannot be confused | this PR |
| 73 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | The "sites rewritten" tile ignored `applied`, announcing rewrites above a step reading "planned but never written" — the **second** `applied` inversion in this file | **Fixed** — tile and step read it from one place | this PR |
| 74 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | `already-green` and `untouched` runs rendered "0 changes taken back", implying there had been something to revert | **Fixed** — the noun comes from `applied`, the number on the tile | this PR |
| 75 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | `--json out --html out` wrote both in turn, reported two successes and exited 0 with the JSON gone | **Fixed** — refused before the suite runs, paths compared resolved | this PR |
| 76 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | `page()`'s docstring named `__main__.report_payload`, a function that was never written — *self-found* | **Fixed** — described by what it is, not by a name that must keep existing | this PR |
| 77 | [#19](https://github.com/aryangorde8/bumpsmith/pull/19) | "It stopped at `no-rule`. the failure classified as UNKNOWN" — every `Stop` reason is a lowercase clause — *self-found by reading the rendered page* | **Fixed** — a dash, and the sentence is terminated | this PR |
| 78 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The pull request body said "of which 1 were rewritten" — the nouns went through `_count` and the verb between them did not — *self-found by reading a pushed commit* | **Fixed** | this PR |
| 79 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The body stated the one-site-against-every-site gap when there was no gap; `report.py` had already decided that question correctly and the markdown did not inherit it — *self-found the same way* | **Fixed** — suppressed on both sides, with a test on each | this PR |
| 80 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `git remote get-url` gives the **fetch** URL; `git push` uses `pushurl` and may have several — the approval named a destination the push would not use | **Fixed** — `get-url --push --all`, and more than one push URL is refused | this PR |
| 81 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The fingerprint bound the URL and the push used the mutable remote *name* | **Fixed** — the push names the URL; the indirection is gone rather than re-checked | this PR |
| 82 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `gh pr create` had no `--repo`, so it picked a repository from the checkout — the one the migration was cloned from | **Fixed** — `--repo` from the approved URL; a non-GitHub URL means `gh` is not run at all | this PR |
| 83 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `checkout -B` starts at HEAD, so a checkout ahead of the base publishes its commits — and the suite went green against HEAD, not the base | **Fixed** — HEAD must *be* the base | this PR |
| 84 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `git commit` commits the whole index, and `git add -- path` stages that file's uncommitted changes too | **Fixed** — `commit --only`, a dirty index refused, each path checked against what the migration first read | this PR |
| 85 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `-B` resets an existing branch, and the default name is reused across runs | **Fixed** — `-b`, and an existing branch is refused | this PR |
| 86 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `--open-pr "$REMOTE"` with the variable unset was read as never having asked | **Fixed** — answered, not absorbed; finding 75's principle two commits later | this PR |
| 87 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | A pushed branch with no pull request exited 0 | **Fixed** — exit 2; a refusal still exits 0, because saying no must stay free | this PR |
| 88 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The proof compared branch *names*, so a rewritten `trunk` passed as untouched | **Fixed** — every ref compared with its object; verified by force-updating trunk | this PR |
| 89 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The proof ignored the CLI's exit status, so a crash read as a refusal honoured | **Fixed** — each case states its status; verified by making refusals exit 1 | this PR |
| 90 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | A timed-out proof child survived `communicate` and outlived the `rmtree` | **Fixed** — killed and reaped; reproduced with a sleeping suite | this PR |
| 91 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | `_git` strips its output and `status --porcelain`'s leading space is significant, so every publish was refused — *self-found fixing 84, by running it* | **Fixed** — two `git diff` reads with no whitespace to lose | this PR |
| 92 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `README.md` told the reader `git -C ./fixtures/B status --ignored` would show `.pytest_cache/`. It cannot: pytest writes the cache at `rootdir`, which for that fixture is the bumpsmith checkout — *self-found on #20's cold clone* | **Fixed** — the line names the seven `__pycache__/` it does leave; the README had already said so 260 lines earlier and contradicted itself | this PR |
| 93 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | The correction at `README.md:194` was right about *what* and wrong about *why* — it blamed stale residue from a previous day's runs, not rootdir resolution — *self-found on #20's cold clone* | **Fixed** — the mechanism named, and it turned out to be worth a section of its own | this PR |
| 94 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | The suite's verdict is not purely the subject's: pytest resolves settings by walking **upward**, so a repository under this checkout is measured under bumpsmith's `addopts` and `testpaths` — *self-found on #20's cold clone* | **Fixed** — `Stop.FOREIGN_CONFIG`, checked before the first run; `bumpsmith.fixtures` writes an empty `pytest.ini` barrier so the documented workflow still runs | this PR |
| 95 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `_runs_pytest` carried a `-m pytest` branch that could never be the reason it returned `True` — the module argument *is* the bare word `pytest`, which the name check already matches — *self-found by breaking it* | **Fixed** — branch deleted; a parametrised test appeared to cover it and passed with the branch gone | this PR |
| 96 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | The test named for an empty `pytest.ini` used a file that still carried `[pytest]`, so the flag making that name always count was never exercised — *self-found by breaking it* | **Fixed** — a zero-byte case added; breaking the flag now fails | this PR |
| 97 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `interpolation=None` on the ini reader guarded a path the code never took: only key *names* were read, and configparser interpolates on value access — *self-found by breaking it* | **Fixed** — the refusal now quotes values as well as names, which makes the guard load-bearing and the message actionable | this PR |
| 98 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `CANDIDATES` knew only `pytest.ini`, but pytest 9 also reads `pytest.toml`, `.pytest.toml` and `.pytest.ini`, and honours a native `[tool.pytest]` table | **Fixed** — all seven names, in pytest's own order, each rule measured with `--collect-only -v`. Both directions were live: a missed foreign config, and a subject refused for a configuration it had already overridden | this PR |
| 99 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `pytest -c FILE` replaces discovery outright, so the guard judged a file the run would never open | **Fixed** — the argv is read for `-c`/`--config-file` in all five spellings and the named file is judged instead of the walk | this PR |
| 100 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `runs_pytest` matched the word anywhere in the argv, so `make pytest` and `python script.py pytest` were refused — contradicting the paragraph directly above it | **Fixed** — pytest must be the program or the `-m` argument. This is also what made finding 95's branch dead; narrowing the scan made it load-bearing again | this PR |
| 101 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `write_barrier` let `OSError` escape, and `clone_all` converts only `FixtureError`, so one unwritable barrier ended the whole command in a traceback | **Fixed** — wrapped as `FixtureError`, so that fixture fails and the rest are still attempted | this PR |
| 102 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | `write_barrier` accepted any existing path, including a **directory**. pytest reads configuration only from files, so the barrier silently was not one | **Fixed** — `is_file()`, and anything else in that place is refused by name. The worst kind of guard is one that appears to be working | this PR |
| 103 | [#21](https://github.com/aryangorde8/bumpsmith/pull/21) | The test written for 101 used a directory, which trips 102's guard instead — so the `OSError` wrapping was covered by nothing — *self-found by breaking it* | **Fixed** — a dangling symlink lands on the write itself; deterministic, and needs no `chmod` a root-owned CI would ignore | this PR |
| 104 | [#22](https://github.com/aryangorde8/bumpsmith/pull/22) | A `REMOVED_INTERNAL` rule said "stop importing `X` from `Y`" and the scan reported only the import line, never where `X` was still read — so following the tool's own advice turns an error at import time into a `NameError` at call time — *self-found while measuring whether a class-5 rewriter could exist* | **Fixed** — `Role.SITE`/`Role.USE` on `Match`, `count` stays sites-only, `_by_path` filters to sites so no planner can be handed a use, and the refusal names the lines that would break. Measured on fixture F4 under pydantic 2.13.4: deleting the import gives `NameError`, repointing at the `pydantic.v1` shim gives `AttributeError` two lines later | this PR |
| 105 | [#22](https://github.com/aryangorde8/bumpsmith/pull/22) | `if not bound: return` read as a correctness guard but is not one — the loop below it tests `node.id in bound`, which already yields nothing for an empty set — *self-found by breaking it and having nothing fail* | **Kept, relabelled** — finding 95's shape a second time. It is a real optimisation, so it stays with the measurement that earns it: 12.6ms → 5.9ms on a file that does not import the symbol, which is nearly every file in a scan | this PR |
| 106 | [#22](https://github.com/aryangorde8/bumpsmith/pull/22) | `_removed_symbol_sites` put imports from every lexical scope into one file-wide set, so a parameter, a local, or a comprehension target sharing the spelling was reported as a line that would break — and the refusal asserts a `NameError` at each line it names, which for those is a specific, checkable, **false** statement about somebody's code. False matches could also fill the five listed slots ahead of the real use | **Fixed** — scope is followed: `_uses_in_scope` subtracts what a scope binds itself before adding what its own import binds, and comprehensions are scopes with their targets as bindings. Verified before accepting: three of Qodo's four sub-claims reproduced; attribute access was already correct. 🔴 **`calls_in_scope` documents this exact failure one function above the one that had it** | this PR |
| 107 | [#22](https://github.com/aryangorde8/bumpsmith/pull/22) | The unpacking-target test used `[a for (a, X) in pairs]`, where the only occurrence of `X` is a **store** — never a use whether unpacking shadows or not, so it passed with the guard removed — *self-found by breaking it* | **Fixed** — the element now reads the name. **The fourth instance of this shape** after 96, 97 and 103 | this PR |
| 108 | [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | The README said the log holds **65 findings**; it held 107 — and the paragraph carrying that number is the one ending *"a stale number was corrected in one file and left standing in two others a `grep` away"* — *self-found by reading the README cold, as a stranger would* | **Fixed** — the sentence is now checked against the log's own table by `tests/test_docs.py`, both the total and the three parts summing to it. Findings 64/65's shape, inside the paragraph that describes it | this PR |
| 109 | [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | This table skipped **20–31**: twelve findings with prose sections and no row — a *documented* choice, with a note under the table saying so, not a silent omission — *self-found the same way* | **Fixed** — twelve rows written from the prose, index contiguous 1..N, and a test fails on the next gap. The note was a fair defence of a weaker thing: a group section explains a finding, and only a row makes it findable by number | this PR |
| 110 | [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | Adding rows 20–31 made the note two lines under the table — *"described in the sections below rather than listed here"* — false, so the log told a reader both that those findings are indexed and that they are not | **Fixed** — the note now describes the arrangement that exists. **Raised by Qodo on the pull request whose subject is a stale sentence left standing beside the thing it described**; 108's own shape, inside 108's fix | this PR |
| 111 | [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | The guard written for 110 searched the whole log, so it failed on the log's own description of 110 — a check that cannot coexist with writing down what it checks — *self-found by running it* | **Fixed** — scoped to the prose between the index and the first section. `test_docs.py`'s module docstring already records this exact mistake being made and undone once before | this PR |
| 112 | [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | `fan_out`'s deadline was decorative. The pool was entered with `with`, whose `__exit__` calls `shutdown(wait=True)` — so after `wait(timeout=...)` gave up, the block still blocked until the abandoned job finished, and the timeout stopped nothing — *self-found by breaking the guard and watching the test take as long as the job it was meant to abandon* | **Fixed** — the shutdown is explicit and does not wait; queued jobs are cancelled, running ones are reported as possibly still running. The test went 20.27s → 0.62s, which is the only reason it was visible at all: it passed either way | this PR |
| 113 | [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | `test_workers_must_be_positive` passed with its guard deleted. It matched `ValueError` on the pattern `"workers"`, and `ThreadPoolExecutor` rejects the same values with *"max_workers must be greater than 0"* — so the test proved somebody's guard existed, not this module's — *self-found by breaking it* | **Fixed** — matched on this module's own wording, plus a case with **no jobs**, where the pool is never built and nothing else objects, so an impossible worker count would otherwise return an empty result as though asked to do nothing. **The fifth instance of this shape** after 96, 97, 103 and 107 | this PR |
| 114 | [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | `fan_out` read the shared results *after* the timed wait and the pool shutdown, so a job finishing after the deadline but before that read was reported as **reached** — a verdict accepted because the bookkeeping in between took long enough, making the timeout nondeterministic exactly at its boundary | **Fixed** — the `done` set `wait` returns *is* the deadline, decided at the instant it passed; the results only supply the value. 🔴 **The comment three lines above the defect stated the correct rule** — *"reading it as unreached is the safe direction"* — and the code did the opposite. Written while fixing 112, in the paragraph belonging to the timeout it broke | this PR |
| 115 | [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | `proofs/fanout.py` said it needed *"pydantic v2 and nothing else"* and probed only pydantic, but every subject is migrated by running `python -m pytest` through that same interpreter — so an interpreter meeting the documented requirement fails all four subjects, and the proof reports it as migrations that did not work rather than as a missing prerequisite | **Fixed** — both are probed before anything is built, and the failure exits 2 naming both. The docstring and `proofs/README.md` corrected. **A missing prerequisite is not a result** — shape 9's family, where not-knowing is reported as an outcome | this PR |
| 116 | [#24](https://github.com/aryangorde8/bumpsmith/pull/24) | Fixing 114 put the rule in `_verdict` and left the *call site* untested: a `fan_out` passing `finished_by_deadline=True` unconditionally passed every test in the file, because the deadline tests use a job that is still blocked and therefore never records a result for the flag to decide about — *self-found by breaking the guard* | **Fixed** — assembly extracted to `_assemble` and checked with futures a test builds itself, one of them recorded but absent from `done`. **Finding 55's shape**: a guarantee spelled across two places needs both halves tested, and the dangerous half is the one that fails quietly | this PR |
| 117 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | `Attempt.ran` asked whether a result *is a verdict* rather than whether it is `Unreached`. Both answers agree for the two types that exist, so swapping one for the other passed all 713 tests — and they disagree for anything else, where the protocol version answers *"nobody reached this subject"* about a subject that was reached. The module's own docstring stated the correct rule; nothing tested it — *self-found by breaking the guard* | **Fixed** — the discriminator is `Unreached`, the type this module owns, and a test now hands `fan_out` a result of a kind it has never met. **Prose stating a property is not the property** (60, 69), and the fourth defect found sitting inside its own recorded warning | this PR |
| 118 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | `_read_exec_result` refused a real harness failure by naming the missing field and discarding the sentence beside it. TrueForge sends `error` as a model turn's **content blocks**, not a string, so the `success is False` branch reported *"no reason given"* while holding the explanation — and the branch for a result with no `success` at all never consulted `error`, which is precisely the shape a sandbox that never came up produces. A live Daytona disk-quota failure surfaced as *"`success` is None"* | **Fixed** — both branches read the reason in either form. Nothing about which results are *accepted* changes; only what a rejected one can say for itself. **Raised by running it, not by reading it**: the string-only shape had been assumed since the module was written and no test could have contradicted it | this PR |
| 119 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | **High.** `_control_is_untouched` built its own `SandboxExec`, which opens a *new session* and therefore a new, empty sandbox — so the negative control's `git status` ran against a filesystem that had never held the control checkout. Normally the subject is simply absent and the proof fails; with unrelated state present it would certify the wrong filesystem as clean | **Fixed** — `SandboxJob` keeps the session it used and exposes `exec_in_its_sandbox`, which refuses before the job has run rather than opening one on the spot. 🔴 **The function's own docstring stated the requirement** — *"a fresh one would have a clean checkout for reasons that say nothing"* — and the code created a fresh one. **Fifth instance**, in the same pull request that named the pattern | this PR |
| 120 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | The control check filtered every `??` line out of `git status --porcelain`, so an agent that *added* a file passed a check whose entire claim is that the files are unchanged | **Fixed** — nothing is dropped. Tracked changes fail; an untracked `.py` fails outright; every untracked path is recorded as evidence either way. The filter had a real reason — C's own suite writes `htmlcov/` and `coverage.xml`, so a naive check never passes — but *"the artefacts of running the suite"* and *"anything untracked"* are different sets, and only one of them was safe to ignore | this PR |
| 121 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | `_read_step` inferred that a scan or plan happened purely from `sites`/`rewritten` being non-null, without checking their types or forbidding `unreadable`/`skipped` entries beside them. A report with `sites: null` and a non-empty `unreadable` list parsed cleanly and derived **`complete = True`** — because completeness asks about a scan, and the step was claiming there was not one | **Fixed** — both counts are checked as int-or-null (`bool` is an `int` in Python, so an unchecked `true` arrives as a count of one), and a phase that never ran may not list what it left behind. The producer never writes that pair; this reader exists for text nobody here produced, which is the only reason it is worth hardening | this PR |
| 122 | [#25](https://github.com/aryangorde8/bumpsmith/pull/25) | `sandbox_fanout.py` opened *"Four subjects go out together"* and fans out **three** — and structurally cannot fan out four, because `EXTRAS` is the only place a measured environment exists and it holds two. The README repeated the figure. Nothing was wrong with the code; the paragraph describing it was wrong, in the module whose entire subject is reports that disagree with their evidence — *self-found when the recorded run printed its own subject count on line one* | **Fixed** — the docstring states the rule (`EXTRAS` decides) instead of a number that has to be maintained beside it, and the one figure kept is the one the run prints. **Prose stating a property is not the property** (60, 69, 117) — sixth instance, and the first found by the proof it describes | this PR |
| 123 | [#26](https://github.com/aryangorde8/bumpsmith/pull/26) | The log entry for 122 said the count *"was contradicted the first time the thing ran"*. It was not. `proofs/sandbox_fanout.py` prints its subject count **before** it fans out, so the quota-failed run on 27 Aug — the one that reached nothing — printed `fanning out over 3 subjects` under a docstring already reading *"Four subjects go out together"*, and so did every run after it. The contradiction was on screen for over an hour before anyone read it; the entry recording that turned "I did not notice" into "it did not happen" — *self-found by checking the claim before repeating it in the write-up* | **Fixed** — the entry now says the line was printed on every run including the ones that reached nothing. **Shape 9** (*"I could not tell" reported as "it did not happen"*; 115), and the entry it corrects is the one about prose that states a property instead of having it | this PR |
| 124 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | **High.** `_refuse_unpublishable` reads each target with `git show HEAD:path` and skips its check entirely when that returns nothing — which is exactly what an **untracked** file returns. The scanner walks Python files, not tracked files, so a migrated untracked file passes a guard whose whole claim is that nothing but the migration goes out, and `git add` then publishes the file's entire pre-existing content as bumpsmith's change | **Fixed** — a target with no committed version is refused by name. `_git_or_none` also **strips**, so the comparison never saw the bytes anyway; `_git_verbatim_or_none` reads without stripping. **Seventh instance of the shape**: `publish.py` opens by arguing that nothing but the migration leaves, and this is the fourth separate way it did not have that property | this PR |
| 125 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The same check compares `committed.rstrip("\n")` against `first_read.rstrip("\n")`, so a pre-existing trailing-newline change on a target is treated as no change at all and is staged with the migration | **Fixed** — the comparison is exact. Finding 91 was `_git` stripping `status --porcelain`, whose leading space means something; a file's contents are the same kind of value and more obviously so | this PR |
| 126 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | The check compares blob **text** and never the file mode, so a pre-existing executable-bit change on a target passes whenever the contents match. Staging the path records the mode change — in a writer that goes out of its way to preserve permissions rather than set them | **Fixed** — the committed mode is read with `ls-tree` and compared against the file's execute bit. 🔴 **The test fake never answered `ls-tree` at all**, so a mode check added without touching the harness would have passed every test while never running | this PR |
| 127 | [#20](https://github.com/aryangorde8/bumpsmith/pull/20) | **The gate one.** `propose()` validates HEAD, the index and the target contents *before* the blocking approval prompt, and `_do_open()` revalidates none of them after it. Anything that changes while a human is deciding — another process, another shell, the person themselves — is inside the approval and outside the checks. The window is bounded by human attention, which is to say it is the longest window in the program | **Fixed** — `_do_open` runs the whole check again before it touches anything, against the contents the approval was granted for, so `Proposal` now carries `originals` and derives `paths` from them rather than storing both. 🔴 **The module already knew about this window for one thing**: the push goes to the approved *URL* rather than the remote name, because `git remote set-url` could land in it. The tree can move in the same window and nothing looked. Tested by a gate whose `decide` changes the repository on its way to returning `Allow` — nothing else in the suite holds the prompt open | this PR |
| 128 | [#28](https://github.com/aryangorde8/bumpsmith/pull/28) | The publish test fake built its committed-blobs map with `dict(committed or {...})`, so passing `{}` — a repository where the target is **untracked**, the exact state finding 124 is about — silently got the default map with the file present. The case could not be expressed in the suite that was supposed to check it — *self-found while writing 124's guard* | **Fixed** — `is not None`, not `or`. The same shape as the defect it was blocking: an absence read as *nothing was specified* rather than as *the answer* | this PR |
| 129 | [#28](https://github.com/aryangorde8/bumpsmith/pull/28) | Revalidating after the approval — the fix for 127, in this same pull request — checked the target against its **pre-migration** contents and never against what the migration actually wrote. HEAD is unchanged either way, so a target edited while the prompt waits passes every question being asked and is staged as this migration's output. Replacing it with a **symlink** passes too, because `is_file()` follows the link and answers about a different file | **Fixed** — `Proposal` carries `(path, before, after, encoding)` and the check asks both questions: *is somebody else's work in the way* against `before`, *is ours still there* against `after`, read back with the encoding and `newline=""` it was written with. Symlinks refused outright. 🔴 **Eighth instance of the shape, and the sharpest**: the fix for a window left the window open for the one thing the window is about | this PR |
| 130 | [#28](https://github.com/aryangorde8/bumpsmith/pull/28) | The contents check added for 129 reads the target with `open(encoding=...)`. Neither `OSError` nor `UnicodeError` is a `PublishError`, and `__main__` catches only the latter — so a target made unreadable, or rewritten with bytes that are not its encoding, during the approval window left the module past the one handler written for it, as a traceback | **Fixed** — both are translated into `NothingToPublishError` naming the file and the encoding. 🔴 **Shape 1 for the fifth time** (*an exception escaping the path meant to handle it*), introduced by the fix for 129, which was itself the fix for 127 | this PR |
| 131 | [#29](https://github.com/aryangorde8/bumpsmith/pull/29) | `_no_sandbox()` — the only text a user of this package ever sees about the sandbox — ended *"carrying the edits across is the missing piece; until it is written and reviewed, this refuses"*. It had been written, eight pull requests earlier, by moving the **agent** instead of the edits: `bumpsmith.remote` installs the package into the sandbox and runs the whole loop there. `remote.py`'s own docstring cites this refusal approvingly, so the two modules agreed about the design and only the sentence a reader is shown still described the hole — *self-found while verifying a deferral before answering it in a review thread* | **Fixed** — the refusal and every line of its reasoning stay, because the refusal is still right. What changes is the ending: the mechanism exists, it is named (`bumpsmith.remote`, `proofs/sandbox_fanout.py`), and the missing piece is narrowed to the command-line route it actually is. **Prose stating a property is not the property** (60, 69, 117, 122) — seventh instance, and the first where the prose described a gap the code had already closed rather than a property the code lacked | this PR |
| 132 | [#29](https://github.com/aryangorde8/bumpsmith/pull/29) | The README dated its finding snapshot *"As of 28 August 2026"*, and every timestamp this repository carries said otherwise: the commit (`2026-08-27T19:54:20Z`), the pull request, and the review comment that caught it (`2026-08-27T19:56:32Z`). The date was read off a clock at UTC+05:30; git and GitHub keep time in UTC. The documentation guards check the total and the arithmetic and had nothing to say about the date, which Qodo noted in the same breath | **Fixed** — the snapshot reads 27 August, and `test_the_readme_finding_snapshot_is_not_future_dated` now fails on any snapshot dated after today in UTC. It can pass and never spuriously fail later, because a date in the past stays in the past. 🔴 **Raised on the pull request whose entire subject is prose drifting from what the code does** — the correction to one stale sentence shipped a fresh one, dated a day into the future | this PR |
| 133 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | The README's *Where the suite runs* section ended with the same sentence finding 131 removed from `_no_sandbox()` — *"carrying the edits across is the missing piece; until it is written and reviewed, a flag that quietly did it would be worse than no flag at all"*. 131 corrected the command-line text and left the README's copy of it standing, in the section a reader arriving for the harness reads first. `proofs/README.md` had described `remote.py` correctly since #23, so **three documents disagreed and only the least-read one was right** — *self-found while auditing the README against the Best Use of TrueForge criteria* | **Fixed** — the refusal paragraph stays; the ending is replaced with what actually happened, naming `remote.py` and `proofs/sandbox_fanout.py` and narrowing the gap to the command-line route. **Prose stating a property is not the property** (60, 69, 117, 122, 131) — eighth instance, and the second in two pull requests where the fix for a stale sentence did not reach every copy of it. Findings 64/65's shape — *a stale number corrected in one file and left standing in another a `grep` away* — applied to a claim rather than a number | this PR |
| 134 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | The module table under *How it is put together* opens "Everything is in `src/bumpsmith/`" and lists **twelve of the sixteen** modules the package ships. The four with no row — `fanout.py`, `remote.py`, `publish.py`, `report.py` — are the parallel fan-out, the sandbox-resident loop, the only irreversible effect the tool has, and the HTML report: four of the project's strongest claims, absent from the map a reader navigates by. Counted, not noticed | **Fixed** — four rows added, and `test_the_readme_maps_every_module_the_package_ships` now derives the expected set from `src/bumpsmith/*.py` so the table cannot fall behind the package again. A second test catches the other direction, a row naming a file that no longer exists. Scoped to the table's first column for the reason `_stop_table` already documents: nearly every module is named elsewhere in the README, so a file-wide search would have reported a complete map | this PR |
| 135 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | *"Twenty-eight pull requests; Qodo reviewed every one; twenty-four raised at least one finding, **90 in total**"* — in the `## Qodo Code Review Evidence` section, which the rules require by name. Live counts at the time of reading: **29** pull requests, **25** with at least one inline finding, **91** findings. #29 merged and none of the three numbers followed. Unlike the finding total two paragraphs above it, this sentence has no test behind it, because the numbers live on GitHub rather than in the repository | **Fixed** — all three corrected against `gh api`, recounted rather than incremented. Left deliberately unguarded, and the reason is worth stating: a test that queried GitHub would fail on a network outage and pass on a stale cache, which is a guard that is wrong in the reassuring direction. The check belongs in the pre-submission pass, and it is written down there instead. **Findings 64/65 for the third time**, now in the one section a rule names | this PR |
| 136 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | The completeness guard written for 134 filtered `__*.py` out of the package before comparing, while the sentence it defends says *"Everything is in `src/bumpsmith/`"*. So the test enforced *everything except dunders* — a claim the README does not make — and `__main__.py`, the command line, could have been dropped from the table without failing anything. **This is the pull request's own subject occurring inside its own fix**, which is the third time in three pull requests that a correction for stale prose has carried the defect it was correcting | **Fixed** — nothing is filtered; `_shipped_modules()` returns every `.py` file the package ships, and `__main__.py` and `__init__.py` were given rows, because on reflection both are things a reader wants to find. The deeper problem was the *pattern*: `startswith("__")` silently adopts files that do not exist yet, so a `__version__.py` added next month would have been out of scope by nobody's decision. Where an exemption is genuinely right — the `__init__` table of 138 — each one is now named individually with its reason | this PR |
| 137 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | `_tabled_modules()` returned a **set**, so both checks written for 134 compared sets and neither could see multiplicity. A table that had drifted into two rows for one module — one of them stale, which is how it happens — satisfied "nothing missing" and "nothing invented" while the one-row-per-module mapping it advertises was gone. The stale row is the one nobody updates, so this is the failure mode that actually occurs | **Fixed** — the helper returns a list, in order and with repeats, and `test_the_readme_module_table_names_each_module_once` is the third check. The two set-difference tests take `set(...)` explicitly at the call site rather than hiding it in the helper, so what each one is blind to is visible where it is used | this PR |
| 138 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | **A third map, found while fixing 136.** `src/bumpsmith/__init__.py` — the docstring `help(bumpsmith)` prints — carries its own table of the package and listed **nine of eighteen** files, missing the same four the README's table missed plus `rootdir` and `sources`. Three hand-written maps of one package, and until this pull request not one of them was checked against the package. The reader it fails is the one at a REPL who never opens the repository — *self-found* | **Fixed** — the table is complete, and `test_the_package_docstring_maps_every_module_it_claims_to` derives the expectation from `src/bumpsmith/*.py`. Its three exemptions (`migrate`, `__main__`, `__init__`) are **named one at a time with the sentence in the docstring that covers each**, rather than matched by pattern, which is 136's lesson applied on the same afternoon it was learned | this PR |
| 139 | [#30](https://github.com/aryangorde8/bumpsmith/pull/30) | **Raised by the follow-up review**, on the fix for 137. The uniqueness check written for 137 was added to the README's table and not to the `__init__` table, which makes the same one-row-per-module claim. Worse, `_init_table_modules()` was written to preserve repeats and its docstring says so — and then all three of its callers took `set(...)` of it, so the multiplicity it was careful to keep was discarded by every reader it had. **Shape 11 — a guarantee enforced at one entrance of a building with two** | **Fixed** — `test_the_package_docstring_names_each_module_once` is the fourth check on that table. The lesson is not "add the test": 137 was fixed *where it was raised* rather than *wherever it applied*, and the second site was in the same file, added in the same commit, twenty lines below. A promise nothing consumes is not a guarantee | this PR |
| 140 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | 135's fix corrected the trail counts and left the sentence in a form that **goes stale by construction**: *"Twenty-nine pull requests … 91 in total"* is a claim about *now*, and every subsequent merge falsifies it. There is no value that can be written there and stay right, which is why the same three numbers had already been wrong twice. Correcting them a third time would have been the third instance of a defect whose real shape is the sentence, not the digits — *self-found while performing the recount 135's own disposition promised* | **Fixed** — the sentence is anchored to a named event, *"as of the merge of #30"*, and carries the `gh api` command that re-derives it. Anchored, it ages instead of lying: a later merge makes it out of date and never false. Recounted live rather than incremented — 30 pull requests, Qodo on all 30, 26 with at least one inline finding, 94 findings. **Findings 64/65, fourth instance, and the first where the fix was to change the sentence's tense rather than its numbers** | this PR |
| 141 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | The narrative for 140 quoted the stale sentence as *"twenty-nine … twenty-five … 90 in total"*, a combination that **never existed**: before 135 it read 28 / 24 / 90, after 135 it read 29 / 25 / 91, and the entry spliced the pull request counts from one state onto the finding count from the other. A fabricated quotation, in an audit narrative, about a sentence whose subject is quoting numbers accurately | **Fixed** — the entry quotes 29 / 25 / 91, the sentence 135 actually left behind, and says so explicitly. The check that would have caught it is the one 135 itself performed and this entry did not: read the value out of the file rather than out of the paragraph describing it. Nothing here is testable — a quotation of a sentence that no longer exists anywhere cannot be verified against anything — which is the argument for quoting from a diff rather than from memory | this PR |
| 142 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | The `gh api` command offered as the way to re-derive the anchored counts queries **inline comments on one pull request**. Four of the thirty have zero of those, and zero from that query is the same answer for *Qodo reviewed this and found nothing* as for *Qodo never reviewed this* — while the sentence it is meant to verify asserts the first for all thirty. **The ninth shape — "I could not tell" reported as "it did not happen" — in the command supplied to check a claim.** The recount actually performed did query both, so the README documented a weaker check than the one that was run | **Fixed** — two queries, with the reason for there being two written between them: inline findings from `/pulls/N/comments`, coverage from `/issues/N/comments`, which Qodo posts whether or not it finds anything. Collapsing them into one number is the mistake, not an inconvenience | this PR |
| 143 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | **Raised by the follow-up review, on the fix for 142.** The coverage query added to answer 142 was written without `--paginate`. GitHub returns thirty issue comments a page, so a Qodo summary posted after the thirtieth comment comes back as **zero** — which is the false *never reviewed* that 142 exists to prevent, reintroduced by the fix for it. **The ninth shape, inside the fix for the ninth shape.** Qodo also named the second-order defect: `gh api --paginate --jq '… | length'` evaluates the filter once per page and prints a count for each, so adding the flag alone would have replaced one wrong number with several | **Fixed** — both queries paginate, and both apply their filter with `jq -s 'add | map(…) | length'` over the concatenated pages rather than with `--jq`, so the aggregate is one number. Verified against #20 (15 findings), #26 (0 findings, 2 coverage — reviewed, found nothing, the case the single query could not distinguish) and #31. Latent rather than live today: no pull request here has yet exceeded one page, so nothing was wrong until somebody's thread got long | this PR |
| 144 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | **Third round on the same paragraph.** The two queries answer for **one** pull request — the README literally substitutes `N` — while the sentence they are offered as the check for is an aggregate over thirty: *30 reviewed, 26 with at least one finding, 94 findings*. None of the three figures can be derived from either command, so the paragraph presented an incomplete procedure as a complete one, which is a claim about the check rather than about the counts | **Fixed** — replaced with the loop that actually produced the numbers, which prints the sentence: `30 pull requests, 30 reviewed by Qodo, 26 with at least one inline finding, 94 findings`. Run before committing it, output pasted above. The three earlier findings on this paragraph (142, 143, 144) are now each explained beside the detail of the command that answers them, so the reasons travel with the code rather than living only here | this PR |
| 145 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | **Fourth round, and the sharpest.** 140 anchored the claim to a named merge; 144 replaced the check with a loop over *everything currently merged*. The two halves disagree: the moment #31 itself lands, the loop returns 31 / 31 / 27 / 97 and appears to **refute a sentence that is still true**. A verification procedure that contradicts a correct claim is worse than none, because the reader believes the procedure. Qodo also named the trap in the obvious fix — filtering by pull request *number* would be wrong, since creation order is not merge order | **Fixed** — the cutoff is #30's own `merged_at`, and the filter is on `mergedAt` rather than on the number. Verified both ways: against #30's timestamp the loop enumerates 30 pull requests and prints the sentence verbatim; against #29's it enumerates 29, which is the check that the cutoff is doing anything at all | this PR |
| 146 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | **Fifth round.** `gh pr list --limit 200` returns the *most recent* two hundred and the #30 cutoff was applied to those, so once two hundred more pull requests have merged the anchored set falls out of the window and the loop reports a smaller total — silently, and about a claim written to be permanent. The verification procedure for a sentence that cannot expire had an expiry date | **Fixed** — the enumeration paginates `pulls?state=closed` and drops the unmerged ones, so there is no window. Verified by extracting the fenced block **out of the README** and running it verbatim rather than running a copy: it prints the sentence. Also renamed the loop's `c` to `cov`, because the enumeration's `jq --arg c` reads as shadowing even though the for-header is evaluated once, before the body ever assigns it | this PR |
| 147 | [#31](https://github.com/aryangorde8/bumpsmith/pull/31) | *"The count is not maintained by hand — `tests/test_docs.py` reads the log's own table and fails if this sentence and that table disagree."* The guards check the **total** against the row count and check that the three parts sum to it. **The split is unchecked**: moving ten findings from `self-found` to `automated review` passes both, while the sentence beside them says it cannot. A guarantee stated about a guard that the guard does not make — **prose stating a property is not the property, tenth instance**, and the first time it has landed on a claim about the tests rather than about the code | **Fixed** — the sentence now says which half is guarded and which is not, and why the second half **deliberately** is not: the log marks provenance in prose and only when a finding is *not* Qodo's, so a row with no marker is a row nobody marked. Inferring *Qodo raised this* from that is reading an absence as evidence — the ninth shape — and it would be most confident about exactly the rows nobody had thought about. Making the split derivable means marking all 147 rows, which is worth doing and is not a thing to do the day before a deadline | this PR |
| 148 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | The README's break-taxonomy table says **"Six classes"**, numbers each one, and marks which have rewriters. Nothing read it. Adding `ITEMS_KEYWORD` to `BreakClass` left all three statements false — the count, the table, and the rewriter tally — and **all 750 tests passed**. This is the module table of findings 133–139 in the other table on the same page: the page was audited for one enumeration and the second was not looked for — *self-found by adding the class and noticing the suite did not care* | **Fixed** — five checks, each deriving a documented fact from the code: every member has a row, the `#` column equals `BreakClass.<NAME>.value`, no row names a member that does not exist, the rewriter column is read from `rewrite.has_rewriter`, and the prose counts its own table. `has_rewriter` is new and public, because a documented fact should be derivable rather than retyped. Verified by breaking each one singly with a no-op control and a byte-identical restore; the first attempt let an invented row die with a `KeyError` in a neighbouring test instead of failing its own, which is a guard that reports the wrong thing. **Prose stating a property is not the property — eleventh instance** | this PR |
| 149 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | **The scope defect, first of three rows on this pull request.** `items_keyword_sites` resolved every call against one file-wide import map, so a name pydantic bound and the module then rebound stayed pydantic's: `from pydantic import conlist` followed by `conlist = our_factory` left `conlist(str, min_items=1)` reported as a site, and `min_items=` renamed on a call the migration must not touch. Verified before it was accepted, and the verification is what made it serious — the same input reported a site through the **merged** `regex_keyword_sites`, which had been green since #11 | **Fixed at the root, not at the report.** `pydantic_names` now subtracts what the module body rebinds. Only *unconditional* rebindings count: `try: from pydantic import validator / except ImportError: validator = None` is the standard optional-import wrapping, the rebinding runs only when the import failed, and the first version of this fix broke the named test that pins it. `validator_parameter_sites` — merged the longest of any rule in the file — had the same defect unraised and is fixed here too, which is finding 139's lesson applied: fix where a defect *applies*, not only where it was raised. Measured across 443 files of three real repositories — every site the four rules found before the fix, they find after | this PR |
| 150 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | Second of three. `calls_in_scope` walked a comprehension with the enclosing names, so `[conlist(str, min_items=1) for conlist in factories]` was reported and rewritten as pydantic's. The comment two hundred lines below said this could not happen: *"a call is not shadowed by an iteration variable. A **name** is."* — true of the wrong node, since a call is resolved *through* a name. **Prose stating a property is not the property, twelfth instance**, and the first where the false sentence was written as the reason for not writing the code | **Fixed** — `nodes_in_scope` narrows at a comprehension, and the outermost iterable keeps the enclosing names because it is evaluated before the target it binds exists. That distinction was already made correctly forty lines away in `_uses_in_scope`, which is the uncomfortable part: the right answer was in the file | this PR |
| 151 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | Third of three. `module_scope_nodes` descended into class bodies, so `from pydantic import conlist` inside one class was collected as a **module** binding and renamed `min_items=` on an unrelated module-level call. Its docstring defended the descent — a decorator inside a class body does resolve through the class namespace — which is true and is a different question from what module scope contains | **Fixed** — the walk stops at class bodies, and `nodes_in_scope` adds a class's bindings on the way *in*. Python does not put class scope on a method's lookup chain either, so a class-body import is now invisible inside that class's own methods: the same wrong edit one level down, which review did not raise and the fix had to decide anyway | this PR |
| 152 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | A line that **gained** a site between scan and plan let the new one stand in for a scanned one: the planner took the first *n* of a fresh parse, so a keyword the scan never saw could be rewritten and the plan still call itself complete. A line that *lost* one was already handled | **Fixed for what line-and-count can see** — a line holding more sites than the scan reported is left alone entirely. The remaining case, one site replaced by another at equal count, is **not fixable at this interface** and is written down rather than implied: the scan carries `(path, line)`, and telling those apart needs the column. What the window needs is a writer editing the tree mid-run, and both leftovers stay honest for the same reason — the finder re-ran, so anything rewritten is a real site | this PR |
| 153 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | The taxonomy guards added in 148 mapped **every** un-backticked class cell to `None`, and all four semantic checks skip `None` rows. So `*(absent)*` — the one intentional exemption — could be replaced by an arbitrary word like `ABSENT` and the invented-class, numbering and rewriter guards would all pass it. A guard whose exemption is a *shape* rather than a *value* exempts everything malformed | **Fixed** — only the exact string `*(absent)*` maps to `None`; any other cell that does not name a class fails where it is parsed. Verified by writing `ABSENT` into the table and watching it fail, with a byte-identical restore | this PR |
| 154 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | The same five guards accepted **duplicate** rows: completeness collapses names into a dict, every other check validates each repeated row happily on its own, and the prose check counts physical rows — so duplicating a real row lets the README claim a class it does not have with all five green. **A guarantee enforced at one entrance of a building with two, fourth instance** — the module table got a uniqueness test in #29 and the taxonomy table, written nine days later, did not | **Fixed** — one row per named class, one number per row, exactly one absent row. Verified by duplicating a real row and by reusing a number, each failing the new guard and the restore checked byte-for-byte. The recurrence is the finding: the fix for a shape does not travel to the next thing of that shape unless somebody carries it | this PR |
| 155 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | **Second round, on the fix for the first.** `_unconditional_rebindings` reads the module body for assignments, loops and `with`, and does not read `:=`. So `(conlist := our_factory)` left the earlier pydantic import active and the call below it was still rewritten — the finding of row 149 surviving its own fix through the one binding form the fix did not enumerate | **Fixed** — a walrus is collected wherever it appears in a module-level statement, comprehensions **included**, since a walrus inside one binds in the enclosing scope. That case was written down in row 149's fix as knowingly missed and is now simply handled; the paragraph saying so is gone rather than left standing as a description of code that no longer behaves that way | this PR |
| 156 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | The new walk built a nested class's body scope from `names`, which inside a class body is the **enclosing class's** namespace. Python does not put an outer class on an inner class's lookup chain, so an import in `Outer` made an unrelated call in `Outer.Inner` look like pydantic's. The previous round fixed precisely this for *methods* and the docstring says so; the fix for the method case did not travel one node sideways to the class case | **Fixed** — a class body starts from `inherited`, the same scope a nested function gets, which is one word and covers both. **A guarantee enforced at one entrance of a building with two, fifth instance** — this time inside the fix for the fourth | this PR |
| 157 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | One `_inside()` map was computed from an entire class body and applied to every statement in it, but a class body binds **sequentially** rather than treating its whole body as static locals the way a function does. So an import written *below* a call reached back up to it, and an assignment written below a genuine pydantic call hid it. Both directions, one cause | **Fixed** — the class body's scope is advanced one statement at a time. The regression pins the direction with the two cases that would pass under either reading if only one were written: an import *above* a call still reaches it, and a shadow *below* one does not | this PR |
| 158 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | The first version of `root_validator_sites` decided a decorator was safe to rewrite by asking whether `pre` or `skip_on_failure` was passed **as a literal**. `@root_validator(**options)` passes neither as a literal, so it came back rewritable — and the rewrite would have appended a second `skip_on_failure=True` to a call that may already carry one, turning a repository that merely needed one argument into one that raises `TypeError: got multiple values`. Reading *I cannot see inside this* as *there is nothing inside this* is **the ninth shape**, and here it would have been written by the fix rather than found by it — *self-found while enumerating the decorator forms, before the first commit* | **Fixed** — a keyword whose `arg` is `None` marks the whole decorator unreadable, and an unreadable decorator is **reported as a site and left alone**: the error names it, so denying it is a site would be the same shape again in the other direction. `Plan.is_complete` goes false and the skip says why, which is the honest output — not *nothing to do here* | this PR |
| 159 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | `@root_validator(skip_on_failure=False)` — the refused form written out explicitly — was classified rewritable and then handed to the branch that appends after the last argument, producing `skip_on_failure=False, skip_on_failure=True`. **`ast.parse` accepts a repeated keyword and `compile` does not**, so this module's own re-parse would not have caught it: the tool would write a file that does not import, and the only thing that would notice is the suite going red on a syntax error in somebody else's code. The most serious of the nine | **Fixed** — an explicit `False` has its **value substituted**, not another keyword appended. The regression test asserts `compile`, not `ast.parse`, because that is the difference that hid it | this PR |
| 160 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | `@root_validator(\n)` is the same empty call with a newline in it. It scanned as rewritable and then skipped, because the empty-call rewrite replaces a single-line span and this has none — a repository using that formatting stayed unmigrated on a site that is statically unambiguous | **Fixed** — the argument goes in just past the `(`, so the decorator keeps the shape its author gave it instead of being reflowed by a migration tool. The `(` is found by walking forward from the end of the callable and **refusing anything but whitespace**: a comment can hold a parenthesis of its own, and inserting an argument into one writes a decorator that is a comment. That case has its own test | this PR |
| 161 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | The fourth consumer of the defect rows 149-151 fixed, and the widest. `root_validator_sites` did not use the scope walk at all — `ast.walk` against one module-wide map — so a function-local, class-scoped or rebound custom `root_validator` was given a `skip_on_failure` argument it does not take. `validator_parameter_sites` had it too, unraised, and had been merged the longest of any rule in the file -- both are fixed, one on each pull request of this stack | **Fixed for all four rules**, which is finding 139's lesson applied — fix where a defect *applies*, not only where it was raised. Decorators now resolve in the scope holding the `def` rather than the one it opens, so a body that assigns `root_validator` can no longer hide the decorator above its own head. Twenty-eight regression cases, each run against the pre-fix code first to confirm it reported the site | this PR |
| 162 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | **Second round.** The same sequential-class-body defect row 157 records, arriving from the other direction: a `root_validator` assignment written *below* a decorated method hid the decorator above it, and the genuine class 8 site went unreported — so the import-time failure the tool exists to fix would have been left in place, silently, after a run that said it had looked | **Fixed by row 157's change**, which is the useful part of the report: one cause, raised twice, on two pull requests, in two directions. It gets its own regression here because a fix that is only tested through the rule that happened to expose it is a fix that comes back | this PR |
| 163 | [#33](https://github.com/aryangorde8/bumpsmith/pull/33) | `global root_validator` followed by an assignment was read as local shadowing, so a real `@root_validator` on a class nested in that function was not reported. A declaration is not a binding: the assignment beside it writes the *module's* name, which is the very name the decorator resolves to. The safe direction of getting scope wrong — it loses a site rather than inventing one — and still a repository left unmigrated by a tool that said it had looked | **Fixed** — `global` and `nonlocal` names are subtracted from what a scope binds. The control is in the same table: take the declaration away and the same assignment shadows exactly as it did before, so the test pins the declaration as the thing that matters rather than the assignment | this PR |
| 164 | [#34](https://github.com/aryangorde8/bumpsmith/pull/34) | The trail sentence, its `gh api` cutoff and its printed output all moved from #30 to #33; the five paragraphs *explaining* them did not. Three still said the aggregate covered "the thirty" and "all thirty" pull requests. **This is finding 145's own defect, committed in the fix that cites finding 145** — 145 exists because a claim and its check must be anchored to the same merge, and the prose that argues for it was left anchored to the old one | **Fixed** — all three read thirty-three. The count of pull requests with no inline finding stays *four*, which is why the paragraph could go stale without reading wrong: 30−26 and 33−29 are the same number, and a figure that survives the change it should have failed is the reason the sentence needed checking rather than glancing at | this PR |
| 165 | [#34](https://github.com/aryangorde8/bumpsmith/pull/34) | The same edit left the sentence "the cutoff is #30's own `merged_at`" directly beneath a command whose cutoff is now `pulls/33`. The prose did not merely age — it *misdescribed the command printed above it*, which is worse than a stale number, because a reader checking the anchor would have been told the wrong one by the paragraph whose entire subject is the anchor | **Fixed** — the sentence names #33, the merge the command and the claim both use. Both rows are Medium and both are documentation, and they are logged at the same weight as the rest: the section they are in is the project's evidence for its own review discipline, and a wrong sentence there costs more than a wrong sentence elsewhere | this PR |
| 166 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | **The follow-up review raised five findings on #32 and the log recorded three.** This is one of the two that were dropped, found by pairing every Qodo thread to a log row before replying to it. `_unconditional_rebindings` counted a module-level `conlist: object` as replacing the import — but a bare annotation writes `__annotations__` and leaves the binding alone, so the name is still pydantic's and the genuine site below it went unreported. The same statement means three different things in three scopes: at module level and in a class body it binds nothing, and in a *function* body it binds without assigning, which is why `x: int` alone is enough to make reading `x` raise `UnboundLocalError` | **Fixed in both places it applies** — the module scan and the class-body scan — with the function case left exactly as it was and pinned by a control test, because there the old reading was right. Finding 139's lesson again, and the first time it has been applied to a defect that was *never logged* rather than one raised in the wrong place | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) |
| 167 | [#32](https://github.com/aryangorde8/bumpsmith/pull/32) | The other dropped one, and the more serious. The scope walk that replaced `ast.walk` in rows 149-151 never traversed **PEP 695 type parameters**, so `class C[T: conlist(str, min_items=1)]` lost a site that the walk it replaced had found. A rewrite of a traversal narrowed what every rule could see, on syntax this project's own `requires-python` guarantees is available, and nothing failed because the failure direction is a missing site | **Fixed** — bounds and defaults are walked, and the parameter names shadow, so a type parameter named `conlist` is not reported as pydantic's. Decorators are walked *outside* that scope because that is where they run. The shadow set is applied to the whole list rather than to the parameters after each one: that can only lose a site, never invent one, and needs somebody to have named a type parameter after a pydantic constructor | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) |
| 168 | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) | **Second round, on the fix for 167.** The type parameter names were subtracted while walking the bases and bounds and then the class body was started from the *unfiltered* map, so `class C[conlist]` shadowed the import above the body and not inside it — nor inside any method of it. Unlike 166 and 167 this fails in the **dangerous** direction: it reports a call that is not pydantic's, and the rewrite that follows edits somebody's unrelated code | **Fixed** — the body and everything nested in it start from the filtered map, so the parameter is bound for the whole statement it heads, which is what binding it means. The two ordinary cases are controls in the same table | this PR |
| 169 | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) | `ast.TypeAlias` was never given a branch, so `type A[conlist] = conlist(int, min_items=1)` read its value under the module's names and reported the type parameter as pydantic's. The same defect as 168 in a third statement — the fix for 167 taught the walker about type parameters in the two places it already knew about and not in the one it did not | **Fixed** — the alias gets its own branch covering the bounds *and* the value, because a type alias binds its parameters for both. A bound that really is a pydantic call is still reported, which is the control that stops the fix from being "ignore aliases" | this PR |
| 170 | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) | **Third round, on the fix for 168.** Filtering the type parameter out of what a method inherits also hid it from a `global` declaration: in `class C[conlist]` a method writing `global conlist` resolves to the *module's* import, and the genuine site went unreported. This is finding 163's rule meeting the type parameter work — 163 stopped the assignment beside a declaration from counting as a binding, and the other half of the same sentence is that `global` reaches past whatever shadowed the name, however far out it was shadowed. **Half the report is not reproducible and is recorded as rejected:** it offers `nonlocal` as the analogous case, and Python refuses that outright — `nonlocal binding not allowed for type parameter` — so the code it describes cannot be written | **Fixed for `global`, rejected for `nonlocal`.** The walker now carries the module namespace and a `global` name is restored from it. The fix is wider than the report: an ordinary class-body shadow with no type parameter anywhere was wrong in the same way and is fixed by the same change, which is the tell that the defect was the missing model rather than the type parameter code. `nonlocal` needs nothing — it names an enclosing *function* binding, which inheritance already models. Four regression cases, two of them controls | this PR |
| 171 | [#35](https://github.com/aryangorde8/bumpsmith/pull/35) | **Fourth round, an ordering bug in the fix for 170.** The module namespace was restored *after* `_inside`, so a function's own `from pydantic import conlist` was overwritten by a snapshot taken before its body was read — and under `global` that import writes the very module name the snapshot was of. A genuine site inside such a function went unreported | **Fixed** — the restore happens first and the body's own bindings land on top, which models both halves. Recorded alongside it, because the report is next to it and the answer is *not* a change: `global conlist` followed by a **non**-pydantic local import or assignment still reports the call. That is finding 163's recorded decision, it behaves identically on the commit before this branch, and it is order-dependent inside a function body in a way this walk does not model — the walker advances statement by statement through a class body and not through a function one. Left as it is rather than traded for 163's case two days from a deadline, and written down here instead of being discovered later | this PR |
| 172 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **`--out` can delete anything.** `build()` recursively removed whatever path `--out` named before recreating it, so `--out .` typed once would destroy a repository rather than fail. Reproduced before accepting: a directory holding `source.py` came back holding five HTML files and no `source.py` | **Fixed.** A build now drops a `.bumpsmith-site` marker into what it writes, and `_clear` refuses a non-empty directory that has no marker. Rebuilding from scratch is kept — it is what stops a page from a deleted run staying published — but it now only applies to directories this script made. An empty directory is still accepted, since nothing there is at risk | this PR |
| 173 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **A manifest outside `pages/` read its payloads from the wrong place.** `build()` resolved run pages against the manifest's own directory but called `index()` without that root, and `index()` re-reads every payload to put an outcome on each card. Reproduced: building a manifest from a temporary directory raised `FileNotFoundError` naming `pages/runs/only.json` — a path belonging to a different manifest | **Fixed** — `index()` takes the root and is given it. The failure mode worth noting is the one that did *not* raise: had a same-named payload existed under `pages/`, the card would have silently described a different run from the page it linked to | this PR |
| 174 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **A slug could climb out of the output directory.** Manifest keys became file names directly, and `[runs."../x"]` is valid TOML, so `out / "../x.html"` resolves above the directory the build was given. Confirmed by path arithmetic rather than by writing the file, since the payload lookup failed first | **Fixed** — a slug is checked against `[a-z0-9]+(?:-[a-z0-9]+)*` when the manifest is read, which is what a file name and a link can both carry, rather than what TOML permits. It raises at load rather than sanitising, because a slug that needs rewriting to be safe is a typo worth seeing | this PR |
| 175 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **The manifest's claims were shallower than its prose.** `expected` checked only how a run ended, so the flagship blurb could keep saying "nineteen sites" and "five" after a regenerated payload stopped containing them, and the test asserting the manifest against the payload would still pass. The finding is against the honesty mechanism itself, which is the part of this PR that most needed one | **Fixed** — every run gained `expected_steps`, restating its per-step claims: break class, whether the edit was applied, how many sites. Verified by breaking rather than by inspection — dropping fixture B's first step from 19 rewrites to 18 now fails the suite, and the payload was restored and sha256-checked afterwards | this PR |
| 176 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **Second round, on the fix for 174.** The slug pattern from 174 accepts `index`, and a run called that writes `index.html` — the gallery's own file. Reproduced: `build()` returned `index.html` twice and the run page won, leaving a site whose only entry point was the page that had replaced it | **Fixed** — `index` is reserved and rejected at manifest load. The marker deliberately gets no reservation: it begins with a dot and 174's own pattern already refuses those, so no slug can ever name it. A test asserts that second half too, so the reasoning is checked rather than trusted | this PR |
| 177 | [#36](https://github.com/aryangorde8/bumpsmith/pull/36) | **Second round, on the fix for 172.** `Path.is_file()` follows symlinks, so a link named `.bumpsmith-site` pointing at any regular file anywhere satisfied the marker check — and the guard written to stop `rmtree` reaching a directory it did not create handed over exactly such a directory. Reproduced: a directory holding `source.py` and a symlinked marker lost `source.py` | **Fixed** — the marker must be a regular file *and* not a symlink, and `out` itself is refused if it is a symlink. Worth recording as the shape rather than the instance: 172's guard asked a question whose answer it did not control, which is the same defect as 174's, one layer down | this PR |
| 178 | [#39](https://github.com/aryangorde8/bumpsmith/pull/39) | **High. The read reported its own failures as absence.** `_read()` was `cat MARKER 2>/dev/null || echo __ABSENT__`, so an unreadable file, a directory or a broken `cat` all exited 0 with the absence token. Leg 3's control — the leg the whole proof rests on — would then pass because something was *broken*, not because the marker was not there. The module's own `ABSENT` docstring asserted this distinction was preserved while the command it documented collapsed it | **Fixed** — the read now answers three ways: `PRESENT:` and the bytes, `ABSENT:` and nothing, or a non-zero exit under `set -e`, which `_ran` refuses. `[ -e ] \|\| [ -L ]` sends a directory and a dangling symlink down the *present* branch so `cat` fails there rather than reporting absence. Reproduced first, in a shell: a missing marker, an unreadable one and a directory all returned `exit=0 __ABSENT__`. Verified after: the same three now give `ABSENT:`, `exit=1`, `exit=1`. Removing the exit check makes one test fail | this PR |
| 179 | [#39](https://github.com/aryangorde8/bumpsmith/pull/39) | **The marker's contents could answer for the marker's absence.** Absence was a reserved *value*, so `--nonce __ABSENT__` wrote that string into the marker and leg 3 read it back as absence. Against a shared sandbox — the exact world leg 3 exists to catch — the proof printed *"the session held: sess-1 kept its sandbox across a new client, and a fresh session (sess-2) could not see the marker"*, which is false | **Fixed** — absence is a position, not a value: the prefix comes first and the payload after, so a marker holding `ABSENT:` reads back `PRESENT:ABSENT:` and parses as present. No contents can imitate the answer. Reproduced against the shared-sandbox fake, where the proof exited 0. `test_a_nonce_shaped_like_the_absence_answer_cannot_forge_the_control` now runs that same case; restoring the value-sentinel makes it, and only it, fail | this PR |
| 180 | [#39](https://github.com/aryangorde8/bumpsmith/pull/39) | **The proof normalised the evidence before comparing it.** `_ran()` stripped whitespace from every command's output, but `_write()` uses `printf %s` and preserves the nonce exactly. A marker of `"  spaced  "` was written and read back correctly by the sandbox and leg 1 still failed, because the value compared was not the value observed | **Fixed** — `_ran()` returns output verbatim and only the *error* message strips, since that is prose for a human. Checked against the recorded evidence first: `sandbox.json` holds `"...\nready\n"`, so the harness is byte-faithful and there is nothing to normalise. Re-adding `.strip()` fails `test_marker_bytes_are_compared_exactly` alone | this PR |
| 181 | [#40](https://github.com/aryangorde8/bumpsmith/pull/40) | **A positional reference, written into the same commit that made it wrong.** The paragraph beside the TrueForge table opened *"The last of those has a control"* — but the row it describes is the fifth of six, and the last is the fan-out. The same commit inserted that row, so unlike findings 164 and 165, where prose aged into being wrong, this prose was false the moment it was written. **Third instance of a positional reference going stale**, and the second time this session after I replaced two others with named ones for exactly this reason | **Fixed** — the paragraph names `session_reconnect.py` instead of pointing at a position, which is correct under any future ordering of the table. The finding total moved 180 → 181 with it, and the sentence recording the 129/129 divergence no longer quotes a split value that keeps drifting | this PR |
| 182 | [#41](https://github.com/aryangorde8/bumpsmith/pull/41) | **High. A wall clock cited to a recording that never held one.** The README's TrueForge table and `proofs/README.md` both stated *"2.1s at one worker, 1.1s at four, measured on the recorded run"*. `proofs/recorded/fanout.json` held five keys — `pydantic`, `pytest`, `workers`, `fanout`, `problems` — and no clock anywhere in the file; `fanout.log` recorded outcomes only; `proofs/fanout.py` never called one; and the committed run was `workers: 4`, so the one-worker half of the comparison had no artefact behind it at all. The numbers were almost certainly observed — commit `82c1838` states them in its own message — which is what makes this the repository's own shape rather than an invention: a remembered number promoted to a cited one, in the file whose whole argument is that claims are anchored to artefacts | **Fixed** — `proofs/fanout.py` measures the fan-out with `perf_counter` and records `wall_seconds`; both worker counts were re-run and committed, and the prose now cites the file each number lives in. Measured 29 August: **1.85s at one worker** (`fanout-one-worker.json`), **0.87s at four** (`fanout.json`). The clock is recorded and never asserted — a proof that fails because a laptop was busy is a proof nobody runs twice | this PR |
| 183 | [#41](https://github.com/aryangorde8/bumpsmith/pull/41) | **A property stated in three places and enforced in none.** `report.py`'s module docstring said values are *"only ever placed in text nodes -- never in an attribute"*; the README repeated it; and `tests/test_report.py` gave it as the reason its sweep was sufficient. `page()` interpolated the run's outcome into `<div class="end {_e(outcome)}">` — a payload value, in an attribute. `_e` quotes, so nothing was executable and no XSS follows from it; the defect is that escaping was the only thing holding a line three documents claimed was held by construction, and all 27 tests in the file passed either way | **Fixed** — the class is taken from the closed `_OUTCOME_BADGE` map, so an outcome nobody defined contributes no class, which is what it styled as anyway. Two tests added: one parses the document with `HTMLParser` and `convert_charrefs=True` and asserts no payload value reaches any attribute value *escaped or not*, and one pins the closed-set fallback. Verified by breaking — restoring the interpolation fails those two and nothing else. The three sentences were then narrowed to the two attributes that do vary, both computed here rather than quoted | this PR |
| 184 | [#41](https://github.com/aryangorde8/bumpsmith/pull/41) | **The packaging one-liner sold the optional half as the product.** `pyproject.toml`, `src/bumpsmith/__init__.py` and `publish.py`'s header all described the tool as *"an agent that turns a failing pydantic v1-to-v2 migration into a reviewed pull request"* — the sentence `pip show bumpsmith` and `help(bumpsmith)` print. Opening a pull request needs `--open-pr` and a typed `yes`; the default run never approaches it. The README's own opening line has always been accurate, which is how three copies of a stronger claim went on living beside it | **Fixed** — all three say the tool migrates a repository and keeps the change only once its suite has come back green, which is what the default does. `publish.py` quoted the old description in its header, so the quote moved with it: **fourth instance of a sentence corrected in one file and left standing in others** | this PR |
| 185 | [#41](https://github.com/aryangorde8/bumpsmith/pull/41) | **Second round, on the fix for 184.** The replacement description — *"migrates a repository from pydantic v1 to v2 and keeps the change only once its test suite has come back green"* — traded one overclaim for another. `Migration.complete` is false when a candidate file could not be parsed or a rewriter declined a site it matched, and `migrate()` keeps the edits anyway whenever the outcome is `MIGRATED`, because a green suite is real evidence and refusing to help a repository over one vendored file would be worse. So `pip show bumpsmith` would advertise a migrated repository for a run the CLI itself prints as `NOT COMPLETE`. `Migration.complete`'s own docstring had already written the rule I broke: *"'the suite passes' and 'the migration is finished' are different claims, and a report that ran them together would let the first quietly stand in for the second."* Qodo also found the precedent — **#16 fixed a misleading completion claim once already** | **Fixed** — all three copies now say the agent rewrites the breaks a suite reports, keeps the edits only once that suite comes back green, and **names whatever it could not do**, which is the clause that stops the sentence implying an ending. The README's own opening line carried the completeness wording before this PR touched anything; finding 184 moved a sentence out of the packaging metadata and this one moved the sentence's other half out of all three at once | this PR |
| 186 | [#42](https://github.com/aryangorde8/bumpsmith/pull/42) | **The index stopped one pull request short of the review.** After #42 merged, the last PR this table named was #41. Qodo had already reviewed #42 — Bugs (0), two coverage comments — and a reader of the finding index would conclude it had not been reviewed. **The ninth shape**: an absence of findings read as an absence of a review. Recording that as a *finding* is how the next pull request goes missing: this row is why #43 exists, and an empty review of #43 would have demanded #44 | **Fixed** — a pull-request table, not a finding per empty review. Every merged PR is a row there, this open PR is the last row, and the next PR replaces that row and adds itself. #26 and #42 (both reviewed, both zero inline findings) now appear without minting findings 187 and 188 | this PR |

Every finding has a row here and a fuller account below. Findings that arrived
in groups keep a shared section, because the group is often the unit that makes
sense of them -- but the group is not a substitute for the row.

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

## 66–69 · Four from Qodo on the README, all accepted

A documentation pull request, and the review found four real defects in it. Three
are claims about the *system* that the README got wrong; the fourth is in the
test written to stop exactly that.

### 66 · The guarantee stopped at bumpsmith's edits; the sentence did not

The README opened with "afterwards a repository is in one of exactly two states:
changed with a green run behind it, or byte-for-byte what it was. **There is no
third state.**" `LocalRunner` has no isolation and runs pytest directly in the
checkout, and `attempt()` tracks and restores only the `Edit` objects it planned.
Everything the suite writes is outside the transaction.

Checked rather than conceded, on the fixture the README quotes:

```
git diff:      []          <- every one of the 25 rewritten sites is back
git status:    []          <- which is what the README offered as proof
git status --ignored:  8 entries — .pytest_cache/ and 7 __pycache__/
```

**The verification was the defect.** `git status` answers "did any *tracked*
file change". It was published as proof of "byte-for-byte what it was", and the
fixture gitignores both artefact directories, so the check was structurally
incapable of seeing the thing it was cited for. Recurring shape 3 — an answer
good enough for one question reused to settle a stronger one — and shape 9, in
that "I did not look there" was reported as "there is nothing there".

Qodo also names the second exit from the two-state claim, and this one is by
design: if something modifies a file after bumpsmith edited it, `_restore` leaves
that file alone and raises `RevertError`, because overwriting somebody's work to
tidy up is worse than the mess. The tree is then in a state nobody chose. The
design is right and the README's description of it was wrong — so the limits
section now names it, along with its `STOP:` on stderr and exit code 2.

Fixed by scoping the claim to what is actually guaranteed, and by replacing the
proof command with `git diff` plus `git status --ignored`, which shows the
artefacts instead of hiding them.

### 67 and 68 · The top of the file drifted from the middle of it, and the top is what got quoted

These two arrived separately and share one root cause, which is the useful part.

**67:** `apply.py`'s module docstring said "an exception, **a crash**, or simply
forgetting all land in the same place". Reverting is a `finally` block, which
covers anything that unwinds the stack and nothing else. `SIGKILL`, `os._exit`, a
segfault in an extension module or a power cut all leave the edits on disk, and
there is no journal to recover from. Sixty lines below, `attempt`'s own docstring
had it right: "an early return, an exception, a forgotten call."

**68:** `failures.py`'s module docstring said "**Dispatch on the return code, not
on the text.** pytest emits three materially different layouts and the return
code names which one you have before any parsing begins." `RunShape.detect()`
tests `_COLLECT_BANNER.search(output)` for rc 2 and `_CONFTEST_HEADER in output`
for rc 4, and there are six layouts plus `UNKNOWN`. Sixty lines below, `RunShape`
had it right: "It is not, however, sufficient on its own."

So in both files the **summary at the top overstates, the precise statement lower
down corrects it, and nothing reconciles them.** Writing the README I quoted the
summaries, because a summary is what a summary is for. The result was a landing
page describing the opposite of the fail-closed behaviour actually implemented,
in a repository whose entire pitch is that its claims are checked.

That is a shape this log had not named, and it is worth naming: **a file's
opening paragraph is documentation of intent, and it decays differently from the
docstring next to the code.** The code keeps the docstring beside it honest.
Nothing keeps the overview honest, and the overview is the part that gets copied.

Both module docstrings are corrected, and both now say why the imprecise version
was wrong rather than quietly reading better.

### 69 · The test that was supposed to stop this did not pin what it claimed

`test_readme_documents_every_stop_reason` searched the entire README for
`` `NAME` ``. A member deleted from the table but mentioned in any other
paragraph would pass. The invariant advertised in its own docstring — and in
findings 64–65 above — is *table* completeness, and that is not what it measured.

**It did not reproduce today**, and saying so precisely matters: all fifteen
members occur exactly once, so every removal is currently caught. That is an
accident of the present text, not a property. Writing `` `MIGRATED` `` in one
example would silently unpin it.

Settled by construction rather than by argument. A README was doctored to delete
the `GREEN` row while mentioning `` `GREEN` `` in unrelated prose:

```
old condition (`GREEN` appears in README.md)  ->  PASSES — missed it
new scoped check (first cell of a table row)  ->  FAILS  — caught it
```

Then all fifteen members were removed from their row or list entry one at a time,
and all fifteen were caught. A stray-row check was added for the other direction:
a renamed member leaves its old row behind, and a reader looking up the name the
code returns finds nothing while the table still looks full.

**The verification had the same defect as the code.** Finding 69 exists because
the test generalised from a substring search; it survived my own review because
*I* generalised from breaking one member and one outcome. Two samples, fifteen
members, and a conclusion stated about all of them. The sweep above is what
establishes the property, and it is the reason the fix is trustworthy where the
original was only plausible.

### The boundary is now a test, because the prose has failed three times

Finding 66 is the third time the byte-for-byte claim has been wrong: **#9** for
CRLF, symlinks and partial rollback; **#16** for a revert that overwrote
somebody else's work; **#18** for the artefacts a test suite writes. Qodo cited
the first two itself, as precedent, which is a fairer summary of this repository
than anything in this log: *the guarantee keeps being right and the sentence
describing it keeps being wrong.*

Correcting the sentence a third time would leave the fourth available. So the
boundary is pinned: `test_what_the_suite_writes_is_outside_the_transaction`
drives the loop with a runner that writes `.pytest_cache/` and a `__pycache__/`
the way pytest does, then asserts both halves at once — every edit taken back
byte for byte, **and** every artefact still there, because it was never ours to
take. Verified by breaking it three ways: stop the runner littering, delete the
artefacts after the run, and leave the edit applied. All three fail.

`apply.py`'s own guarantee was already covered well — CRLF, BOM, codec aliases,
symlinks, permissions, partial-write rollback, and a whole-tree byte snapshot at
the loop level across ten tests. What nothing covered was the *edge* of it. A
guarantee with a well-tested middle and an undescribed edge is exactly the shape
that produces three findings in three pull requests.

---

## 70 · The fix for 66 made the same mistake 66 was about

Caught by the cold clone, running the README's own instructions from a fresh
checkout with a fresh fixture, which is the only reason it was caught at all.

The corrected paragraph said the run "left `.pytest_cache/` and seven
`__pycache__/` directories behind". Seven `__pycache__/` is right. `.pytest_cache/`
was not created by that run at all — the directory I read it from was dated
**2026-08-25 01:31**, from the previous day's manual pytest runs, and today's loop
never touched it. In a clean reproduction only the seven appear.

So the fix for finding 66 committed finding 66's error a second time, one
paragraph later. 66 was "a check that could not see what it was cited for";
this is "a listing that contained more than the run put there, read as though
the run put it there". Both are residue mistaken for evidence, and both were
produced by looking at a working directory that had been used for something else
first.

The general lesson is not "check harder". It is that **a development directory is
not an instrument.** It accumulates, and everything measured in one carries
whatever else has happened there. The cold clone exists precisely because it
cannot accumulate, and it earned its place here: the whole of #18 passed every
local check, CI, and a Qodo re-review, and this survived all of them.

Corrected to what reproduces, with the reproduction conditions stated in the
README rather than assumed.

---

## 71–75 · Five from Qodo on the page, all accepted

Every one is a *correctness* finding on `report.py`, and four of the five share
one cause worth naming before the individual entries.

**The page is the payload's second reader, and the payload was shaped for the
first one.** `--json` has existed since #16, and until #19 the only thing that
ever read a run was `__main__`'s terminal report — which holds the `Migration`
object, so it derives whatever it needs directly from it. It counts the files a
scan matched with `len({match.path for match in step.scan.matches})`, and it
prints each unreadable file's path *and* its reason, straight off the object.
`as_dict` never carried either, because nothing had ever needed them: it
serialised the plan's file count and the unreadable *paths*, and that was
sufficient for a review trail nobody was rendering.

The page cannot reach the object. It gets the payload, by deliberate design —
that is what stops the two renderings drifting into two descriptions of one run.
So it reached for the keys that were there, and got numbers that meant something
close to, but not, what it printed. **A payload adequate for its only consumer
stopped being adequate the moment it had two,** and the failure mode was not a
missing key raising an error — it was a present key answering a different
question. Findings 71 and 72 are both that. So the fix is in `as_dict`, not only
in the renderer: every key that counts something now says where the count came
from (`match_files` from the scan, `edit_files` from the plan), and `unreadable`
carries the reason the class has always held.

### 71 · The page promised evidence it did not show

The ending says a migration is **not complete** because "at least one site was
skipped or could not be read, and is listed with its reason above". `_step_block`
rendered `skipped` and never rendered `unreadable` at all. An unreadable file is
the more serious of the two — some v1 code the rule named is still in a file
nothing could parse — and the page named neither the file nor the reason while
pointing at a list containing both halves of neither.

The payload half is the older defect and the one that matters more: `as_dict`
serialised `str(u.path)` and dropped `u.reason`, so **`--json` has been losing it
since #16**. `Unreadable` has carried `path` and `reason` since it was written;
only the serialisation ever had one. Anything downstream of the JSON — this page,
a reviewer, a later tool — got "this file could not be read" with no way to find
out why.

Fixed in both places, and the page reads the old list-of-strings shape too: a
report written by an older build is still a report, and refusing to open the
evidence it was pointed at is a worse failure than showing it without a reason
it never carried.

### 72 · Two numbers from two sources, joined into one sentence

"Rule matched 19 sites across 2 files" read `sites` from the **scan** and `files`
from the **plan**. A file whose every match is skipped produces no edit, so it
disappears from a count offered as the rule's reach — understating exactly the
case a reviewer is being warned about, in the sentence warning them.

Fixture B never showed this, and could not: nothing is skipped there, so
`match_files` and `edit_files` are equal at every step. The measurement that
would have caught it is one the demo repository cannot produce.

The fix is the rename, not the substitution. `files` was a name that invited the
reading it got; `match_files` and `edit_files` cannot be confused for one another
because their names no longer let them.

### 73 · The tile contradicted the step directly beneath it

"Sites rewritten" summed every step's `rewritten` regardless of `applied`, so a
run whose plan was refused announced *19 sites rewritten* above a step correctly
reading *"planned but never written"*.

`rewritten` is what the plan intended; `applied` is what the disk received, and
`apply.attempt` can refuse a plan outright. This is the **second** time this file
has read `applied` wrongly — the first was found before the PR opened, by
rendering a run and reading it, and it was the same confusion in the other
direction. Recorded as a repeat because that is the useful part: the summary and
the detail were deriving one fact from two places, and one of them was wrong.
They now read it from the same place.

### 74 · A reversion announced for runs with nothing to revert

The fourth tile chose its noun from `kept` alone, so every `already-green` and
`untouched` run — both of which apply nothing by definition — rendered "0 changes
taken back". True in the sense that nothing is also nothing, and false in the
sense a skimmer takes it: that there had been something to take back.

The label is now chosen from `applied`, which is the quantity actually printed on
the tile. A run with no applications has neither kept nor reverted anything, and
says so.

### 75 · Two reports, one path, both reported written

`--json out --html out` wrote the JSON, then overwrote it with HTML, then printed
two successful writes and exited 0. The report the user asked for was gone and
nothing said so.

Refused, and refused **before the suite runs** — the migration takes minutes and
edits the repository, and the whole error was visible from the command line
alone. Paths are compared resolved, because `out.html` and `./out.html` are one
file and a check on the spellings would miss it. The test asserts stdout is
completely empty, not merely that the exit code is 2: a bad invocation should
cost nothing, and "nothing was printed at all" is the only assertion that proves
the loop was never entered.

## 76–77 · Two more, found the same way the last three were

Neither came from Qodo. Both came from doing the thing that found three defects
before this PR opened: render a real run, and read it.

### 76 · A docstring naming a function that was never written

`page()` documented its argument as "exactly what `bumpsmith.__main__.report_payload`
builds". There is no `report_payload`; the payload is assembled inline in
`main()`. The reference was to a function I had apparently intended and then not
needed — a docstring describing an earlier draft of the code beneath it.

This is finding 59's shape and 67/68's shape again, in a file written after both
were logged. It is now described by what it is rather than by a name that has to
keep existing.

### 77 · The stop reason did not read as a sentence

Rendering fixture B produced:

> It stopped at `no-rule`. the failure classified as UNKNOWN, which does not
> narrow to one rule…

Every `Stop` reason is written as a lowercase clause meant to *follow* something.
The terminal report gives each one its own indented line, where that works
perfectly. The page ended the sentence and then began a new one in lower case.

No test could have caught this and none should have: it is a defect in how the
page *reads*, on a page whose entire purpose is to read well to somebody who was
not there. It is now a dash rather than a full stop, and the sentence is
terminated — unless the reason already ends in punctuation, which
`the suite could not be run: {exc}` can.

**Reading the rendered output has now found five defects across this one PR and
every one of them was invisible to a passing suite.** That is not an argument
against the tests; it is the argument for the page. A report nobody reads is a
report nobody checks.

---

## 78–79 · Two from reading a pull request this actually opened

Both in the body `bumpsmith.publish` writes. Neither is a crash, neither could
fail a test that did not already know to look, and both were on a real remote
before they were found — which is the argument for opening one against a bare
repository in a temporary directory before opening one against anybody's project.

### 78 · "of which 1 were rewritten"

Verb agreement, in the sentence that carries the number a reviewer is being asked
to accept. The module has a `_count` helper for exactly this problem and it was
used for the nouns on either side -- `1 site`, `1 file` -- and not for the verb
between them. The half of the sentence that was hand-written is the half that was
wrong, which is the ordinary shape of this.

### 79 · A gap stated where there was no gap

> The failure named one site. The rule matches **1 site across 1 file**, of which
> 1 was rewritten.

Three numbers, all the same, arranged to look like a comparison. The whole reason
this project emits a rule rather than a patch is that those figures usually
differ; saying so when they do not spends a reviewer's attention and returns
nothing, and it makes the case where the numbers *do* differ harder to notice
because the sentence is always there.

`bumpsmith.report` already decided this exact question and decided it correctly
-- the gap bar is suppressed when `found <= reported`, with a comment saying that
drawing one anyway "would dress up the least interesting case as the point". The
markdown body was written afterwards and did not inherit the decision.

**Two renderings of one run, and one of them had learned something the other had
not.** That is finding 71's shape at one remove: not a payload with one consumer,
but a *judgment* with one consumer. Both now suppress it, and there is a test on
each side rather than a comment pointing at the other.

---

## 80–90 · Eleven from Qodo on the pull request, all accepted

The largest review this repository has had, on the one module where being wrong
is expensive, and **it found things the module's own docstring claimed were
handled.** That is the entry. `publish.py` opened with three paragraphs arguing
that the destination must never be inferred and that nothing but the migration
may go out, and then inferred the destination in three places and let four
different kinds of other people's work through.

### The destination was still being inferred — 80, 81, 82

**80 · The URL shown was the one that would not be used.** ``git remote get-url``
answers about *fetching*. ``git push`` uses ``pushurl`` when a remote has one,
and a remote may have several -- in which case one push goes to all of them, and
none of them is the URL the approval named. The whole module exists to make the
destination visible before somebody agrees to it, and it read the destination
with the one git command that looks like it answers the question and does not.

Now ``get-url --push --all``, and **more than one push URL is refused outright**.
"Send my code to these three places" is not something to slip past a person
inside a migration tool's prompt.

**81 · The fingerprint bound the URL and the push used the name.** The gate binds
an approval to the resolved URL, and then ``_do_open`` pushed to
``proposal.remote`` -- a name ``git remote set-url`` can re-point in between. The
approved destination and the actual one were connected by nothing but the
assumption that nobody had moved it.

The fix is not a re-check, it is removing the indirection: **the push names the
URL.** A re-check would have left the same class of problem one loop tighter.

**82 · The pull request went wherever ``gh`` felt like.** No ``--repo`` and no
owner-qualified head, so repository selection fell to the checkout's own remotes
-- which, for a migration, is *the repository this was cloned from*. The branch
would go to the approved fork and the pull request would be attempted against
somebody else's project. Now ``--repo`` comes from the approved URL, and a URL
that is not GitHub means ``gh`` is not run at all: a bare repository is a fine
place to push a branch and not a place pull requests exist, and reporting ``gh``'s
failure there described something going wrong when nothing had.

### Staging the right paths stopped almost nothing — 83, 84, 85

This is the cluster worth remembering. The module said:

> The commit stages the migration's own paths, explicitly, one by one. Never
> ``git add -A``.

True, verified by a test, and **not the guarantee it was standing in for.** Four
routes carry somebody else's work into a pull request and the pathspec closes
one:

**83 · The branch, not the commit.** ``checkout -B`` starts the branch at ``HEAD``.
A pull request is a diff against the *base*, so a checkout three commits ahead
publishes all three no matter what the new commit touches. Restricting the
commit never addressed the branch.

And the deciding argument turned out not to be about other people's commits at
all: **the suite that went green ran against ``HEAD`` plus these edits.** A pull
request against a different base is a different change from the one that was
tested, offered with this project's whole claim attached. So ``HEAD`` must *be*
the base, and anything else is refused.

**84 · The index, and the file itself.** One finding, two mechanisms, and neither
is touched by choosing a pathspec:

* ``git commit`` commits what is *staged*. A caller who had run ``git add``
  before starting the migration got their staged work in bumpsmith's commit,
  whatever pathspec added ours. Now ``commit --only`` with the pathspec, and a
  non-empty index is refused before that.
* ``git add -- path`` stages that file's *current* contents -- the migration's
  edit **plus** whatever was already uncommitted in it. Staging the right path
  does not make the right change. Each path is now checked against what the
  migration first read, which is why the equivalent question inside
  ``_originals_of`` needed the *first* ``before`` per file rather than the last.

**85 · The branch already existing.** ``-B`` resets it, and `DEFAULT_BRANCH` is
deliberately reused across runs -- so the *ordinary* case was the dangerous one,
leaving a previous run's commit unreachable. Now ``-b``, and an existing branch
is refused with what to do about it.

### The command line — 86, 87

**86 · An empty ``--open-pr`` was absorbed rather than answered.** ``--open-pr
"$REMOTE"`` with the variable unset asks for a pull request and names nowhere; a
truthiness test read that as never having asked, and the migration exited 0
having silently skipped the operation. This is finding 75's principle -- a bad
invocation is answered, not absorbed -- failing in a flag added two commits after
75 was fixed.

**87 · A pull request that did not happen exited 0.** The branch is pushed, there
is no pull request, and the exit status said success. Now 2: 1 means the suite is
red, and here the suite is green -- what failed is the operation. A *refusal*
stays 0, because somebody was asked and said no, and making that cost something
would make it expensive to say no.

### And three on the proof itself — 88, 89, 90

A proof that passes for the wrong reason is worse than no proof, because it gets
quoted.

**88 · It compared branch names.** A refusal that rewrote ``trunk``, or altered an
existing branch, changed no *name* -- and the recorded conclusion said the remote
was untouched after every refusal. Now every ref is compared with its object.
Verified by making the approved push also force-update ``trunk``: the set of
names is unchanged and the run fails on ``moved``.

**89 · It ignored the exit status.** Verdicts rested entirely on whether a branch
appeared, so a crash before the prompt was ever printed would be recorded as a
refusal correctly honoured. Each case now states the status it expects. Verified
by making refusals exit 1: every remote check still passes and the run fails.

**90 · A timed-out child survived.** ``communicate`` raising leaves the process
running -- here, a migration with an approved push in front of it, holding the
temporary repository the proof is about to ``rmtree`` underneath it. Reproduced
by making the fixture suite sleep so the timeout lands mid-run: without the kill,
one ``python -m bumpsmith`` outlives the proof; with it, none.

### What this review is evidence of

Every one of the eleven is in code whose docstring is the argument for it. The
module reasons carefully about the destination and then reads it with the wrong
command; it reasons carefully about other people's work and then defends the
narrowest of the four routes it travels by.

**A guarantee stated well is not a guarantee tested well, and prose is where the
two diverge without anything failing.** This log already has a name for the
neighbouring shape -- *"prose stating a property is not the property"*, findings
60 and 69, where the fix was to stop stating it and start pinning it. These are
the same failure with the confidence turned up: the property was not merely
unstated, it was argued for at length, in a file that did not have it.

---

## 91 · `_git` strips its output, and one git format needs the whitespace

Self-found, fixing 84, by running it.

The check for a dirty tree read ``git status --porcelain`` and looked at
``line[:2]`` for the two status columns. ``_git`` ends with ``.strip()`` -- fine
for every other git command in the module, and it eats the leading space of the
*first* porcelain line, whose first column is a space precisely when a change is
unstaged. So the migration's own modified file arrived as ``M `` instead of
`` M``, read as staged, and every publish was refused with a message naming the
one file that was allowed to be there.

Caught in a second by the end-to-end proof and invisible to the unit tests, which
were feeding the fake git a string that had never been through ``strip``.

Replaced with ``git diff --cached --name-only`` and ``git diff --name-only``:
two questions asked separately, each answering exactly one of the two things 84
is about, and neither with any leading whitespace to lose.

---

---

## 92–97 · A cold clone, and the question nobody had asked pytest

Six findings, none from a reviewer. Three came out of running the merge gate on
[#20](https://github.com/aryangorde8/bumpsmith/pull/20) — a fresh clone, a fresh
venv, all four checks, the fixture end to end. Three more came out of trying to
fix the third one, and were caught by breaking the guards written for it.

### The question

The cold clone left `.pytest_cache/` somewhere the README said it would not be.
Chasing that turned up something the project had never asked: **which
configuration file governs the subject's suite?**

pytest does not read its settings from the directory it runs in. It walks
*upward* for the first file that counts as an inifile and takes `rootdir`,
`addopts` and `testpaths` from whatever it finds. `fixtures/B` has a
`pyproject.toml` with no `[tool.pytest.ini_options]`, so the walk continued out
of the fixture and landed on **bumpsmith's own**. The tell was in pytest's own
output all along — the nodeid it prints for the fixture's suite is
`fixtures/B/tests/test_emnify.py`, a path relative to the bumpsmith checkout.

Same tree, same interpreter, same command, on a project with one unregistered
marker:

| where the subject sits | what pytest does |
|---|---|
| under a checkout that configures pytest | `1 error`, exit **2** |
| anywhere else | `1 passed, 1 deselected`, exit **0** |

### Why it is a refusal and not a note

Only one of the two directions is loud. A *stricter* outside configuration turns
green into red, and the cost is a wasted migration attempt against a break that
was never a pydantic break. An outside configuration that **deselects** —
`-m "not slow"`, a narrowing `testpaths`, an `--ignore` — runs fewer tests than
the repository's own suite would, so a suite that should have gone red goes green
and the loop keeps the edits.

That second one is `WRONG_PLACE`'s defect arriving by a different road, and
`WRONG_PLACE` is already a hard stop. `migrate.py` had argued the general form of
this in its own docstring — *"a paragraph is not an enforcement"* — about a
different mechanism, one level up.

**Latent, not live.** Of the four fixtures only B lacks a pytest configuration of
its own, and B uses no markers, so nothing was misbehaving. That is the kind of
luck that stops being true without anything failing.

### The shape of the fix

`Stop.FOREIGN_CONFIG`, checked once before the first run, never after a verdict
exists to argue with — a scripted green answer sits in the test and is never
consumed, which is how "before" is asserted rather than inferred.

The check is deliberately blunt. Rather than decide which pytest settings are
dangerous — a list that would be wrong the first time pytest grows an option —
an outside inifile that sets **anything at all** is refused and one that sets
nothing is allowed through. An empty `[pytest]` counts as an inifile while
contributing no settings, so `python -m bumpsmith.fixtures` writes exactly that
barrier into `fixtures/`, and the documented workflow runs unchanged: verified
end to end, three breaks peeled, reverted, working tree hashing to the same tree
object as `HEAD`.

### The three the break run found

Sixteen guards were broken one at a time to check the suite noticed. Thirteen
were caught; **three were not**, and each was a real defect in the new code:

- **95** — `_runs_pytest` had a `-m pytest` branch. Deleting it changed no
  answer, because the module argument *is* the bare word `pytest` and the name
  check matches it one iteration later. A parametrised test covering
  `python -m pytest` passed with the branch gone.
- **96** — the test named for an *empty* `pytest.ini` used a file that still
  carried `[pytest]`. The flag that makes that filename count regardless of
  contents — which is the whole reason the barrier works — was never exercised.
- **97** — `interpolation=None` guarded a path the code could not reach.
  configparser interpolates on value *access*, and only names were being read.
  Fixed by reading the values too, which makes the guard load-bearing and turns
  the refusal from "sets `addopts`" into "sets `addopts = -m 'not slow'`".

97 is the one worth keeping. A defensive line with a comment explaining why it is
needed, in code that cannot reach it, reads exactly like a guard — and the test
written for it passed either way. It is the same shape as
[80–90](https://github.com/aryangorde8/bumpsmith/pull/20): *a guarantee stated
well is not a guarantee tested well.* The break run is what tells them apart.

---

## 98–103 · Five from Qodo, on a module whose whole job is to be right about pytest

The largest single lesson in the log, and it is not about any of the five
individually. `rootdir.py` exists to encode **another program's behaviour**. Every
one of these findings is a place where it encoded what that behaviour used to be,
or what it would be if pytest were simpler than it is.

### The pinned pytest was never asked

**98** is the one that matters. `CANDIDATES` listed four filenames. The pinned
pytest — 9.1.1, in this repository's own dev extra — reads **seven**, and the
three that were missing (`pytest.toml`, `.pytest.toml`, `.pytest.ini`) all
*outrank* the one that was there.

Both directions were live:

- a foreign configuration in one of the missing names is **not seen**, and the
  refusal never fires — the dangerous direction;
- a subject that configures *itself* in one of them is walked straight past and
  **refused for a configuration it had already overridden** — a false refusal on
  the exact arrangement the refusal message tells people to adopt.

The rules are not uniform, either, which is the part no amount of care would have
produced from first principles:

| file | counts when |
|---|---|
| `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini` | always, even empty |
| `pyproject.toml` | `[tool.pytest.ini_options]` present — **or** `[tool.pytest]` non-empty |
| `tox.ini` / `setup.cfg` | `[pytest]` / `[tool:pytest]` present |

An empty `[tool.pytest.ini_options]` counts; an empty `[tool.pytest]` does not.
Nobody would guess that. It was measured.

**The instrument was there all along.** `pytest --collect-only -v` prints
`configfile:` and names every file it ignored:

```
configfile: pytest.toml (WARNING: ignoring pytest config in .pytest.toml,
pytest.ini, .pytest.ini, tox.ini, setup.cfg!)
```

pytest will simply *say* which file it chose. The original module was written
from a reading of how discovery works instead of from asking, and
`test_pytest_agrees_about_the_barrier` — the one test whose whole point was to
check the module against the real program — only ever exercised `pytest.ini`, so
it agreed about the one name that was right.

### The other four

**99** — `pytest -c FILE` replaces discovery. The guard walked upward regardless,
so it could clear a run whose explicitly named configuration sat outside the
tree, and refuse one that explicitly named its own. Verified by running pytest
with `-c` against a subject that already had a barrier: the barrier was ignored.

**100** — `runs_pytest` matched the word anywhere in the argv, so `make pytest`
was refused. The docstring one line above promised the opposite. This is also the
answer to finding **95**: that `-m` branch was only dead *because* the scan was
too wide. Narrowing it made the branch necessary again, so 95 was a correct
observation about incorrect code, and deleting the branch was right at the time
and wrong afterwards.

**101 / 102** — the barrier. `OSError` escaped `write_barrier` while `clone_all`
converts only `FixtureError`, so one unwritable barrier ended the whole command
in a traceback rather than failing that fixture. And `write_barrier` accepted any
existing path, **including a directory** — pytest reads configuration from files
only, so the promised protection silently was not there. A guard that appears to
be working is worse than an absent one.

### 103, and the pattern it completes

Twenty-five guards were broken one at a time. Twenty-four were caught. The one
that was not: the test written for **101** used a *directory* to provoke the
failure — which trips **102**'s check first, so the `OSError` wrapping it was
written for was never reached.

That is the third time in two pull requests: **96** (a test for an empty
`pytest.ini` that used a file with a section), **97** (a guard the code could not
reach), and now **103** -- with **107** on #22 making four. The shape is always
the same — *the test provokes a
different failure than the one it names, and passes either way.* Reading it will
not find it. Only breaking the line it claims to cover will.

---

## 104–105 · The task that turned out to be the wrong task

The plan for Friday said **Fixture F4 (class 5)** — write the rewriter for
`REMOVED_INTERNAL` and take the project from three rewritable break classes to
four. The measurement said not to.

F4 is the real repository that carries this break. `proto.py:10` imports
`pydantic.utils:DUNDER_ATTRIBUTES`, which v2 deleted, and `proto.py:40` still
reads it. Both mechanical edits a rewriter could make were run against F4's own
source under pydantic 2.13.4:

| candidate edit | result |
|---|---|
| delete the removed import | `NameError: name 'DUNDER_ATTRIBUTES' is not defined` |
| repoint it at the `pydantic.v1` shim | `AttributeError: 'FieldInfo' object has no attribute 'field_info'` |

The second is the more dangerous. The import *succeeds*, so the failure moves to
a different line and would come back classified as a fresh, unrelated break —
progress that is really a loop.

Fixture C is the same repository one migration later, so upstream's real fix is
on record: drop the dunder check because v2's `__dict__` no longer carries those
keys, `__fields__` → `model_fields`, `field_info.repr` → `.repr`. Three
coordinated semantic changes, none derivable from the import line.

So `_PLANNERS` omitting this class was already right, and the docstring saying
*"only some of them reduce to an edit safe enough to write without asking"* was
already right. **What was wrong was one level up.** The rule said "stop importing
`X` from `Y`" and the scan reported the import. A person doing exactly what they
were told got the `NameError` — the tool was correct about the site and silent
about the consequence, which is a way of being wrong that reads as being right.

The fix is not a rewriter. It is a scan that reports uses beside sites, a `count`
that still means sites because that number is shown to somebody immediately
before they approve an edit, a `_by_path` that filters to sites so no rewriter
written later can be handed a use to edit, and a refusal that names the lines
that would break — because `UnsupportedRuleError` is the sentence read at the
moment the work is handed back to a human.

**105 is finding 95 for the second time.** Ten guards were broken one at a time
and nine failed a test. The tenth, `if not bound: return`, failed nothing —
because the loop below it tests `node.id in bound` and already yields nothing for
an empty set. It is not a guard. It is a genuine optimisation, so it stays, now
labelled as one and carrying the measurement that earns it: 12.6ms → 5.9ms on a
file that does not import the symbol, which is nearly every file in a scan.
Finding 95 was deleted for being unreachable and had to come back two commits
later; this one is kept, which is the other correct answer to the same question.

→ **The lesson, named: advice that is true can still be incomplete enough to
break the repository that follows it.** The neighbouring shapes are 60/69
(*prose stating a property is not the property*) and 80–90 (*a guarantee stated
well is not a guarantee tested well*). This is the third: **a correct statement,
acted on as instructions, producing a defect the statement never mentioned.**

---

## 106–107 · The paragraph one function above the mistake

Qodo raised exactly one finding on #22, and it was on the code written to fix
104: `_removed_symbol_sites` collected imports from every lexical scope into one
file-wide set of names, then called every load of that spelling a use.

The claims were checked before the finding was accepted. Three of four
reproduced — a parameter sharing the spelling, a function-local import leaking
into module scope, and a comprehension target. The fourth, "class/method names",
did not: attribute access is an `Attribute` node, never a bare `Name`, and was
already correct.

The docstring had *pre-defended* this: "naming one line too many costs a
moment's attention, and naming one too few costs the `NameError` this exists to
prevent." That direction is right, and it is not a defence of what shipped. The
refusal does not merely list lines — it says **"the name is still read at X:N, so
removing the site alone would replace this error with a NameError."** For a
parameter, that sentence is false about a specific line in somebody's code. And
with `_USES_LISTED = 5`, false matches can fill the list ahead of the real use.
Over-reporting is the safe direction for a list that is read rather than edited,
but only while what is said about each line is true.

**The worst part is where the answer already was.** `calls_in_scope` sits one
function above, and its docstring is this finding, written before the bug:

> One module-wide import map applied to the whole tree gets this wrong in both
> directions: it misses a pydantic import made inside a function, and -- the
> dangerous half -- it claims a *parameter* named `constr` is pydantic's

The project had met this problem, solved it, and written down which half was
dangerous. The new function was written next to that paragraph without using it.
The fix reuses the machinery it should have used first: `_locally_bound` for what
a scope binds, subtracted before the scope's own import is added, plus
comprehension scopes, which `calls_in_scope` does not need and a name-resolver
does.

**107** is the fourth appearance of the shape 96, 97 and 103 named. The test for
unpacking used `[a for (a, X) in pairs]` — where the only `X` is a *store*, and a
store is never a use whether unpacking shadows or not. It passed with the guard
removed. Fifteen guards were broken one at a time; fourteen failed a test, and
the fifteenth found this.

→ **The lesson, named: the fix for a defect is written at the moment you are
most convinced you understand it.** 104 was found by measuring instead of
assuming; 106 was created three hours later by assuming instead of reading the
function directly above. Neighbouring shapes: 95/105 (*a branch that is not the
reason the code behaves as it does*) and 80–90 (*a guarantee argued for at
length in a file that did not have it*).

---

## 108–109 · Reading the README the way a stranger would

Both of these were found by following the README from a cold clone — installing
from it, running its commands, and checking its claims one at a time — rather
than by anything failing.

Most of it held, and the strongest claim held best. The section headed *"One run,
verbatim"* is **byte-identical** to a real run against fixture B from a fresh
clone. `git -C ./fixtures/B diff` is empty; `git -C ./fixtures/B status
--ignored` is exactly the seven `__pycache__/` it says and nothing else, which is
also #21's barrier still doing its job. `--html` is 7,716 bytes with **zero**
external references and **zero** script tags. "No runtime dependencies" is true:
`pip install -e .` brings in nothing but bumpsmith.

Two things were wrong, and both are about the review trail the README calls a
deliverable.

**108.** The README said the log holds **65 findings**. It held 107 — stale by
42. The sentence that says it ends:

> Two of the entries are that lesson failing: a stale number was corrected in one
> file and left standing in two others a `grep` away.

The paragraph describing the stale-number defect contained a stale number. That
is findings 64 and 65 exactly, recurring inside their own description.

The fix for the `Stop` count was to stop restating it, because the table was on
the same page. That is not available here: the log is another file, and how much
review this project has actually had is worth telling a reader. So the number is
restated and **checked** — `tests/test_docs.py` reads the log's table and fails
if the sentence disagrees with it, in the total and in the three parts summing to
it.

**109.** The log's index table skipped **20 through 31**. Twelve findings, all
three of that round's pull requests (#10, #11, #12), had prose sections and no
row.

This was a *documented* choice, not a silent omission -- a note two lines under
the table said those rows are described below because they arrived in groups.
The first draft of this entry called them "indistinguishable from one nobody
recorded", which was too strong, and the note is why. What the note defends is
still the weaker arrangement: a group section explains a finding, and only a row
makes it findable by the number everything else in this project refers to it by.
The twelve rows are written from the prose, the index is contiguous, and a test
fails on the next gap.

**110, from Qodo, on this pull request.** Adding those rows made the note false.
The log then told a reader both that 20-31 are indexed and that they are not.

That is 108's shape -- a sentence left standing beside the thing it described --
occurring inside 108's own fix, two lines below the table being edited, in a
pull request whose entire subject is stale sentences. It was found by review and
not by me, and the reason is plain: I read the rows I was inserting and not the
line under them.

**111**, immediately after: the guard written for 110 searched the whole file and
failed on this very section, which has to quote the sentence it bans. That
mistake is already recorded in `test_docs.py`'s module docstring -- made once,
undone, written down, and made again by the test added to prevent a repeat. It is
now scoped to the prose between the index and the first section, and a no-op
control confirms the scoping holds rather than merely passing.

**Finding 29 is worth the detour.** It is one of the twelve that had no row, and
it reads: *a function parameter named `constr` was treated as pydantic's, because
one module-wide import map was applied to every call in the file.* That is
**106**, which Qodo raised on #22 — the same defect, in a new function, written
directly beneath the docstring that `calls_in_scope` carries *because of finding
29*. The project fixed it on #12, wrote down which half was dangerous, and
reintroduced it eleven pull requests later.

→ **The lesson, named: a defect the project has already fixed and documented is
not thereby prevented.** 29 → 106 is that in its clearest form, and 108 → 110 is
it happening within a single pull request. Neighbouring
shapes: 64/65 (*a summary restating a number the table already owns*) and 60/69
(*prose stating a property is not the property*).

---

## 112–113 · Concurrency, where a wrong figure is quiet

Two findings from one module, both found the same way — by breaking each guard
and checking something failed — and both the same family: **a guard not doing the
job its name claimed.**

**112 — a deadline that stopped nothing.** `fan_out` takes a timeout, waits on
the futures with it, and records anything unfinished as `Unreached`. All correct,
and all defeated by the line above it: the pool was entered with `with`, and
`ThreadPoolExecutor.__exit__` calls `shutdown(wait=True)`. The timeout expired,
the code moved on, and the *exit from the block* then blocked until the abandoned
job finished anyway. A caller asking for a thirty-minute ceiling would have waited
as long as the slowest sandbox took.

Nothing failed. The test asserted the right things and got them, because by the
time it looked, the hung job had completed and recorded a real result. What gave
it away was the clock: 20.27s, in a file whose other twenty-nine tests take under
a second together, on a test whose entire subject is *not waiting*. A timeout that
stops waiting has to stop waiting everywhere, including in cleanup nobody wrote.

**113 — a guard whose test was satisfied by somebody else's guard.**
`test_workers_must_be_positive` asked for a `ValueError` matching `"workers"`.
Deleting the check under test still passed, because `ThreadPoolExecutor` rejects
`max_workers < 1` with *"max_workers must be greater than 0"* — which also
contains the word. The test was true of the standard library.

This is **the fifth instance** of the shape named at 96, 97, 103 and 107: *the
test provokes a different failure from the one it names, and passes either way.*
Four of the five were found by breaking the guard rather than by reading the
test, which is now the only method this project trusts for the question.

The guard turned out to be real, and the case that proves it is the empty one.
With no jobs, `fan_out` returns before the pool is ever built — so nothing else is
there to object, and `fan_out([], workers=0)` would have returned an empty result
as though it had been asked to do nothing. The fix is both halves: match on this
module's own wording, and test at zero jobs.

**One guard was broken and correctly changed nothing.** `counting()` filters to
attempts that ran, and iterating every attempt gives the same answer today,
because an unreached attempt's `outcome` is `None` and `None` is never an
`Outcome` member. Finding 95's question again, answered as 105 was: kept, because
it states the rule where the rule matters rather than inheriting it from another
class's behaviour — but labelled redundant instead of left looking load-bearing,
with the property it leans on now pinned by its own test. The sweep also carried a
**no-op control**, so a guard scoped so tightly it matches nothing cannot pass as
one that works.

## 114–116 · The comment that was right and the code that was not

Qodo raised two on the fan-out module. Both accepted after checking them, and
the first is worse than the report says.

**114 — a deadline that let late verdicts through.** `fan_out` waits on the
futures with the caller's timeout, then shuts the pool down, then reads the
shared results. A job finishing in the gap between the wait giving up and that
read has written a real migration by the time anyone looks — and it was reported
as **reached**. The verdict was genuine; it just arrived after the deadline and
was accepted because the bookkeeping in between happened to take long enough.
Two identical runs could report differently, in a class whose own docstring
promises the same subjects produce the same report twice.

🔴 **The comment three lines above the defect stated the correct rule.** It read:
*"A job finishing between the deadline and this line would otherwise appear in
some figures and not others. Reading it as unreached is the safe direction:
nobody waited for that verdict, so nothing here claims it."* The code did the
opposite of its own paragraph. Worse, that paragraph was written while fixing
**112** — the timeout it belongs to — and the same rewrite dropped the
`done, not_done =` capture that had made the boundary crisp. The fix for one
half of the deadline removed the other half and wrote down that it had not.

That is the third time in this project a defect has appeared inside its own
recorded warning: **29 → 106** eleven pull requests apart, **108 → 110** two
lines apart, and now a comment and the statement below it. *Prose stating a
property is not the property* (60, 69), with the prose written by the person who
knew.

The fix makes the `done` set `wait` returns the deadline itself — a fact decided
at the instant it passed, not a question asked afterwards. The results only
supply the value.

**115 — a prerequisite reported as a result.** `proofs/fanout.py` advertised that
it needed *"pydantic v2 and nothing else"*, and probed exactly that. Every
subject is then migrated by running `python -m pytest` through the same
interpreter. So an interpreter satisfying the documented requirement fails all
four subjects, and the proof reports them as migrations that did not work rather
than as a prerequisite that was never there. Shape 9's family: *"I could not
tell"* arriving as an outcome. Both are now probed before anything is built and
the refusal exits 2 naming both.

**116 — the fix's own untested half.** Fixing 114 put the rule in `_verdict`, a
pure function, and tested it thoroughly. Nothing tested whether `fan_out` handed
it the right arguments. A call site passing `finished_by_deadline=True`
unconditionally passed every test in the file — because the deadline tests use a
job that is still blocked, so it never records a result for the flag to decide
about. The rule was right and the wiring was unchecked, which looks identical
from outside.

Found by breaking it. **Finding 55's shape**: a guarantee spelled across a setup
site and a use site needs both halves tested, and the dangerous version is the
one that fails quietly. Assembly is now `_assemble`, checked with futures a test
builds itself — one of them recorded but absent from `done`, which is the case
no real run can be made to produce on demand.

**17 of 17 real guards caught** on the re-run, plus the no-op control. The
eighteenth remains `counting()`'s redundant filter, unchanged and still
labelled.

## 117–118 · Two refusals that were right and said the wrong thing

Both findings here are the same mistake in two places, and neither changes what
the code *accepts*. They change what it says when it refuses — which is the half
nobody tests, because a refusal that fires looks like a success from the test's
point of view.

**117 — the discriminator that was documented and not tested.** `fanout` was
widened to take a `Verdict` protocol so that a report read back from a sandbox
could be one without pretending to be a `Migration`. That left a choice: ask
whether a result *is* a verdict, or ask whether it is an `Unreached`. The module
already had a paragraph explaining why the second is correct — testing for the
protocol means a result of an unfamiliar kind reads as a subject nobody reached,
which is a fact nobody established, in the one direction the module exists to
refuse.

The paragraph was there. The test was not. Swapping the two passed **all 713
tests**, because the two answers are identical for both types that exist today;
they differ only for a third, and no test had ever produced one. Writing the
reason down had felt like doing the work.

That is the fourth time in this project a defect has been found inside its own
recorded warning — 29 → 106 eleven PRs apart, 108 → 110 two lines apart, 114's
comment contradicting the statement below it, and now a rule explained in prose
and left unchecked. It is worth naming as a pattern rather than as four
coincidences: **the act of writing down why something matters reliably feels
like having handled it.**

**118 — the refusal that threw away its reason.** A fan-out of four sandboxes
came back with every subject unreached and this explanation: `` `success` is
None, which is neither true nor false ``. True, unhelpful, and hiding the actual
answer, which was sitting in the same payload — Daytona's disk quota was
exhausted, and it said so in a sentence.

Two bugs, one shape. The `success is False` branch read `error` as a string; the
harness sends it as a model turn's content blocks, so a genuine failure with a
genuine explanation reported *"no reason given"*. And the branch for a payload
with no `success` field at all never looked at `error` — which is exactly the
shape a sandbox that failed to *start* produces, so the case with the most to
say was the case that said the least.

Neither could have been found by reading. The string form is what the API
documents, the tests used the documented form, and every one of them passed. It
took a real quota failure in a real harness. That makes this the fourth finding
in the log raised by running the thing rather than reviewing it, and it is the
clearest of them: **a rejection is a diagnostic, and a diagnostic that discards
the diagnosis is a correct answer to the wrong question.**

**18 of 18 real guards caught** on the run that found 117, plus the no-op
control — a "break" scoped so tightly it changes nothing, which looks exactly
like a guard that works.

## 119–123 · The fifth time, in the paragraph that named the pattern

Finding 117, three sections up, is about writing down why something matters and
mistaking that for having handled it. It was recorded as the *fourth* instance of
a defect sitting inside its own recorded warning.

**119 is the fifth, and it is in the same pull request.**

The negative control has to be checked against a filesystem, not only against a
report — a loop that edited the control and reverted it perfectly produces the
same report as one that never touched it. So `_control_is_untouched` runs
`git status` in the sandbox. Its docstring said, in as many words:

> Its own session, so the answer comes from the sandbox the migration ran in — a
> fresh one would have a clean checkout for reasons that say nothing.

The function then constructed a fresh `SandboxExec`, which opens a new session
and a new sandbox. The sentence naming the failure mode sat directly above the
line implementing it. Qodo caught it; nothing in 732 tests could have, because
the check only runs against a live harness.

Two things are worth separating here. The first is that this is now a *reliable*
pattern rather than a run of bad luck — five times, across eleven pull requests,
a warning has been written and then contradicted within a few lines of itself.
The second is more uncomfortable: **117 and 119 were committed together.** The
paragraph diagnosing the habit and a fresh instance of the habit went in on the
same branch, hours apart. Naming a class of mistake does not confer immunity
from it, and this log would be more flattering and less useful if that were
quietly separated into two pull requests.

**120 — the filter with a real reason and the wrong scope.** The control check
dropped every `??` line from `git status`, which let an agent that *added* a file
pass. The reason it was there is genuine: fixture C's own pytest run writes
`htmlcov/` and `coverage.xml`, so a check that fails on any untracked path never
passes at all. But "the artefacts of running the suite" and "anything untracked"
are different sets, and only one of them is safe to ignore. Nothing is dropped
now — tracked changes fail, an untracked `.py` fails, and every untracked path is
recorded either way, so a reader can see what the run left behind instead of
taking the script's word that it did not matter.

**121 — a contradiction that resolved in the reassuring direction.** A report
saying `sites: null` beside a non-empty `unreadable` list parsed perfectly and
derived `complete = True`, because completeness asks about a scan and the step
was claiming there had not been one. The producer never writes that pair. That is
exactly why it was worth fixing: `read_report` exists to read text this project
did not produce, and a reader that only survives well-formed input is a reader
whose strictness is decorative.

**122 — the count in the first paragraph.** The module opens *"Four subjects go
out together"*; the run's first line says `fanning out over 3 subjects`. There
was never a fourth: `EXTRAS` is the only place a measured environment exists, the
script refuses a fixture without one, and `EXTRAS` holds two. So the number could
not have drifted — it was wrong when it was written, survived every test, every
type check and every review, and was contradicted by the script's own first line
of output on every run it ever made — including the ones that died on a disk
quota without reaching a single subject.

It is worth recording for where it was rather than what it cost. This is the
module built on the position that a report is not a migration and that a
conclusion must be derived from its evidence rather than asserted beside it — and
its own summary paragraph asserted a figure beside evidence that said otherwise.
The fix is not the corrected number. It is that the docstring now names `EXTRAS`
as what decides, so there is no second copy of the count to be wrong; the only
figure left is the one the run prints for itself.

**123 — the entry about the wrong sentence had a wrong sentence in it.** The
paragraph above originally closed *"and was contradicted the first time the thing
ran."* That is a nicer story than the truth and it is not the truth. The script
prints its subject count *before* it fans out, so the run that died on Daytona's
disk quota — reaching nothing, migrating nothing — still printed `fanning out
over 3 subjects`, an hour earlier, beneath a docstring already claiming four. So
did every run after it. What actually happened is that the line was on screen and
went unread until a run succeeded and there was finally something else on screen
worth comparing it to.

The distance between those two sentences is the whole of **shape 9**: *"I could
not tell" reported as "it did not happen."* "Contradicted the first time it ran"
describes a fact about the script. "I read past it several times" describes a
fact about the reader. The first is flattering and unfalsifiable from the outside;
the second is checkable, and checking it took one `git log` against one file
timestamp. It was caught only because the sentence was about to be repeated in
the submission write-up, and a claim worth putting in front of a judge is worth
being sure of first — which is an uncomfortable thing to learn about a log whose
entire purpose is to be the thing you can check.

**4 of 4 guards caught** on the re-run, plus the no-op control.

## 124–127 · What asking for a second review cost

The rules page was edited mid-week and grew a requirement: the README must show
*"a follow-up review against the final code."* Qodo posts one review per pull
request and does not re-review after a push — verified across #20, #21 and #23 —
so the only way to produce one is to ask, by commenting `/agentic_review`.

Asked on #20 on 27 August, against a branch merged the day before, it raised
**four more findings**. Not stylistic ones. Three are further ways the
publishability check fails to mean what it says: it reads `git show HEAD:path`
and treats *nothing* as *nothing to check*, which is what an untracked file
returns; it strips trailing newlines from both sides of the comparison; and it
compares text while ignoring the file mode. Each is a different route to the same
place — something that is not the migration going out under the migration's name.

The fourth is the one worth stopping on. `propose()` validates HEAD, the index and
every target, then blocks on a human typing `yes`. `_do_open()` validates nothing
again. Every check the gate performs is therefore a statement about the moment
*before* the pause, and the pause is the longest interval in the program because
its length is a person's attention. This project's answer to *"does the agent stop
before anything irreversible"* is its strongest claim, and the stop had a hole in
it that nothing in 732 tests could see, because no test holds the prompt open and
changes the tree underneath it.

They were recorded open, on the day they were raised, because that is the rule —
*a finding is recorded when it is raised, not when it is resolved* — and because a
log that only gains entries it can immediately mark **Fixed** is a log being
managed rather than kept. They are fixed now, and the entries above say so
separately from having said they existed.

Two things surfaced while fixing them and are worth keeping. `_git_or_none`
**strips its output**, so the contents comparison had never seen the bytes it was
comparing — finding 91 was this same function stripping `status --porcelain`,
whose leading space means something, and a file's contents are the same kind of
value and more obviously so. And the test fake built its map of committed blobs
with `dict(committed or {...})`, so a test that passed `{}` to describe *an
untracked target* was quietly handed the default map with the file present: the
case that finding 124 is entirely about could not be written. That is finding
128, and it is the same shape as the defect it was hiding — an absence read as
"nothing was specified" rather than as the answer.

Then Qodo reviewed the fix and raised **129**, which is the best finding in this
log. Revalidating after the approval compared each target against what it held
*before* the migration — and never against what the migration wrote. HEAD is
unchanged either way, so somebody editing a target while the prompt waits passes
every question the revalidation asks, and is then staged as this run's output.
Replacing the file with a symlink passes as well, because `is_file()` follows the
link and answers about a different file.

The fix for the window left the window open for the one thing the window is
about. It is the eighth instance of the shape this log keeps naming, and the
first where the defect is *inside the remedy for the previous instance of it* —
not prose that failed to match code, but a repair that reproduced the flaw it was
repairing, one level down. `Proposal` now carries `(path, before, after,
encoding)` and the check asks both questions, reading the file back with the
encoding and `newline=""` it was written with.

Then the follow-up review on *that* fix raised **130**: the contents check reads
the file, and neither `OSError` nor `UnicodeError` is a `PublishError`, so a
target made unreadable or rewritten with foreign bytes during the same window
left the module as a traceback past the only handler the CLI has. That is **shape
1 for the fifth time** — an exception escaping the path meant to handle it — and
it arrived inside the fix for 129, which was the fix for 127.

Three rounds, each one finding a defect in the previous round's repair, each one
smaller than the last: the window, then the half of the window the fix did not
cover, then the exception the cover could raise. That is what a review loop looks
like when it is actually running rather than being described, and it is the whole
argument for the rule that made us ask for a second review at all.

**8 of 8 guards caught** when broken one at a time, plus a no-op control on each
round.

## 131 · The gap that had already closed

`--sandbox` refuses, and the refusal is correct: the flag would edit a checkout
on this filesystem and run the suite on the sandbox's, so the suite would answer
a question about code the edits never reached. That is the defect
`bumpsmith.run` exists to prevent, one level up, and the refusal has been the
right call since the day it was written.

The last sentence was not. It read:

> Carrying the edits across is the missing piece; until it is written and
> reviewed, this refuses.

By the time anyone read that, the piece was written. Not the way the sentence
imagined — nothing carries edits across — but by removing the split it was
about. `bumpsmith.remote.SandboxJob` installs this package into the sandbox from
its own public repository and runs the entire loop there, so editing and testing
happen on one filesystem again, just not this one.
`proofs/sandbox_fanout.py` does it to two real third-party repositories at once
and the output is committed.

**The two modules already agreed.** `remote.py` opens by citing this very
refusal and endorsing it: *"`python -m bumpsmith --sandbox` refuses, and the
refusal is right ... The way past that is not to relax the rule but to stop
splitting."* The design was coherent in both directions. What was stale was the
one paragraph a person running the command actually sees — the only place where
being out of date costs a reader anything.

That is **the seventh instance of prose stating a property the code does not
have** (60, 69, 117, 122), and it is the first of a different sub-kind. The
earlier six were prose claiming a property that was absent. This is prose
claiming an *absence* that had been filled. Both are the same failure of
maintenance and only one of them looks like a bug, which is presumably why this
one survived eight pull requests: a paragraph confessing a limitation reads as
humility, and nobody re-checks humility.

Found while verifying a deferral in order to answer it in a Qodo thread, which
is the second time this week that preparing to say something in public has
turned up the thing that made it untrue. Recorded as self-found, because the
review did not raise it — but it would not have been looked for without the
review.

**1 of 1 guard caught** when broken, plus a no-op control:
`test_the_refusal_names_where_the_loop_does_run_in_a_sandbox` fails against the
old text and passes against the new, and `__main__.py` was restored byte-for-byte
after the break.

### 132 · and the correction was dated a day early

Qodo reviewed the above and raised one thing: the README's snapshot said *"As of
28 August 2026"*, and nothing in the repository agreed. The commit was
`2026-08-27T19:54:20Z`, the pull request `2026-08-27T19:54:53Z`, and Qodo's own
comment `2026-08-27T19:56:32Z`. The date came off a local clock at UTC+05:30,
where it was already the 28th; git and GitHub both keep time in UTC, where it was
not.

Accepted without argument, after checking all three timestamps rather than
taking the finding's word for it. The value of the finding is not the day — it is
that a **dated accounting claim disagreed with the commit that made it**, in a
file whose whole purpose is that its numbers can be checked.

The review also named why nothing caught it: the documentation guards validate
the total and the breakdown and say nothing about the date.
`test_the_readme_finding_snapshot_is_not_future_dated` closes that. It asserts
the snapshot is not after today in UTC — which permits a snapshot to age, because
ageing is what a snapshot does, and forbids the one direction only a misread
clock can produce.

**The shape is worth stating.** This pull request exists to correct a sentence
that had drifted from the code. Its own correction shipped a fresh sentence that
disagreed with its own commit. That is not the same defect twice — 131 was prose
describing an absence that had been filled, 132 is prose asserting a fact the
artifact contradicts — but it is the same *cause*, which is that prose is not
executed and therefore is not checked unless something is written to check it.
Two guards now do, in the one file where the numbers are the argument.

**1 of 1 guard caught** when broken, plus a no-op control.

## 133–135 · The README understated the project

Read cold, against the two tracks it is being judged on, rather than for
correctness. That is a different pass and it found a different class of thing:
not a claim that is false about the code, but a document that is **behind** it.

### 133 · the same stale sentence, in the room with more visitors

Finding 131 removed a sentence from `_no_sandbox()` that said carrying the edits
into the sandbox was the missing piece. It had stopped being true eight pull
requests earlier, when `bumpsmith.remote` started moving the *agent* instead of
the edits. What #29 did not do was look for other copies of it. There was one, in
`README.md` under *Where the suite runs* — which is the section a reader arriving
for the harness reads first, and the one a hackathon judge scoring *use of
sponsor tools* reads at all.

So three documents described the same design and the ranking was backwards:

| document | what it said | right? |
|---|---|---|
| `proofs/README.md` | `remote.py` installs the package into the sandbox and runs the whole loop there | ✅ since #23 |
| `src/bumpsmith/__main__.py` | the same, after #29 | ✅ since yesterday |
| `README.md` | carrying the edits across is the missing piece | ❌ since #23 |

**The least-read document was the accurate one.** That is the part worth keeping.
131 was recorded as *"prose stating a property is not the property"*, and the fix
for it was itself prose — so it inherited the defect it was fixing, and inherited
it in the direction that costs most. Findings 64 and 65 named this exact
mechanism for numbers: a stale value corrected in one file and left standing in
another a `grep` away. It applies to claims, and nothing about a claim makes it
easier to grep for.

### 134 · a map missing a quarter of its territory

The module table says "Everything is in `src/bumpsmith/`" and then lists twelve
of sixteen files. This was found by counting rather than by reading, which is the
only way it *could* be found: every row present is correct, the prose around it is
correct, and nothing about the table looks short. A reader has no way to know what
is not on a list.

The four absent were `fanout.py`, `remote.py`, `publish.py` and `report.py` — the
parallel fan-out, the loop that lives in the sandbox, the one irreversible effect
the tool has, and the report a person reads. Four of the project's five strongest
claims, and the table that maps the package to a stranger did not mention them.

The fix is a test, not four rows. `test_the_readme_maps_every_module_the_package_ships`
derives the expected set from `src/bumpsmith/*.py`, so a module added tomorrow
fails the suite until the table follows. It is scoped to the table's **first
column** for the reason `_stop_table` already gives: `remote` and `report` and
`publish` all appear in the README's prose, so a search of the whole file would
have found every one of them and reported a complete map.

Verified by breaking, one at a time, with a no-op control:

| break | result |
|---|---|
| delete the `fanout.py` row | ❌ `modules in src/bumpsmith/ with no row: fanout.py` |
| delete the `remote.py`, `publish.py`, `report.py` rows | ❌ all three named |
| rename a row's module to `fanout2.py` | ❌ both directions fire — one missing, one invented |
| reword the table header | ❌ the anchor assertion, naming itself as the thing to update |
| touch the README without changing the table | ✅ green |

### 135 · the numbers in the section the rules name

*"Twenty-eight pull requests; Qodo reviewed every one; twenty-four raised at
least one finding, 90 in total."* Live: twenty-nine, twenty-five, ninety-one.
#29 merged, Qodo reviewed it, raised finding 132, and none of the three numbers
in `## Qodo Code Review Evidence` moved.

Two paragraphs above it sits a finding total that **cannot** go stale, because
`test_the_readme_finding_count_matches_the_log_it_describes` reads the log's own
table and fails when the sentence disagrees with it. The difference is where the
truth lives. The finding total is checkable from the repository; the pull request
counts are only checkable from GitHub.

That is the reason this one is left unguarded, and it is a decision rather than
an omission. A test that queried the API would fail when the network is down and
pass when a cache is stale — wrong in both directions, and in the second one it
is wrong *reassuringly*, which finding 9's shape says is the expensive kind. So
the recount is a step in the pre-submission pass with the command written beside
it, where a human is already looking, rather than a green tick that means nothing.

**This is findings 64/65 for the third time.** Twice is a coincidence; three
times is the shape asserting itself. Every instance has been the same: a number
that is derived somewhere, written down somewhere else, and true on the day it
was typed.

### 136–138 · and the fix carried the defect it was fixing

Qodo reviewed #30 in under a minute and raised two Medium findings on the guard
written for 134. Both are right, and the first one is this pull request's own
subject happening inside its own fix.

**136 — the guard enforced a claim the README does not make.** `_shipped_modules()`
filtered `__*.py` out of the package before comparing. The sentence it defends
says *"Everything is in `src/bumpsmith/`"*. So the test meant *everything except
dunders*, and `__main__.py` — the command line, the file a reader is most likely
to open second — could have been dropped from the table without failing anything.

The docstring even argued for it: the column is "what it guarantees", and a
dunder is not a guarantee. That was a reasonable position and it was still wrong,
because **it was a position about the table and the README had made a promise
about the directory.** Prose stating a property is not the property, ninth
instance, and the third pull request running in which a correction for stale
prose has shipped carrying the thing it was correcting:

| PR | the fix | what it carried |
|---|---|---|
| #29 | 131, a stale sentence in `_no_sandbox()` | 132 — the correction was dated a day into the future |
| #30 | 133, the same stale sentence in the README | 136 — the guard for it enforced a narrower claim than the sentence |

The deeper problem is not the exclusion, it is that the exclusion was a
**pattern**. `startswith("__")` silently adopts every file that has not been
written yet: a `__version__.py` added next month would have been outside the
guard's scope, and nobody would have decided that. Where an exemption is
genuinely right — 138's table below — each one is now named individually with the
sentence that justifies it, so a new module fails the suite until somebody
chooses.

**137 — set-difference cannot see a duplicate.** `_tabled_modules()` returned a
set, so both checks compared sets: one for names present in the package and
absent from the table, one for the reverse. Neither can see the same name twice.
A table with two rows for one module passes both while being precisely the thing
the table promises not to be — and the second row is the stale one, because the
person editing finds the first.

The helper now returns a list, in order and with repeats, and the two
set-difference tests take `set(...)` **at the call site** rather than in the
helper, so what each check is blind to is visible where it is used.

### 138 · a third map, found by fixing the second

Fixing 136 meant reading `src/bumpsmith/__init__.py` to decide whether it
deserved a row. It has a table of its own — the one `help(bumpsmith)` prints —
listing **nine of the eighteen** files the package ships. The same four the
README omitted, plus `rootdir` and `sources`.

So there were three hand-written maps of one package:

| map | its reader | listed |
|---|---|---|
| `README.md` | somebody arriving at the repository | 12 of 18 |
| `src/bumpsmith/__init__.py` | somebody at a REPL who never opens it | 9 of 18 |
| `proofs/README.md` | somebody checking a claim | (proofs, not modules — and complete) |

and until this pull request not one of them was checked against the package.
Every one was correct about the rows it had; each was wrong only about the rows
it did not have, which is the one error a reader cannot detect.

The guard for it derives the expectation from `src/bumpsmith/*.py` and names its
three exemptions one at a time — `migrate`, because the sentence above the table
says "Start at `bumpsmith.migrate` … every other module is a part it uses";
`__main__`, because the sentence below it says `python -m bumpsmith` runs the
loop; `__init__`, because it is the file the docstring is in. That is 136's
lesson applied the same afternoon it was learned.

Verified by breaking, one at a time, with a no-op control — **5 of 5**:

| break | result |
|---|---|
| drop the `__main__.py` row from the README | ❌ named (this is 136's fix; it passed before) |
| drop the `__init__.py` row from the README | ❌ named |
| duplicate the `gate.py` row | ❌ `modules with more than one row: gate.py` (137's fix) |
| drop the `remote` row from the `__init__` table | ❌ `modules absent from the table in src/bumpsmith/__init__.py: remote.py` |
| rename an `__init__` row to `bumpsmith.nowhere` | ❌ both directions fire |
| touch neither table | ✅ green |

`README.md` and `src/bumpsmith/__init__.py` both restored byte-identical.

### 139 · fixed where it was raised, not where it applied

The follow-up `/agentic_review` against `21aea24` raised one more, and it is the
same defect as 137 at the other end of the same file.

137's fix added a uniqueness check to the README's table. The `__init__` table
makes the identical one-row-per-module claim and did not get one — so duplicating
a `:mod:` row left both of its assertions green. And `_init_table_modules()` was
written to return repeats **on purpose**; its docstring says "in order, with
repeats". All three of its callers then took `set(...)` of it. The multiplicity
it went out of its way to preserve was discarded by every reader it had.

**Shape 11 again** — *a guarantee enforced at one entrance of a building with two.*
The previous instance was `--sandbox`, refused on the command line and only
documented on `migrate()`. This one is narrower and more embarrassing: the second
entrance was in the same file, added in the same commit, twenty lines below the
first.

The general lesson is not "add the missing test". It is that **137 was fixed
where it was raised rather than wherever it applied**, and that reading the
finding is not the same as reading for the finding's shape. Verified by breaking:
duplicating the `gate` row fails with `modules with more than one row in
src/bumpsmith/__init__.py: gate.py`; no-op control green; file restored
byte-identical.


### 140 · the sentence, not the digits

Finding 135's disposition said the recount belonged in the pre-submission pass
rather than in a test. Doing that recount is what found this.

*"Twenty-nine pull requests; Qodo reviewed every one; twenty-five raised at least
one finding, 91 in total."* That is the sentence **135 left behind** — the one it
had just corrected, from 28 / 24 / 90. But
the sentence is a claim about **now**, and every merge after it falsifies it —
including the merge of the pull request that corrected it. There is no value that
can be written there and stay right. That is why the same three numbers had
already been wrong twice, and correcting them a third time would have been the
third instance of a defect whose actual shape is the sentence rather than the
digits in it.

So the fix is the tense. *"The whole trail, as of the merge of #30"* is true when
written and stays true; a later merge makes it **out of date**, which is a
different thing from **wrong**, and a reader can see which one they are looking
at. The `gh api` incantation that re-derives the count sits beside it, because an
anchored number nobody can check is only a better-dated assertion.

Recounted live rather than incremented: thirty pull requests, Qodo on all thirty,
twenty-six with at least one inline finding, ninety-four findings.

**Findings 64/65, fourth instance** — and the first where the answer was not a
guard and not a corrected value. The three before it were fixed by making the
number derivable. This one could not be, because the truth lives on GitHub, so it
was fixed by making the sentence honest about when it was true.

### 141–142 · the audit entry misquoted, and its own check could not tell

Qodo reviewed #31 and raised two. Both land on the entry for 140, which is an
entry about quoting numbers accurately.

**141 — the quotation never existed.** The narrative for 140 quoted the stale
sentence as *"twenty-nine … twenty-five … 90 in total"*. Before 135 it read
**28 / 24 / 90**; after 135 it read **29 / 25 / 91**. The entry took the pull
request counts from the corrected state and the finding count from the stale one
and presented the splice as a quotation.

The check that would have caught it is the one 135 itself performed and this
entry did not: read the value out of the file rather than out of the paragraph
describing it. And nothing here is testable — a quotation of a sentence that no
longer exists in any file cannot be verified against anything — which is the
argument for quoting from the diff rather than from memory.

**142 — the verification command could not tell.** The `gh api` incantation
offered as the way to re-derive the anchored counts queries inline comments on
one pull request. Four of the thirty have **zero** of those, and zero from that
query is the same answer for two opposite facts:

| what happened | what the query returns |
|---|---|
| Qodo reviewed it and found nothing | `0` |
| Qodo never reviewed it | `0` |

The sentence being verified asserts the *first* for all thirty. **This is the
ninth shape — "I could not tell" reported as "it did not happen" — occurring in
the command supplied to check a claim**, which is a worse place for it than the
claim. The recount that produced the numbers did query both; the README
documented the weaker half of what was actually run.

Fixed with two queries and the reason for there being two written between them.
Coverage comes from `/issues/N/comments`, which carries the summary Qodo posts
whether or not it finds anything; findings come from `/pulls/N/comments`.
Collapsing them into one number is the mistake, not an inconvenience.

### 143 · the ninth shape, inside the fix for the ninth shape

142 was that a query could not tell *reviewed and found nothing* from *never
reviewed*. The fix added a second query, against the summary Qodo posts either
way — and wrote it without `--paginate`.

GitHub returns thirty issue comments a page. A Qodo summary posted after the
thirtieth comment is on page two, and the query returns **zero**: the same false
*never reviewed*, reintroduced by the fix for it, one commit later, in the
paragraph explaining why that answer is dangerous.

The follow-up review also named the second-order defect, which is the one worth
keeping. Adding `--paginate` alone would not have fixed it:

```
gh api --paginate ... --jq '[...] | length'   # one count per page, printed in sequence
```

`--jq` is evaluated **per page**, so a two-page thread prints `30` then `4`
rather than `34` — a different number that looks exactly like this one, and a
line that would have read as a plausible answer forever. Both queries now
concatenate first and filter once, with `jq -s 'add | map(…) | length'`.

Latent rather than live: no pull request in this repository has yet exceeded one
page, so nothing here was ever wrong. Verified against #20 (15 findings), #26
(0 findings and 2 coverage comments — reviewed, found nothing, which is the case
the single query could not distinguish) and #31.

**This is the third time in two pull requests that a fix has carried the defect
it was fixing** — 131→132, 133→136, and now 142→143 — and every one was caught by
review rather than by the fix's own author. That is not a coincidence about these
three; it is what the fourth shape says. *The fix is not automatically safer than
the defect.*

### 144 · and the procedure answered for one of thirty

Third round on the same paragraph, and the finding is not in the commands — both
are now correct — but in what they are offered as.

The sentence they check is an aggregate: *thirty pull requests, thirty reviewed
by Qodo, twenty-six with at least one inline finding, ninety-four findings.* Each
command answers for **one** pull request; the README substitutes `N`. Not one of
the four figures is derivable from either of them. So the paragraph presented an
incomplete procedure as a complete one — a claim about the *check*, which is the
harder kind to notice, because every part of it was true.

Replaced with the loop that actually produced the numbers in the first place. It
was run before being committed, and it prints the sentence:

```
30 pull requests, 30 reviewed by Qodo, 26 with at least one inline finding, 94 findings
```

**Three rounds on one paragraph, and every round was the previous round's fix.**

| finding | what was offered | what was wrong with it |
|---|---|---|
| **142** | one query, inline findings | zero could not be told from never reviewed |
| **143** | a second query, for coverage | no `--paginate`; and `--jq` would have counted per page |
| **144** | both queries, correct | they answer for one pull request out of thirty |

Each fix was right about the thing it fixed and silent about the next layer out,
which is the argument for the follow-up review being a separate review rather
than a re-read. The reasons now live beside the detail of the command that
answers each one, so somebody editing the command finds out why it is shaped that
way before they simplify it.

### 145 · the claim was anchored and its check was not

140 anchored the sentence to a named merge so it would age instead of lying.
144 replaced its check with a loop over **every currently merged pull request**.
Each was right on its own and together they contradict each other: the moment
#31 lands, the loop returns

```
31 pull requests, 31 reviewed by Qodo, 27 with at least one inline finding, 97 findings
```

and appears to refute a sentence that is still perfectly true.

**A verification procedure that contradicts a correct claim is worse than no
procedure**, because a reader who runs it believes it over the prose. The claim
would have looked stale to everybody who checked, and only to them.

Qodo also named the trap sitting in the obvious fix: filter by pull request
*number* and it breaks quietly, because creation order is not merge order. The
cutoff is #30's `merged_at` and the comparison is against `mergedAt`.

Verified in both directions, which for a filter means showing it excludes
something:

| cutoff | pull requests enumerated |
|---|---|
| #30's `merged_at` — `2026-08-28T04:52:58Z` | **30**, and the loop prints the sentence verbatim |
| #29's `merged_at` — `2026-08-27T20:11:19Z` | **29** |

**Four rounds on one paragraph**, and each round was the previous round's fix.
The paragraph is eleven lines of shell. What it is *about* is a sentence
containing four numbers.

### 146 · the check for a permanent claim had an expiry date

`gh pr list --state merged --limit 200` returns the **most recent** two hundred,
and the #30 cutoff was applied to what came back. So the procedure works today,
works for the next hundred and seventy pull requests, and then starts quietly
reporting a smaller total — because the pull requests the snapshot is *about*
have fallen out of the window before the filter ever sees them.

The sentence it checks was deliberately written so it could never expire. Its
check expires.

Nothing about it would look wrong when it happened. It would return a plausible
smaller number, which is the ninth shape wearing its fifth coat on this
paragraph: *a limit reported as a result.*

Fixed by paginating `pulls?state=closed` and dropping the unmerged ones, which
has no window at all. Verified by extracting the fenced block **out of the
README** and running that, rather than running a copy of it — the block prints:

```
30 pull requests, 30 reviewed by Qodo, 26 with at least one inline finding, 94 findings
```

**Five rounds on one paragraph.** Worth stating plainly, because it is the
strongest thing this log has to say about review: every one of the five was found
by the reviewer, on the fix for the previous one, and not one was found by the
person who wrote the fix. The author was satisfied five times.

### 147 · a guarantee about the guard that the guard does not make

Not the trail paragraph this time — the one above it, and the one that has been
held up throughout as the example of a number that *cannot* go stale.

> *"The count is not maintained by hand — `tests/test_docs.py` reads the log's own
> table and fails if this sentence and that table disagree."*

Two guards stand behind it. One compares the stated total to the number of rows.
The other checks that the three parts sum to the total. **Neither looks at the
split.** Move ten findings from *self-found* to *automated review* and both stay
green while the sentence beside them says they cannot.

**Prose stating a property is not the property, tenth instance** — and the first
time it has landed on a claim about the *tests* rather than about the code. That
is a worse place for it: a reader who distrusts prose can check code, and a
reader told the code checks the prose has nowhere left to stand.

The split **could** be derived, and deliberately is not. The log marks provenance
in prose, and only when a finding is not Qodo's — *found by audit*, *self-found
while…*, *raised by the live harness*. A row with no marker is a row **nobody
marked**, which is a different fact from a row Qodo raised. A test inferring the
second from the first would be the ninth shape again, reading an absence as
evidence, and it would be most confident about precisely the rows nobody had
thought about. It would also be wrong today: writing that inference is what
produced two false exclusions the last time it was tried, on rows 5 and 35.

So the sentence now says which half is guarded and which is a claim by the
author. Making the split derivable means giving all 147 rows an explicit
provenance field. That is worth doing and it is not a thing to start the day
before a deadline.

## The site's own review — 172 to 175

Four findings on the pull request that publishes the recorded runs, and the
useful thing about them is where they landed. None is in the migration loop;
every one is in the machinery built to *show* the migration loop, which had
existed for about an hour and had therefore been read by nobody.

Three are the same shape: a path built from something the code did not check.
`--out` was passed to `rmtree` unexamined, a manifest root was computed and then
not used, and a TOML key became a file name. Each was reproduced before it was
accepted — the first by watching a file called `source.py` disappear, the second
by a `FileNotFoundError` naming a payload under the wrong directory, the third by
resolving the path rather than writing through it.

The fourth is the one worth keeping. `runs.toml` writes down what each run is
supposed to demonstrate so that a regenerated payload which no longer
demonstrates it fails the suite instead of going up as a nicer story than the
truth. The review pointed out that the written-down part covered only how a run
*ended* — so the flagship blurb could go on claiming nineteen rewritten sites
long after the payload stopped containing nineteen, and the test would still
pass. That is a finding against the honesty mechanism, raised against the one
artefact in this repository whose whole purpose is to be believed. It was the
weakest link in the change and it was found by review, not by the author.

All four fixes were verified by removing the fix and watching the test fail:

| Fix removed | Test that failed |
| --- | --- |
| the `rmtree` guard | `test_a_directory_the_build_did_not_write_is_never_deleted` |
| the index root | `test_a_manifest_outside_pages_resolves_its_own_payloads` |
| the slug check | `test_a_slug_cannot_climb_out_of_the_output_directory` |
| a payload's step count | `test_each_run_still_has_the_steps_its_blurb_describes` |

`pages/build_site.py` and `pages/runs/fixture-b.json` were restored and
sha256-checked afterwards.

## The second round on the same PR — 176 and 177

Both of these are findings on the fixes for 172 and 174, and they share a shape
worth naming: each of the first-round guards asked a question whose answer it did
not control.

174 restricted slugs to what a file name can carry, and `index` passes that test
while still colliding with the one file the build writes itself. 172 required a
marker file, and `is_file()` answers yes to a symlink pointing anywhere at all.
Neither original fix was wrong about the danger; both were checking a proxy for
the property they wanted.

The second round of fixes checks the property. `index` is reserved by name, and
the marker must be a regular file that is not a link. The marker needed no entry
in the reserved set — it begins with a dot, which the slug pattern already
refuses — and that reasoning is asserted in a test rather than left in a comment,
because a comment claiming something is impossible is how it becomes possible
later.

Both were reproduced before being accepted and verified by removal afterwards:

| Fix removed | Test that failed |
| --- | --- |
| the reserved-name check | `test_a_run_cannot_claim_a_name_the_build_writes_itself` |
| the symlink check | `test_a_symlinked_marker_does_not_unlock_the_guard` |

## An outside audit of `main` — 182 to 184

The first review here that was not a pull request. An external AI code audit
(Cursor, Grok 4.6) was pointed at the tree at `f6ff5e0` and asked for security
findings and claim findings in one pass. Its report is committed verbatim at
[`reviews/2026-08-29-outside-audit.md`](reviews/2026-08-29-outside-audit.md) —
unedited, including the parts rejected below, because a summary of a review that
nobody else can read is the thing this file exists to stop. The severities in it
are the auditor's own and are not endorsed by being stored. Recorded as their own batch because
their provenance is neither Qodo nor a live run, and the README's split counts
"automated review" as one column that now has two sources in it.

It reported fourteen security findings. **None was accepted as a vulnerability**,
and that is the honest summary rather than a defensive one: the tree was
re-inspected for each, and every one either described a trust boundary this
README already states out loud (`LocalRunner` runs a stranger's suite on your
machine), an architectural limit already written down (a sandbox `exec` the model
issues is weaker evidence than a local argv), or a hardening idea with no
demonstrated failure behind it (`git push` without a `--`, an unvalidated
`--pr-branch`). Several are worth doing and are not done here; a finding logged
as fixed on the day before a deadline, in the module that performs the
irreversible action, would be the worst possible trade this repository could make.

What it did find was three claims, and those are the three above. All three are
the same defect wearing different clothes — **prose asserting a property nothing
checks**, which is this log's recurring shape and the reason the log exists. One
quoted a measurement no file contained. One described an invariant the code did
not have. One advertised a gated, optional path as the default. Two of the three
had a test file sitting next to them that passed regardless.

The audit also listed a dozen things as "unverifiable" that are better described
as not attempted — the live site was not fetched, `git log` was not read, the
fixtures were not cloned. Those are scope notes, and they are not counted here.
A finding is something somebody can act on.

## 186 · The index stopped one pull request short of the review

[#42](https://github.com/aryangorde8/bumpsmith/pull/42) merged at
`2026-08-29T15:08:06Z` after Qodo posted its summary and then its review:
Bugs (0), Rule violations (0), Requirement gaps (0). The queries the README
already documents return the same split they return for #26 — `0` from
`/pulls/42/comments` for inline findings, `2` from `/issues/42/comments` for
coverage — which is *reviewed and found nothing*, not *never reviewed*.

The finding table still ended at #41. Under a strict reading that table is
findings, Qodo raised none, and there was nothing to add. That reading is the
ninth shape: the index was also how a reader saw that a review happened.

The first version of this entry tried to close the gap by *becoming* the row
for #42. That is how #43 exists, and it is a process that cannot terminate:
every empty review mints a pull request whose own empty review mints another.
The fix is the other table at the top of this file. #26 and #42 are both in
it. This pull request is the last row, as `this PR`, so it does not need
finding 187.

## How this stays honest

- A finding is recorded when it is raised, not when it is resolved.
- Rejections are recorded with the reason, in the same detail as fixes. A log
  that only lists what was fixed is a list of compliments.
- Where a finding was tested rather than assumed, the log says what was measured.
- Pull requests are merged with `--merge`, never `--squash`. Each carries a "here
  is the work" commit and a "here is what review changed" commit, and squashing
  would destroy the evidence that the second one exists.
- An empty Qodo review is a row in the pull-request table, not a new finding.
  The next pull request replaces `this PR` with the review that landed and adds
  itself. A finding whose only job is to name the last pull request is how the
  next one goes missing.
