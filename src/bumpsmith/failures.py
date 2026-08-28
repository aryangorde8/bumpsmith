"""Turn a failing pytest run into structured facts about *why* it failed.

The agent needs to know which pydantic v1-to-v2 break it is looking at before it
can decide what to write. That decision is made here, from the text pytest
prints, because in the cases that matter most pytest produces no machine-readable
output at all.

Two things drive the design, both measured rather than assumed.

**Let the return code narrow it before the text does.** pytest emits several
materially different layouts depending on how far it got. The return code is
available before any parsing and cannot be confused by message content, which
makes it the right *first* question -- but it is not sufficient on its own, and
saying otherwise here would contradict :class:`RunShape` sixty lines below. A
collection failure and a Ctrl-C both exit 2; a conftest that will not import and
a misinvoked pytest both exit 4. So the code narrows each to two candidates and
one marker in the text picks between them, which means no pattern ever has to be
right about the layout *and* the content at once. Anything unrecognised is
``UNKNOWN`` rather than guessed.

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

_ITEMS_CALL = re.compile(r"\bcon(?:list|set|frozenset)\(\)")
r"""The constrained-collection constructors, as they name themselves in a TypeError.

Written out rather than matched as `con\w+`, which would also catch `conint`
and `condecimal`. Those never took `min_items`, so a site reported in one of
them would be a rewrite of code that was never broken.
"""

# "____________ ERROR collecting tests/test_thing.py ____________" -- pytest
# prints one of these per test module that failed to import.
_COLLECT_BANNER = re.compile(r"^_+ ERROR collecting (?P<target>.+?) _+$", re.MULTILINE)

# A conftest that fails to import stops the session before collection begins.
_CONFTEST_HEADER = "ImportError while loading conftest"

# Trailing sections that belong to the run as a whole, not to the last error.
# Text after these must not be attributed to the error block above them.
_TRAILER = re.compile(
    r"^(?:=+ (?:warnings summary|short test summary info)|!+ Interrupted:)", re.MULTILINE
)

# Anything under an installed-packages directory is the library's own stack, and
# anything under an interpreter's own `lib/pythonX.Y` is the standard library's.
# Neither is code this project can edit.
_VENDORED = "site-packages"
_STDLIB = re.compile(r"/lib/python\d+\.\d+/")


class RunShape(Enum):
    """Which output layout pytest produced.

    The return code is the primary signal because it is available before any
    parsing and cannot be confused by message content. It is not, however,
    sufficient on its own: pytest documents exit code 2 as *interrupted* and
    exit code 4 as *usage error*, and the layouts this parser cares about are
    only two of the things each can mean. A collection failure and a Ctrl-C
    both exit 2, and they print nothing alike.

    So the code narrows the possibilities and one marker in the text picks
    between them. Anything unrecognised is :attr:`UNKNOWN` rather than guessed,
    because a wrong layout produces confidently wrong parsing.
    """

    PASSED = "passed"
    """rc 0 -- nothing to extract."""

    TESTS_FAILED = "tests-failed"
    """rc 1 -- the suite ran. Per-test detail lives in JUnit XML, not in this text."""

    COLLECTION_ERROR = "collection-error"
    """rc 2 with collection banners -- test modules failed to import. One block each."""

    INTERRUPTED = "interrupted"
    """rc 2 without banners -- the session was aborted. Not a migration break."""

    CONFTEST_IMPORT_ERROR = "conftest-import-error"
    """rc 4 with the conftest header -- bare traceback, no banners, no summary."""

    USAGE_ERROR = "usage-error"
    """rc 4 without it -- pytest was invoked wrongly. A harness bug, not a break."""

    UNKNOWN = "unknown"

    @classmethod
    def detect(cls, returncode: int, output: str) -> RunShape:
        """Identify the layout from the return code, disambiguated by the text.

        Args:
            returncode: pytest's exit status.
            output: the combined stdout and stderr of the same run.
        """
        if returncode == 0:
            return cls.PASSED
        if returncode == 1:
            return cls.TESTS_FAILED
        if returncode == 2:
            # Collection errors are reported as an interrupted session, so the
            # banner is what separates them from a real interruption.
            if _COLLECT_BANNER.search(output):
                return cls.COLLECTION_ERROR
            return cls.INTERRUPTED
        if returncode == 4:
            if _CONFTEST_HEADER in output:
                return cls.CONFTEST_IMPORT_ERROR
            return cls.USAGE_ERROR
        return cls.UNKNOWN

    @property
    def is_migration_break(self) -> bool:
        """Whether this layout can carry a pydantic break at all.

        An interrupted session and a misinvoked pytest are problems with the
        harness, not with the code under migration. Treating them as breaks
        would have the agent write a rule to fix a timeout.
        """
        return self in {
            RunShape.TESTS_FAILED,
            RunShape.COLLECTION_ERROR,
            RunShape.CONFTEST_IMPORT_ERROR,
        }


class BreakClass(Enum):
    """Which pydantic v1-to-v2 break this is.

    Numbering follows the project's six-class taxonomy. Class 2 -- a field V1
    made optional by implication and V2 requires -- is the one member missing
    here, and it is missing for a weaker reason than it used to be. It now has a
    recorded sample: peel classes 4, 3 and 1 off fixture B and the run turns from
    a collection error into five failing tests, every one of them a
    ``ValidationError`` for a field nobody declared a default for. What it does
    not have is a classifier, because that signature is a ``ValidationError``
    like any other and telling "V1 would have defaulted this" from "this input
    really is missing a field" is not something the traceback text settles.

    A pattern authored against an unobserved signature would misfile real
    failures while looking like coverage; a pattern authored against an
    ambiguous one would do the same more quietly. Both are reasons to leave the
    member out rather than to define it and guess.
    """

    VALIDATOR_FIELD_CONFIG = 1
    """``@validator`` taking ``field`` or ``config``, which V2 accepts neither of.

    The error text says to use ``info`` instead. Under the ``@validator`` shim
    that is wrong -- ``info`` belongs to V2's ``@field_validator`` and the shim
    refuses it -- so the migration is to remove both parameters and leave
    ``values``, which still works. ``proofs/validator.py`` is the run that
    settles this against a real pydantic.
    """

    REGEX_KEYWORD = 3
    """A ``regex=`` argument, which V2 renamed to ``pattern=``.

    Two signatures reach here and only one carries pydantic's slug. ``Field``
    raises ``PydanticUserError`` with ``removed-kwargs``; ``constr`` raises a
    plain builtin ``TypeError`` from Python's own argument binding, before
    pydantic sees the call at all. Both are recorded samples.
    """

    ROOT_MODEL = 4
    """A field named ``__root__``, which V2 replaced with ``pydantic.RootModel``."""

    ITEMS_KEYWORD = 7
    """``min_items=``/``max_items=``, which V2 renamed to ``min_length=``/``max_length=``.

    Only the constrained-collection constructors raise. ``Field`` accepts both
    spellings in V2 and emits a deprecation warning instead, so a rule matching
    the keyword alone would report sites that are not broken and rewrite code
    that runs today -- the same distinction :attr:`REGEX_KEYWORD` draws, in the
    other direction: there ``Field`` raises and here it does not.
    """

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
    def is_foreign(self) -> bool:
        """True when this frame is somebody else's code rather than the project's.

        Two kinds of somebody else: installed packages under `site-packages`, and
        the standard library under an interpreter's own `lib/pythonX.Y` *that the
        run had to leave the project to reach*. Testing for the first alone was
        enough until a uv-managed interpreter turned up.
        uv keeps CPython under `~/.local/share/uv/python/cpython-.../lib/python3.13/`,
        which contains no `site-packages`, so `typing.py` read as project code --
        and a tool whose job is to say where the break is would have answered
        with a line in the standard library.
        """
        if _VENDORED in self.path:
            return True
        # A stdlib-shaped substring is not proof of an interpreter root: a project
        # holding its own `lib/python3.13/` directory reads the same. pytest
        # prints project files relative to rootdir, so anything that has to climb
        # out or start from the root is by definition not in the project.
        return _STDLIB.search(self.path) is not None and self.path.startswith(("/", "../"))

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
    """The last frame that is the project's own code.

    Tracebacks read outermost-first, so the project's own code sits between the
    entry point above it and the library that actually raised below it. Taking
    the *last* frame the project owns therefore lands on the deepest line it can
    edit, which is the line to report.

    This relies on the project's frames all preceding the library's. That holds
    whenever a library raises during import or construction, which is every case
    in the fixture set -- including the one whose traceback opens inside the
    standard library's ``importlib``. It would not hold for a callback invoked by
    a library, where project code appears below vendored code; such a failure
    would report the callback, which is still a defensible answer.
    """
    for frame in reversed(frames):
        if not frame.is_foreign:
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


def _blocks(output: str, shape: RunShape) -> list[str]:
    """Split a run's output into one section per distinct error.

    Only the collection-error layout is genuinely multi-error: pytest prints a
    banner per test module that failed to import, and each carries its own
    traceback and its own exception. A conftest failure stops the session before
    collection, so it is one error by construction.

    The rc 1 layout is also multi-error, but its per-test detail belongs in
    JUnit XML rather than in scraped text, so it is not split here. Returning
    the whole output as one block means a caller gets the first failure rather
    than a wrong one.
    """
    if shape is not RunShape.COLLECTION_ERROR:
        return [output]

    banners = list(_COLLECT_BANNER.finditer(output))
    if not banners:
        return [output]

    # Trailing sections describe the run, not the last error. Attributing them
    # to the final block would let one error inherit another's docs link.
    trailer = _TRAILER.search(output, banners[-1].end())
    stop = trailer.start() if trailer is not None else len(output)

    bounds = [m.start() for m in banners] + [stop]
    return [output[bounds[i] : bounds[i + 1]] for i in range(len(banners))]


def _classify(
    error_type: str | None,
    message: str | None,
    pydantic_code: str | None,
    project_packages: frozenset[str],
) -> BreakClass:
    """Decide which break this is, preferring pydantic's own error slug.

    The slug is authoritative when present. It is absent for two signatures, and
    for the same underlying reason: the failure happens before pydantic can
    attach one. A ``__root__`` field raises a plain builtin ``TypeError`` from
    pydantic's namespace inspection, and ``constr(regex=...)`` raises one from
    Python's argument binding. For those two, and only those two, the English
    message text is load-bearing -- which is why the fallbacks below exist.
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

    # `constr(regex=...)` fails in Python's argument binding, so pydantic never
    # gets to attach a slug. Narrowed to the one callable that ever took `regex`
    # rather than to the phrase alone, which any function in any library can
    # produce.
    if error_type == "TypeError" and "constr()" in message and "'regex'" in message:
        return BreakClass.REGEX_KEYWORD

    # The same failure mode one constructor over: Python rejects the keyword
    # while binding the arguments, so there is no slug to key on. `Field` is
    # deliberately absent -- it still accepts `min_items` in V2 and only warns,
    # so a message-only match would classify a run that never broke here.
    if (
        error_type == "TypeError"
        and _ITEMS_CALL.search(message) is not None
        and ("'min_items'" in message or "'max_items'" in message)
    ):
        return BreakClass.ITEMS_KEYWORD

    # `removed-kwargs` is the one slug in the set that does not identify a single
    # break: `const` and `unique_items` were removed too and raise it with the
    # same code. Filing those here would write a regex rule, find whatever
    # `regex=` sites happen to exist, and rewrite them -- leaving the argument
    # that actually stopped collection exactly where it was.
    if pydantic_code == "removed-kwargs" and "regex" in message:
        return BreakClass.REGEX_KEYWORD

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

        The collection-error layout genuinely carries several: pytest prints a
        banner per test module that failed to import, and each is parsed
        separately. REVIEW.md requires that partial failure be reported per
        item, and collapsing them would hide every break after the first.

    A run that failed but yielded nothing parseable returns a :class:`Failure`
    whose fields are ``None`` rather than an empty list. The caller must be able
    to tell "this suite passed" from "this suite broke in a way I could not
    read", and an empty list would collapse those into one answer.
    """
    shape = RunShape.detect(returncode, output)
    if shape is RunShape.PASSED:
        return []

    return [_failure_from(block, shape, project_packages) for block in _blocks(output, shape)]


def _failure_from(block: str, shape: RunShape, project_packages: frozenset[str]) -> Failure:
    """Build one :class:`Failure` from a single error's section of the output."""
    error_type, message = _error(block)
    doc = _DOC_URL.search(block)
    symbol_match = _SYMBOL.search(message) if message is not None else None

    return Failure(
        shape=shape,
        break_class=_classify(error_type, message, doc["slug"] if doc else None, project_packages),
        error_type=error_type,
        message=message,
        culprit=_culprit(_frames(block)),
        pydantic_code=doc["slug"] if doc else None,
        symbol=symbol_match["symbol"] if symbol_match is not None else None,
    )
