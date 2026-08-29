# Cursor Repository Audit Report

## 1. Audit Metadata

| Field | Value |
|---|---|
| **Repository / project** | `bumpsmith` (`aryangorde8/bumpsmith`) |
| **Local path audited** | `/home/aryan/bumpsmith` |
| **Audit purpose** | Read-only security/vulnerability review plus claims/assertions review, then an independent adversarial second pass, consolidated for action planning |
| **Date of audit** | 29 August 2026 |
| **Models used** | Cursor Grok 4.6 (both passes, same conversation) |
| **Scope** | Static inspection of `src/bumpsmith/`, `tests/`, `proofs/`, `pages/`, `README.md`, `REVIEW.md`, `REVIEW-LOG.md`, `pyproject.toml`, `.github/`, `fixtures.toml`. GitHub metadata was read for the public repo description. |
| **Out of scope / not executed** | No code changes, no commits, no live harness/Daytona runs, no `pytest`/`ruff`/`mypy` execution in this environment (sandbox/shell was unavailable), no `pip-audit` / CVE database scan, no live fetch of `https://aryangorde.com/bumpsmith/` |
| **Important limitation** | This is an **AI-assisted static/repository audit**, not a formal penetration test, not a paid security assessment, and not proof that the software is “secure.” Exploit scenarios below are inferred from code; most were not demonstrated against a running process. |

**How this report was produced:** two independent audits of the same tree (comprehensive first pass; adversarial second pass that challenged the first). This file **does not blindly merge them**. Where they disagreed, the repository was re-inspected and the evidence-backed conclusion is used. See §11.

---

## 2. Executive Summary

**Overall health.** This is a carefully written local CLI/library for pydantic v1→v2 migration. Security engineering in the *intended* threat model (operator runs the tool, irreversible git/PR actions must not fire without `yes`) is unusually strong: fail-closed `Gate`, push-URL fingerprinting, AST-based rewrites, revert-by-default transactions, HTML escaping tests, SHA-pinned GitHub Actions, zero PyPI runtime dependencies.

**Most important security concerns (do not inflate):**

1. **Default path runs the subject’s test suite on the host** with the operator’s full environment (`GH_TOKEN`, cloud keys, git helpers). That is documented, but it is the real operator-risk for anyone pointing the tool at third-party clones (the project’s own fixture workflow).
2. **Sandbox “verification” is model-mediated `exec`**, not a direct Daytona API. A green sandbox result is weaker evidence than a local argv subprocess. This is architecture, not a default-CLI RCE.
3. **Sandbox jobs install bumpsmith from unpinned `main`** (`git clone --depth 1`), unlike fixtures which pin and verify SHAs.

There are **no confirmed remotely exploitable, unauthenticated critical vulnerabilities** in the default CLI. There is **no application user database, no JWT/session product, no public HTTP API** in the package itself.

**Most important documentation / claim concerns:**

1. Packaging/GitHub one-liners imply every run becomes a **reviewed pull request**; the PR path is optional and gated.
2. README/module text claims HTML report values are **never placed in attributes**; `report.py` puts values in `class` and `style` attributes (escaped — XSS not evidenced, claim is still false).
3. Fan-out timings **“2.1s at one worker, 1.1s at four”** are cited as measured on the recorded run; the committed recording **does not contain those numbers**.
4. **“No runtime dependencies”** is true for PyPI; git / subject pytest / `gh` are still required for real use.

**Major strengths.** Honest “what it does not do” section; `Stop`/`Outcome` split; incomplete vs green kept distinct in types; review log + tests that pin README totals; publish destination never inferred; `--sandbox` refused on the CLI because split filesystem would fake verification.

**Major unknowns.** Live site contents; whether sandbox timings still reproduce; hackathon “no pre-window design” vs git history (not re-run here); dependency CVEs; whether Qodo “37 PRs / 129 findings through #37” still matches GitHub.

**Highest-priority issues for Claude Pro:** qualify README/pyproject/GitHub claims; pin or document sandbox self-clone; either record fan-out wall clocks or remove the 2.1s/1.1s sentence; lead operator docs with host-execution + env inheritance; do not add “production-ready / secure / AI-powered migration” language.

---

## 3. Repository Overview

### Purpose

Deterministic **agent-shaped loop** (not an LLM rewriter): run a caller-supplied test suite, classify pydantic v1→v2 breaks from pytest output, match sites on the AST, apply text edits at AST positions, keep edits only if the suite goes green, otherwise revert. Optionally propose a git push + `gh pr create` after a typed `yes`.

### Architecture (modules)

| Module | Role |
|---|---|
| `migrate.py` | Loop; `keep()` only on `Outcome.MIGRATED` |
| `failures.py` | pytest output → `Failure` / `BreakClass` |
| `rules.py` | `Failure` → `Rule` + AST scan |
| `rewrite.py` | sites → `Edit`s; five planners in `_PLANNERS` |
| `apply.py` | Transaction; revert default; refuse paths outside root / symlinks |
| `run.py` | `LocalRunner` / `SandboxRunner` |
| `gate.py` | Fail-closed approval; SHA-256 fingerprint of request |
| `publish.py` | PR proposal + open after gate |
| `harness.py` | TrueForge `tool.approval_required` → same `Gate` |
| `trueforge.py` | Only package code that opens sockets (`urllib`) |
| `remote.py` | Whole loop inside sandbox via shell scripts |
| `fanout.py` | Concurrent jobs; unreached ≠ already-green |
| `report.py` | `--json` payload → `--html` page |
| `rootdir.py` | Foreign pytest config detection |
| `fixtures.py` | Clone pinned third-party SHAs |
| `__main__.py` | CLI; refuses `--sandbox`; default `LocalRunner` |

### Technology stack

- Python **≥3.13**, hatchling, **no PyPI runtime deps** (`pyproject.toml`)
- Dev: `ruff==0.14.5`, `mypy==1.18.2`, `pytest==9.1.1`
- Optional ops: **git**, subject **pytest**, **gh** for PRs, **TrueForge** + sandbox provider (Daytona in proofs) for harness paths
- Static site: `pages/build_site.py` → GitHub Pages workflow

