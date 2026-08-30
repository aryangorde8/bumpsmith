"""Pin the claims the README makes about enums it presents as complete.

The README tells a reader that every exit from the loop is one of eleven `Stop`
reasons and lists all of them, and that `Outcome` has exactly four members. Both
are the kind of statement that is true when written and quietly false two pull
requests later -- which has already happened here, and was found by reading
rather than by anything failing.

REVIEW-LOG.md calls this shape "prose stating a property is not the property".
The counter-measure is to stop stating it in prose only. These tests fail when a
member is added or renamed without the README following, which is the moment the
drift is cheap to fix.

Scoped on purpose
-----------------
Each check reads the specific table or sentence the README offers as exhaustive,
never the whole file. Searching the whole file was the first version and it was
wrong in a way worth recording: a member deleted from the table would still be
found in some unrelated paragraph, so the test would pass while the invariant it
advertises had been broken. It happened to hold only because every name occurs
exactly once today -- an accident of the current text, not a property. A test
whose guarantee depends on nobody ever writing `` `MIGRATED` `` in an example is
not pinning anything.

Deliberately narrow in the other direction too: these check the enums the README
presents as *exhaustive*, because those are the claims a reader acts on. They do
not police wording anywhere else.
"""

import re
from datetime import UTC, datetime
from pathlib import Path

from bumpsmith.failures import BreakClass
from bumpsmith.migrate import Outcome, Stop
from bumpsmith.rewrite import has_rewriter

README = Path(__file__).resolve().parent.parent / "README.md"

_STOP_TABLE_HEADER = "| `Stop` | meaning |"
_OUTCOME_ANCHOR = "`Outcome` says what is on disk"
_MODULE_TABLE_HEADER = "| module | what it guarantees |"
PACKAGE = Path(__file__).resolve().parent.parent / "src" / "bumpsmith"


def _readme() -> str:
    assert README.is_file(), f"expected the README beside the package, at {README}"
    return README.read_text(encoding="utf-8")


def _stop_table(text: str) -> list[str]:
    """The rows of the README's `Stop` table, and nothing else.

    Returns the body rows only -- header and separator dropped -- so a member
    name occurring anywhere else in the README cannot stand in for its entry.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(_STOP_TABLE_HEADER)]
    assert len(starts) == 1, (
        f"expected exactly one `Stop` table header starting {_STOP_TABLE_HEADER!r}, "
        f"found {len(starts)}. If the table moved or was reworded, update this anchor."
    )
    rows: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    assert rows, "the `Stop` table header is not followed by any rows"
    return rows[1:]  # drop the |---|---|---| separator


def _outcome_paragraph(text: str) -> str:
    """The paragraph in which the README lists every `Outcome` member."""
    for block in text.split("\n\n"):
        if _OUTCOME_ANCHOR in block:
            return block
    raise AssertionError(
        f"no paragraph in the README contains {_OUTCOME_ANCHOR!r}. If the list moved "
        f"or was reworded, update this anchor."
    )


def _module_table(text: str) -> list[str]:
    """The rows of the README's module table, and nothing else.

    Same scoping as :func:`_stop_table`, for the same reason: nearly every module
    is named somewhere else in the README, so a file-wide search would report a
    complete map while the table a reader actually navigates by was missing rows.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(_MODULE_TABLE_HEADER)]
    assert len(starts) == 1, (
        f"expected exactly one module table header starting {_MODULE_TABLE_HEADER!r}, "
        f"found {len(starts)}. If the table moved or was reworded, update this anchor."
    )
    rows: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    assert rows, "the module table header is not followed by any rows"
    return rows[1:]  # drop the |---|---| separator


def _shipped_modules() -> set[str]:
    """Every ``.py`` file the package ships, with nothing filtered out.

    The first version of this excluded ``__*.py`` by pattern, on the reasoning
    that the table's column is "what it guarantees" and a dunder is not a
    guarantee. Review rejected it, and correctly: the README's sentence is
    "Everything is in ``src/bumpsmith/``", so a guard that means *everything
    except dunders* enforces a claim the README does not make -- which is this
    file's own subject happening inside this file. Worse, a pattern excludes
    modules that do not exist yet: a ``__version__.py`` added next month would
    have been silently out of scope, and nobody would have chosen that.

    So nothing is filtered. ``__main__.py`` and ``__init__.py`` have rows,
    because on reflection both are things a reader wants to find.
    """
    assert PACKAGE.is_dir(), f"expected the package beside the tests, at {PACKAGE}"
    return {path.name for path in PACKAGE.glob("*.py")}


