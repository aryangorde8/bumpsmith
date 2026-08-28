"""Render the recorded runs in `runs.toml` as a static site.

This is the third rendering of one payload. :mod:`bumpsmith.report` already
turns the mapping :option:`--json` writes into a page; ``--json`` itself is the
second. This module adds an index over several of them and nothing else -- it
does not read a repository, run a suite, or compute a number that the payloads
do not already contain. If a figure appears on the site, some run produced it.

Why it lives here and not in the package
----------------------------------------
``bumpsmith`` is a command-line tool for migrating a repository. Publishing a
gallery is not part of that job, and putting it in ``src/`` would widen the
package's surface for a reason the package does not have. It is held to the same
standard anyway -- ``ruff`` covers the whole repository, ``mypy`` is configured
to include this directory, and :mod:`tests.test_pages` runs against it offline --
because the alternative is a corner of the repository where the standard quietly
stops applying.

Why it borrows the stylesheet rather than copying it
-----------------------------------------------------
:data:`bumpsmith.report.STYLE` is imported, not duplicated. Two copies of the
same CSS is two things to keep in step, and this project has a review log full of
what happens to a second copy of anything. The index adds the few rules it needs
of its own and reuses the rest, so a run page and the index that links to it
cannot drift into two different-looking sites.

The directory it writes is disposable. Nothing reads it back, so it is rebuilt
from scratch on every run rather than updated in place -- a stale file left over
from a run that has since been removed would otherwise stay published forever.
"""

import argparse
import html
import json
import re
import shutil
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bumpsmith.report import STYLE, page

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "runs.toml"

# The site is one page per run plus an index, so the extra CSS is small on
# purpose. Everything structural -- colour, type, the panel and badge classes --
# comes from the imported stylesheet.
_INDEX_STYLE = """
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
        padding: 1.15rem 1.3rem; margin-bottom: 0.85rem; }
.card h3 { margin: 0 0 0.5rem; font-size: 1.05rem; letter-spacing: -0.01em; }
.card h3 a { color: var(--ink); text-decoration: none; }
.card h3 a:hover, .card h3 a:focus { color: var(--accent); text-decoration: underline; }
.card p { margin: 0.5rem 0 0; }
.prov { margin-top: 0.8rem; font-size: 0.82rem; color: var(--muted); }
.prov code { background: var(--code-bg); padding: 0.1em 0.35em; border-radius: 3px; }
a { color: var(--accent); }
a:focus-visible, .card h3 a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
"""

_OUTCOME_CLASS = {"migrated": "ok", "reverted": "warn", "untouched": "warn"}

# A slug is a TOML table key that becomes a file name and a link, and neither of
# those tolerates the full range of a TOML key. `[runs."../x"]` is valid TOML and
# would put `x.html` a directory above the one the build was asked to write to.
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# Written into the output directory so a rebuild can tell a directory it made
# from a directory it was merely pointed at. See `build`.
_MARKER = ".bumpsmith-site"

# File names the build writes itself. A run may not claim one: `[runs.index]` is
# a perfectly good TOML key, and its page would land on `index.html` and replace
# the gallery with itself -- leaving a site whose only way in was the page that
# ate it. The marker needs no entry here: it begins with a dot, and `_SLUG`
# already refuses those, so no slug can ever name it.
_RESERVED = frozenset({"index"})


def _text(mapping: Mapping[str, Any], key: str) -> str:
    """The value at *key* as text, or empty when it is absent or not a string."""
    value = mapping.get(key)
    return value if isinstance(value, str) else ""


def escape(value: object) -> str:
    """Render *value* as text that cannot become markup.

    The payloads carry strings from somebody else's repository -- file paths,
    error messages, identifier names -- and so does the manifest. None of it is
    trusted as HTML.

    Takes ``object`` rather than ``str`` for the reason
    :func:`bumpsmith.report._e` does: a helper that only accepted ``str`` would
    invite an ``f"{...}"`` at the call site to satisfy it, and that is the one
    place the escaping would then not happen.
    """
    return html.escape(str(value), quote=True)


def inline(text: str) -> str:
    """Escape *text*, then mark up the two inline forms the manifest uses.

    ```code``` becomes ``<code>``, ``**strong**`` becomes ``<strong>``.

    The order is the whole safety argument and is not an implementation detail:
    the text is escaped *first*, so by the time either pattern is matched there
    is no ``<`` left in the string that this function did not put there. A
    version that marked up first and escaped afterwards would escape its own
    tags; a version that escaped only the parts it did not match would be one
    unbalanced backtick away from putting manifest text into markup. Neither is
    reachable from here.

    Args:
        text: prose from `runs.toml`.

    Returns:
        HTML for a text node, with no attribute and no URL anywhere in it.
    """
    escaped = escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)


