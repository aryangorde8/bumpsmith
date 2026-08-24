"""Tests for rule derivation and matching.

The tests that matter most here are the ones that assert a rule does *not*
match. A migration rule that fires on everything named `validator` would look
productive and would corrupt any library that happens to define one.
"""

import textwrap
from pathlib import Path

import pytest

from bumpsmith.failures import BreakClass, Failure, RunShape, parse_failures
from bumpsmith.rules import Rule, RuleKind, find_matches, write_rule

DATA = Path(__file__).parent / "data"


def _failure(
    break_class: BreakClass, *, symbol: str | None = None, message: str | None = None
) -> Failure:
    return Failure(
        shape=RunShape.COLLECTION_ERROR,
        break_class=break_class,
        error_type=None,
        message=message,
        culprit=None,
        symbol=symbol,
    )


def _rule(break_class: BreakClass, *, symbol: str | None = None) -> Rule:
    rule = write_rule(_failure(break_class, symbol=symbol))
    assert rule is not None, f"expected a rule for {break_class}"
    return rule


def _tree(root: Path, files: dict[str, str]) -> Path:
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source).lstrip())
    return root


# --------------------------------------------------------------------------
# Not matching: the part that makes this a rule rather than a replace
# --------------------------------------------------------------------------


def test_a_validator_that_is_not_pydantics_is_left_alone(tmp_path: Path) -> None:
    """A library may define its own decorator called `validator`.

    One of the candidate fixtures does exactly that, and a textual rewrite of
    `@validator` would destroy it. The tree knows the name came from elsewhere.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from mylib.decorators import validator

            class Survey:
                @validator("topics")
                def check(cls, value, field, config):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 0


def test_a_relative_import_is_not_pydantic(tmp_path: Path) -> None:
    """`from .utils import validator` is the project's own, whatever it is called."""
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from .utils import validator

            class Model:
                @validator("x")
                def check(cls, value, config):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 0


def test_a_validator_taking_neither_field_nor_config_is_not_this_break(tmp_path: Path) -> None:
    """v2 kept `@validator`. It removed two of its parameters."""
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic import validator

            class Model:
                @validator("x")
                def check(cls, value):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 0


def test_a_removed_symbol_from_another_package_is_left_alone(tmp_path: Path) -> None:
    """The name is not the break. Where it came from is."""
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from mylib.utils import DUNDER_ATTRIBUTES
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    assert find_matches(rule, root).count == 0


def test_a_module_level_root_dunder_is_not_a_field(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"mine.py": "__root__ = 'not a model field'\n"})

    assert find_matches(_rule(BreakClass.ROOT_MODEL), root).count == 0


def test_a_function_local_pydantic_import_does_not_capture_a_module_level_name(
    tmp_path: Path,
) -> None:
    """An import inside a function binds a local nothing outside it can see.

    Collecting it let an unrelated import three functions down overrule the
    module-level `from mylib.decorators import validator`, and the decorator was
    matched as pydantic's.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from mylib.decorators import validator

            class Survey:
                @validator("topics")
                def check(cls, value, field, config):
                    return value

            def helper():
                from pydantic import validator
                return validator
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 0


def test_a_pydantic_import_wrapped_in_try_except_still_counts(tmp_path: Path) -> None:
    """The fix for function-local imports must not throw these away too.

    A pydantic import guarded by try/except ImportError, or by TYPE_CHECKING, is
    still a module-level binding, and both wrappings are common.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            try:
                from pydantic import validator
            except ImportError:
                validator = None

            class Model:
                @validator("x")
                def check(cls, value, field):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 1