def _tabled_modules(text: str) -> list[str]:
    """The module named in the first column of each row, **in order, with repeats**.

    A list rather than a set, and that is the whole point. Set-difference catches
    a missing name and an invented one; neither notices the same name twice, so a
    table that had drifted into two rows for one module -- one of them stale --
    would have satisfied both checks while the mapping it advertises was gone.
    Raised in review on the first version of this file.
    """
    return [row.split("|")[1].strip().strip("*").split("`")[1] for row in _module_table(text)]


def test_the_readme_does_not_restate_the_number_of_stop_reasons() -> None:
    """The table owns the list; a count beside it is a number waiting to go stale.

    This replaced a test that checked the spelled-out number against `len(Stop)`.
    That test was not useless -- it is precisely what failed when
    `FOREIGN_CONFIG` was added, which is how the sentence was found. But keeping
    a restated number correct is a weaker aim than not restating it, and
    `test_readme_table_has_a_row_for_every_stop_reason` below already guarantees
    the part a reader actually needs. Findings 64 and 65 are the same shape: a
    summary restating a number the table already owns.

    The pattern is the old test's, inverted, so it pins the exact wording that
    regressed rather than every conceivable way of writing a number down.
    """
    match = re.search(r"one\s+of\s+(\w+)\s+members\s+of\s+a\s+`Stop`\s+enum", _readme())
    assert match is None, (
        f"the README has gone back to counting `Stop` members ({match.group(1)!r} of them). "
        f"The table below that sentence is the list; let it be the only place."
    )


def test_readme_table_has_a_row_for_every_stop_reason() -> None:
    """A `Stop` a caller can receive and cannot look up is a worse answer than a message.

    The whole argument for an enum over prose is that the reader can find out
    what one means. That only holds while the table is complete, so the name has
    to be in the table's first column -- not merely somewhere in the file.
    """
    rows = _stop_table(_readme())
    documented = {row.split("|")[1].strip() for row in rows}
    missing = [stop.name for stop in Stop if f"`{stop.name}`" not in documented]
    assert not missing, f"`Stop` members with no row in the README table: {', '.join(missing)}"


def test_readme_table_invents_no_stop_reason() -> None:
    """The other direction: a row for a member that no longer exists.

    A renamed member leaves the old row behind, and a reader looking up the name
    the code actually returns finds nothing while the table still looks full.
    """
    rows = _stop_table(_readme())
    known = {f"`{stop.name}`" for stop in Stop}
    strays = [row.split("|")[1].strip() for row in rows if row.split("|")[1].strip() not in known]
    assert not strays, f"README table rows matching no `Stop` member: {', '.join(strays)}"


def test_readme_lists_every_outcome() -> None:
    """The README names all four `Outcome` members in one sentence, so all four must be there."""
    paragraph = _outcome_paragraph(_readme())
    missing = [outcome.name for outcome in Outcome if f"`{outcome.name}`" not in paragraph]
    assert not missing, (
        f"`Outcome` members absent from the paragraph that lists them: {', '.join(missing)}"
    )


def test_the_readme_maps_every_module_the_package_ships() -> None:
    """A module with no row is a module a reader of the README does not know exists.

    Found by counting: the table offered itself as the map of ``src/bumpsmith/``
    and listed twelve of sixteen. The four it omitted -- ``fanout.py``,
    ``remote.py``, ``publish.py`` and ``report.py`` -- were the ones doing the
    work the project most wanted read, and the omission cost nothing that failed.
    """
    missing = sorted(_shipped_modules() - set(_tabled_modules(_readme())))
    assert not missing, (
        f"modules in src/bumpsmith/ with no row in the README's module table: {', '.join(missing)}"
    )


def test_the_readme_module_table_invents_no_module() -> None:
    """The other direction: a row for a file that was renamed or removed.

    A stale row is worse than a missing one. The table still looks complete, and
    the link in it goes nowhere.
    """
    strays = sorted(set(_tabled_modules(_readme())) - _shipped_modules())
    assert not strays, (
        f"README module table rows naming no file in src/bumpsmith/: {', '.join(strays)}"
    )


# --------------------------------------------------------------------------
# The package's own map of itself
#
# Found while fixing the review finding above. `src/bumpsmith/__init__.py` is a
# *third* description of the same package -- the one `help(bumpsmith)` prints --
# and it listed nine of the eighteen files. The same four the README omitted were
# among them. Three maps of one package, all written by hand, and until now none
# of them was checked against the package.
# --------------------------------------------------------------------------

