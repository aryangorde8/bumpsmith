"""Turn a failing pytest run into structured facts about *why* it failed.

The agent needs to know which pydantic v1-to-v2 break it is looking at before it
can decide what to write. That decision is made here, from the text pytest
prints, because in the cases that matter most pytest produces no machine-readable
output at all.

Two things drive the design, both measured rather than assumed.

**Dispatch on the return code, not on the text.** pytest emits three materially
different layouts depending on how far it got, and the return code names which
one you have before any parsing begins. Guessing from the text instead means
writing patterns that have to be right about the layout *and* the content.

**Never key on the summary line.** A conftest import failure prints no
``short test summary info`` block, no ``=== ERRORS ===`` banner and no
``N error in Xs`` line -- it prints a bare traceback and stops. A parser that
looks for the summary reports *zero failures* for the most comprehensively
broken repository it will ever see. That is worse than crashing, because it
looks like success.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "BreakClass",
    "Failure",
    "Frame",
    "RunShape",
    "parse_failures",
]

# A traceback frame as pytest prints it: "path/to/file.py:27: in <module>".
_FRAME = re.compile(r"^(?P<path>\S.*?\.py):(?P<line>\d+): in ")

# The raised exception: "E   pydantic.errors.PydanticUserError: message text".
# The type is dotted; the message is everything after the first colon-space.
_ERROR_LINE = re.compile(
    r"^E\s+(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Warning)):\s*(?P<message>.+)$"
)

# pydantic links its own docs as errors.pydantic.dev/<version>/u/<slug>. The slug
# is the most reliable classifier available -- when pydantic emits one at all.
_DOC_URL = re.compile(r"errors\.pydantic\.dev/[^/\s]+/u/(?P<slug>[\w-]+)")

# A moved or deleted attribute, named back-ticked as "module.path:NAME".
_SYMBOL = re.compile(r"`(?P<symbol>[\w.]+:[\w]+)`")

# The missing module in "No module named 'typing_inspect'".
_MISSING_MODULE = re.compile(r"No module named ['\"](?P<module>[\w.]+)['\"]")

# Anything under an installed-packages directory is the library's own stack,
# not code this project can edit.
_VENDORED = "site-packages"


class RunShape(Enum):
    """Which output layout pytest produced, selected by its return code.

    The codes are pytest's own. Only the four below have been observed against
    the fixture set; anything else is reported as :attr:`UNKNOWN` rather than
    guessed at, because a wrong shape produces confidently wrong parsing.
    """

    PASSED = "passed"
    """rc 0 -- nothing to extract."""

    TESTS_FAILED = "tests-failed"
    """rc 1 -- the suite ran. Per-test results exist and JUnit XML is meaningful."""

    COLLECTION_ERROR = "collection-error"
    """rc 2 -- a test module failed to import. Has banners and a summary line."""

    CONFTEST_IMPORT_ERROR = "conftest-import-error"
    """rc 4 -- conftest itself failed to import. Bare traceback, no summary."""

    UNKNOWN = "unknown"

    @classmethod
    def from_returncode(cls, returncode: int) -> RunShape:
        """Map a pytest return code to the layout it implies."""
        return {
            0: cls.PASSED,
            1: cls.TESTS_FAILED,
            2: cls.COLLECTION_ERROR,
            4: cls.CONFTEST_IMPORT_ERROR,
        }.get(returncode, cls.UNKNOWN)


class BreakClass(Enum):
    """Which pydantic v1-to-v2 break this is.

    Numbering follows the project's six-class taxonomy. Classes 2 and 3 exist in
    that taxonomy but have no recorded sample, so no classifier is written for
    them: a pattern authored against an unobserved signature would misfile real
    failures while looking like coverage.
    """

    VALIDATOR_FIELD_CONFIG = 1
    """``@validator`` taking ``field`` or ``config``, which V2 replaced with ``info``."""

    ROOT_MODEL = 4
    """A field named ``__root__``, which V2 replaced with ``pydantic.RootModel``."""

    REMOVED_INTERNAL = 5
    """An import of a pydantic internal that V2 deleted."""

    TRANSITIVE_DEPENDENCY = 6
    """A third-party package the repository depends on is itself unmigrated."""

    UNKNOWN = 0


@dataclass(frozen=True, slots=True)
class Frame:
    """One line of a traceback."""

    path: str
    line: int

    @property
    def is_vendored(self) -> bool:
        """True when this frame is inside installed packages rather than the project."""
        return _VENDORED in self.path

    def __str__(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True, slots=True)
class Failure:
    """One structured failure, extracted from a pytest run.

    ``culprit`` is the line a human would open first. Everything below it in the
    traceback belongs to pydantic and cannot be edited.
    """

    shape: RunShape
    break_class: BreakClass
    error_type: str | None
    message: str | None
    culprit: Frame | None
    pydantic_code: str | None = None
    symbol: str | None = None


def _frames(text: str) -> list[Frame]:
    """Every traceback frame in the output, in the order pytest printed them."""
    frames: list[Frame] = []
    for raw in text.splitlines():
        match = _FRAME.match(raw)
        if match is not None:
            frames.append(Frame(path=match["path"], line=int(match["line"])))
    return frames


def _culprit(frames: list[Frame]) -> Frame | None:
    """The last frame that is not inside installed packages.

    Tracebacks read outermost-first, so the project's own code sits between the
    entry point above it and the library that actually raised below it. Taking
    the *last* non-vendored frame therefore lands on the deepest line the project
    owns, which is the line to edit.

    This relies on the project's frames all preceding the library's. That holds
    whenever a library raises during import or construction, which is every case
    in the fixture set -- including the one whose traceback opens inside the
    standard library's ``importlib``. It would not hold for a callback invoked by
    a library, where project code appears below vendored code; such a failure
    would report the callback, which is still a defensible answer.
    """
    for frame in reversed(frames):
        if not frame.is_vendored:
            return frame
    return None


def _error(text: str) -> tuple[str | None, str | None]:
    """The raised exception type and its message.

    Takes the first ``E``-prefixed line that names an exception. pydantic follows
    that with a blank ``E`` line and a docs link; neither is part of the message.
    """
    for raw in text.splitlines():
        match = _ERROR_LINE.match(raw)
        if match is not None:
            return match["type"], match["message"].strip()
    return None, None


def _classify(
    error_type: str | None,
    message: str | None,
    pydantic_code: str | None,
    project_packages: frozenset[str],
) -> BreakClass:
    """Decide which break this is, preferring pydantic's own error slug.

    The slug is authoritative when present. It is absent for exactly one class:
    a ``__root__`` field raises a plain builtin ``TypeError`` from inside
    pydantic's namespace inspection, with no error code and no docs link. For
    that class, and only that class, the English message text is load-bearing --
    which is why the fallbacks below exist at all.
    """
    if pydantic_code == "validator-field-config-info":
        return BreakClass.VALIDATOR_FIELD_CONFIG
    if pydantic_code == "import-error":
        return BreakClass.REMOVED_INTERNAL

    if error_type is None or message is None:
        return BreakClass.UNKNOWN

    if error_type == "ModuleNotFoundError":
        # The discriminator is ownership: nothing in this repository is wrong, a
        # package it depends on is. A missing module that *is* ours is a
        # different problem and must not be filed here.
        #
        # Without the package list that question cannot be answered, and an
        # empty set would make every module look third-party -- `not in` is
        # vacuously true against nothing. REVIEW.md: "fail closed, not open:
        # when a check cannot be completed, the safe result is refusal".
        if not project_packages:
            return BreakClass.UNKNOWN
        missing = _MISSING_MODULE.search(message)
        if missing is not None and missing["module"].split(".")[0] not in project_packages:
            return BreakClass.TRANSITIVE_DEPENDENCY
        return BreakClass.UNKNOWN

    if error_type == "TypeError" and "__root__" in message and "RootModel" in message:
        return BreakClass.ROOT_MODEL

    if error_type.endswith("PydanticUserError") and "field" in message and "config" in message:
        return BreakClass.VALIDATOR_FIELD_CONFIG

    if error_type.endswith("PydanticImportError") and "has been removed" in message:
        return BreakClass.REMOVED_INTERNAL

    return BreakClass.UNKNOWN


def parse_failures(
    output: str,
    returncode: int,
    project_packages: frozenset[str] = frozenset(),
) -> list[Failure]:
    """Extract structured failures from a pytest run.

    Args:
        output: Everything pytest wrote to stdout and stderr, combined.
        returncode: pytest's exit status. This selects the output layout and is
            trusted over anything found in the text.
        project_packages: Top-level package names the repository owns. Used only
            to tell a repository's own missing module from an unmigrated
            third-party one. Omitting it makes that distinction unavailable, so
            such failures are reported as :attr:`BreakClass.UNKNOWN` rather than
            guessed.

    Returns:
        One :class:`Failure` per distinct error. Empty when the run passed.

    A run that failed but yielded nothing parseable returns a :class:`Failure`
    whose fields are ``None`` rather than an empty list. The caller must be able
    to tell "this suite passed" from "this suite broke in a way I could not
    read", and an empty list would collapse those into one answer.
    """
    shape = RunShape.from_returncode(returncode)
    if shape is RunShape.PASSED:
        return []

    error_type, message = _error(output)
    doc = _DOC_URL.search(output)
    pydantic_code = doc["slug"] if doc is not None else None
    culprit = _culprit(_frames(output))
    symbol_match = _SYMBOL.search(message) if message is not None else None

    return [
        Failure(
            shape=shape,
            break_class=_classify(error_type, message, pydantic_code, project_packages),
            error_type=error_type,
            message=message,
            culprit=culprit,
            pydantic_code=pydantic_code,
            symbol=symbol_match["symbol"] if symbol_match is not None else None,
        )
    ]
