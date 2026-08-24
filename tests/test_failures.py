"""Tests for failure ingestion, driven by recorded output from real repositories.

Every expectation here was read off an actual broken run, not invented. The
files in ``data/`` are that output verbatim, so a change in pydantic's wording
or pytest's layout fails these tests rather than silently degrading the agent.
"""

from __future__ import annotations

import pathlib

import pytest

from bumpsmith.failures import BreakClass, RunShape, parse_failures

DATA = pathlib.Path(__file__).parent / "data"


def _recorded(name: str) -> str:
    return (DATA / f"{name}-broken.txt").read_text()


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


def _two_collection_errors() -> str:
    """Compose one run that fails to collect two modules, from two real captures.

    pytest prints a banner per failing module and one shared trailer. Both
    blocks here are recorded output; only the arrangement is assembled, because
    no single recorded run in the fixture set happens to fail two modules at
    once.
    """
    b = _recorded("B")
    f4 = _recorded("F4")
    head, _, tail = f4.partition("=============================== warnings summary")
    return b.replace("=========================== short test summary info", "") + head + tail


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