INIT = PACKAGE / "__init__.py"

#: Modules the ``__init__`` table legitimately leaves out, each named in its own
#: prose instead. Named individually rather than matched by pattern, for the
#: reason :func:`_shipped_modules` gives: a pattern silently adopts files that do
#: not exist yet, and a decision nobody made is not a decision.
_INIT_TABLE_EXEMPT = {
    "migrate.py",  # "Start at bumpsmith.migrate ... every other module is a part it uses"
    "__main__.py",  # "python -m bumpsmith runs the loop from a command line"
    "__init__.py",  # the file the docstring is in
}

_INIT_ROW = re.compile(r"^:mod:`bumpsmith\.(\w+)`", re.MULTILINE)


def _init_table_modules() -> list[str]:
    """The modules named in the package docstring's table, in order, with repeats."""
    assert INIT.is_file(), f"expected the package's __init__ at {INIT}"
    doc = INIT.read_text(encoding="utf-8")
    rows = [m.group(1) + ".py" for m in _INIT_ROW.finditer(doc)]
    assert rows, (
        "no ``:mod:`bumpsmith.X```  rows found in the package docstring. If the table "
        "moved or was reworded, update this anchor."
    )
    return rows


def test_the_package_docstring_maps_every_module_it_claims_to() -> None:
    """`help(bumpsmith)` is a map too, and it was missing six of the files it maps.

    The docstring says every module other than `migrate` is a part the loop uses,
    and then lists them. That is the same promise the README's table makes, made
    to a different reader -- somebody at a REPL who never opens the repository.
    """
    expected = _shipped_modules() - _INIT_TABLE_EXEMPT
    missing = sorted(expected - set(_init_table_modules()))
    assert not missing, (
        f"modules absent from the table in src/bumpsmith/__init__.py: {', '.join(missing)}"
    )


def test_the_package_docstring_invents_no_module() -> None:
    """A row in the docstring for a file that is not there, which `help()` still prints."""
    strays = sorted(set(_init_table_modules()) - _shipped_modules())
    assert not strays, (
        f"rows in src/bumpsmith/__init__.py naming no file in the package: {', '.join(strays)}"
    )


def test_the_package_docstring_names_each_module_once() -> None:
    """The same check the README's table has, on the other table that makes the claim.

    Finding 137 was fixed where it was raised and not where it also applied.
    `_init_table_modules` was written to return repeats -- its docstring says so --
    and then every caller took `set(...)` of it, so the multiplicity it was
    careful to preserve was thrown away by all three readers. A promise nothing
    consumes is not a guarantee, and this table makes the same one-row-per-module
    claim the README's does.
    """
    named = _init_table_modules()
    repeated = sorted({name for name in named if named.count(name) > 1})
    assert not repeated, (
        f"modules with more than one row in src/bumpsmith/__init__.py: {', '.join(repeated)}"
    )


def test_the_readme_module_table_names_each_module_once() -> None:
    """One row per module, which neither of the two checks above can see.

    Both of those compare sets, and a set has already thrown multiplicity away by
    the time they run. A table with two rows for one module passes them while
    being exactly the thing the table promises not to be -- and the second row is
    the one nobody updates.
    """
    named = _tabled_modules(_readme())
    repeated = sorted({name for name in named if named.count(name) > 1})
    assert not repeated, (
        f"modules with more than one row in the README's module table: {', '.join(repeated)}"
    )


# --------------------------------------------------------------------------
# The review log's own index
#
# Found by reading the README cold, the way somebody arriving at the repository
# would. Two things were wrong at once, and both are this file's subject:
# the README claimed 65 findings when the log held 107, and the log's table --
# which the README calls "every finding raised and what happened to it" --
# skipped 20 through 31 entirely. Those twelve had prose sections and no row, so
# a reader scanning the index would not have found them.
#
# The stale sentence is the one that ends "a stale number was corrected in one
# file and left standing in two others a `grep` away". Findings 64 and 65 named
# that shape; this is it happening inside the paragraph that describes it.
# --------------------------------------------------------------------------

REVIEW_LOG = Path(__file__).resolve().parent.parent / "REVIEW-LOG.md"