def load_manifest(path: Path = MANIFEST) -> Mapping[str, Any]:
    """Read `runs.toml`.

    Args:
        path: the manifest to read.

    Returns:
        The parsed manifest, exactly as written.
    """
    with path.open("rb") as handle:
        return tomllib.load(handle)


def ordered_runs(manifest: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """The manifest's runs, in the order it gives them.

    Args:
        manifest: the parsed `runs.toml`.

    Returns:
        ``(slug, entry)`` pairs sorted by each entry's ``order``. Sorting on a
        written-down number rather than on dictionary order means reordering the
        site is an edit to the manifest, not to this file.
    """
    runs = manifest.get("runs")
    if not isinstance(runs, dict):
        return []
    entries = []
    for slug, entry in runs.items():
        if not isinstance(entry, dict):
            continue
        if not _SLUG.fullmatch(slug):
            raise ValueError(
                f"{slug!r} is not a usable run name: a slug becomes a file name and a "
                "link, so it is restricted to lowercase letters, digits and hyphens"
            )
        if slug in _RESERVED:
            raise ValueError(
                f"{slug!r} is a name the build writes itself, so a run cannot take it. "
                f"Reserved: {', '.join(sorted(_RESERVED))}"
            )
        entries.append((slug, entry))
    return sorted(entries, key=lambda pair: (pair[1].get("order", 0), pair[0]))


def load_payload(entry: Mapping[str, Any], root: Path = HERE) -> Mapping[str, Any]:
    """The recorded `--json` payload an entry names.

    Args:
        entry: one run's table from the manifest.
        root: the directory its ``payload`` path is relative to.

    Returns:
        The payload as written, with nothing added or removed.

    Raises:
        ValueError: if the entry names no payload.
        TypeError: if the file it names does not hold a JSON object.
    """
    relative = _text(entry, "payload")
    if not relative:
        raise ValueError("a run entry names no payload")
    loaded = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{relative} does not contain a JSON object")
    return loaded


def _card(slug: str, entry: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    """One run's entry on the index."""
    outcome = _text(payload, "outcome")
    badge = _OUTCOME_CLASS.get(outcome, "stop")
    upstream = _text(entry, "upstream")
    sha = _text(entry, "sha")

    provenance = [f"pydantic <code>{escape(_text(entry, 'pydantic'))}</code>"]
    if upstream.startswith("https://"):
        provenance.insert(0, f'<a href="{escape(upstream)}">{escape(upstream)}</a>')
    elif upstream:
        provenance.insert(0, escape(upstream))
    if sha:
        provenance.append(f"at <code>{escape(sha[:12])}</code>")

    return (
        '<div class="card">'
        f'<h3><a href="{escape(slug)}.html">{escape(_text(entry, "title"))}</a></h3>'
        f'<span class="badge {badge}">{escape(outcome)}</span>'
        f"<p>{inline(_text(entry, 'blurb'))}</p>"
        f'<p class="prov">{" &middot; ".join(provenance)}</p>'
        "</div>"
    )


def index(
    manifest: Mapping[str, Any],
    runs: Sequence[tuple[str, Mapping[str, Any]]],
    root: Path = HERE,
) -> str:
    """Render the page that links to every run.

    Args:
        manifest: the parsed manifest, for the provenance footer.
        runs: ``(slug, entry)`` pairs already paired with their payloads.
        root: the directory each entry's ``payload`` path is relative to. It has
            to be passed in rather than defaulted to :data:`HERE`, because the
            index reads every payload a second time to put an outcome on each
            card -- and a build driven by a manifest somewhere else would
            otherwise render pages from one directory and cards from another.

    Returns:
        A complete HTML document with no scripts and no external assets.
    """
    cards = []
    for slug, entry in runs:
        cards.append(_card(slug, entry, load_payload(entry, root)))

    captured = escape(_text(manifest, "captured"))
    commit = _text(manifest, "bumpsmith")
    provenance = f"Captured {captured}"
    if commit:
        provenance += f" against bumpsmith <code>{escape(commit[:12])}</code>"
    provenance += ". "

    body = [
        '<div class="wrap">',
        "<h1>bumpsmith</h1>",
        '<p class="sub">An agent that turns a failing pydantic v1&ndash;to&ndash;v2 '
        "migration into a reviewed pull request &mdash; and stops when it cannot.</p>",
        "<h2>What these are</h2>",
        "<p>Every page below is a real run against a real repository, rendered from the "
        "same JSON the tool writes with <code>--json</code>. Three of the four end "
        "without a migration. That is the point: a migration tool that always edits "
        "something is not reporting what it found, it is guessing.</p>",
        "<h2>The runs</h2>",
        "".join(cards),
        "<h2>Where TrueForge fits</h2>",
        "<p>The loop refuses to edit a checkout in one place and test it in another, "
        "because the suite would then answer a question about code the edits never "
        "reached. So the whole migration goes into a TrueForge sandbox together &mdash; "
        "clone, edit, run, revert &mdash; one sandbox per repository, many at once. "
        "Opening a pull request is gated on a human answering through the harness, and "
        "the destination is never inferred from the clone's own <code>origin</code>.</p>",
        '<p><a href="https://github.com/aryangorde8/bumpsmith">Source, review log and '
        "pull request history on GitHub</a></p>",
        "<footer>",
        provenance,
        "Each payload is verbatim <code>--json</code> output with one mechanical "
        "substitution: the capturing machine's absolute path, replaced with a stable "
        "name. <code>pages/runs.toml</code> records the swap for every run.",
        "</footer>",
        "</div>",
    ]

    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>bumpsmith &mdash; recorded runs</title>"
        f"<style>{STYLE}{_INDEX_STYLE}</style></head>"
        f"<body>{''.join(body)}</body></html>\n"
    )


def _clear(out: Path) -> None:
    """Empty *out*, but only if emptying it is this module's business.

    Rebuilding from scratch is the property that keeps a page from a deleted run
    published forever, and it wants ``rmtree``. But ``--out`` takes any path a
    person can type, and ``--out .`` typed once into the wrong terminal would
    then delete a repository rather than fail. So the directory has to identify
    itself first: a build drops :data:`_MARKER` into whatever it writes, and a
    directory that already has files but no marker is something this module did
    not create and will not remove.

    The marker has to be a *regular file and not a symlink*. ``is_file()`` alone
    follows symlinks, so a link named ``.bumpsmith-site`` pointing at any file
    anywhere would answer yes and hand the whole directory to ``rmtree`` -- which
    is the exact guarantee this function exists to make, defeated by a one-line
    link. A marker this build wrote is never a symlink.

    Raises:
        FileExistsError: if *out* holds files that no build put there.
    """
    if not out.exists():
        return
    if not out.is_dir() or out.is_symlink():
        raise FileExistsError(f"{out} is not a directory this script may replace")
    marker = out / _MARKER
    if any(out.iterdir()) and not (marker.is_file() and not marker.is_symlink()):
        raise FileExistsError(
            f"{out} is not empty and was not written by this script -- it has no "
            f"{_MARKER} regular file. Refusing to delete it. Pass an empty or new "
            "directory."
        )
    shutil.rmtree(out)


def build(out: Path, manifest_path: Path = MANIFEST) -> list[Path]:
    """Write the whole site into *out*.

    Args:
        out: the directory to write into. Emptied first, so a file from a run
            that has since been deleted cannot survive a rebuild -- but only
            when it is empty or carries this script's marker. See :func:`_clear`.
        manifest_path: the manifest to build from. Everything it names is
            resolved relative to *its* directory, not to this file's, so a
            manifest outside `pages/` builds the same way.

    Returns:
        Every path written, index first. The marker is not among them: it is
        bookkeeping for the next build, not part of the site.

    Raises:
        FileExistsError: if *out* holds files this script did not write.
    """
    manifest = load_manifest(manifest_path)
    runs = ordered_runs(manifest)
    root = manifest_path.resolve().parent

    _clear(out)
    out.mkdir(parents=True)
    (out / _MARKER).write_text(
        "Written by pages/build_site.py. Its presence is what allows the next "
        "build to empty this directory.\n",
        encoding="utf-8",
    )

    written = [out / "index.html"]
    written[0].write_text(index(manifest, runs, root), encoding="utf-8")

    for slug, entry in runs:
        payload = load_payload(entry, root)
        target = out / f"{slug}.html"
        target.write_text(
            page(payload, title=f"bumpsmith — {_text(entry, 'title')}"), encoding="utf-8"
        )
        written.append(target)

    cname = root / "CNAME"
    if cname.is_file():
        destination = out / "CNAME"
        destination.write_text(cname.read_text(encoding="utf-8"), encoding="utf-8")
        written.append(destination)

    return written


def main(argv: Sequence[str] | None = None) -> int:
    """Build the site from the command line.

    Args:
        argv: arguments to parse, or ``None`` to read ``sys.argv``.

    Returns:
        ``0``. Anything that goes wrong raises rather than returning a code, so
        a broken build fails the workflow instead of publishing half a site.
    """
    parser = argparse.ArgumentParser(
        prog="python pages/build_site.py",
        description="Render the runs recorded in runs.toml as a static site.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "_site",
        help="directory to write the site into (default: pages/_site)",
    )
    args = parser.parse_args(argv)

    for path in build(args.out):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