### Auth / data / deploy

- **No** end-user authentication, passwords, JWT, OAuth, or database in this package.
- Irreversible git/PR uses operator `git`/`gh` credentials and an in-process `Gate`.
- TrueForge client sends **unauthenticated** JSON to `base_url` (default `http://localhost:8790/api/v1`).
- CI: `.github/workflows/ci.yml` (`contents: read`, Actions SHA-pinned). Pages: `pages.yml` (`pages: write`, `id-token: write`).

### Important execution flows

1. **Default CLI:** `python -m bumpsmith PATH -- <suite>` → `LocalRunner` → `migrate()` → optional `--json`/`--html` → optional `--open-pr` + terminal `yes`.
2. **Sandbox job:** `SandboxJob` builds `sh -c` scripts that clone this GitHub repo (unpinned), install it, clone a fixture at pinned SHA, run `python -m bumpsmith` **inside** the sandbox so edits and tests share a filesystem.
3. **Harness approval:** `ApprovalBridge` reads the model message; unread calls are denied; send failures do not re-ask.

---

## 4. Security Findings

| ID | Severity | Finding | File | Symbol/Location | Confidence | Status |
|---|---|---|---|---|---|---|
| SEC-001 | Medium (operator data exposure) | Subject suite inherits host environment | `src/bumpsmith/run.py` | `LocalRunner.run` | High | Documented trust boundary + potential data exposure |
| SEC-002 | Info / Low (sandbox path) | Sandbox command integrity is model-mediated | `src/bumpsmith/trueforge.py` | `SandboxExec` | High | Architectural limitation, not default-CLI vuln |
| SEC-003 | Medium (sandbox jobs only) | Sandbox installs bumpsmith from unpinned `main` | `src/bumpsmith/remote.py` | `REPO_URL`, `setup_script` | High | Potential supply-chain / integrity gap |
| SEC-004 | Low–Medium (if harness exposed) | TrueForge HTTP client: no auth, no scheme allowlist, HTTP default | `src/bumpsmith/trueforge.py` | `Client.call`, `DEFAULT_BASE_URL` | High | Hardening / deployment risk |
| SEC-005 | Low | `git push` URL not after `--` | `src/bumpsmith/publish.py` | `_do_open` | High (code); Medium (practical exploit) | Hardening |
| SEC-006 | Low | `--pr-branch` not format-checked | `src/bumpsmith/__main__.py`, `publish.py` | `--pr-branch`, `_do_open` | High (no validation); Low (working takeover) | Hardening |
| SEC-007 | Medium (keep-on-green integrity) | Wrapper suite argv skips `FOREIGN_CONFIG` | `src/bumpsmith/rootdir.py`, `migrate.py` | `runs_pytest`, `migrate` | High | Documented limitation; trust-boundary |
| SEC-008 | Info (correctness/claims) | Incomplete plans can still be kept and published | `src/bumpsmith/migrate.py`, `publish.py` | `Migration.complete`, `propose` | High | Not a vuln; claims/product behavior |
| SEC-009 | Low | PR body interpolates pytest text as Markdown | `src/bumpsmith/publish.py` | `body_for` | High (no escape); Low (GitHub XSS) | Hardening |
| SEC-010 | Low | `--json`/`--html` write any path | `src/bumpsmith/__main__.py` | `main` | High | Operator footgun |
| SEC-011 | Low | Residual race after approval vs `git add` | `src/bumpsmith/publish.py` | `_do_open` | High (window exists) | Hardening |
| SEC-012 | Info | Committed proof logs contain home paths | `proofs/recorded/` | validator/pull_request artefacts | High | Data exposure (paths, not tokens) |
| SEC-013 | Info | Dependabot covers GitHub Actions only | `.github/dependabot.yml` | n/a | High | Config hardening |
| SEC-014 | Info | Gate fingerprint is not authentication | `src/bumpsmith/gate.py` | `Request.fingerprint` | High | Documented design |

**Not listed as vulnerabilities (explicitly):** XSS in `--html` (escaping + tests exist); missing JWT/CORS/CSRF (no web app); SQL injection (no DB); default CLI command injection (argv lists, `shell=False`); apply path traversal outside root (refused); `rmtree` of arbitrary `--out` on the site builder (marker + non-symlink guard).

---

### SEC-001: Subject suite inherits the host environment

- **Severity:** Medium (data exposure when secrets are present). Not a remote RCE.
- **Confidence:** High that `Popen` inherits `os.environ`. Exploitability depends on the subject tree.
- **Status:** Documented trust boundary + potential data exposure
- **File:** `src/bumpsmith/run.py`
- **Symbol:** `LocalRunner.run`
- **Line:** 198–213 (`subprocess.Popen` with no `env=`)
- **Also:** `src/bumpsmith/fixtures.py` `_git` line 270: `environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}`
- **CLI default:** `src/bumpsmith/__main__.py` line 438: `LocalRunner(timeout=args.timeout)`
- **Evidence:** No environment scrubbing. Default command is pytest (`DEFAULT_COMMAND` line 36).
- **What the code does:** Runs the operator-supplied argv in a subprocess on this machine, capturing combined stdout/stderr, killing the process group on timeout (POSIX).
- **Why it is a security concern:** The project’s own workflow clones **third-party** repositories and runs **their** tests. Those tests see `GH_TOKEN`, AWS keys, `git` credential helpers, etc.
- **Potential exploitation scenario:** Malicious or compromised `conftest.py` reads the environment and exfiltrates tokens during a migration attempt.
- **Preconditions:** Operator runs bumpsmith (or fixture clone) with secrets in the environment against code they did not fully trust.
- **Impact:** Credential theft; same class of risk as “I ran pytest in this repo myself,” plus the tool *encourages* third-party checkouts.
- **Recommended direction:** Document at the top of README; optionally pass a filtered `env=` (allowlist) for `LocalRunner`; prefer sandbox for untrusted trees.
- **Notes:** Audit 1 called this HIGH “no isolation.” Audit 2 downgraded isolation-as-vuln to INFO and added the **env** angle. Final: isolation is documented and expected; **secret inheritance is the actionable finding.**