_FINDING_TABLE_HEADER = "| # | PR | Finding | Disposition | Where |"
_PR_COVERAGE_HEADER = "| PR | Qodo | Inline findings | Coverage comments |"
_PR_LINK = re.compile(r"\[#(\d+)\]")
_ROW = re.compile(r"^\|\s*(\d+)\s*\|")
_README_SNAPSHOT_DATE = re.compile(
    r"As of (\d{1,2}) (January|February|March|April|May|June|July|August|September"
    r"|October|November|December) (\d{4}) it holds"
)
_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}
_README_TOTAL = re.compile(r"it holds \*\*(\d+) findings\*\*")
_README_SPLIT = re.compile(
    r"\*\*(\d+) findings\*\*: (\d+) raised by automated review, (\d+)\b.*?and (\d+)\b",
    re.DOTALL,
)


def _review_log() -> str:
    assert REVIEW_LOG.is_file(), f"expected the review log beside the README, at {REVIEW_LOG}"
    return REVIEW_LOG.read_text(encoding="utf-8")


def _table_body(text: str, header: str) -> list[str]:
    """Body rows of one table, scoped the way :func:`_stop_table` is.

    A second table in REVIEW-LOG.md with a leading ``| 1 |`` would otherwise
    be counted as finding 1. The finding index is the table whose header is
    ``# | PR | Finding``; the pull-request table is the other one.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(header)]
    assert len(starts) == 1, (
        f"expected exactly one table header starting {header!r}, found {len(starts)}"
    )
    rows: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("|"):
            break
        rows.append(line)
    assert rows, f"{header!r} is not followed by any rows"
    return rows[1:]  # drop the separator


def _logged_ids() -> list[int]:
    ids: list[int] = []
    for row in _table_body(_review_log(), _FINDING_TABLE_HEADER):
        match = _ROW.match(row)
        assert match is not None, f"finding row is not numbered: {row[:80]!r}"
        ids.append(int(match.group(1)))
    return ids


def _coverage_pr_numbers() -> list[int]:
    """Merged PRs named in the coverage table, in order, excluding `this PR`."""
    numbers: list[int] = []
    for row in _table_body(_review_log(), _PR_COVERAGE_HEADER):
        found = _PR_LINK.findall(row.split("|")[1])
        numbers.extend(int(n) for n in found)
    return numbers


def _index_note(text: str) -> str:
    """The prose between the index table and the first finding section.

    Scoped for the reason this module's docstring gives. The first version read
    the whole file and failed immediately -- on the log's own description of
    finding 110, which necessarily quotes the sentence being banned. A check
    that cannot coexist with writing down what it checks is not usable here.
    """
    after = text.split("| 110 |", 1)[-1]
    body = after.split("\n", 1)[1] if "\n" in after else ""
    return body.split("\n## ", 1)[0]


def test_the_log_index_numbers_every_finding_from_one_with_no_gaps() -> None:
    """A table presenting itself as the index has to be one.

    20-31 were missing when this was written: twelve findings with prose
    sections and no row. Prose is where a finding is *explained*; the table is
    where a reader finds out it exists at all. A gap there is indistinguishable
    from a finding nobody recorded, which is exactly what the README promises
    cannot happen here.
    """
    ids = _logged_ids()
    assert ids, "no numbered rows found in REVIEW-LOG.md -- has the table format changed?"
    expected = list(range(1, len(ids) + 1))
    missing = sorted(set(expected) - set(ids))
    assert ids == expected, (
        f"the review log's index is not 1..{len(ids)} in order. "
        f"Missing: {missing or 'none'}. First disagreement at position "
        f"{next((i for i, (a, b) in enumerate(zip(ids, expected, strict=False)) if a != b), len(ids))}."
    )


def test_the_pr_coverage_table_names_each_pr_once_through_the_open_one() -> None:
    """Every pull request, including the open one that carries this file.

    Finding 186: `this PR` as a placeholder hid the number a reader looks for.
    The table is 1..N with no gaps, and N is the last row.
    """
    named = _coverage_pr_numbers()
    assert named, "the pull-request table names no pull requests"
    expected = list(range(1, max(named) + 1))
    assert named == expected, (
        f"the pull-request table is not 1..{max(named)} in order. "
        f"Missing: {sorted(set(expected) - set(named)) or 'none'}."
    )
    rows = _table_body(_review_log(), _PR_COVERAGE_HEADER)
    last = rows[-1].split("|")[1]
    assert f"#{max(named)}" in last, (
        f"the last coverage row must name #{max(named)}, not a placeholder. Got {last!r}."
    )


def test_every_finding_names_a_pr_the_coverage_table_lists() -> None:
    """The finding index is allowed to skip a PR; the coverage table is not.

    #26 and #42 are the cases: Qodo reviewed them, raised nothing, and the
    finding table never named them. That is not a gap in the finding table.
    It is a gap if the coverage table does not name them either.
    """
    coverage = set(_coverage_pr_numbers())
    missing: list[int] = []
    for row in _table_body(_review_log(), _FINDING_TABLE_HEADER):
        cells = row.split("|")
        pr_cell = cells[2] if len(cells) > 2 else ""
        if pr_cell.strip() in {"this PR", "—", "-"}:
            continue
        found = _PR_LINK.findall(pr_cell)
        for n in found:
            if int(n) not in coverage:
                missing.append(int(n))
    assert not missing, "findings name pull requests the coverage table does not: " + ", ".join(
        f"#{n}" for n in missing
    )


def test_the_readme_finding_count_matches_the_log_it_describes() -> None:
    """The README's most quotable number, checked against the table that owns it.

    Findings 64 and 65 are a summary restating a number the table already owns.
    The `Stop` count was fixed by not restating it, because the table was on the
    same page. This one is in another file and is worth telling a reader, so it
    is restated and *checked* instead.
    """
    match = _README_TOTAL.search(_readme())
    assert match is not None, (
        "the README no longer states a finding total in the form "
        "'it holds **N findings**'. If the wording changed, update this anchor."
    )
    claimed = int(match.group(1))
    actual = len(_logged_ids())
    assert claimed == actual, (
        f"the README says the log holds {claimed} findings; its table has {actual} rows."
    )


def test_the_readme_finding_snapshot_is_not_future_dated() -> None:
    """The snapshot cannot be dated after the moment it is read.

    Finding 132. The date was written as 28 August from a clock at UTC+05:30
    while every timestamp the repository actually carries -- the commit, the
    pull request, the review that caught it -- said 27 August. A snapshot may
    be older than now, because that is what a snapshot is. It may never be
    newer, and a date read off the wrong clock is the only way it gets there.

    This can pass and then never spuriously fail: a date in the past stays in
    the past.
    """
    stated = _README_SNAPSHOT_DATE.search(_readme())
    assert stated is not None, (
        "the README no longer says 'As of <D> <Month> <YYYY> it holds'. "
        "If the wording changed, update this anchor."
    )
    day, month, year = stated.group(1), stated.group(2), stated.group(3)
    claimed = datetime(int(year), _MONTHS[month], int(day), tzinfo=UTC)
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    assert claimed <= today, (
        f"the README dates its finding snapshot {day} {month} {year}, which is "
        f"after today in UTC ({today:%d %B %Y}). Check the clock's timezone."
    )


def test_the_readme_finding_breakdown_adds_up_to_its_own_total() -> None:
    """Three sources, and they have to sum to the number beside them.

    This is the arithmetic version of the same defect: a total corrected without
    the parts, or the reverse, reads as precise while being wrong.
    """
    match = _README_SPLIT.search(_readme())
    assert match is not None, (
        "could not read the README's finding breakdown. If the sentence was "
        "reworded, update this anchor."
    )
    total, review, harness, author = (int(group) for group in match.groups())
    assert review + harness + author == total, (
        f"the README's breakdown does not sum to its own total: "
        f"{review} + {harness} + {author} = {review + harness + author}, stated as {total}."
    )


def test_the_log_does_not_claim_findings_are_unindexed_while_indexing_them() -> None:
    """Finding 110: the note under the table outlived the arrangement it described.

    Adding rows 20-31 made "described in the sections below rather than listed
    here" false, so the log said both things at once. Raised by review, on the
    pull request whose subject was stale sentences, two lines below the table
    being edited.

    Written as the inverted pattern rather than a positive assertion about the
    note's wording, for the reason `test_the_readme_does_not_restate_the_number_
    of_stop_reasons` gives: pin the sentence that regressed, not every way of
    writing a true one.
    """
    note = _index_note(_review_log())
    match = re.search(r"rather than listed here|are not listed (?:here|in the table)", note)
    assert match is None, (
        f"the note under the index again says findings are not listed there "
        f"({match.group(0)!r}), while the index is contiguous 1..{len(_logged_ids())}. "
        f"One of the two is wrong."
    )


_TAXONOMY_TABLE_HEADER = "| # | class | what it is | rewriter |"

_TAXONOMY_PROSE = re.compile(
    r"^(?P<classes>\w+) classes, numbered by the project's own taxonomy\. "
    r"(?P<rewriters>\w+) have rewriters;",
    re.MULTILINE,
)

_NUMBER_WORDS = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
    "Six": 6,
    "Seven": 7,
    "Eight": 8,
    "Nine": 9,
    "Ten": 10,
    "Eleven": 11,
    "Twelve": 12,
}
"""Written out because the README writes them out, and the README is right to.

A guard that forced the prose to say "7 classes" would be the test dictating
style to the document it exists to serve.
"""

_TAXONOMY_EXEMPT = {
    "UNKNOWN": (
        "not a break the project can name but the absence of one -- the table "
        "numbers what the classifier recognises, and UNKNOWN is what it reports "
        "when it recognises nothing. A row for it would claim a taxonomy entry "
        "that does not exist"
    ),
}
"""Members with no row, each named individually with the reason it has none.

Named one at a time rather than matched by pattern, which is the lesson of the
module table: a pattern silently adopts members that do not exist yet, so a
class added next month would fall out of scope by nobody's decision.
"""


_ABSENT_CELL = "*(absent)*"
"""The one spelling a class cell may take without naming a `BreakClass`.

Matched exactly. Mapping *every* un-backticked cell to "deliberately absent" is
how an arbitrary word like `ABSENT` slipped past the invented-class, numbering
and rewriter guards at once -- each of them skips the rows this returns `None`
for, so a cell that is merely malformed inherited the one intentional exemption.
"""


def _taxonomy_rows(text: str) -> list[tuple[int, str | None, bool]]:
    """Each row of the break-taxonomy table as ``(number, class name, has rewriter)``.

    The name is ``None`` only for the row that records a *deliberately absent*
    class, which is a fact about the taxonomy rather than about the enum. Any
    other cell that does not name a class is an error here rather than a row the
    checks below quietly pass over.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(_TAXONOMY_TABLE_HEADER)]
    assert len(starts) == 1, f"expected one taxonomy table, found {len(starts)}"
    rows: list[tuple[int, str | None, bool]] = []
    for line in lines[starts[0] + 2 :]:  # +2 skips the |---| separator
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 4, f"taxonomy row does not have four cells: {line}"
        number, name, _what, rewriter = cells
        if name == _ABSENT_CELL:
            named = None
        else:
            assert len(name) > 2 and name.startswith("`") and name.endswith("`"), (
                f"taxonomy class cell is neither `a name` nor {_ABSENT_CELL}: {line}"
            )
            named = name.strip("`")
        rows.append((int(number), named, rewriter == "✅"))
    assert rows, "the taxonomy table header is not followed by any rows"
    return rows


