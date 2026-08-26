"""Pin the claims the README makes about enums it says are complete.

The README tells a reader that every exit from the loop is one of eleven `Stop`
reasons and lists all of them, and that `Outcome` has exactly four members. Both
are the kind of statement that is true when written and quietly false two pull
requests later -- which has already happened once here, and was found by reading
rather than by anything failing.

REVIEW-LOG.md calls this shape "prose stating a property is not the property".
The counter-measure is to stop stating it in prose only. These tests fail when a
member is added or renamed without the README following, which is the moment the
drift is cheap to fix.

Deliberately narrow. They check the enums the README claims are *exhaustive*,
because those are the claims a reader acts on; they do not police wording
anywhere else in the file.
"""

import re
from pathlib import Path

from bumpsmith.migrate import Outcome, Stop

README = Path(__file__).resolve().parent.parent / "README.md"

_NUMBERS = {
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
}


def _readme() -> str:
    assert README.is_file(), f"expected the README beside the package, at {README}"
    return README.read_text(encoding="utf-8")


def test_readme_counts_the_stop_reasons_correctly() -> None:
    """The spelled-out number in the README must be `len(Stop)`.

    Failing here means one of two edits was made without the other: a member was
    added to `Stop`, or the sentence was reworded. Both are fine; leaving them
    disagreeing is not.
    """
    text = _readme()
    # `\s+` rather than a literal space: the README is hard-wrapped, so the
    # sentence being matched is split across a line ending and a pattern
    # assuming spaces finds nothing. The first run of this test failed that way.
    match = re.search(r"one\s+of\s+(\w+)\s+members\s+of\s+a\s+`Stop`\s+enum", text)
    assert match is not None, (
        "the README no longer claims a count of `Stop` members in the expected "
        "wording. If the claim was dropped on purpose, drop this test with it; "
        "if it was reworded, update the pattern."
    )
    spelled = match.group(1)
    assert spelled in _NUMBERS, f"unrecognised spelled number in the README: {spelled!r}"
    assert _NUMBERS[spelled] == len(Stop)


def test_readme_documents_every_stop_reason() -> None:
    """A `Stop` a caller can receive and cannot look up is a worse answer than a message.

    The whole argument for an enum over prose is that the reader can find out
    what one means. That only holds while the table is complete.
    """
    text = _readme()
    missing = [stop.name for stop in Stop if f"`{stop.name}`" not in text]
    assert not missing, f"Stop members absent from the README: {', '.join(missing)}"


def test_readme_documents_every_outcome() -> None:
    """The README lists all four `Outcome` members inline, so all four must be there."""
    text = _readme()
    missing = [outcome.name for outcome in Outcome if f"`{outcome.name}`" not in text]
    assert not missing, f"Outcome members absent from the README: {', '.join(missing)}"