---

### SEC-002: Sandbox command integrity depends on the model calling `exec` verbatim

- **Severity:** Info for default CLI; Low–Medium as *evidence quality* on the sandbox path
- **Confidence:** High
- **Status:** Architectural limitation (potential vulnerability only if a sandbox green is treated as cryptographic proof)
- **File:** `src/bumpsmith/trueforge.py`
- **Symbol:** `SandboxExec.INSTRUCTIONS`, `SandboxExec.__call__`
- **Line:** 379–427 (docstring 383–386; prompt 424)
- **Evidence:** “There is no endpoint that runs a command in Daytona — `exec` is a tool the model calls.” Prompt asks the model to call `exec` once verbatim.
- **What the code does:** Creates a TrueForge session with sandbox enabled, posts a natural-language prompt, polls for an `exec` tool result JSON.
- **Why it is a security concern:** A misaligned/compromised model or hostile harness can run a different command and still return a JSON-shaped success. `migrate()` will not keep *local* edits from a `where="sandbox"` result (`SAME_TREE` in `migrate.py` ~78–94, ~513–518). `SandboxJob` runs the **whole loop inside** the sandbox with `LocalRunner` there, so a lying `exec` can still lie about *that* filesystem.
- **Potential exploitation scenario:** Model reports `exitCode: 0` for a command it did not run; a remote job’s JSON report looks green.
- **Preconditions:** Using `SandboxExec` / `SandboxJob` / proofs against a live harness. Not `python -m bumpsmith` default.
- **Impact:** False verification of sandbox jobs; not host compromise of the operator laptop by default.
- **Recommended direction:** Prefer a non-LLM exec API if TrueForge adds one; document that sandbox greens are weaker than local argv; do not market “cryptographically isolated verification.”
- **Notes:** Audit 1 = HIGH vuln. Audit 2 = over-graded. **Final: not a confirmed default-CLI vulnerability.**

---

### SEC-003: Sandbox setup clones this package from floating `main`

- **Severity:** Medium (integrity of sandbox jobs and live proofs)
- **Confidence:** High
- **Status:** Potential supply-chain / reproducibility gap
- **File:** `src/bumpsmith/remote.py`
- **Symbol:** `REPO_URL` (line 93), `setup_script` (lines 469–470)
- **Evidence:** `git clone --depth 1 -q https://github.com/aryangorde8/bumpsmith` then `pip install -q ./bumpsmith`. Contrast `fixtures.clone`, which verifies `HEAD == fixture.sha`.
- **What the code does:** Because the harness has download-from-sandbox but no upload, the job installs the public repo inside the sandbox.
- **Why it is a security concern:** The sandbox may not run the commit under review. Compromise or unexpected `main` movement changes agent behavior.
- **Potential exploitation scenario:** Attacker with push to `main` (or a swapped default branch) alters what sandbox jobs execute.
- **Preconditions:** `SandboxJob` / `proofs/sandbox_fanout.py`, network, public clone.
- **Impact:** Wrong or malicious agent in Daytona; proof/repro drift.
- **Recommended direction:** Clone a specific SHA/tag matching the operator’s checkout; or copy a wheel if the harness gains upload.
- **Notes:** Both audits agreed. Scope is **sandbox jobs**, not laptop CLI.

---

### SEC-004: TrueForge client has no credentials and no URL-scheme allowlist

- **Severity:** Low on localhost; Medium if `base_url` is a network-exposed or unexpected scheme
- **Confidence:** High on missing auth/allowlist
- **Status:** Security hardening / deployment risk
- **File:** `src/bumpsmith/trueforge.py`
- **Symbol:** `DEFAULT_BASE_URL` (line 43), `Client.call` (lines 200–208)
- **Evidence:** Headers are only `Content-Type` / `Accept`. `# noqa: S310` on `Request`/`urlopen`. `base_url` is `rstrip("/")` with no `https://` check. Stdlib `urlopen` can use `file:` and follow HTTP redirects.
- **What the code does:** JSON HTTP(S) to `{base}{path}` for sessions/turns/events.
- **Why it is a security concern:** Anyone who can reach an unauthenticated harness API can drive turns/sandboxes. A caller-supplied `file://` or cloud-metadata URL is not rejected in this client.
- **Potential exploitation scenario:** Mis-bound TrueForge on a LAN; or a wrapper passing a hostile `base_url`.
- **Preconditions:** Non-localhost or attacker-controlled `base_url`. Not input from the migrated repository.
- **Impact:** Unauthorized harness use; possible unexpected URL fetches.
- **Recommended direction:** Allowlist `http(s)` (and maybe Unix sockets); require HTTPS + auth for non-loopback; document localhost-only assumption.
- **Notes:** Audit 1 emphasized missing auth. Audit 2 added scheme/SSRF. Both kept; neither is a confirmed unauthenticated vuln in the CLI itself.

---

### SEC-005: `git push` does not place the URL after `--`

- **Severity:** Low
- **Confidence:** High that `--` is absent; Medium that a real remote URL would start with `-`
- **Status:** Security hardening recommendation
- **File:** `src/bumpsmith/publish.py`
- **Symbol:** `_do_open`
- **Line:** 739: `_git(runner, root, "push", proposal.url, f"HEAD:refs/heads/{proposal.branch}")`
- **Contrast:** Lines 718 and 732 use `"add"|"commit", "--", *paths`. `fixtures.py` lines 43–45 refuse URLs git would treat as options.
- **What the code does:** Pushes to the **approved URL** (not the remote name).
- **Why it is a security concern:** A push URL beginning with `-` can be parsed as a git option (`-f`, `--mirror`, `--upload-pack=…`).
- **Potential exploitation scenario:** Local `.git/config` / `pushurl` set to an option-shaped string.
- **Preconditions:** Attacker or confused operator can set the named remote’s push URL. Usual `https://github.com/…` URLs are unaffected.
- **Impact:** Unexpected git behavior; possible extra flags; not proven RCE in this audit.
- **Recommended direction:** `git push -- {url} {refspec}` and reject URLs starting with `-`.
- **Notes:** Missed by audit 1; added by audit 2; re-verified.