def test_the_readme_taxonomy_gives_each_class_exactly_one_row() -> None:
    """One row per class, one number per row, and exactly one absent row.

    The fourth time this shape has been found: a table gets per-row checks and
    nothing checks that the rows are *distinct*. Completeness collapses the names
    into a dict, every other check validates each repeated row happily on its
    own, and the prose count reads the physical rows -- so duplicating a real row
    lets the README claim a class it does not have, with all five guards green.
    """
    rows = _taxonomy_rows(_readme())

    named = [name for _, name, _ in rows if name is not None]
    repeated = sorted({name for name in named if named.count(name) > 1})
    assert not repeated, f"break classes with more than one taxonomy row: {repeated}"

    numbers = [number for number, _, _ in rows]
    reused = sorted({number for number in numbers if numbers.count(number) > 1})
    assert not reused, f"taxonomy numbers used by more than one row: {reused}"

    absent = [name for _, name, _ in rows if name is None]
    assert len(absent) == 1, (
        f"expected exactly one {_ABSENT_CELL} row in the taxonomy, found {len(absent)}"
    )


def test_the_readme_taxonomy_lists_every_break_class() -> None:
    """A class with no row is a class the README's taxonomy denies exists.

    Found by adding one. `ITEMS_KEYWORD` went into `BreakClass`, the table kept
    saying "Six classes", and all 750 tests passed -- the same shape as the
    module table two pull requests earlier, in the other table on this page.
    """
    tabled = {name: number for number, name, _ in _taxonomy_rows(_readme()) if name}
    missing = sorted(
        member.name
        for member in BreakClass
        if member.name not in _TAXONOMY_EXEMPT and member.name not in tabled
    )
    assert not missing, f"BreakClass members with no row in the README's taxonomy: {missing}"


