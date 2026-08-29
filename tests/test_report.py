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
from html.parser import HTMLParser
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
    "match_files": 2,
    "scan_complete": True,
    "unreadable": [],
    "rewritten": 19,
    "edit_files": 2,
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
    out = page(_run(steps=[{**_STEP, "sites": 1, "rewritten": 1, "match_files": 1}]))
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


def test_a_run_that_applied_nothing_does_not_claim_a_reversion() -> None:
    """`already-green` and `untouched` had nothing to take back.

    "0 changes taken back" is true only in the sense that nothing is also
    nothing. A skimmer reads the noun, and the noun asserted there had been
    something to revert.
    """
    for outcome in ("already-green", "untouched"):
        out = page(_run(outcome=outcome, applied=0, kept=False, steps=[]))
        assert "changes taken back" not in out, f"{outcome} implies a reversion"
        assert "changes kept" not in out, f"{outcome} implies edits survived"
        assert "changes applied" in out


def test_sites_never_written_are_not_counted_as_rewritten() -> None:
    """The tile and the step below it must not contradict each other.

    A refused plan leaves `applied` false, and the step already says "planned
    but never written". Summing `rewritten` regardless put "19 sites rewritten"
    directly above it -- the same inversion of `applied` this file shipped once
    already, in the other direction.
    """
    out = page(_run(applied=0, steps=[{**_STEP, "applied": False}]))
    assert '<div class="n">0</div><div class="k">sites rewritten</div>' in out
    assert "planned but never written" in out


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


def test_the_stop_reason_reads_as_one_sentence() -> None:
    """Every `Stop` reason is a lowercase clause, so it cannot follow a full stop.

    Found by rendering a real run and reading it: "It stopped at `no-rule`. the
    failure classified as UNKNOWN" is the sentence a stranger arrives at, on
    the page whose entire job is to read well to a stranger.
    """
    out = page(_RUN)
    assert "</code>. the failure" not in out
    assert "&mdash; the failure classified as UNKNOWN" in out
    assert "classified as UNKNOWN.</p>" in out, "the sentence does not end"


def test_a_reason_that_already_ends_in_punctuation_gets_no_second_full_stop() -> None:
    """`the suite could not be run: {exc}` can arrive already terminated."""
    out = page(_run(reason="the suite could not be run: no such file."))
    assert "no such file." in out
    assert "no such file.." not in out


def test_an_incomplete_migration_says_it_is_incomplete() -> None:
    out = page(_run(complete=False))
    assert "not complete" in out


def test_the_file_that_made_a_migration_incomplete_is_named_with_its_reason() -> None:
    """The page promises this evidence in the ending, so it has to be on the page.

    An unreadable file is the most common reason a run reports NOT COMPLETE,
    and it is the one thing a reviewer has to act on: some v1 code the rule
    named is still there, in a file nothing could parse. Saying so without
    naming the file leaves the reader worse off than the terminal report, which
    has always printed both.
    """
    out = page(
        _run(
            complete=False,
            steps=[
                {
                    **_STEP,
                    "scan_complete": False,
                    "unreadable": [
                        {"path": "emnify/vendor/legacy.py", "reason": "invalid syntax (line 4)"}
                    ],
                }
            ],
        )
    )
    assert "emnify/vendor/legacy.py" in out
    assert "invalid syntax (line 4)" in out


def test_an_older_payload_listing_unreadable_paths_alone_still_renders() -> None:
    """`unreadable` used to be a list of strings, and old reports are still reports.

    Raising on the old shape would mean the page cannot open the very evidence
    it was pointed at, which is a worse failure than rendering it without the
    reason it never carried.
    """
    out = page(_run(steps=[{**_STEP, "unreadable": ["emnify/vendor/legacy.py"]}]))
    assert out.startswith("<!doctype html>")
    assert "emnify/vendor/legacy.py" in out


def test_a_hostile_unreadable_entry_is_escaped_in_both_halves() -> None:
    """Both the path and the reason came out of the migrated repository."""
    attack = "<script>alert(1)</script>"
    out = page(_run(steps=[{**_STEP, "unreadable": [{"path": attack, "reason": attack}]}]))
    assert attack not in out
    assert html.escape(attack) in out


def test_the_matched_file_count_comes_from_the_scan_not_the_plan() -> None:
    """ "Rule matched N sites across M files" must describe one thing, not two.

    A file whose every match is skipped produces no edit, so the plan's file
    count is smaller than the rule's reach. Joining the scan's site count to
    the plan's file count produced a sentence describing neither -- and it
    understated exactly the case a reviewer is being warned about.
    """
    out = page(_run(steps=[{**_STEP, "sites": 19, "match_files": 3, "edit_files": 2}]))
    assert "19 sites across 3 files" in out
    assert "19 sites across 2 files" not in out


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

    That last clause was false when it was written. The outcome was interpolated
    into `class="end {outcome}"` -- escaped, so this sweep still passed, but for
    a reason the docstring did not give (finding 183). `report.page` now takes
    that class from a closed map, and the test below asserts the clause rather
    than leaving it as something a reader has to take on faith.
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


class _AttributeValues(HTMLParser):
    """Every attribute value the document actually has, as a parser resolves it.

    `convert_charrefs=True` matters: it undoes the escaping on the way out, so a
    value that reached an attribute *escaped* is still caught. Asserting on the
    raw source instead would pass on exactly the case worth failing on.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.values.extend(value for _, value in attrs if value is not None)


def test_no_payload_value_reaches_an_attribute() -> None:
    """The module's docstring says it; this is the part that checks it.

    Swept over the same fields as the markup test, because the guarantee is the
    same guarantee: what a repository wrote goes into a text node or it does not
    go into the page. An attribute is the one place where escaping is the only
    thing standing between inert and executed, so the rule here is that nothing
    from the payload gets that far in the first place.
    """
    fields = ("repository", "outcome", "stop", "reason")
    step_fields = ("where", "break_class", "message", "culprit", "rule")

    for attack in _ATTACKS:
        for field in fields:
            parser = _AttributeValues()
            parser.feed(page(_run(**{field: attack})))
            for value in parser.values:
                assert attack not in value, f"{field} reached the attribute {value!r}"

        for field in step_fields:
            parser = _AttributeValues()
            parser.feed(page(_run(steps=[{**_STEP, field: attack}])))
            for value in parser.values:
                assert attack not in value, f"step.{field} reached the attribute {value!r}"


def test_an_outcome_the_page_does_not_know_styles_as_nothing() -> None:
    """The closed map is the whole mechanism, so the fallback is worth pinning.

    An outcome nobody defined has no CSS rule either way -- only `migrated` and
    `reverted` are styled -- so dropping it costs the page nothing and buys the
    docstring back.
    """
    assert '<div class="end migrated">' in page(_run(outcome="migrated"))
    assert '<div class="end">' in page(_run(outcome="not-an-outcome"))


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
    assert figures["sites rewritten"] == sum(
        step["rewritten"] for step in payload["steps"] if step["applied"] is True
    )
    assert figures["changes taken back"] == payload["applied"]
    assert figures["breaks classified"] == len(
        [s for s in payload["steps"] if s["break_class"] != "UNKNOWN"]
    )