---

### SEC-006: `--pr-branch` is interpolated into refspecs without format checks

- **Severity:** Low
- **Confidence:** High that validation is absent; Low that this yields a working push to an unintended ref
- **Status:** Security hardening recommendation
- **File:** `src/bumpsmith/__main__.py` (lines 176–180), `src/bumpsmith/publish.py` (checkout `-b` ~714; push refspec ~739; `rev-parse` `refs/heads/{branch}` ~500)
- **Evidence:** No `git check-ref-format`; `checkout -b` not followed by `--`.
- **Recommended direction:** Validate branch names; pass `--` before the branch to `checkout`.
- **Notes:** Not a confirmed vulnerability. Do not treat as proven privilege escalation.

---

### SEC-007: `FOREIGN_CONFIG` only runs when argv “looks like pytest”

- **Severity:** Medium as **keep-on-green integrity** (wrong tests → false green → kept edits). Not remote authz failure.
- **Confidence:** High
- **Status:** Documented limitation / trust-boundary
- **File:** `src/bumpsmith/rootdir.py` `runs_pytest` (lines 233–260); `src/bumpsmith/migrate.py` lines 456–467
- **Evidence:** Docstring: `tox`, `uv run pytest`, `make pytest` are left alone. An outside inifile that **deselects** tests can yield rc=0; `outcome_of(GREEN, applied)` → `MIGRATED` → `keep()` (lines 486–488).
- **Mitigation already present:** Default CLI command **is** `sys.executable -m pytest -q` (line 36), which **is** detected. README examples using `-m pytest` are covered.
- **Recommended direction:** Keep the blunt check; document loudly that wrappers skip it; optionally warn when `runs_pytest` is false.
- **Notes:** Audit 1 listed FOREIGN_CONFIG as a verified control. Audit 2 correctly narrowed it. **Final: control is real for default argv, incomplete for wrappers.**

---

### SEC-008: Green incomplete migrations can be kept and opened as PRs

- **Severity:** Info (product/claims). Not a security vuln.
- **Confidence:** High
- **Status:** Intended behavior with documentation risk
- **File:** `src/bumpsmith/migrate.py` `Migration.complete` (lines 333–347, especially 340–346); `keep()` 486–488; `publish.propose` requires only `Outcome.MIGRATED` (~391)
- **Evidence:** Loop does **not** refuse incomplete plans. Terminal report prints `NOT COMPLETE` (`__main__.py` 250–254). PR body warns later (`body_for` ~301–304) after stronger “suite passes with these edits” sentences (~258–260).
- **Recommended direction:** Do not describe every kept run as a finished v1→v2 migration; lead PR copy with completeness.
- **Notes:** Both audits: keep-on-green is true; “finished” is not implied by green.

---

### SEC-009: Pull-request Markdown is not escaped

- **Severity:** Low
- **Confidence:** High (no escaping); Low (GitHub executing script)
- **Status:** Hardening
- **File:** `src/bumpsmith/publish.py` `body_for` (~258–268)
- **Evidence:** Failure messages interpolated inside backticks; rationale/skips unescaped Markdown.
- **Impact:** Broken rendering / review confusion. GitHub sanitizes HTML; stored XSS not evidenced.
- **Recommended direction:** Escape backticks or use fenced blocks with a safe delimiter.

---

### SEC-010: Report flags write arbitrary filesystem paths

- **Severity:** Low
- **Confidence:** High
- **Status:** Operator footgun
- **File:** `src/bumpsmith/__main__.py` (~461–469) `path.write_text`
- **Evidence:** No root jail. Collision of `--json` and `--html` on the same resolved path is refused (~400–409).
- **Recommended direction:** Optional refuse-to-overwrite / stay under cwd.

---

### SEC-011: Residual publish race after human approval

- **Severity:** Low (Medium only if you assume a hostile local concurrent writer)
- **Confidence:** High that a window remains; the long human-window class of bugs was already mitigated
- **Status:** Hardening
- **File:** `src/bumpsmith/publish.py` `_do_open` (~688–718): re-runs `_require_a_publishable_tree` then `checkout`/`add`
- **Evidence:** Recheck vs `git add` is not atomic.
- **Recommended direction:** Stage from known blobs (`hash-object` / index from `edit.after`).
- **Notes:** Audit 1 MEDIUM; audit 2 LOW. **Final: Low.**

---

### SEC-012: Recorded proofs leak local absolute paths

- **Severity:** Info
- **Confidence:** High
- **Status:** Data exposure (paths/username), not secrets
- **File:** `proofs/recorded/validator.log` line 1; `validator.json` `"python"`; `pull_request.json` / `.log`
- **Evidence:** `/home/aryan/bumpsmith-work/venv-b2/bin/python`, `/home/aryan/bumpsmith/.venv/bin/python`
- **Recommended direction:** Redact like `pages/runs.toml` `redacted` for JSON reports.

---

### SEC-013: Dependabot does not cover Python deps

- **Severity:** Info
- **Confidence:** High
- **Status:** Config hardening
- **File:** `.github/dependabot.yml` (github-actions only)
- **Evidence:** Runtime deps are empty; **dev** pins (`ruff`/`mypy`/`pytest`) can still rot. No pip-audit in CI.
- **Unknown:** Actual CVEs (not scanned in this audit).

---

### SEC-014: Approval fingerprint is not a cryptographic capability token

- **Severity:** Info
- **Confidence:** High
- **Status:** Documented design
- **File:** `src/bumpsmith/gate.py` `Request.fingerprint` (lines 104–132)
- **Evidence:** Docstring: binds identity of the request in-process; anyone holding the request can compute it; forging `Allow` implies ability to call the effect anyway.
- **Do not “fix”** by treating this as missing HMAC unless there is a multi-process approval protocol.

---

## 5. Claims and Assertions Audit

