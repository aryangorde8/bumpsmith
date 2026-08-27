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
from pathlib import Path

from bumpsmith.migrate import Outcome, Stop

README = Path(__file__).resolve().parent.parent / "README.md"

_STOP_TABLE_HEADER = "| `Stop` | meaning |"
_OUTCOME_ANCHOR = "`Outcome` says what is on disk"


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
