"""The site publishes recorded runs, and publishes nothing else.

A gallery of a tool's own output is the easiest artefact in this repository to
quietly falsify. Nobody re-runs it, the numbers look authoritative rendered, and
a payload edited by hand to say something better reads exactly like one that was
not. So the manifest writes down what each run is *supposed* to demonstrate, and
this module checks that claim against the payload the site actually renders. A
regenerated run that no longer shows what its blurb says it shows fails here
rather than going up as a nicer story than the truth.

The other half is the same argument :mod:`tests.test_report` makes, one level
out. `runs.toml` is prose written by hand and the payloads are strings from
repositories nobody here wrote, and all of it lands in a document a stranger
opens. None of it may arrive as markup.
"""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
from build_site import build, escape, index, inline, load_manifest, load_payload, ordered_runs

PAGES = Path(__file__).resolve().parent.parent / "pages"
MANIFEST = PAGES / "runs.toml"

_RUNS = ordered_runs(load_manifest(MANIFEST))


def _ids() -> list[str]:
    return [slug for slug, _ in _RUNS]


# --------------------------------------------------------------------------
# The manifest describes the runs it actually has
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("slug", "entry"), _RUNS, ids=_ids())
def test_each_run_demonstrates_what_the_manifest_claims(slug: str, entry: dict[str, Any]) -> None:
    """`expected` is the blurb's claim, in a form a test can check.

    The prose beside each run says it reverted, or declined to edit, or was
    kept. That prose is not checkable, so the manifest restates the checkable
    part as key/value pairs and this asserts them against the payload. Rewriting
    the blurb to say something the run did not do now requires editing
    `expected` to match, which is the point at which somebody notices.
    """
    payload = load_payload(entry, PAGES)
    expected = entry.get("expected", {})
    assert expected, f"{slug} claims nothing"
    for key, value in expected.items():
        assert payload.get(key) == value, f"{slug}: payload {key}={payload.get(key)!r}"


@pytest.mark.parametrize(("slug", "entry"), _RUNS, ids=_ids())
def test_no_run_carries_a_path_from_the_machine_that_captured_it(
    slug: str, entry: dict[str, Any]
) -> None:
    """The payloads are published, so nobody's home directory may be in them.

    `runs.toml` records one mechanical substitution per run. This is the check
    that it was actually applied -- to the whole payload, not just to the
    `repository` field that happens to be the visible one.
    """
    raw = json.dumps(load_payload(entry, PAGES))
    assert "/home/" not in raw, f"{slug} still names a home directory"
    assert "/Users/" not in raw, f"{slug} still names a home directory"


def test_the_manifest_records_a_commit_and_a_date() -> None:
    """A run with no provenance is a screenshot: it proves nothing about when."""
    manifest = load_manifest(MANIFEST)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(manifest.get("captured", "")))
    assert re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("bumpsmith", "")))


# --------------------------------------------------------------------------
# Nothing arrives as markup
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hostile",
    [
        "<script>alert(1)</script>",
        '"><img src=x onerror=alert(1)>',
        "`<script>alert(1)</script>`",
        "**<b>bold</b>**",
        "`unbalanced",
        "**unbalanced",
        "`<a href='x'>` and **<i>y</i>**",
    ],
)
def test_inline_markup_cannot_be_smuggled_through_the_manifest(hostile: str) -> None:
    """`inline` escapes first and marks up second, and this is why that matters.

    Every tag in the result is one this function put there. A `<` that arrived
    in the text is `&lt;` by the time either pattern runs, so no input can close
    a tag, open an attribute, or reach a URL.
    """
    rendered = inline(hostile)
    assert "<script" not in rendered
    assert "<img" not in rendered
    assert "<b>" not in rendered
    assert "<a " not in rendered
    assert "onerror" not in rendered or "&lt;" in rendered
    for tag in re.findall(r"</?([a-z]+)", rendered):
        assert tag in {"code", "strong"}, f"{tag} is not a tag this function emits"


def test_inline_still_marks_up_the_two_forms_it_promises() -> None:
    """Escaping first must not cost the formatting the manifest relies on."""
    assert inline("a `b` c") == "a <code>b</code> c"
    assert inline("a **b** c") == "a <strong>b</strong> c"
    assert inline("`a<b>c`") == "<code>a&lt;b&gt;c</code>"


def test_escape_takes_anything() -> None:
    """The manifest is hand-written, so a number where a string was meant is a
    typo rather than a crash -- and must still not become markup."""
    assert escape(12) == "12"
    assert escape(None) == "None"
    assert escape("<b>") == "&lt;b&gt;"


# --------------------------------------------------------------------------
# The built site
# --------------------------------------------------------------------------


def test_building_writes_an_index_and_one_page_for_each_run(tmp_path: Path) -> None:
    """The count is derived from the manifest, not written down twice."""
    written = build(tmp_path / "out", MANIFEST)
    names = {path.name for path in written}
    assert "index.html" in names
    for slug, _ in _RUNS:
        assert f"{slug}.html" in names, f"{slug} was not rendered"


def test_a_rebuild_removes_a_page_whose_run_is_gone(tmp_path: Path) -> None:
    """The output directory is rebuilt, not updated.

    A page left behind by a run that has since been removed from the manifest
    would stay published forever, and would keep answering requests long after
    the evidence for it was withdrawn.
    """
    out = tmp_path / "out"
    build(out, MANIFEST)
    stale = out / "a-run-that-was-removed.html"
    stale.write_text("stale", encoding="utf-8")
    build(out, MANIFEST)
    assert not stale.exists()


def test_the_built_site_needs_no_network(tmp_path: Path) -> None:
    """Self-contained is the property that makes the pages evidence.

    Anything the page fetches at view time is something that can change, or stop
    answering, after the run it describes. The only external references allowed
    are links a reader clicks.
    """
    out = tmp_path / "out"
    for path in build(out, MANIFEST):
        if path.suffix != ".html":
            continue
        text = path.read_text(encoding="utf-8")
        assert "<script" not in text, f"{path.name} carries a script"
        for match in re.findall(r'(?:src|href)="([^"]+)"', text):
            assert not match.startswith(("http://", "//")), f"{path.name} fetches {match}"
        for match in re.findall(r'src="([^"]+)"', text):
            assert not match.startswith("https://"), f"{path.name} fetches {match}"


def test_the_index_names_every_run_and_its_outcome() -> None:
    """The index is the only page a visitor is guaranteed to see."""
    manifest = load_manifest(MANIFEST)
    rendered = index(manifest, _RUNS)
    for slug, entry in _RUNS:
        assert f'href="{slug}.html"' in rendered
        assert escape(entry["title"]) in rendered
        assert escape(load_payload(entry, PAGES)["outcome"]) in rendered


def test_a_manifest_entry_with_no_payload_is_an_error() -> None:
    """Silently skipping it would publish an index that links to nothing."""
    with pytest.raises(ValueError, match="names no payload"):
        load_payload({"title": "x"}, PAGES)


def test_runs_are_ordered_by_the_manifest_not_by_chance() -> None:
    """Dictionary order would make the site's running order an accident of
    editing, and the first card is the one that gets read."""
    orders = [entry.get("order", 0) for _, entry in _RUNS]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders), "two runs claim the same position"


def test_every_payload_the_manifest_names_is_a_file_that_exists() -> None:
    """A manifest naming a payload that is not committed builds a broken site
    in CI and a working one on the machine that has the file."""
    with MANIFEST.open("rb") as handle:
        raw = tomllib.load(handle)
    for slug, entry in raw["runs"].items():
        assert (PAGES / entry["payload"]).is_file(), f"{slug} names a missing payload"
