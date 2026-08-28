"""Tests for failure ingestion, driven by recorded output from real repositories.

Every expectation here was read off an actual broken run, not invented. The
files in ``data/`` are that output verbatim, so a change in pydantic's wording
or pytest's layout fails these tests rather than silently degrading the agent.
"""

from __future__ import annotations

import pathlib

import pytest

from bumpsmith.failures import BreakClass, Frame, RunShape, parse_failures

DATA = pathlib.Path(__file__).parent / "data"


def _recorded(name: str) -> str:
    return (DATA / f"{name}-broken.txt").read_text()


def _collection_error(message: str) -> str:
    """A minimal collection error carrying one message, in pytest's own layout.

    Used only where the *message* is the whole subject -- the recorded runs
    cover the layout, and writing a dozen of those to vary one string would be
    recording the parser's input rather than testing the classifier.
    """
    return (
        "==================================== ERRORS ===================================\n"
        "_________________________ ERROR collecting test_app.py ________________________\n"
        "test_app.py:1: in <module>\n"
        "    from app import Basket\n"
        "app.py:7: in Basket\n"
        "    items: broken\n"
        f"E   TypeError: {message}\n"
    )


# --------------------------------------------------------------------------
# Shape dispatch
# --------------------------------------------------------------------------


_COLLECT_BANNER_LINE = "_______ ERROR collecting tests/test_thing.py _______"


@pytest.mark.parametrize(
    ("returncode", "output", "expected"),
    [
        (0, "", RunShape.PASSED),
        (1, "", RunShape.TESTS_FAILED),
        (2, _COLLECT_BANNER_LINE, RunShape.COLLECTION_ERROR),
        (
            4,
            "ImportError while loading conftest '/work/repo/tests/conftest.py'.",
            RunShape.CONFTEST_IMPORT_ERROR,
        ),
        (3, "", RunShape.UNKNOWN),
        (5, "", RunShape.UNKNOWN),
        (99, "", RunShape.UNKNOWN),
    ],
)
def test_return_code_plus_one_marker_selects_the_shape(
    returncode: int, output: str, expected: RunShape
) -> None:
    assert RunShape.detect(returncode, output) is expected


def test_rc2_without_banners_is_an_interruption_not_a_collection_error() -> None:
    """pytest exits 2 for any interrupted session, not only for collection errors.

    A timeout or a Ctrl-C lands here too, and prints nothing like a collection
    failure. Calling it COLLECTION_ERROR would have the parser claim a layout
    that is not present.
    """
    assert RunShape.detect(2, "!!!! KeyboardInterrupt !!!!") is RunShape.INTERRUPTED


def test_rc4_without_the_conftest_header_is_a_usage_error() -> None:
    """rc 4 is pytest's command-line usage error; a broken conftest merely also uses it."""
    assert RunShape.detect(4, "ERROR: file or directory not found: nope/") is RunShape.USAGE_ERROR


@pytest.mark.parametrize(
    ("shape", "expected"),
    [
        (RunShape.TESTS_FAILED, True),
        (RunShape.COLLECTION_ERROR, True),
        (RunShape.CONFTEST_IMPORT_ERROR, True),
        (RunShape.INTERRUPTED, False),
        (RunShape.USAGE_ERROR, False),
        (RunShape.PASSED, False),
        (RunShape.UNKNOWN, False),
    ],
)
def test_only_some_layouts_can_carry_a_migration_break(shape: RunShape, expected: bool) -> None:
    """An interrupted or misinvoked run is a harness problem, not a pydantic break.

    Without this distinction the agent could be asked to write a migration rule
    that fixes a timeout.
    """
    assert shape.is_migration_break is expected


def test_a_passing_run_yields_no_failures() -> None:
    assert parse_failures("", returncode=0) == []


def test_an_unreadable_failure_is_not_silently_empty() -> None:
    """A broken run that yields nothing parseable must still report a failure.

    The caller has to distinguish "the suite passed" from "the suite broke in a
    way I could not read". An empty list would collapse those into one answer,
    and the second one would look like success.
    """
    failures = parse_failures("something went wrong in a way we do not model", returncode=2)

    assert len(failures) == 1
    assert failures[0].break_class is BreakClass.UNKNOWN
    assert failures[0].error_type is None
    assert failures[0].culprit is None


# --------------------------------------------------------------------------
# Fixture A -- conftest import failure. The shape with no summary line.
# --------------------------------------------------------------------------


def test_fixture_a_is_classified_from_the_error_slug() -> None:
    (failure,) = parse_failures(_recorded("A"), returncode=4)

    assert failure.shape is RunShape.CONFTEST_IMPORT_ERROR
    assert failure.break_class is BreakClass.VALIDATOR_FIELD_CONFIG
    assert failure.pydantic_code == "validator-field-config-info"
    assert failure.error_type == "pydantic.errors.PydanticUserError"
    assert str(failure.culprit) == "dbt_cloud/command/command.py:27"