def test_the_readme_taxonomy_numbers_each_class_as_the_enum_does() -> None:
    """The `#` column is the enum's value, so a class added with the wrong number fails."""
    # Filtered to names the enum knows, so an invented row fails its own test
    # with its own message rather than killing this one with a `KeyError`.
    wrong = [
        (name, number, BreakClass[name].value)
        for number, name, _ in _taxonomy_rows(_readme())
        if name is not None and name in BreakClass.__members__ and BreakClass[name].value != number
    ]
    assert not wrong, f"taxonomy rows numbered differently from BreakClass: {wrong}"


def test_the_readme_taxonomy_invents_no_break_class() -> None:
    """The other direction: a row for a class that was renamed or removed."""
    known = {member.name for member in BreakClass}
    invented = sorted(
        name for _, name, _ in _taxonomy_rows(_readme()) if name and name not in known
    )
    assert not invented, f"taxonomy rows naming no BreakClass member: {invented}"


def test_the_readme_taxonomy_marks_a_rewriter_where_one_exists() -> None:
    """The rewriter column is a claim about `rewrite._PLANNERS`, so it is read from it.

    The column is the part a reader acts on: it is the difference between "this
    tool will fix it" and "this tool will tell you about it".
    """
    disagree = [
        (name, marked, has_rewriter(BreakClass[name]))
        for _, name, marked in _taxonomy_rows(_readme())
        if name is not None
        and name in BreakClass.__members__
        and marked != has_rewriter(BreakClass[name])
    ]
    assert not disagree, f"taxonomy rewriter column disagrees with rewrite._PLANNERS: {disagree}"


