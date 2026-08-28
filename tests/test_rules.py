"""Tests for rule derivation and matching.

The tests that matter most here are the ones that assert a rule does *not*
match. A migration rule that fires on everything named `validator` would look
productive and would corrupt any library that happens to define one.
"""

import ast
import textwrap
from pathlib import Path

import pytest

from bumpsmith.failures import BreakClass, Failure, RunShape, parse_failures
from bumpsmith.rules import (
    Role,
    Rule,
    RuleKind,
    find_matches,
    items_keyword_sites,
    regex_keyword_sites,
    validator_parameter_sites,
    write_rule,
)

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


# --------------------------------------------------------------------------
# Class 3 -- the `regex=` keyword.
# --------------------------------------------------------------------------


_REGEX_FAILURE = Failure(
    shape=RunShape.COLLECTION_ERROR,
    break_class=BreakClass.REGEX_KEYWORD,
    error_type="TypeError",
    message="constr() got an unexpected keyword argument 'regex'",
    culprit=None,
)


def test_a_regex_failure_becomes_a_rename_rule() -> None:
    rule = write_rule(_REGEX_FAILURE)

    assert rule is not None
    assert rule.kind is RuleKind.SOURCE
    assert "pattern" in rule.summary


def test_both_pydantic_callables_that_took_regex_are_found(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(
        "from pydantic import BaseModel, Field, constr\n"
        "\n"
        "\n"
        "class Account(BaseModel):\n"
        '    sort_code: str = Field(..., regex=r"^\\d+$")\n'
        '    branch: constr(regex=r"^\\w+$") = "x"\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    scan = find_matches(rule, tmp_path)

    assert scan.count == 2
    assert [m.line for m in scan.matches] == [5, 6]


def test_a_regex_argument_to_something_else_is_not_a_site(tmp_path: Path) -> None:
    """`constr` is an ordinary identifier until an import says otherwise.

    This is the same discipline as the validator rule: whether a name is
    pydantic's depends on what the module imported, never on how it is spelled.
    """
    (tmp_path / "models.py").write_text(
        "from mylib.helpers import constr, Field\n"
        "\n"
        "\n"
        'x = constr(regex=r"^\\d+$")\n'
        'y = Field(regex=r"^\\d+$")\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    assert find_matches(rule, tmp_path).count == 0


def test_an_aliased_constr_is_still_found(tmp_path: Path) -> None:
    (tmp_path / "models.py").write_text(
        'from pydantic import constr as constrained\n\n\nx = constrained(regex=r"^\\d+$")\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    assert find_matches(rule, tmp_path).count == 1


def test_a_parameter_shadowing_a_pydantic_name_is_not_a_site(tmp_path: Path) -> None:
    """The dangerous direction of getting scope wrong.

    One module-wide import map applied to the whole tree says this `constr` is
    pydantic's. It is a parameter, and rewriting the call would change code that
    has nothing to do with pydantic.
    """
    (tmp_path / "models.py").write_text(
        'from pydantic import constr\n\n\ndef build(constr):\n    return constr(regex=r"^a$")\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    assert find_matches(rule, tmp_path).count == 0


def test_a_pydantic_import_made_inside_a_function_is_a_site(tmp_path: Path) -> None:
    """The other direction, which the same mistake caused."""
    (tmp_path / "models.py").write_text(
        'def build():\n    from pydantic import constr\n    return constr(regex=r"^a$")\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    scan = find_matches(rule, tmp_path)
    assert scan.count == 1
    assert scan.matches[0].line == 3


def test_a_name_shadowed_only_inside_a_function_still_matches_outside_it(
    tmp_path: Path,
) -> None:
    """Shadowing is scoped, so refusing the whole file would be its own bug."""
    (tmp_path / "models.py").write_text(
        "from pydantic import constr\n"
        "\n"
        'OUTSIDE = constr(regex=r"^a$")\n'
        "\n"
        "\n"
        "def build(constr):\n"
        '    return constr(regex=r"^b$")\n'
    )
    rule = write_rule(_REGEX_FAILURE)
    assert rule is not None

    scan = find_matches(rule, tmp_path)
    assert [m.line for m in scan.matches] == [3]


# --------------------------------------------------------------------------
# A removed internal that is still used
#
# `pydantic.utils:DUNDER_ATTRIBUTES` is deleted in v2, so the rule says to stop
# importing it. In fixture F4 -- the real repository that carries this break --
# the name is read two lines below the import. Acting on the rule alone was
# measured against pydantic 2.13.4: deleting the import turns a
# `PydanticImportError` at import time into a `NameError` at call time. These
# tests exist so the scan cannot go back to reporting only half of that.
# --------------------------------------------------------------------------


def test_a_use_of_the_removed_name_is_reported_beside_the_import(tmp_path: Path) -> None:
    """The shape of F4's `proto.py`, which is where this was found."""
    root = _tree(
        tmp_path,
        {
            "proto.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES

            def repr_args(self):
                return [k for k in self.__dict__ if k not in DUNDER_ATTRIBUTES]
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    scan = find_matches(rule, root)

    assert [(m.line, m.role) for m in scan.matches] == [(1, Role.SITE), (4, Role.USE)]
    assert scan.uses[0].excerpt == "return [k for k in self.__dict__ if k not in DUNDER_ATTRIBUTES]"


def test_a_use_is_not_counted_as_a_site(tmp_path: Path) -> None:
    """`count` is shown to a person right before they agree to an edit.

    A use is not a place the rule applies, and counting it as one would inflate
    that number. One import that is read four times is still one site.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES
            a = DUNDER_ATTRIBUTES
            b = DUNDER_ATTRIBUTES
            c = DUNDER_ATTRIBUTES
            d = DUNDER_ATTRIBUTES
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    scan = find_matches(rule, root)

    assert scan.count == 1
    assert len(scan.sites) == 1
    assert len(scan.uses) == 4


def test_the_bound_name_is_followed_through_a_rename(tmp_path: Path) -> None:
    """`as` rebinds it, and the rest of the file reads the new name.

    Following `alias.name` here would report the import and miss every use --
    exactly the half-answer these tests exist to prevent, but harder to notice.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES as DA
            x = DA
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    scan = find_matches(rule, root)

    assert [(m.line, m.role) for m in scan.matches] == [(1, Role.SITE), (2, Role.USE)]


def test_the_original_name_is_not_followed_after_a_rename(tmp_path: Path) -> None:
    """After `as DA`, a bare `DUNDER_ATTRIBUTES` is some other name.

    It is not what the import bound, so reporting it would send a person to a
    line that has nothing to do with this break.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES as DA
            DUNDER_ATTRIBUTES = object()
            y = DUNDER_ATTRIBUTES
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    scan = find_matches(rule, root)

    assert [m.line for m in scan.uses] == []


def test_two_uses_on_one_line_are_one_line_to_go_and_look_at(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES
            z = DUNDER_ATTRIBUTES or set(DUNDER_ATTRIBUTES)
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    assert [m.line for m in find_matches(rule, root).uses] == [2]


def test_a_store_of_the_name_is_not_a_use(tmp_path: Path) -> None:
    """Assigning to the name does not read the deleted internal.

    A store survives the import being removed, so listing it would name a line
    that is not a problem.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES
            DUNDER_ATTRIBUTES = set()
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    assert [m.line for m in find_matches(rule, root).uses] == []


def test_a_name_matching_nothing_imported_is_not_a_use(tmp_path: Path) -> None:
    """Without the import there is no binding, so there is nothing to report.

    Otherwise every repository with a variable of that name would be told it
    has a pydantic break.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            DUNDER_ATTRIBUTES = set()
            print(DUNDER_ATTRIBUTES)
            """
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    assert find_matches(rule, root).matches == ()


def test_uses_are_found_only_in_the_file_that_imported_the_name(tmp_path: Path) -> None:
    """An import binds a module-local name. Another file's `DUNDER_ATTRIBUTES`
    is its own name, and reporting it would send a person to the wrong file."""
    root = _tree(
        tmp_path,
        {
            "imports_it.py": """
            from pydantic.utils import DUNDER_ATTRIBUTES
            a = DUNDER_ATTRIBUTES
            """,
            "does_not.py": """
            DUNDER_ATTRIBUTES = set()
            b = DUNDER_ATTRIBUTES
            """,
        },
    )
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    scan = find_matches(rule, root)

    assert {m.path.name for m in scan.matches} == {"imports_it.py"}


def test_a_rule_that_draws_no_distinction_reports_every_match_as_a_site(
    tmp_path: Path,
) -> None:
    """`role` defaults, so the classes with rewriters are untouched by it.

    If this ever fails, a planner is about to be handed something to edit that
    was never a site.
    """
    root = _tree(
        tmp_path,
        {
            "mine.py": """
            from pydantic import BaseModel

            class M(BaseModel):
                __root__: list[int]
            """
        },
    )
    rule = _rule(BreakClass.ROOT_MODEL)

    scan = find_matches(rule, root)

    assert scan.matches
    assert all(m.role is Role.SITE for m in scan.matches)
    assert scan.uses == ()
    assert scan.count == len(scan.matches)


# --------------------------------------------------------------------------
# Scope
#
# Qodo raised this on #22: one file-wide set of bound names reports unrelated
# locals and parameters as lines that would break. It was verified before it was
# accepted -- a parameter sharing the spelling really was reported. The refusal
# says "removing the site alone would replace this error with a NameError" about
# each line it names, and for a parameter that is a specific, checkable, false
# statement about somebody's code.
#
# `calls_in_scope` documents this exact failure one function above the one that
# had it. Over-reporting is the safe direction for a list that is read rather
# than edited, but only while what is said about each line is true.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "body", "expected"),
    [
        (
            "a parameter that happens to share the spelling",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            def unrelated(DUNDER_ATTRIBUTES):
                return DUNDER_ATTRIBUTES + 1
            """,
            [],
        ),
        (
            "a lambda parameter that shares the spelling",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            f = lambda DUNDER_ATTRIBUTES: DUNDER_ATTRIBUTES
            """,
            [],
        ),
        (
            "a local assignment shadowing the module-level import",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            def f():
                DUNDER_ATTRIBUTES = set()
                return DUNDER_ATTRIBUTES
            """,
            [],
        ),
        (
            "a function-local import leaves the module-level name alone",
            """
            def inner():
                from pydantic.utils import DUNDER_ATTRIBUTES
                return DUNDER_ATTRIBUTES

            DUNDER_ATTRIBUTES = "mine"
            print(DUNDER_ATTRIBUTES)
            """,
            [3],
        ),
        (
            "a comprehension target shadows for the whole comprehension",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            xs = [DUNDER_ATTRIBUTES for DUNDER_ATTRIBUTES in range(3)]
            """,
            [],
        ),
        (
            "a comprehension that really reads it",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            xs = [k for k in DUNDER_ATTRIBUTES]
            """,
            [3],
        ),
        (
            "the outermost iterable is evaluated before the target binds",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            xs = [x for DUNDER_ATTRIBUTES in DUNDER_ATTRIBUTES for x in DUNDER_ATTRIBUTES]
            """,
            [3],
        ),
        (
            "an unpacking target shadows too",
            # The element must *read* the name. With `[a for (a, X) in pairs]` the
            # only occurrence of X on that line is a store, which is never a use
            # whether unpacking shadows or not -- the test would pass either way.
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            xs = [DUNDER_ATTRIBUTES for (a, DUNDER_ATTRIBUTES) in pairs]
            """,
            [],
        ),
        (
            "a real use two scopes down is still inherited",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            def outer():
                def inner():
                    return DUNDER_ATTRIBUTES
                return inner
            """,
            [5],
        ),
        (
            "a real use inside a method, which is F4's own shape",
            """
            from pydantic.utils import DUNDER_ATTRIBUTES

            class M:
                def __repr_args__(self):
                    return [k for k in self.__dict__ if k not in DUNDER_ATTRIBUTES]
            """,
            [5],
        ),
    ],
)
def test_a_use_is_a_use_only_where_the_import_is_what_binds_the_name(
    tmp_path: Path, label: str, body: str, expected: list[int]
) -> None:
    root = _tree(tmp_path, {"mine.py": body})
    rule = _rule(BreakClass.REMOVED_INTERNAL, symbol="pydantic.utils:DUNDER_ATTRIBUTES")

    uses = sorted(match.line for match in find_matches(rule, root).uses)

    assert uses == expected, label


# --------------------------------------------------------------------------
# Scope, the second time
#
# Qodo raised this on #32 against the new constrained-collection rule, and it
# was true of the merged `regex` rule, of `@root_validator`, and of `@validator`
# as well: four consumers of one file-wide import map, three of which had been
# green for twenty pull requests. A second consumer is what exposed it.
#
# Every case below was run against the code before the fix and reported a site.
# The four rules are checked together on purpose -- the defect was shared, so a
# test that covers one of them would go green again the next time a rule is
# added beside it.
# --------------------------------------------------------------------------


def _sites(source: str, finder: object) -> list[int]:
    tree = ast.parse(textwrap.dedent(source).lstrip("\n"))
    return [found[0] for found in finder(tree)]  # type: ignore[operator]


_ITEMS = (items_keyword_sites, "conlist", "conlist(str, min_items=1)")
_REGEX = (regex_keyword_sites, "constr", "constr(regex='a')")


@pytest.mark.parametrize(("finder", "name", "call"), [_ITEMS, _REGEX])
@pytest.mark.parametrize(
    ("label", "template"),
    [
        (
            "rebound at module level after the import",
            "from pydantic import {name}\n{name} = our_factory\nx = {call}\n",
        ),
        (
            "shadowed by an assignment in the class body",
            "from pydantic import {name}\nclass C:\n    {name} = ours\n    x = {call}\n",
        ),
        (
            "shadowed by a comprehension target",
            "from pydantic import {name}\nxs = [{call} for {name} in factories]\n",
        ),
        (
            "imported inside a class, called outside it",
            "class C:\n    from pydantic import {name}\nx = {call}\n",
        ),
        (
            "imported inside a class, called inside a method",
            "class C:\n    from pydantic import {name}\n    def m(self):\n        return {call}\n",
        ),
    ],
)
def test_a_shadowed_constructor_is_not_pydantics(
    finder: object, name: str, call: str, label: str, template: str
) -> None:
    """A name pydantic bound and something else rebound is not pydantic's any more.

    The dangerous half of getting scope wrong. Each of these renames a keyword
    on a call the migration must not touch, and every one of them is silent:
    the file still imports pydantic, so nothing downstream looks twice.
    """
    assert _sites(template.format(name=name, call=call), finder) == [], label


@pytest.mark.parametrize(("finder", "name", "call"), [_ITEMS, _REGEX])
@pytest.mark.parametrize(
    ("label", "template"),
    [
        ("the plain module-level import", "from pydantic import {name}\nx = {call}\n"),
        (
            "an import inside the function that calls it",
            "def f():\n    from pydantic import {name}\n    return {call}\n",
        ),
        (
            "an import inside the class that calls it",
            "class C:\n    from pydantic import {name}\n    x = {call}\n",
        ),
        (
            "a call in the element of a comprehension that shadows nothing",
            "from pydantic import {name}\nxs = [{call} for _ in rows]\n",
        ),
        (
            "a call in the outermost iterable, evaluated outside the comprehension",
            "from pydantic import {name}\nxs = [y for y in {call}]\n",
        ),
    ],
)
def test_a_real_constructor_is_still_found(
    finder: object, name: str, call: str, label: str, template: str
) -> None:
    """The other direction, because narrowing a scope too far loses real sites.

    The fifth case is the one worth naming: a comprehension's first iterable is
    evaluated where the comprehension is *written*, before the target it is
    about to bind exists, so it keeps the enclosing names.
    """
    found = _sites(template.format(name=name, call=call), finder)
    assert len(found) == 1, label


def test_a_shadowed_validator_is_not_pydantics() -> None:
    """The same fix, on the rule that has been merged the longest."""
    source = """
    from pydantic import validator
    validator = ours

    class M:
        @validator("x")
        def v(cls, value, field): return value
    """
    assert _sites(source, validator_parameter_sites) == []


# --------------------------------------------------------------------------
# Scope, the third time
#
# The follow-up review on #32, against the walk the previous round introduced.
# All three are the same class of mistake as the ones they replaced -- a scope
# modelled *nearly* the way Python models it -- and all three were confirmed by
# running them before the fix.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "source", "expected"),
    [
        (
            "a module-level walrus rebinds like an assignment",
            """
            from pydantic import conlist

            (conlist := our_factory)
            x = conlist(str, min_items=1)
            """,
            [],
        ),
        (
            "a walrus inside a comprehension binds outside it",
            """
            from pydantic import conlist

            ys = [(conlist := factory) for factory in factories]
            x = conlist(str, min_items=1)
            """,
            [],
        ),
        (
            "an inner class does not see the outer class namespace",
            """
            class Outer:
                from pydantic import conlist

                class Inner:
                    x = conlist(str, min_items=1)
            """,
            [],
        ),
        (
            "an import below a call does not reach back up to it",
            """
            class C:
                x = conlist(str, min_items=1)
                from pydantic import conlist
            """,
            [],
        ),
        (
            "an import above a call still reaches it",
            """
            class C:
                from pydantic import conlist
                x = conlist(str, min_items=1)
            """,
            [3],
        ),
        (
            "a shadow below a call does not reach back up either",
            """
            from pydantic import conlist

            class C:
                x = conlist(str, min_items=1)
                conlist = ours
            """,
            [4],
        ),
    ],
)
def test_a_class_body_binds_in_order_and_inherits_like_a_function(
    label: str, source: str, expected: list[int]
) -> None:
    """A class body is not a function body, in two ways this walk had wrong.

    It executes top to bottom rather than treating its whole body as static
    locals, and Python does not put an enclosing class on the lookup chain of a
    class nested inside it. The last two cases are the ones that pin the
    direction: an import above a call is still the same call's import, and a
    shadow written below it was not in scope when the call ran.
    """
    assert _sites(source, items_keyword_sites) == expected, label
