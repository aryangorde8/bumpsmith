"""Render a migration run as a page a person can read.

The terminal report says what happened. This says it to somebody who was not
there — which is a different job, and the one that matters when the output of an
agent has to be *reviewed* before anybody agrees to it.

That is not decoration. :mod:`bumpsmith.rules` emits a **rule**, not a patch, and
the argument for that is in the numbers: one failing test names one site, and the
rule it implies usually names more. The gap between those two figures is the
thing a human wants before agreeing to anything, and a gap is much easier to see
than to read.

One payload, two renderings
---------------------------
This takes the same mapping :option:`--json` writes, and nothing else. Not the
:class:`~bumpsmith.migrate.Migration` object — the payload built from it. If the
page were rendered from the object directly, the page and the JSON would be two
descriptions of one run maintained in two places, and this project has a log full
of what happens next. Anything the page can show is therefore something the JSON
already contains, by construction rather than by discipline.

Everything here is somebody else's text
---------------------------------------
Repository paths, pytest's output, exception messages, file names, the rule's own
summary: all of it originates in a repository this process did not write, and all
of it lands in a document somebody opens in a browser. So every value is escaped
on the way in, and values are only ever placed in text nodes -- never in an
attribute, a ``<script>``, a ``<style>``, or a URL. A migration report that
executed a repository's error message would be a remarkable way to lose.

The page needs no network, no fonts and no scripts: it is one file that opens
from ``file://``, which is the only form that can be attached to a review, mailed
to somebody, or committed as evidence.
"""

import html
from collections.abc import Mapping
from typing import Any

_STYLE = """
:root {
  --bg: #fbfbfa; --panel: #ffffff; --line: #e4e2dd; --ink: #1a1917;
  --muted: #6b6862; --accent: #2f5d50; --warn: #8a5a1e; --stop: #8f3a34;
  --code-bg: #f4f3f0;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #17181a; --panel: #1e2022; --line: #2f3235; --ink: #e8e6e3;
    --muted: #9a978f; --accent: #7fb3a0; --warn: #d3a259; --stop: #d98a83;
    --code-bg: #26282b;
  }
}
:root[data-theme="dark"] {
  --bg: #17181a; --panel: #1e2022; --line: #2f3235; --ink: #e8e6e3;
  --muted: #9a978f; --accent: #7fb3a0; --warn: #d3a259; --stop: #d98a83;
  --code-bg: #26282b;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2.5rem 1.25rem 4rem; background: var(--bg); color: var(--ink);
  font: 16px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.wrap { max-width: 52rem; margin: 0 auto; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.9em; }
h1 { font-size: 1.5rem; margin: 0 0 0.25rem; letter-spacing: -0.01em; }
h2 { font-size: 1rem; margin: 2.5rem 0 0.75rem; text-transform: uppercase;
     letter-spacing: 0.08em; color: var(--muted); font-weight: 600; }
.sub { color: var(--muted); margin: 0 0 1.5rem; }
.sub code { background: var(--code-bg); padding: 0.1em 0.35em; border-radius: 3px; }
.badge { display: inline-block; padding: 0.2em 0.7em; border-radius: 999px;
         font-size: 0.8rem; font-weight: 600; letter-spacing: 0.02em; }
.badge.ok { background: var(--accent); color: var(--bg); }
.badge.warn { background: var(--warn); color: var(--bg); }
.badge.stop { background: var(--stop); color: var(--bg); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
         gap: 0.75rem; margin: 1.5rem 0; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
        padding: 0.9rem 1rem; }
.tile .n { font-size: 1.75rem; font-weight: 650; line-height: 1.1; letter-spacing: -0.02em; }
.tile .k { color: var(--muted); font-size: 0.8rem; margin-top: 0.15rem; }
.step { background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
        padding: 1.1rem 1.25rem; margin-bottom: 0.75rem; }
.step-head { display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap;
             margin-bottom: 0.6rem; }
.step-n { font-weight: 650; }
.klass { font-family: ui-monospace, monospace; font-size: 0.78rem; font-weight: 600;
         padding: 0.15em 0.5em; border-radius: 4px; background: var(--code-bg); color: var(--accent); }
.rc { color: var(--muted); font-size: 0.85rem; }
.msg { background: var(--code-bg); border-radius: 5px; padding: 0.6rem 0.8rem;
       margin: 0 0 0.7rem; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.3rem 1rem; margin: 0; }
dt { color: var(--muted); font-size: 0.85rem; }
dd { margin: 0; }
.gap { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.8rem;
       flex-wrap: wrap; font-size: 0.9rem; }
.bar { flex: 1 1 8rem; height: 6px; background: var(--code-bg); border-radius: 3px;
       overflow: hidden; min-width: 5rem; }
.bar span { display: block; height: 100%; background: var(--accent); }
.end { border-left: 3px solid var(--line); padding: 0.2rem 0 0.2rem 1rem; margin: 1rem 0; }
.end.reverted { border-color: var(--warn); }
.end.migrated { border-color: var(--accent); }
ul.skips { margin: 0.2rem 0 0; padding-left: 1.1rem; color: var(--muted); font-size: 0.9rem; }
p.lab { margin: 0.7rem 0 0; color: var(--muted); font-size: 0.78rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.06em; }
p.lab.bad { color: var(--stop); }
footer { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--line);
         color: var(--muted); font-size: 0.85rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.scroll { overflow-x: auto; }
"""