def test_the_readme_taxonomy_prose_counts_its_own_table() -> None:
    """ "Seven classes ... Four have rewriters" -- both counted rather than typed.

    The sentence above the table is the part a reader believes without checking,
    and it is the part nothing checked.
    """
    match = _TAXONOMY_PROSE.search(_readme())
    assert match is not None, "the sentence introducing the taxonomy table has changed shape"
    rows = _taxonomy_rows(_readme())
    assert _NUMBER_WORDS[match["classes"]] == len(rows), (
        f"the README says {match['classes']} classes; the table has {len(rows)} rows"
    )
    with_rewriter = sum(1 for _, _, marked in rows if marked)
    assert _NUMBER_WORDS[match["rewriters"]] == with_rewriter, (
        f"the README says {match['rewriters']} have rewriters; the table marks {with_rewriter}"
    )


# --------------------------------------------------------------------------
# Finding 187. The two checks below are about the documents as they are *read*
# rather than as they are parsed. Everything above this line reads a table by
# splitting on `|` in Python, which is a more forgiving parser than the one a
# reader actually gets, and every one of those checks passed while two rows of
# REVIEW-LOG.md displayed no disposition at all on github.com.
# --------------------------------------------------------------------------

_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_AUDIT_HEADING = re.compile(r"^## An outside audit of `main` — (\d+) to (\d+)$", re.MULTILINE)
_README_AUDIT_RANGE = re.compile(
    r"outside audit of `main` that raised findings\s+(\d+) to (\d+)", re.DOTALL
)


def _delimiters(row: str) -> list[int]:
    """Offsets of the pipes GitHub reads as cell boundaries.

    A pipe is escaped by an **odd** run of backslashes before it. `\\|` is a
    literal pipe; `\\\\|` is a literal backslash followed by a delimiter. The
    first version of this asked only whether the previous character was a
    backslash, which reads the second as escaped -- finding 190.
    """
    at: list[int] = []
    for index, char in enumerate(row):
        if char != "|":
            continue
        backslashes = 0
        while index - backslashes - 1 >= 0 and row[index - backslashes - 1] == "\\":
            backslashes += 1
        if backslashes % 2 == 0:
            at.append(index)
    return at


def _cells(row: str) -> list[str]:
    """One row's cells. The outer pipes are optional in GitHub's grammar."""
    text = row.strip()
    at = _delimiters(text)
    parts: list[str] = []
    start = 0
    for offset in at:
        parts.append(text[start:offset])
        start = offset + 1
    parts.append(text[start:])
    if at and at[0] == 0:  # a leading pipe opens no cell
        parts = parts[1:]
    if at and at[-1] == len(text) - 1:  # nor does a trailing one close a real cell
        parts = parts[:-1]
    return parts


def _is_separator(row: str) -> bool:
    cells = _cells(row)
    return bool(cells) and all(_SEPARATOR_CELL.match(cell.strip()) for cell in cells)


def _table_rows_against_their_width(text: str) -> list[tuple[int, int, int, str]]:
    """Every table row, with the column count its separator declared.

    A table is found by its `---` line rather than by rows starting with `|`,
    because outer pipes are optional and a table written without them was
    invisible to the first version of this -- finding 189. The separator fixes
    the width; the header above it and the rows below it are measured against
    that. A row offering more cells does not wrap: the surplus is dropped,
    silently, from the right.
    """
    lines = text.splitlines()
    found: list[tuple[int, int, int, str]] = []
    for index, line in enumerate(lines):
        if not line.strip() or not _is_separator(line):
            continue
        width = len(_cells(line))
        rows: list[tuple[int, str]] = [(index, lines[index - 1])] if index else []
        for offset in range(index + 1, len(lines)):
            row = lines[offset]
            if not row.strip() or not _delimiters(row.strip()):
                break
            rows.append((offset + 1, row))
        found.extend((number, len(_cells(row)), width, row.strip()) for number, row in rows)
    return found