def test_fixture_a_has_no_summary_line_to_key_on() -> None:
    """Pin the trap this parser exists to avoid.

    A conftest import failure prints no summary block. Any implementation that
    looks for one reports zero failures for the most broken repository in the
    set. This test fails loudly if that assumption about the input ever changes.
    """
    recorded = _recorded("A")

    assert "short test summary info" not in recorded
    assert "=== ERRORS ===" not in recorded
    assert parse_failures(recorded, returncode=4) != []


# --------------------------------------------------------------------------
# Fixture B -- the class that emits no error code at all.
# --------------------------------------------------------------------------


def test_fixture_b_is_classified_from_message_text() -> None:
    """``__root__`` raises a bare builtin TypeError with no code and no docs link.

    Classification has to fall back to the English message here. This is the
    only class where that is true, and it is why the fallback branch exists.
    """
    (failure,) = parse_failures(_recorded("B"), returncode=2)

    assert failure.shape is RunShape.COLLECTION_ERROR
    assert failure.break_class is BreakClass.ROOT_MODEL
    assert failure.pydantic_code is None
    assert failure.error_type == "TypeError"
    assert str(failure.culprit) == "emnify/modules/api/models.py:397"


def test_fixture_b_really_carries_no_error_code() -> None:
    """Guard the premise of the test above rather than trusting it."""
    assert "errors.pydantic.dev" not in _recorded("B")


# --------------------------------------------------------------------------
# Fixture F4 -- removed internal, and the traceback that breaks a naive rule.
# --------------------------------------------------------------------------


def test_fixture_f4_extracts_the_removed_symbol() -> None:
    (failure,) = parse_failures(_recorded("F4"), returncode=2)

    assert failure.break_class is BreakClass.REMOVED_INTERNAL
    assert failure.pydantic_code == "import-error"
    assert failure.symbol == "pydantic.utils:DUNDER_ATTRIBUTES"
    assert str(failure.culprit) == "connect/eaas/core/proto.py:10"


def test_f4_culprit_survives_a_leading_stdlib_frame() -> None:
    """The first non-vendored frame is wrong; the last one is right.

    F4's traceback opens inside the standard library's importlib, which is
    neither vendored nor project code. A rule that took the first non-vendored
    frame would blame the interpreter. This pins why the rule reads backwards.
    """
    recorded = _recorded("F4")
    assert "/opt/python/lib/python3.13/importlib/__init__.py:88" in recorded

    (failure,) = parse_failures(recorded, returncode=2)
    assert failure.culprit is not None
    assert "importlib" not in failure.culprit.path


# --------------------------------------------------------------------------
# Class 6 -- ownership, not syntax, is the discriminator.
# --------------------------------------------------------------------------

_TRANSITIVE = """\
ImportError while loading conftest '/work/repo/tests/conftest.py'.
tests/conftest.py:3: in <module>
    import typing_inspect
E   ModuleNotFoundError: No module named 'typing_inspect'
"""


def test_a_third_party_missing_module_is_a_transitive_break() -> None:
    (failure,) = parse_failures(
        _TRANSITIVE, returncode=4, project_packages=frozenset({"myproject"})
    )

    assert failure.break_class is BreakClass.TRANSITIVE_DEPENDENCY


def test_the_projects_own_missing_module_is_not_a_transitive_break() -> None:
    """Same exception, opposite meaning, decided by who owns the module.

    Filing a repository's own broken import as a dependency problem would send
    the agent to edit a manifest when the bug is in the source.
    """
    own = _TRANSITIVE.replace("typing_inspect", "myproject")

    (failure,) = parse_failures(own, returncode=4, project_packages=frozenset({"myproject"}))

    assert failure.break_class is not BreakClass.TRANSITIVE_DEPENDENCY


def test_ownership_is_unknowable_without_the_package_list() -> None:
    """Called without project_packages, the distinction is reported as unknown.

    Defaulting to "third party" would be wrong half the time and confident
    about it. REVIEW.md: fail closed, not open.
    """
    (failure,) = parse_failures(_TRANSITIVE, returncode=4)

    assert failure.break_class is BreakClass.UNKNOWN


# --------------------------------------------------------------------------
# Several errors in one run
# --------------------------------------------------------------------------


# Landmarks for the composition below, quoted from the recordings rather than
# matched with the parser's own regexes. A test that located its input using the
# code under test would agree with that code even when both were wrong.
_B_TRAILER_MARK = "short test summary info"
_F4_BANNER_MARK = "ERROR collecting tests/connect/eaas/core/test_proto.py"