def test_the_v1_compatibility_namespace_is_not_this_break(tmp_path: Path) -> None:
    """`pydantic.v1` is v2's bundled copy of the old API.

    Code importing from it kept v1 behaviour on purpose, so the v2 signature
    change does not apply. Counting it would inflate the number with sites that
    are not broken.
    """
    root = _tree(
        tmp_path,
        {
            "from_import.py": """
            from pydantic.v1 import validator

            class Legacy:
                @validator("x")
                def check(cls, value, field):
                    return value
            """,
            "module_import.py": """
            import pydantic.v1 as pv1

            class AlsoLegacy:
                @pv1.validator("x")
                def check(cls, value, config):
                    return value
            """,
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 0


def test_vendored_directories_are_not_scanned(tmp_path: Path) -> None:
    """Installed packages are not this project's code to change."""
    root = _tree(
        tmp_path,
        {
            ".venv/lib/site-packages/other/models.py": """
            class Wrapped:
                __root__ = None
            """,
            "__pycache__/cached.py": """
            class Cached:
                __root__ = None
            """,
        },
    )

    assert find_matches(_rule(BreakClass.ROOT_MODEL), root).count == 0


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


def test_an_aliased_pydantic_import_still_matches(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic import validator as check

            class Model:
                @check("x")
                def rule(cls, value, field):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 1


def test_a_module_qualified_validator_matches(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            import pydantic as pd

            class Model:
                @pd.validator("x")
                def rule(cls, value, config):
                    return value
            """
        },
    )

    assert find_matches(_rule(BreakClass.VALIDATOR_FIELD_CONFIG), root).count == 1


def test_root_fields_match_annotated_and_plain(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "annotated.py": """
            from pydantic import BaseModel

            class Listing(BaseModel):
                __root__: list[str]
            """,
            "plain.py": """
            from pydantic import BaseModel

            class Mapping(BaseModel):
                __root__ = {}
            """,
        },
    )

    assert find_matches(_rule(BreakClass.ROOT_MODEL), root).count == 2


def test_one_failure_can_imply_many_sites(tmp_path: Path) -> None:
    """The reason bumpsmith emits a rule instead of a patch.

    pytest reports the first module that failed to import. The rule that failure
    implies is true of every module in the repository.
    """
    root = _tree(
        tmp_path,
        {
            "one.py": """
            from pydantic import BaseModel

            class A(BaseModel):
                __root__: list[str]
            """,
            "pkg/two.py": """
            from pydantic import BaseModel

            class B(BaseModel):
                __root__: dict[str, str]

            class C(BaseModel):
                __root__: int
            """,
        },
    )

    result = find_matches(_rule(BreakClass.ROOT_MODEL), root)

    assert result.count == 3
    assert {match.path.name for match in result.matches} == {"one.py", "two.py"}


def test_matches_come_back_in_a_stable_order(tmp_path: Path) -> None:
    """ast.walk is documented to yield in no specified order.

    The list is read in a pull request diff, so two runs over the same tree have
    to produce the same order or the diff is noise.
    """
    root = _tree(
        tmp_path,
        {
            "b.py": """
            from pydantic import BaseModel

            class Second(BaseModel):
                __root__: int

            class First(BaseModel):
                __root__: str
            """,
            "a.py": """
            from pydantic import BaseModel

            class Only(BaseModel):
                __root__: bytes
            """,
        },
    )

    matches = find_matches(_rule(BreakClass.ROOT_MODEL), root).matches

    ordered = sorted(matches, key=lambda match: (match.path.as_posix(), match.line))
    assert list(matches) == ordered
    assert [match.path.name for match in matches] == ["a.py", "b.py", "b.py"]


def test_a_source_with_a_coding_cookie_is_read_not_written_off(tmp_path: Path) -> None:
    """PEP 263 says a Python file may declare its own encoding.

    Forcing UTF-8 marked such a file unreadable, which undercounted the matches
    and reported the scan incomplete for a file Python itself parses fine.
    """
    tmp_path.joinpath("latin.py").write_bytes(
        "# -*- coding: latin-1 -*-\n"
        "from pydantic import BaseModel\n\n"
        "NOTE = 'caf\xe9'\n\n"
        "class Model(BaseModel):\n"
        "    __root__: int\n".encode("latin-1")
    )

    result = find_matches(_rule(BreakClass.ROOT_MODEL), tmp_path)

    assert result.count == 1
    assert result.is_complete


def test_a_match_carries_the_line_and_the_source(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    match = find_matches(rule, root).matches[0]

    assert match.line == 1
    assert match.excerpt == "from pydantic.utils import DUNDER_ATTRIBUTES"


# --------------------------------------------------------------------------
# Rules that are not source rules
# --------------------------------------------------------------------------


def test_a_dependency_rule_matches_nothing_and_that_is_the_answer(tmp_path: Path) -> None:
    """No edit in this repository fixes an unmigrated dependency.

    Zero here is a finding, not a gap, so the scan is still complete.
    """
    root = _tree(tmp_path, {"mine.py": "import something\n"})
    rule = write_rule(_failure(BreakClass.TRANSITIVE_DEPENDENCY, message="No module named 'x'"))
    assert rule is not None

    result = find_matches(rule, root)

    assert rule.kind is RuleKind.DEPENDENCY
    assert result.count == 0
    assert result.is_complete


def test_the_dependency_rule_repeats_what_pytest_said() -> None:
    rule = write_rule(
        _failure(BreakClass.TRANSITIVE_DEPENDENCY, message="No module named 'dj_rql'")
    )
    assert rule is not None
    assert "dj_rql" in rule.rationale


# --------------------------------------------------------------------------
# Refusing to write a rule
# --------------------------------------------------------------------------


def test_an_unclassified_failure_produces_no_rule() -> None:
    """A rule that names the wrong transformation is worse than no rule."""
    assert write_rule(_failure(BreakClass.UNKNOWN)) is None


def test_a_removed_import_without_a_symbol_produces_no_rule() -> None:
    """Nothing to search for, so nothing to promise."""
    assert write_rule(_failure(BreakClass.REMOVED_INTERNAL, symbol=None)) is None


@pytest.mark.parametrize("symbol", ["pydantic.utils", ":DUNDER", "pydantic:", ""])
def test_a_malformed_symbol_produces_no_rule(symbol: str) -> None:
    assert write_rule(_failure(BreakClass.REMOVED_INTERNAL, symbol=symbol)) is None


# --------------------------------------------------------------------------
# Reading failures
# --------------------------------------------------------------------------


def test_a_file_that_does_not_parse_is_reported_not_skipped(tmp_path: Path) -> None:
    """A count that quietly excludes what it choked on looks complete and is not."""
    root = _tree(
        tmp_path,
        {
            "broken.py": "class Nope(\n",
            "fine.py": """
            from pydantic import BaseModel

            class Model(BaseModel):
                __root__: int
            """,
        },
    )

    result = find_matches(_rule(BreakClass.ROOT_MODEL), root)

    assert result.count == 1
    assert not result.is_complete
    assert [item.path.name for item in result.unreadable] == ["broken.py"]
    assert "could not parse" in result.unreadable[0].reason


# --------------------------------------------------------------------------
# End to end, from the recorded runs
# --------------------------------------------------------------------------


def _only_failure(name: str) -> Failure:
    output = (DATA / f"{name}-broken.txt").read_text()
    failures = parse_failures(
        output,
        returncode=2,
        project_packages=frozenset({"dbt_cloud", "emnify", "connect"}),
    )
    assert len(failures) == 1
    return failures[0]


@pytest.mark.parametrize(
    ("name", "break_class"),
    [
        ("A", BreakClass.VALIDATOR_FIELD_CONFIG),
        ("B", BreakClass.ROOT_MODEL),
        ("F4", BreakClass.REMOVED_INTERNAL),
    ],
)
def test_every_recorded_failure_yields_a_source_rule(name: str, break_class: BreakClass) -> None:
    rule = write_rule(_only_failure(name))

    assert rule is not None
    assert rule.break_class is break_class
    assert rule.kind is RuleKind.SOURCE


def test_the_removed_import_rule_carries_the_symbol_from_the_recording() -> None:
    """F4's symbol is read out of pydantic's own message, not guessed."""
    rule = write_rule(_only_failure("F4"))

    assert rule is not None
    assert rule.module == "pydantic.utils"
    assert rule.name == "DUNDER_ATTRIBUTES"