| ID | Claim | Location | Classification | Evidence | Confidence |
|---|---|---|---|---|---|
| CL-001 | Turns a failing v1→v2 migration into a reviewed pull request | `pyproject.toml` L8; `src/bumpsmith/__init__.py` L1 | PARTIALLY VERIFIED | Capability exists via `--open-pr` + `yes`; default CLI does not open a PR | High |
| CL-002 | No runtime (PyPI) dependencies | `pyproject.toml` L13–16; README Install | PARTIALLY VERIFIED | `dependencies = []`; git/pytest/`gh`/TrueForge still needed for full use | High |
| CL-003 | No model decides the rewrite | README “No model decides the rewrite”; loop modules | VERIFIED | `failures`/`rules`/`rewrite`/`migrate` are deterministic; tests exist | High |
| CL-004 | `--sandbox` is parsed and refused | README; `__main__.py` ~376–378 | VERIFIED | Exits 2 with reason | High |
| CL-005 | Revert by default; keep only if suite green | README; `apply.attempt`; `migrate` 486–488 | VERIFIED | `keep()` only on `Outcome.MIGRATED`; SIGKILL exception is documented | High |
| CL-006 | Edits stay inside root; symlinks refused | `apply._verify` | VERIFIED | Tests in `tests/test_apply.py` | High |
| CL-007 | HTML report: escaped; no scripts; no network | README; `report.py`; `tests/test_report.py` | PARTIALLY VERIFIED | Escape + no `<script>` tested; “never in an attribute” is false | High |
| CL-008 | Values never placed in an attribute, script, style, or URL | `report.py` L27–28; README ~232–234 | CONTRADICTED | `class="end {_e(outcome)}"` L346; `style="width:{share}%"` L216. Gallery `href` is a different file | High |
| CL-009 | Five rewriters; class 2 absent; 8 classes | README taxonomy; `rewrite._PLANNERS`; `BreakClass` | VERIFIED | `_PLANNERS` has 5; `has_rewriter`; `test_docs.py` pins taxonomy | High |
| CL-010 | FOREIGN_CONFIG / WRONG_PLACE stop unsafe greens | README; `migrate.py`; `rootdir.py` | PARTIALLY VERIFIED | True for pytest-shaped argv and `where`; wrappers skipped (SEC-007) | High |
| CL-011 | 181 findings in REVIEW-LOG as of 28 Aug 2026 | README; `REVIEW-LOG.md`; `tests/test_docs.py` | VERIFIED (count) | Table row count + test; **split** 133/4/44 is hand-maintained (README admits) | High / Medium on split |
| CL-012 | Qodo: 37 PRs, 37 reviewed, 129 inline findings through #37 | README | UNVERIFIABLE here | Procedure given; GitHub not re-counted in this audit | Medium that the *anchored* sentence is internally consistent |
| CL-013 | Sandbox fan-out ~44.3s wall | README; `proofs/recorded/sandbox_fanout.json` | VERIFIED | `wall_seconds: 44.25`; log `44.3s wall clock` | High for **that recorded run** |
| CL-014 | Fan-out 2.1s @1 worker, 1.1s @4, “measured on the recorded run” | README TrueForge table; `proofs/README.md` ~270 | CONTRADICTED (citation) / UNSUPPORTED (numbers in-repo) | `proofs/recorded/fanout.json` has no wall time; `proofs/fanout.py` does not record worker-scaling timings | High |
| CL-015 | Four recorded runs published at aryangorde.com/bumpsmith | README | PARTIALLY VERIFIED | `pages/runs/*.json`, `build_site.py`, Pages workflow exist; live URL not fetched | Medium |
| CL-016 | bump-pydantic table (31/24/347 passed, 0 tests recovered, 18 files, …) | README | UNVERIFIABLE | Dates and pins in `fixtures.toml`; this audit did not re-run those suites | High that we cannot verify |
| CL-017 | C: classes 1/3/4 match zero sites (24 Aug 2026) | README | UNVERIFIABLE | Would require cloning fixture C at pinned SHA and scanning | High |
| CL-018 | Hackathon: no project code/design before 24 Aug 2026 | README | UNVERIFIABLE | Needs git history dating; not executed here | High |
| CL-019 | Nothing pushed to `main` directly; `--merge` not squash | README | UNVERIFIABLE | Needs GitHub/git history | High |
| CL-020 | AI assistants used; author can explain the system | README | UNVERIFIABLE | Disclosure is present; competence is not a repo fact | High |
| CL-021 | MIT license; fixtures not vendored | README; `LICENSE`; `fixtures.toml` | VERIFIED | Clone-from-upstream design | High |
| CL-022 | GitHub repo description “TrueForge” | GitHub API (`aryangorde8/bumpsmith`) | PARTIALLY VERIFIED / misleading | Repo exists and is public; description does not state pydantic migration | High |
| CL-023 | “Runs the suite somewhere safe” (TrueForge table) | README | PARTIALLY VERIFIED | Wiring + recorded Daytona run exist; safety = provider + model `exec` (SEC-002) | High |
| CL-024 | Stops for a person before anything irreversible | README; `gate.py`; `publish.py`; `__main__._AskAtTheTerminal` | PARTIALLY VERIFIED | True for push/PR and harness tools; **false** for local pytest side effects | High |
| CL-025 | Suite command after `--`; exit 0/1/2 meanings | README; `__main__.py` | VERIFIED | Parser and `_status` | High |

### Non-VERIFIED claims (detail)

**CL-001 — “reviewed pull request” as the product.**  
Exact claim: *“An agent that turns a failing pydantic v1-to-v2 migration into a reviewed pull request.”*  
Repo demonstrates: `publish.open_pull_request` + gate + `yes`. Default `main()` never calls it unless `--open-pr` is set.  
**Safe:** “Can open a PR after a green keep, if you name a remote and type `yes`.”  
**Do not claim:** Default or fully automatic PR creation.

**CL-002 — No runtime dependencies.**  
**Safe:** “No third-party PyPI packages at runtime.”  
**Do not claim:** Zero external tools.

**CL-007 / CL-008 — HTML safety wording.**  
Implementation escapes with `html.escape(..., quote=True)` and tests hostile payloads (`tests/test_report.py`). Untrusted strings **are** placed in HTML **attributes** (`class`, and integer `style` width). Gallery index adds `href` for `https://` upstream (`pages/build_site.py` `_card` ~202–204).  
**Safe:** “Untrusted text is HTML-escaped; no JS; `--html` has no external assets.”  
**Do not claim:** “Never in an attribute or URL” without qualifying the gallery vs `--html`.