def _line_index(lines: list[str], mark: str, source: str) -> int:
    for index, line in enumerate(lines):
        if mark in line:
            return index
    raise AssertionError(f"recording {source} no longer contains a line matching {mark!r}")


def _two_collection_errors() -> str:
    """Compose one run that fails to collect two modules, from two real captures.

    pytest prints a banner per failing module and one shared trailer. Both
    blocks here are recorded output; only the arrangement is assembled, because
    no single recorded run in the fixture set happens to fail two modules at
    once.

    The seam is cut on line boundaries: B up to its trailer, then F4 from its
    banner onward, so B's trailer and F4's duplicate ERRORS header both fall
    away whole. An earlier version spliced by substring and left ` ====`
    fragments behind that pytest cannot emit, and kept B's mid-run
    `Interrupted:` line. :func:`test_the_composition_manufactures_no_lines`
    pins that neither can come back.
    """
    b_lines = _recorded("B").splitlines(keepends=True)
    f4_lines = _recorded("F4").splitlines(keepends=True)
    b_end = _line_index(b_lines, _B_TRAILER_MARK, "B")
    f4_start = _line_index(f4_lines, _F4_BANNER_MARK, "F4")
    return "".join(b_lines[:b_end] + f4_lines[f4_start:])


def test_the_composition_manufactures_no_lines() -> None:
    """The vault's whole claim is that its contents are verbatim.

    ``data/README.md`` promises nothing was edited -- not the tracebacks, not
    the frame ordering, not the error text. A helper that assembles those
    recordings into a line pytest could never print quietly breaks that promise,
    and the parser would then be pinned against output no run produces.
    """
    recorded = set(_recorded("B").splitlines()) | set(_recorded("F4").splitlines())
    manufactured = sorted(
        {line for line in _two_collection_errors().splitlines() if line not in recorded}
    )

    assert manufactured == []


def test_the_composition_keeps_one_shared_trailer() -> None:
    """Two banners, and the trailer belongs to the run rather than to a block."""
    composed = _two_collection_errors()

    assert composed.count("ERROR collecting") == 2
    assert composed.count(_B_TRAILER_MARK) == 1
    assert "Interrupted:" in composed.split(_B_TRAILER_MARK)[1]


def test_every_collection_error_is_reported() -> None:
    """REVIEW.md: partial failure in a batch must be reported per item.

    Returning only the first error would hide every break after it, and the
    agent would write a rule for one class while the repository carries two.
    """
    failures = parse_failures(_two_collection_errors(), returncode=2)

    assert len(failures) == 2
    assert {f.break_class for f in failures} == {BreakClass.ROOT_MODEL, BreakClass.REMOVED_INTERNAL}


def test_each_error_keeps_its_own_culprit_and_code() -> None:
    """Blocks must not inherit each other's docs link or traceback.

    The __root__ break emits no error code at all. If block boundaries leaked,
    it would pick up the import-error slug from the block below it and be
    misclassified with total confidence.
    """
    by_class = {f.break_class: f for f in parse_failures(_two_collection_errors(), returncode=2)}

    root = by_class[BreakClass.ROOT_MODEL]
    removed = by_class[BreakClass.REMOVED_INTERNAL]

    assert root.pydantic_code is None
    assert str(root.culprit) == "emnify/modules/api/models.py:397"

    assert removed.pydantic_code == "import-error"
    assert str(removed.culprit) == "connect/eaas/core/proto.py:10"


# --------------------------------------------------------------------------
# Class 3 -- one break, two signatures, only one of them carrying a slug.
# --------------------------------------------------------------------------


def test_a_field_regex_break_is_classified_from_its_slug() -> None:
    (failure,) = parse_failures(_recorded("field-regex"), returncode=2)

    assert failure.break_class is BreakClass.REGEX_KEYWORD
    assert failure.pydantic_code == "removed-kwargs"
    assert str(failure.culprit) == "mypkg/__init__.py:5"


def test_a_constr_regex_break_arrives_with_no_slug_at_all() -> None:
    """`constr(regex=...)` never reaches pydantic's error machinery.

    Python rejects the keyword while binding the call, so there is no code and no
    docs link -- the same situation as `__root__`, reached a different way.
    """
    (failure,) = parse_failures(
        _recorded("B-regex"), returncode=2, project_packages=frozenset({"emnify"})
    )

    assert failure.break_class is BreakClass.REGEX_KEYWORD
    assert failure.pydantic_code is None
    assert failure.error_type == "TypeError"