def test_no_table_row_loses_a_column_to_an_unescaped_pipe() -> None:
    """Finding 187: a `|` inside a code span still ends the cell.

    Rows 143 and 178 carried shell -- `... || echo __ABSENT__`, `jq 'add | map(…)'`
    -- in inline code, which does not protect the character. Both rendered with
    more cells than the header declares, so GitHub dropped the surplus: the
    **Disposition** column and everything right of it. A `High` finding read
    online as one nobody had closed, in the table whose stated promise is that
    this cannot happen.

    Nothing above this test could see it. They all split on `|` in Python, which
    keeps the extra cells rather than discarding them. This one counts instead,
    and covers the README because nothing about the mistake is particular to the
    log.
    """
    wrong = [
        (name, number, got, want, row)
        for name, text in (("REVIEW-LOG.md", _review_log()), ("README.md", _readme()))
        for number, got, want, row in _table_rows_against_their_width(text)
        if got != want
    ]
    assert not wrong, "table rows whose surplus cells GitHub will drop:\n" + "\n".join(
        f"  {name}:{number} offers {got} cells, the header declares {want} -- "
        f"escape the pipes as `\\|`: {row[:100]}..."
        for name, number, got, want, row in wrong
    )


def test_the_readme_names_the_same_audit_findings_the_log_does() -> None:
    """Finding 188: the README said the audit "raised the last three".

    It raised 182 to 184. 185 was Qodo's second round on the fix for 184 and
    landed in the same pull request, so the sentence was false in the commit
    that wrote it, and every finding added since has moved it further. A reader
    following it lands on rows the audit never saw and credits them to it.

    The fix was to name the range, and naming it is only worth more than
    counting it if the two files cannot drift apart -- so the README's numbers
    are read against the heading of the log's own section for that batch. This
    is finding 181's lesson, which is that a row is identified by its number and
    never by where it sits.
    """
    heading = _AUDIT_HEADING.search(_review_log())
    assert heading is not None, (
        "REVIEW-LOG.md no longer has a section headed 'An outside audit of `main` — N to M'. "
        "If the batch was renamed, update this anchor and the README sentence together."
    )
    stated = _README_AUDIT_RANGE.search(_readme())
    assert stated is not None, (
        "the README no longer says the outside audit 'raised findings N to M'. "
        "If the wording changed, update this anchor -- but do not go back to a "
        "positional reference; that is finding 188."
    )
    assert stated.groups() == heading.groups(), (
        f"the README says the outside audit raised {stated.group(1)} to {stated.group(2)}; "
        f"the log's section for that batch is headed {heading.group(1)} to {heading.group(2)}."
    )


def test_the_table_guard_sees_the_two_shapes_it_first_could_not() -> None:
    """Findings 189 and 190, both raised on the guard added for 187.

    Neither shape occurs in either document today, and that is the reason they
    are pinned against literals rather than left to the files: a check whose
    blind spots are visible only in the text it currently happens to read is
    one nobody can trust the next time that text changes. 189 was accepted with
    its stated evidence corrected -- it named the README's recorded-runs table
    as an existing leadingless one, and that table has outer pipes like every
    other here.
    """
    leadingless = "Run | Ends\n--- | ---\none | `a || b`\n"
    assert [(got, want) for _, got, want, _ in _table_rows_against_their_width(leadingless)] == [
        (2, 2),  # the header, which is fine
        (4, 2),  # the row whose `||` GitHub would truncate
    ], "a table written without outer pipes is not being measured"

    literal_backslash = "| a | b |\n|---|---|\n| a\\\\| x | b |\n"
    assert [(got, want) for _, got, want, _ in _table_rows_against_their_width(literal_backslash)][
        -1
    ] == (3, 2), "a pipe after an even run of backslashes is a delimiter, not an escape"

    escaped = "| a | b |\n|---|---|\n| a \\| x | b |\n"
    assert all(got == want for _, got, want, _ in _table_rows_against_their_width(escaped)), (
        "an odd run of backslashes does escape the pipe, and this row is fine"
    )