**CL-010 — FOREIGN_CONFIG always saves you.**  
**Safe:** “When the suite argv is pytest (or `-m pytest`), an outside inifile that sets anything is refused.”  
**Do not claim:** All suite wrappers are covered.

**CL-011 split 133/4/44.** README states the split is **not** machine-checked. Treat totals as verified by `test_docs.py`; treat provenance split as author claim.

**CL-014 — 2.1s / 1.1s.** Do **not** invent replacement timings. Either re-record with wall clocks in `proofs/recorded/` or delete the numbers.

**CL-015 — live site.** Code can build the site; this audit did not GET the public URL.

**CL-016 / CL-017 / CL-018 / CL-019.** Empirical or historical; do not repeat as proven in new docs without re-measurement or `git log`/`gh` evidence.

**CL-022.** Change GitHub description to match README, or keep “TrueForge hackathon entry” **and** pydantic migrator.

**CL-023 / CL-024.** Qualify “safe” and “irreversible”: local pytest is irreversible from a *host* perspective (code execution, leftover caches).

---

## 6. Documentation vs Implementation

| Documented | Actual | Evidence | Importance | Correction direction |
|---|---|---|---|---|
| Product = reviewed PR | Optional gated PR | `pyproject.toml`; `__main__.py` | High (marketing) | Qualify one-liners |
| `--html`: never in attributes | Attributes used | `report.py` 216, 346 | Medium (honesty; XSS still tested) | Narrow the sentence to “escaped; not in script/URL for `--html`” |
| Fan-out 2.1s/1.1s on recorded run | Recording has no wall times | `proofs/recorded/fanout.json` | High (false citation) | Remove or re-record |
| FOREIGN_CONFIG as general pytest-config defense | Skipped for non-pytest argv | `runs_pytest` | Medium | Already partly documented; don’t oversell in interviews |
| `--sandbox` “run in sandbox” flag help text | Flag refused | `__main__.py` 189–192, 376–378 | Low (honest in long README) | Help string already says refused |
| Remote whole-loop sandbox exists | Exists without CLI flag | `remote.py`; README | Low | Docs already say CLI route missing |
| “No isolation when local” | Matches `LocalRunner` | README + `run.py` 183–187 | Positive match | Keep; add env/secrets |
| Site never committed (`pages/_site/`) | `.gitignore` lists it | `.gitignore` | Low | OK if local `_site` exists after builds |
| GitHub description “TrueForge” | README is pydantic migrator | GitHub API vs README | Medium | Align metadata |
| Module table “everything in src” | Guarded by `test_docs.py` | `tests/test_docs.py` | Positive | Keep tests |
| Incomplete vs green | Types separate; PR copy leads with “suite passes” | `complete` vs `body_for` | Medium | Lead with completeness in PR template |

**Setup instructions** (`pip install -e ".[dev]"`, `python -m bumpsmith PATH -- …`) match `__main__.py` and `pyproject.toml` at a glance. This audit did **not** execute them.

**CI claims** (ruff, mypy, pytest on 3.13, SHA-pinned actions) match `.github/workflows/ci.yml`. Whether GitHub currently goes green is **unknown**.

---

## 7. Resume / Portfolio / Interview Claim Audit

| Claim type | Classification | Notes |
|---|---|---|
| Deterministic pydantic v1→v2 migration loop driven by pytest, AST rewrite, revert-by-default | **SAFE TO CLAIM** | Core of `migrate`/`rules`/`rewrite`/`apply` |
| Fail-closed human gate for push/PR; remote never inferred; push to URL not name | **SAFE TO CLAIM** | `gate.py`, `publish.py`; tests |
| Optional TrueForge integration: sandbox jobs, approval bridge, recorded deny (0 tool calls) | **NEEDS QUALIFICATION** | Proofs are dated recordings; MCP tool exercised is the one **refused** (README admits) |
| “AI-powered / LLM migrates the code” | **DO NOT CLAIM** | README explicitly: no model in rewrite path |
| “Fully automated PRs / no human” | **DO NOT CLAIM** | Requires `yes`; non-TTY denies |
| “Production-ready / enterprise-grade / secure” | **DO NOT CLAIM** | Not claimed in README; do not add |
| “Runs safely in a sandbox by default” | **DO NOT CLAIM** | Default is `LocalRunner`; `--sandbox` refused |
| “High performance / scalable / 99.9%” | **DO NOT CLAIM** | No SLO, no load test |
| Sandbox fan-out **44.3s** on the recorded 27 Aug run (B+C+unreachable, 4 workers) | **NEEDS QUALIFICATION** | Cite the artefact (`sandbox_fanout.json`); not a general benchmark |
| Fan-out **2.1s / 1.1s** | **DO NOT CLAIM WITHOUT ADDITIONAL EVIDENCE** | Not in recorded JSON |
| bump-pydantic recovered **0** tests on three pinned repos | **NEEDS QUALIFICATION** | Cite date, pins, versions; re-run before putting on a resume as current fact |
| Review culture: 181 logged findings, Qodo on PRs, tests pin README totals | **NEEDS QUALIFICATION** | 181 is file-backed; Qodo 129 is **anchored to #37**, not “now”; split 133/4/44 is manual |
| “I built an agent harness” | **NEEDS QUALIFICATION** | TrueForge is the harness; this repo is a **client** + proofs |
| Real-time / streaming agent | **DO NOT CLAIM** | Polling HTTP client |
| User counts / production traffic | **DO NOT CLAIM** | No evidence |

**Conservative resume bullet (safe):**  
*Built a stdlib-only Python 3.13 CLI that classifies pydantic v1→v2 test failures, rewrites matching AST sites, and keeps edits only after the subject’s suite returns green—otherwise reverts. Irreversible git/PR actions go through a fail-closed approval gate that binds the push URL, not the remote name.*

**Unsafe resume bullet:**  
*AI agent that automatically migrates production codebases in a secure sandbox and opens PRs.*

---

## 8. Verified Technical Capabilities

