"""The page renders the run, and renders nothing it was not given.

Two things are being defended here and they pull in opposite directions.

The page has to *say* what happened, or it is decoration. And every word it says
came out of a repository nobody here wrote — pytest's output, an exception
message, a file path, a rule summary — so it also has to say all of it as text
and none of it as markup. A migration report that executed the error message of
the repository it was migrating would be a remarkable way to lose.
"""

import html
import json
import re
from typing import Any

from bumpsmith.report import page

_STEP: dict[str, Any] = {
    "step": 1,
    "returncode": 2,
    "where": "local",
    "break_class": "ROOT_MODEL",
    "message": "To define root models, use `pydantic.RootModel`",
    "culprit": "emnify/modules/api/models.py:397",
    "rule": "Replace a `__root__` field with pydantic.RootModel",
    "sites": 19,
    "scan_complete": True,
    "unreadable": [],
    "rewritten": 19,
    "files": 2,
    "skipped": [],
    "applied": True,
}

_RUN: dict[str, Any] = {
    "repository": "/repos/emnify",
    "command": ["python", "-m", "pytest", "-q"],
    "outcome": "reverted",
    "stop": "no-rule",
    "reason": "the failure classified as UNKNOWN",
    "applied": 1,
    "kept": False,
    "complete": True,
    "steps": [_STEP],
}


def _run(**changes: Any) -> dict[str, Any]:
    return {**_RUN, **changes}


# --------------------------------------------------------------------------
# It says what happened
# --------------------------------------------------------------------------


def test_the_page_is_a_complete_document() -> None:
    out = page(_RUN)
    assert out.startswith("<!doctype html>")
    assert out.rstrip().endswith("</html>")


def test_the_page_needs_nothing_from_the_network() -> None:
    """It has to open from `file://`, or it cannot be attached to a review.

    No scripts either. A report that runs code is a report somebody has to trust
    before reading, which defeats the point of writing one.
    """
    out = page(_RUN)
    for forbidden in ("http://", "https://", "<script", "<iframe", "src=", "@import"):
        assert forbidden not in out, f"the page reaches for {forbidden!r}"


def test_the_run_is_actually_described() -> None:
    out = page(_RUN)
    for expected in (
        "/repos/emnify",
        "ROOT_MODEL",
        "emnify/modules/api/models.py:397",
        "no-rule",
        "the failure classified as UNKNOWN",
    ):
        assert expected in out, f"the page does not mention {expected!r}"


def test_the_gap_between_one_site_and_every_site_is_shown() -> None:
    """The reason this project emits a rule rather than a patch is this number."""
    out = page(_RUN)
    assert "the rule found <strong>19</strong>" in out
    assert "pytest named <strong>1</strong>" in out


def test_no_gap_is_drawn_when_there_is_no_gap() -> None:
    """A rule matching exactly what pytest named has no ratio to show.

    Drawing a full bar there would dress up the least interesting case as the
    point of the page.
    """
    out = page(_run(steps=[{**_STEP, "sites": 1, "rewritten": 1, "files": 1}]))
    assert "the rule found" not in out


def test_a_reverted_run_does_not_read_as_a_successful_one() -> None:
    """The tiles are what a skimmer reads, so they cannot imply the opposite."""
    out = page(_RUN)
    assert "changes taken back" in out
    assert "changes kept" not in out
    assert "every one of them was taken back" in out


def test_a_kept_run_says_so() -> None:
    out = page(_run(outcome="migrated", kept=True, stop="green", reason=""))
    assert "changes kept" in out
    assert "came back green and the edits were kept" in out


def test_edits_that_never_reached_disk_are_not_described_as_written() -> None:
    """`applied` is whether the disk was touched, and the page must not invert it."""
    out = page(_run(steps=[{**_STEP, "applied": False}]))
    assert "planned but never written" in out
    assert "written to disk" not in out


def test_a_step_reports_only_as_far_as_it_got() -> None:
    """A step that read a failure and wrote no rule must not invent the rest."""
    bare = {"step": 4, "returncode": 1, "where": "local", "break_class": "UNKNOWN"}
    out = page(_run(steps=[bare]))
    assert "UNKNOWN" in out
    assert "rule written" not in out
    assert "rule matched" not in out


def test_an_incomplete_migration_says_it_is_incomplete() -> None:
    out = page(_run(complete=False))
    assert "not complete" in out


def test_skipped_sites_are_listed_with_their_reasons() -> None:
    reason = "check reads `field`, so removing it would change what runs"
    out = page(_run(steps=[{**_STEP, "skipped": [reason]}]))
    assert html.escape(reason) in out


def test_an_empty_run_renders_rather_than_raising() -> None:
    """The empty case is a real case: `--steps 0` produces one."""
    out = page({"repository": "/repos/x", "outcome": "untouched", "steps": []})
    assert "No runs were recorded." in out


