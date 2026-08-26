# Recorded pytest output

Verbatim stdout from three real repositories after `bump-pydantic` ran on them
and left the suite broken. Captured 22 August 2026; the runs are reproducible
from the pinned SHAs in the fixture manifest.

`B-regex-broken.txt` was captured differently and the difference is the point.
It is fixture B **after bumpsmith fixed the `__root__` break**, which is the only
way this failure can be seen at all: while `__root__` aborts collection, the
`regex=` break underneath it is invisible. It is the first recording here of a
break that had to be uncovered rather than found. Captured 25 August 2026.

It is also ten times the size of the others, and that is not an accident either.
Fixing the first break lets 282 deprecation warnings through that collection
previously never reached. Real output gets noisier as it gets closer to working,
and the parser has to hold up in the noise, so the recording keeps it.

One substitution was applied: absolute paths from the capturing machine were
replaced with `/work/repo`, `/work/.venv` and `/opt/python`. Nothing else was
edited -- not the tracebacks, not the frame ordering, not the error text.

The frame ordering matters. `F4-broken.txt` opens with a standard-library
`importlib` frame, which is neither vendored nor project code. It is kept
because it is the case that would break a naive "first non-vendored frame"
rule, and the test suite pins that behaviour.

`field-regex-broken.txt` is the odd one out and is labelled as such. It is not a
capture from a fixture but a four-line package written to produce one signature:
`Field(regex=...)`, which raises `PydanticUserError` carrying the
`removed-kwargs` slug. Its sibling `B-regex-broken.txt` is the same break class
arriving with **no slug at all**, because `constr(regex=...)` is rejected by
Python while binding the arguments, before pydantic can attach one. Keeping both
is the point: one class, two signatures, and only one of them can be classified
the reliable way. Real pytest output against pydantic 2.12.5, captured 25 August
2026.

---

# Recorded harness events

`approval-call-tool.json` is not pytest output. It is the event stream of one
real TrueForge turn, captured 25 August 2026 from the standalone harness at
v0.1.4 running `bedrock-mantle/qwen-3-coder-480b`, and it is here because the
schema and the harness disagree about something that matters.

The agent was asked to open a pull request. The tool it wanted lives on an MCP
server and was annotated `destructiveHint: true`, so the harness's **default**
approval policy paused it -- no configuration was added to make that happen. The
recording holds ten events: a first attempt to call a tool that was not in
context, the deferred-discovery round trip that finds it, the call that was
actually paused, the `tool.approval_required` that paused it, and the
`tool.response` carrying the refusal that `bumpsmith.harness` sent back.

Two things in it are worth the file's size.

The paused call is `call_tool`, a `truefoundry-system` tool, and its `tool_info`
says exactly that. The tool that would have run -- `open_pull_request` on
`irreversible-things` -- appears only inside the *arguments*. A client that
describes the call from `tool_info` names the wrong tool, and names it
identically for every deferred call on the machine. `tests/test_harness.py` pins
both halves: what the event says, and what the module reports after unwrapping it.

The first attempt carries `"server_id": "unknown", "server_name": "unknown"` --
what the harness fills in when it cannot resolve a server. It is a real example
of an attribution that is present, well-formed, and worth nothing.

Nothing in the file was edited. It contains no credentials; the repository and
branch names in it are this project's own and are public.

# Recorded sandbox runs

`sandbox-exec-regex.json` — one `exec` tool result, verbatim from a TrueForge
0.1.4 session with the Daytona sandbox provider (26 Aug 2026). The command built
a project with the class-3 break and ran pytest against it in the sandbox; the
result came back `{"success": true, "response": {"exitCode": 2, "result": …}}`.

It is here because `bumpsmith.run` is a module about reading one wire format
correctly, and a hand-written example of that format only proves the module
agrees with its author. The `exitCode: 2` is pytest's collection-error layout,
so the same file exercises the join to `bumpsmith.failures` as well.