Useful for later documentation. Each item is **directly** in the tree.

| Capability | Evidence | Path | Symbol |
|---|---|---|---|
| Classify pytest failures into a closed `BreakClass` set; unknown ≠ guess | `failures.py`; tests | `src/bumpsmith/failures.py` | `parse_failures`, `BreakClass` |
| Map failure → rule; AST scan with import/alias awareness | `rules.py`; tests | `src/bumpsmith/rules.py` | `write_rule`, `find_matches` |
| Five textual rewriters at AST positions (not `ast.unparse`) | `_PLANNERS` | `src/bumpsmith/rewrite.py` | `plan`, `has_rewriter` |
| Apply all-or-nothing; revert default; refuse outside root / symlinks / stale content | `apply.py`; tests | `src/bumpsmith/apply.py` | `attempt`, `_verify` |
| Keep edits only when stop is green and something was applied | `outcome_of` + `keep()` | `src/bumpsmith/migrate.py` | `migrate`, `outcome_of` |
| Refuse suite results from `where != "local"` in this process | `SAME_TREE` | `src/bumpsmith/migrate.py` | `_peel` |
| Refuse outside pytest inifile for pytest-shaped argv | `foreign_config` | `src/bumpsmith/rootdir.py` | `runs_pytest`, `foreign_config` |
| Local subprocess runner; timeout kills process group on POSIX | `run.py`; tests | `src/bumpsmith/run.py` | `LocalRunner`, `_end_process_tree` |
| Sandbox runner parses TrueForge exec JSON strictly | `_read_exec_result` | `src/bumpsmith/run.py` | `SandboxRunner` |
| HTTP client to TrueForge; treat ambiguous transport as “may have run” | `trueforge.py` | `src/bumpsmith/trueforge.py` | `Client`, `SandboxExec` |
| Fail-closed gate; fingerprint bind; no env bypass | `gate.py`; tests | `src/bumpsmith/gate.py` | `Gate.run` |
| Terminal approver requires exact `yes`; non-TTY denies | `__main__.py` | `_AskAtTheTerminal.decide` | ~272–300 |
| Publish: named remote, push URL, refuse multi-pushurl, `gh --repo` from URL | `publish.py`; tests | `src/bumpsmith/publish.py` | `propose`, `_push_url`, `_github_slug`, `_do_open` |
| Harness: unread tool call denied; wrapper `call_tool` unwrapped; failed send not re-asked | `harness.py` | `ApprovalBridge` | ~504–566, 600–626 |
| Fan-out: unreached jobs not counted as already-green | `fanout.py`; tests | `src/bumpsmith/fanout.py` | `fan_out` |
| Remote sandbox job scripts quote with `shlex`; report must checksum | `remote.py` | `setup_script`, `read_report` | |
| HTML report from same payload as JSON | `report.py`; tests | `page` | |
| Site build: slug allowlist; rmtree only with regular-file marker | `pages/build_site.py`; `tests/test_pages.py` | `_clear`, `_SLUG` | |
| Fixtures: HTTPS/`file://` only; 40-char SHA; HEAD verify; no delete of existing dest | `fixtures.py` | `clone`, `load_manifest` | |
| CI: contents read; Actions pinned to SHAs; Dependabot for actions | `.github/` | `ci.yml`, `pages.yml`, `dependabot.yml` | |
| Docs tests pin Stop/Outcome/module tables and finding **total** | `tests/test_docs.py` | | |
| Recorded proofs (sandbox, deny, fanout, validator, session_reconnect, pull_request) | `proofs/recorded/` | | |

---

## 9. Unknowns and Missing Evidence

| Unknown | Why unverifiable here | Evidence that would verify |
|---|---|---|
| Live https://aryangorde.com/bumpsmith/ matches `pages/runs/` | URL not fetched | HTTP GET + compare to `pages/_site` build |
| Fan-out 2.1s / 1.1s | Not in `proofs/recorded/fanout.json` | Re-run `proofs/fanout.py` at 1 and 4 workers; commit wall times |
| 44.3s still reproducible | Recording is historical | Re-run `sandbox_fanout.py` with same model/provider |
| bump-pydantic comparison table | Not re-run | Fresh clones at `fixtures.toml` SHAs + bump-pydantic 0.8.0 + pydantic 2.13.4 |
| Fixture C zero matches for classes 1/3/4 | Not scanned in this audit | Clone C; run `find_matches` for those rules |
| Hackathon window vs first project commits | Shell/git history not used for dating | `git log --reverse --format='%ci %s'` vs 24 Aug 2026 08:00 London |
| Direct pushes to `main` / squash merges | History not fully enumerated | `git log origin/main`; GitHub merge settings |
| Qodo 37/37/129 **as of now** | README anchors to #37; GitHub not re-looped | Re-run the README `gh`/`jq` script with cutoff |
| Dev-tool CVEs | No scanner | `pip-audit` on `.[dev]` |
| Whether GH_TOKEN is present when users run fixtures | Environment-specific | N/A — document the risk |
| TrueForge 0.1.4 still matches client | Proofs dated Aug 2026 | Live protocol tests |
| Production reliability / users / scale | No ops telemetry | Would need actual production |

**Do not invent** any of the above.

---

## 10. Consolidated Priority List