def test_a_payload_missing_everything_still_renders() -> None:
    """Nothing here may raise on a malformed report.

    The page is the last thing to run, after a migration that may already have
    gone wrong. Failing here would replace a partial answer with no answer.
    """
    assert page({}).startswith("<!doctype html>")


def test_wrong_types_are_ignored_rather_than_rendered() -> None:
    """A number where a string belongs is a bug upstream, not a reason to crash."""
    out = page({"repository": 42, "outcome": ["reverted"], "steps": "not a list"})
    assert out.startswith("<!doctype html>")
    assert "No runs were recorded." in out


# --------------------------------------------------------------------------
# It renders nothing it was not given
# --------------------------------------------------------------------------

_ATTACKS = (
    "<script>alert(1)</script>",
    '"><script>alert(1)</script>',
    "</style><script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "</div></body></html><h1>owned",
    "' onmouseover='alert(1)",
)


def _assert_inert(out: str, attack: str, escaped: str, where: str) -> None:
    """The value reached the page as text and not as markup.

    Stated as "the raw value never appears" rather than as a list of banned
    substrings. The first version of this banned `onerror=`, which fails on
    `&lt;img src=x onerror=alert(1)&gt;` -- a string that is completely inert,
    because the delimiters around it are escaped. Banning the fragments of an
    attack tests the attacks somebody thought of; requiring that nothing hostile
    survives unescaped tests the property.

    A value with no HTML-special characters escapes to itself, and that is fine:
    `javascript:alert(1)` in a text node is six words, because nothing here ever
    puts a payload value in an attribute or a URL.
    """
    if escaped != attack:
        assert attack not in out, f"{where} rendered {attack!r} unescaped"


def test_no_field_of_the_report_can_inject_markup() -> None:
    """Every string on the page came from somebody else's repository.

    Swept over every field rather than spot-checked, because the field that gets
    missed is the one nobody thought of. A repository can choose its own paths,
    its own module names and — through the exception it raises — most of the
    text pytest prints.
    """
    fields = ("repository", "outcome", "stop", "reason")
    step_fields = ("where", "break_class", "message", "culprit", "rule")

    for attack in _ATTACKS:
        escaped = html.escape(attack, quote=True)
        for field in fields:
            out = page(_run(**{field: attack}))
            _assert_inert(out, attack, escaped, f"{field}")
            assert escaped in out, f"{field} did not render at all"

        for field in step_fields:
            out = page(_run(steps=[{**_STEP, field: attack}]))
            _assert_inert(out, attack, escaped, f"step.{field}")

        out = page(_run(steps=[{**_STEP, "skipped": [attack]}]))
        _assert_inert(out, attack, escaped, "a skipped reason")


def test_the_document_has_no_stray_tags_after_a_hostile_value() -> None:
    """Closing the document early is the attack that escaping alone can hide.

    A value that closes `</body></html>` and starts fresh content would leave a
    page that looks intact and is not, so the shape is asserted rather than the
    absence of one substring.
    """
    out = page(_run(repository="</div></body></html><h1>owned</h1>"))
    assert out.count("</html>") == 1
    assert out.count("<body>") == 1
    assert "<h1>owned</h1>" not in out


def test_the_title_is_escaped_too() -> None:
    """The title is the one value that does not come from the payload, and the
    caller supplying it is `__main__`, using the repository's own directory name."""
    out = page(_RUN, title="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def test_a_hostile_value_cannot_escape_the_stylesheet() -> None:
    """No payload value is placed in a style context, so the sheet stays closed."""
    out = page(_run(outcome="</style><script>alert(1)</script>"))
    assert out.count("<style>") == 1
    assert out.count("</style>") == 1


# --------------------------------------------------------------------------
# One payload, two renderings
# --------------------------------------------------------------------------


def test_the_page_shows_only_what_the_json_already_carries() -> None:
    """The page and `--json` are two readings of one run, not two records of it.

    Every number the page prints is checked back against the payload that
    produced it, so a figure invented in the renderer -- the easiest way for the
    two to start disagreeing -- fails here.
    """
    out = page(_RUN)
    payload = json.loads(json.dumps(_RUN))  # the round trip `--json` performs

    tiles = re.findall(r'<div class="n">(\d+)</div><div class="k">([^<]+)</div>', out)
    figures = {label: int(number) for number, label in tiles}

    assert figures["suite runs"] == len(payload["steps"])
    assert figures["sites rewritten"] == sum(step["rewritten"] for step in payload["steps"])
    assert figures["changes taken back"] == payload["applied"]
    assert figures["breaks classified"] == len(
        [s for s in payload["steps"] if s["break_class"] != "UNKNOWN"]
    )
