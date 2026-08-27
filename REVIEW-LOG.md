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
| 109 | [#23](https://github.com/aryangorde8/bumpsmith/pull/23) | This table skipped **20–31**: twelve findings with prose sections and no row, in the file the README calls *"every finding raised and what happened to it"* — *self-found the same way* | **Fixed** — twelve rows written from the prose, index now contiguous 1..N, and a test fails on the next gap. A finding in prose but absent from the index is indistinguishable from one nobody recorded | this PR |

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
row. They were explained and unindexed, in the file whose own promise is that
nothing closes silently. Prose is where a finding is explained; the table is
where a reader learns it exists at all. The twelve rows are written from the
prose, the index is contiguous, and a test fails on the next gap.

**Finding 29 is worth the detour.** It is one of the twelve that had no row, and
it reads: *a function parameter named `constr` was treated as pydantic's, because
one module-wide import map was applied to every call in the file.* That is
**106**, which Qodo raised on #22 — the same defect, in a new function, written
directly beneath the docstring that `calls_in_scope` carries *because of finding
29*. The project fixed it on #12, wrote down which half was dangerous, and
reintroduced it eleven pull requests later.

→ **The lesson, named: a defect the project has already fixed and documented is
not thereby prevented.** 29 → 106 is that in its clearest form. Neighbouring
shapes: 64/65 (*a summary restating a number the table already owns*) and 60/69
(*prose stating a property is not the property*).

---

## How this stays honest

- A finding is recorded when it is raised, not when it is resolved.
- Rejections are recorded with the reason, in the same detail as fixes. A log
  that only lists what was fixed is a list of compliments.
- Where a finding was tested rather than assumed, the log says what was measured.
- Pull requests are merged with `--merge`, never `--squash`. Each carries a "here
  is the work" commit and a "here is what review changed" commit, and squashing
  would destroy the evidence that the second one exists.