| Priority | ID | Issue | Why it matters | Evidence | Recommended next step |
|---|---|---|---|---|---|
| P1 | CL-001, CL-022 | One-liners oversell PR / GitHub description | Resume, judges, `pip show` | `pyproject.toml` L8; GitHub description | Qualify copy; do not change behavior unless desired |
| P1 | CL-014 | 2.1s/1.1s cited against a recording that lacks timings | False citation (project’s own anti-pattern) | `proofs/README.md` vs `proofs/recorded/fanout.json` | Delete numbers or re-record wall clocks — **do not invent new numbers** |
| P1 | SEC-003 | Unpinned `main` clone in sandbox jobs | Proofs/jobs may not match reviewed commit | `remote.setup_script` L469 | Pin SHA/tag |
| P1 | SEC-001 | Host env inherited by third-party tests | Token theft risk on the advertised fixture workflow | `LocalRunner.run`; `fixtures._git` | Document prominently; consider env allowlist |
| P2 | CL-008 | “Never in an attribute” vs code | Honesty of XSS writeup | `report.py` 27–28 vs 216, 346 | Tighten wording |
| P2 | CL-023, SEC-002 | “Somewhere safe” vs model `exec` | Interview overclaim | `SandboxExec` docstring | Qualify sandbox evidence |
| P2 | SEC-007 | Wrapper argv skips FOREIGN_CONFIG | False green keep | `runs_pytest` | Document; optional warning |
| P2 | SEC-004 | Harness client auth/schemes | Only if harness is exposed | `Client.call` | Allowlist + localhost docs |
| P2 | SEC-008 | PR body leads with “suite passes” | Incomplete can still publish | `body_for`; `Migration.complete` | Lead with completeness |
| P3 | SEC-005 | `git push` without `--` | Option-shaped push URLs | `publish.py` L739 | Add `--` |
| P3 | SEC-006 | Unvalidated `--pr-branch` | Argv/ref confusion | `__main__.py` 176–180 | `check-ref-format` |
| P3 | SEC-009 | Markdown in PR body | Review UI confusion | `body_for` | Escape |
| P3 | SEC-010 | Report path overwrite | Footgun | `__main__.py` 467–469 | Optional guards |
| P3 | SEC-011 | Post-approval add race | Local concurrent writer | `_do_open` | Blob staging |
| P4 | SEC-012 | Home paths in proofs | Minor disclosure | `proofs/recorded/validator.log` | Redact |
| P4 | SEC-013 | Dependabot pip | Dev pin drift | `dependabot.yml` | Add pip ecosystem if desired |
| P4 | CL-011 split | 133/4/44 not machine-checked | README already admits | README Review section | Leave or mark rows in the log |
| P4 | SEC-014 | Fingerprint ≠ auth | Easy to “fix” wrongly | `gate.py` | Do not add a fake HMAC story |

**No P0 (critical/immediate remote compromise) was evidenced.**

---

## 11. Disagreements Between Audits

| Topic | Audit 1 | Audit 2 | Repository evidence | Final conclusion | Confidence |
|---|---|---|---|---|---|
| `SandboxExec` severity | HIGH vulnerability | Over-graded; architectural | Default CLI never uses it; `--sandbox` refused; docstring admits model `exec` | **Not a confirmed default-CLI vuln.** Document as evidence-quality limit on sandbox greens. | High |
| `LocalRunner` isolation | HIGH (then hedged INFO) | Isolation is documented INFO; **env inheritance** was missed | `Popen` no `env=`; README “no isolation”; fixtures clone third-party code | **Do not call HIGH RCE.** **Do** treat env inheritance as Medium operator data-exposure. | High |
| TrueForge client | MEDIUM missing auth | Add scheme allowlist; over-scoped as “open proxy” | No auth headers; `urlopen` S310; default localhost | Combine: **hardening**. Severity depends on harness bind address. | High |
| Publish TOCTOU | MEDIUM | LOW after revalidation | `_do_open` rechecks then add | **Low** residual race | High |
| FOREIGN_CONFIG | VERIFIED control | PARTIAL (wrappers) | `if runs_pytest(command)` | **Partial.** Default argv is covered. | High |
| “No runtime deps” | VERIFIED | PARTIAL (git/gh/pytest) | `dependencies = []` vs publish/fixtures | **Partial** | High |
| HTML “never in attributes” | Lumped into verified escaped HTML | CONTRADICTED | `report.py` L27–28 vs L216, L346 | **Claim contradicted; XSS still not evidenced** | High |
| Fan-out 2.1s/1.1s | UNSUPPORTED + contradicted citation | Agreed | `fanout.json` has no `wall_seconds` | **Do not use the numbers** | High |
| 44.3s sandbox fan-out | VERIFIED | Agreed | `wall_seconds: 44.25` | **Verified for that recording only** | High |
| `git push --` / `--pr-branch` | Missed | Added as Low | L739 vs add/commit `--` | **Include as hardening** | High |
| Critical vulns | None | None | No unauthenticated remote RCE found | **None confirmed** | High |

There **were** meaningful disagreements; they were about **severity and claim labels**, not about whether the files exist.

---

# Handoff to Claude Pro

This file is the **standalone** result of two repository audits of `bumpsmith` (29 August 2026). Treat it as a briefing, not as a substitute for reading the code.

**Confirmed (high confidence, in-tree):** deterministic non-LLM rewrite loop; revert-by-default; keep only on green; CLI `--sandbox` refused; gate fail-closed; publish destination not inferred; HTML escaping tests; zero PyPI runtime deps; SHA-pinned Actions; sandbox self-clone is unpinned `main`; `LocalRunner` inherits the environment; `FOREIGN_CONFIG` skips non-pytest argv; `report.py` places some values in attributes despite “never in an attribute”; fan-out 2.1s/1.1s is **not** in the recorded JSON; 44.3s **is** in `sandbox_fanout.json`.

**Uncertain / not vulnerabilities:** model-mediated sandbox `exec` (architecture); `--pr-branch` takeover (unproven); SSRF via `file://` `base_url` (operator-controlled); GitHub XSS from PR Markdown (unproven); live site; CVEs; git-history hackathon window.

**Safe to claim:** stdlib CLI; pytest-driven classification; AST rewrites; transactional revert; gated optional PR; TrueForge *client* with recorded proofs.

**Needs qualification:** “agent,” “reviewed PR,” “safe sandbox,” review-count splits, bump-pydantic table, 44.3s as a general performance claim.

**Do not claim:** production-ready, enterprise-secure, AI writes the migration, fully automated PRs, 2.1s/1.1s, default sandbox isolation.

**Prioritize:** documentation/claim honesty (P1), pin sandbox clone (P1), operator env warning (P1), then hardening items in §10. **Do not invent metrics** to replace removed timings.

Independently verify important conclusions in the repository before editing. Goal: fix real issues and tighten docs **without inventing capabilities**.

> Treat repository evidence as the source of truth. Do not assume a claim is valid simply because it appears in this report. Before making a change, verify the relevant implementation in the repository.