_OUTCOME_BADGE = {
    "migrated": ("ok", "migrated"),
    "already-green": ("ok", "already green"),
    "reverted": ("warn", "reverted"),
    "untouched": ("stop", "untouched"),
}

_OUTCOME_SENTENCE = {
    "migrated": "The suite came back green and the edits were kept.",
    "already-green": "The suite passed before anything was changed. Nothing was edited.",
    "reverted": "The edits did not make the suite pass, so every one of them was taken back.",
    "untouched": "The suite was red and nothing was ever applied.",
}


def _e(value: object) -> str:
    """Escape anything on its way into the page.

    Deliberately takes ``object``. Every caller is handing over text that came
    from a repository nobody here wrote, and a helper that only accepted ``str``
    would invite an ``f"{...}"` at the call site to satisfy it -- which is the
    one place the escaping would then not happen.
    """
    return html.escape(str(value), quote=True)


def _int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _steps(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = payload.get("steps")
    if not isinstance(raw, list):
        return []
    return [step for step in raw if isinstance(step, Mapping)]


def _count(number: int, noun: str) -> str:
    """``1 site``, ``3 sites``. The page is read by people."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _unreadable(raw: object) -> list[tuple[str, str]]:
    """``unreadable`` as ``(path, reason)`` pairs, whatever shape it arrives in.

    :class:`~bumpsmith.rules.Unreadable` has always carried both, but the
    payload used to serialise the path alone, so a report written by an older
    build has a list of strings here. Both are read, because failing on the old
    shape would mean the page cannot open the evidence it was pointed at -- and
    nothing in this module may raise on a malformed report.
    """
    if not isinstance(raw, list):
        return []
    pairs: list[tuple[str, str]] = []
    for entry in raw:
        if isinstance(entry, Mapping):
            path = entry.get("path")
            reason = entry.get("reason")
            pairs.append(("" if path is None else str(path), "" if reason is None else str(reason)))
        else:
            pairs.append((str(entry), ""))
    return [pair for pair in pairs if pair[0] or pair[1]]


def _listing(items: list[str], label: str, bad: bool = False) -> str:
    if not items:
        return ""
    body = "".join(f"<li>{item}</li>" for item in items)
    return f'<p class="lab{" bad" if bad else ""}">{_e(label)}</p><ul class="skips">{body}</ul>'


def _tile(number: object, label: str) -> str:
    return (
        f'<div class="tile"><div class="n">{_e(number)}</div><div class="k">{_e(label)}</div></div>'
    )


def _gap_bar(reported: int, found: int) -> str:
    """One site named by pytest against every site the rule matched.

    The whole argument for emitting a rule rather than a patch is that these two
    numbers differ. Drawn rather than stated because a reader takes a ratio off a
    bar without doing arithmetic, and the point is the ratio.
    """
    if found <= reported:
        # Nothing to show. The bar exists to make a ratio visible, and a rule
        # that matched exactly what pytest named has no ratio -- drawing one
        # anyway would dress up the least interesting case as the point.
        return ""
    share = max(2, round(100 * reported / found)) if found else 100
    return (
        '<div class="gap">'
        f"<span>pytest named <strong>{_e(reported)}</strong></span>"
        f'<span class="bar"><span style="width:{share}%"></span></span>'
        f"<span>the rule found <strong>{_e(found)}</strong></span>"
        "</div>"
    )


def _changes_label(applied: int, *, kept: bool) -> str:
    """What the fourth tile is counting.

    Branching on ``kept`` alone read "0 changes taken back" for every
    ``already-green`` and ``untouched`` run (finding 74) -- true only in the
    sense that nothing is also nothing, and false in the sense a skimmer takes
    it: that there was something to take back. ``applied`` is the quantity on
    the tile, so it is what decides the noun; a run with no applications has
    neither kept nor reverted anything.
    """
    if applied == 0:
        return "changes applied"
    return "changes kept" if kept else "changes taken back"


def _step_block(step: Mapping[str, Any]) -> str:
    number = _int(step, "step")
    returncode = _int(step, "returncode")
    where = _str(step, "where")
    klass = _str(step, "break_class")
    message = _str(step, "message")
    culprit = _str(step, "culprit")
    rule = _str(step, "rule")
    sites = _int(step, "sites")
    # From the scan, both of them. Joining `sites` to the plan's file count was
    # finding 72: a file whose every match is skipped produces no edit, so a
    # sentence offered as the rule's reach quietly dropped it.
    match_files = _int(step, "match_files")
    rewritten = _int(step, "rewritten")
    applied = step.get("applied") is True

    head = [f'<span class="step-n">Step {_e(number)}</span>']
    if klass:
        head.append(f'<span class="klass">{_e(klass)}</span>')
    head.append(f'<span class="rc">rc={_e(returncode)}{f" · {_e(where)}" if where else ""}</span>')

    rows = []
    if culprit:
        rows.append(f"<dt>pytest blamed</dt><dd><code>{_e(culprit)}</code></dd>")
    if rule:
        rows.append(f"<dt>rule written</dt><dd>{_e(rule)}</dd>")
    if sites:
        where_text = _count(sites, "site")
        if match_files:
            where_text += f" across {_count(match_files, 'file')}"
        rows.append(f"<dt>rule matched</dt><dd>{_e(where_text)}</dd>")
    if rewritten:
        # `applied` is whether these edits reached the disk. Whether they were
        # *kept* is a property of the whole run, not of this step, and it is
        # stated once at the end rather than guessed at four times here.
        reached = "written to disk" if applied else "planned but never written"
        rows.append(f"<dt>edits</dt><dd>{_e(rewritten)} {_e(reached)}</dd>")

    skipped = step.get("skipped")
    skips = _listing(
        [_e(item) for item in skipped] if isinstance(skipped, list) else [],
        "matched, left alone",
    )
    # The one a reviewer most needs and the one the page used to omit entirely:
    # an unreadable file is why a migration says NOT COMPLETE, and "some file
    # somewhere could not be read" is not evidence anybody can act on.
    unread = _listing(
        [
            f"<code>{_e(path)}</code>{f' — {_e(reason)}' if reason else ''}"
            for path, reason in _unreadable(step.get("unreadable"))
        ],
        "could not be read",
        bad=True,
    )

    parts = [f'<div class="step"><div class="step-head">{"".join(head)}</div>']
    if message:
        parts.append(f'<p class="msg mono">{_e(message)}</p>')
    if rows:
        parts.append(f"<dl>{''.join(rows)}</dl>")
    if sites:
        parts.append(_gap_bar(1, sites))
    parts.append(skips)
    parts.append(unread)
    parts.append("</div>")
    return "".join(parts)


def page(payload: Mapping[str, Any], *, title: str = "bumpsmith run") -> str:
    """Render the payload :option:`--json` writes as one self-contained page.

    Args:
        payload: the mapping :option:`--json` serialises -- a run's
            :meth:`~bumpsmith.migrate.Migration.as_dict` plus the repository
            and the suite command. Nothing else is read.
        title: the document title, for a reader with several of these open.

    Returns:
        A complete HTML document. No network, no scripts, no external assets.
    """
    repository = _str(payload, "repository")
    command = payload.get("command")
    command_text = " ".join(str(part) for part in command) if isinstance(command, list) else ""
    outcome = _str(payload, "outcome")
    stop = _str(payload, "stop")
    reason = _str(payload, "reason")
    applied = _int(payload, "applied")
    complete = payload.get("complete") is True
    steps = _steps(payload)

    css_class, label = _OUTCOME_BADGE.get(outcome, ("stop", outcome or "unknown"))
    # Only steps whose edits reached the disk. `rewritten` is what the plan
    # intended, and `apply.attempt` can refuse a plan outright -- so summing it
    # unconditionally made a NOT_APPLIED run announce sites rewritten directly
    # above a step correctly reading "planned but never written" (finding 73).
    # This is the second time this file has inverted `applied`; the tile and the
    # step now read it from the same place.
    sites = sum(_int(step, "rewritten") for step in steps if step.get("applied") is True)
    classes = [_str(step, "break_class") for step in steps]
    named = [item for item in classes if item and item != "UNKNOWN"]

    tiles = [
        _tile(len(steps), "suite runs"),
        _tile(len(named), "breaks classified"),
        _tile(sites, "sites rewritten"),
        _tile(applied, _changes_label(applied, kept=payload.get("kept") is True)),
    ]

    ending = [
        f'<div class="end {_e(outcome)}">',
        f"<p><strong>{_e(_OUTCOME_SENTENCE.get(outcome, 'The run ended.'))}</strong></p>",
    ]
    if stop:
        ending.append(f"<p>It stopped at <code>{_e(stop)}</code>")
        if reason:
            # A dash, not a full stop. Every `Stop` reason is written as a
            # lowercase clause meant to follow something -- the terminal report
            # gives each one its own indented line, which works. Ending the
            # sentence first and then starting a new one in lower case does not,
            # and it was visible the moment a real run was rendered and read.
            ending.append(f" &mdash; {_e(reason)}")
            ending.append("" if reason.rstrip()[-1:] in ".!?" else ".")
        else:
            ending.append(".")
        ending.append("</p>")
    if not complete:
        ending.append(
            "<p>This migration is <strong>not complete</strong>: at least one site was "
            "skipped or could not be read, and is listed with its reason above.</p>"
        )
    ending.append("</div>")

    body = [
        '<div class="wrap">',
        f"<h1>{_e(title)}</h1>",
        f'<p class="sub"><code>{_e(repository)}</code>',
        f"<br>suite: <code>{_e(command_text)}</code></p>" if command_text else "</p>",
        f'<p><span class="badge {css_class}">{_e(label)}</span></p>',
        f'<div class="tiles">{"".join(tiles)}</div>',
        "<h2>The chain, one break at a time</h2>",
        "".join(_step_block(step) for step in steps) or "<p>No runs were recorded.</p>",
        "<h2>How it ended</h2>",
        "".join(ending),
        "<footer>Generated by bumpsmith from the same report <code>--json</code> writes. "
        "Every value on this page came from the migrated repository and is shown as text, "
        "never as markup.</footer>",
        "</div>",
    ]

    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_e(title)}</title><style>{_STYLE}</style></head>"
        f"<body>{''.join(body)}</body></html>\n"
    )


__all__ = ["page"]
