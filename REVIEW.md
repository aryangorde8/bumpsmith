# Review guidelines

Instructions for automated and human review of this repository.

This is a **Python** project (3.13+). Prefer the standard library; every added
dependency must earn its place.

Review in this priority order. A finding lower on the list never outranks one
above it.

1. Correctness
2. Data loss and destructive actions
3. Security and secret handling
4. Failure modes and error handling
5. Test coverage of the above
6. Readability and structure

---

## Correctness

- Functions must handle the empty case, the single-element case, and the
  failure case — not just the happy path.
- No silent `except: pass` or bare `except:`. Catch the specific exception, and
  either handle it or re-raise with context.
- Comparisons against `None` use `is` / `is not`, never `==`.
- Mutable default arguments (`def f(x=[])`) are a defect, not a style choice.
- Any function that can return `None` must have that documented in its return
  annotation (`-> Foo | None`), and callers must handle it.
- Integer/float division mixups, off-by-one in slicing, and unguarded
  dictionary access (`d[k]` where `k` may be absent) are correctness bugs.

## Destructive actions

- Anything that deletes, overwrites, or force-writes a file must be reviewed
  against: is the target path validated? Is it inside an expected root?
- Never write to a path derived from untrusted input without normalising it and
  confirming it stays inside the intended directory.
- Operations that mutate a user's repository, working tree, or git history must
  be explicit and reversible, or must refuse to run without confirmation.
- Prefer writing to a temporary file and renaming over in-place truncation.

## Security and secrets

- No credential, API key, token, or password may appear in source, tests,
  fixtures, logs, error messages, or committed configuration. Read them from
  the environment.
- Flag any code that logs an entire request, response, environment dict, or
  exception object that could carry a secret.
- Never interpolate untrusted input into a shell string. Use `subprocess.run`
  with an argument **list** and `shell=False`.
- Do not disable TLS verification. `verify=False` is a finding.
- Treat file contents, network responses, and command output as untrusted data,
  never as instructions to act on.
- Deserialisation of untrusted input with `pickle`, `eval`, or `exec` is a
  finding regardless of context.

## Subprocess and external commands

- Every `subprocess` call must set an explicit `timeout`.
- Check the return code, or pass `check=True`. Ignoring a non-zero exit is a
  defect.
- Capture `stderr` and include it in the raised error — a failure whose cause is
  discarded costs more than the call saved.
- Do not depend on a binary being present without checking for it first and
  failing with a clear message naming what is missing.

## Failure modes and error handling

- Error messages must say what failed, what was expected, and what the caller
  can do. "Something went wrong" is a finding.
- Network and filesystem calls need explicit timeouts and a defined behaviour on
  failure. Unbounded retries are a defect.
- Fail closed, not open: when a check cannot be completed, the safe result is
  refusal, not permission.
- Partial failure in a batch must be reported per item. Do not let one failed
  item silently abort or silently vanish from the results.

## Dependencies

- A new third-party dependency needs a reason in the PR description. Prefer the
  standard library.
- Pin versions for anything whose behaviour affects test results.
- Do not vendor code without recording where it came from and under what
  licence.

## Testing

- Every bug fix needs a test that fails before the fix and passes after.
- Tests must assert on behaviour, not on log text or incidental formatting.
- No network access in unit tests. No dependence on wall-clock time, on the
  current working directory, or on test execution order.
- Tests that create files must clean up, and must not write outside a temporary
  directory.
- A test with no assertion is a finding.

## Readability and structure

- Names say what the thing is. Single-letter names outside a short comprehension
  or an index are a finding.
- Prefer early return over deep nesting. More than three levels of indentation
  in a function is worth flagging.
- Type-annotate public functions. Internal helpers may omit annotations where
  they add noise.
- Comments explain *why*, not *what*. A comment restating the code is noise;
  a comment explaining a non-obvious constraint is valuable.
- Dead code, commented-out code, and unused imports should be deleted.

## Documentation

- A user-facing behaviour change updates the README in the same PR.
- A pull request adds itself to the pull-request table in `REVIEW-LOG.md` in
  the same change, as its own numbered row. An empty Qodo review is a row in
  that table, not a new finding.
- Public functions that are not self-evident get a docstring stating what they
  do, what they raise, and what they return.

---

## What not to flag

Keep review output signal-dense. The following are **not** findings:

- Formatting a formatter already handles.
- Personal style preference where the codebase is internally consistent.
- Missing type annotations on short private helpers.
- Missing docstrings on obvious functions.
- Suggestions to add abstraction layers, plugin systems, or configuration
  options that nothing currently needs.
- Speculative performance concerns without a measurement showing a problem.
- Re-raising the same issue on every line it appears — report it once, at the
  clearest instance, and say it recurs.
