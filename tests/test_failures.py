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


@pytest.mark.parametrize(
    ("returncode", "expected"),
    [
        (0, RunShape.PASSED),
        (1, RunShape.TESTS_FAILED),
        (2, RunShape.COLLECTION_ERROR),
        (4, RunShape.CONFTEST_IMPORT_ERROR),
        (3, RunShape.UNKNOWN),
        (5, RunShape.UNKNOWN),
        (99, RunShape.UNKNOWN),
    ],
)
def test_return_code_selects_the_shape(returncode: int, expected: RunShape) -> None:
    assert RunShape.from_returncode(returncode) is expected


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