def test_the_culprit_is_the_project_line_not_the_standard_library() -> None:
    """A uv-managed interpreter keeps CPython outside any `site-packages`.

    The deepest frame in this traceback is `typing.py`, reached through an
    annotation pydantic was evaluating. Testing only for `site-packages` made the
    standard library read as project code, and the answer to "where is the break"
    came back as a line in `typing.py`.
    """
    recorded = _recorded("B-regex")
    assert "/lib/python3.13/typing.py" in recorded, "the recording no longer has a stdlib frame"

    (failure,) = parse_failures(recorded, returncode=2, project_packages=frozenset({"emnify"}))

    assert str(failure.culprit) == "emnify/modules/api/models.py:640"


def test_the_same_keyword_from_something_that_is_not_pydantic_is_not_this_class() -> None:
    """The phrase is generic; the callable is not.

    Any function in any library can be handed an unexpected `regex` argument, and
    filing those here would be a confident answer to a question nobody asked.
    """
    mutated = _recorded("B-regex").replace("constr()", "some_other_helper()")

    (failure,) = parse_failures(mutated, returncode=2, project_packages=frozenset({"emnify"}))

    assert failure.break_class is BreakClass.UNKNOWN


def test_another_removed_keyword_sharing_the_slug_is_not_this_class() -> None:
    """`removed-kwargs` does not identify one break.

    `const` and `unique_items` were removed too and raise it with the same code.
    Filing those here would write a regex rule, find whatever `regex=` sites
    happen to exist, rewrite them, and leave the argument that actually stopped
    collection exactly where it was.
    """
    mutated = _recorded("field-regex").replace(
        "`regex` is removed. use `pattern` instead",
        "`const` is removed, use `Literal` instead",
    )

    (failure,) = parse_failures(mutated, returncode=2)

    assert failure.pydantic_code == "removed-kwargs"
    assert failure.break_class is not BreakClass.REGEX_KEYWORD


def test_a_project_directory_shaped_like_an_interpreter_is_still_the_project() -> None:
    """A project may hold its own `lib/python3.13/` directory.

    pytest prints project files relative to rootdir, so the discriminator is not
    the substring but whether the run had to leave the project to reach the file.
    """
    assert not Frame(path="lib/python3.13/thing.py", line=1).is_foreign
    assert not Frame(path="src/lib/python3.13/thing.py", line=1).is_foreign

    assert Frame(path="/opt/python/lib/python3.13/typing.py", line=1).is_foreign
    assert Frame(path="../../../uv/python/x/lib/python3.13/typing.py", line=1).is_foreign
    assert Frame(path="../../.venv/lib/python3.13/site-packages/pydantic/x.py", line=1).is_foreign


# --------------------------------------------------------------------------
# Class 7 -- one keyword, broken in one callable and merely deprecated in another
# --------------------------------------------------------------------------


def test_a_conlist_items_break_arrives_with_no_slug() -> None:
    """`conlist(min_items=...)` is rejected while binding the call, like `constr`.

    Recorded from a real pytest run rather than written here, because the shape
    the parser has to survive -- the caret line under the annotation, the
    truncated `short test summary` echo -- is not something worth inventing.
    """
    (failure,) = parse_failures(_recorded("conlist-items"), returncode=2)

    assert failure.break_class is BreakClass.ITEMS_KEYWORD
    assert failure.pydantic_code is None
    assert failure.error_type == "TypeError"
    assert str(failure.culprit) == "app.py:7"


@pytest.mark.parametrize(
    "message",
    [
        "conlist() got an unexpected keyword argument 'min_items'",
        "conlist() got an unexpected keyword argument 'max_items'",
        "conset() got an unexpected keyword argument 'min_items'",
        "confrozenset() got an unexpected keyword argument 'max_items'",
    ],
)
def test_every_constrained_collection_constructor_is_recognised(message: str) -> None:
    output = _collection_error(message)

    (failure,) = parse_failures(output, returncode=2)
    assert failure.break_class is BreakClass.ITEMS_KEYWORD


@pytest.mark.parametrize(
    ("message", "why"),
    [
        (
            "conint() got an unexpected keyword argument 'min_items'",
            "conint never took min_items, so this is somebody else's TypeError",
        ),
        (
            "shopping_list() got an unexpected keyword argument 'min_items'",
            "a project function may be called anything, including something ending in list",
        ),
        (
            "conlist() got an unexpected keyword argument 'unique_items'",
            "unique_items was removed rather than renamed; there is no length to rewrite it to",
        ),
    ],
)
def test_a_lookalike_typeerror_is_not_this_break(message: str, why: str) -> None:
    """The keyword alone is not the signal, and neither is the word `list`."""
    (failure,) = parse_failures(_collection_error(message), returncode=2)

    assert failure.break_class is BreakClass.UNKNOWN, why
