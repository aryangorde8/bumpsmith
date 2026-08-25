"""Tests for turning a rule into edits.

Two things are checked everywhere in here. That the rewrite is correct, and that
it is *small* -- a file comes back byte for byte identical apart from the sites
the rule matched. The second is not decoration: the output of this module is a
diff somebody has to read before approving it, and a correct migration inside an
unreadable diff does not get approved.
"""

from pathlib import Path

import pytest

from bumpsmith.failures import BreakClass
from bumpsmith.rewrite import Plan, UnsupportedRuleError, plan
from bumpsmith.rules import Match, Rule, RuleKind, ScanResult, find_matches

_ROOT_MODEL_RULE = Rule(
    break_class=BreakClass.ROOT_MODEL,
    kind=RuleKind.SOURCE,
    summary="Replace a `__root__` field with pydantic.RootModel",
    rationale="v2 removed __root__ in favour of subclassing RootModel.",
)

_VALIDATOR_RULE = Rule(
    break_class=BreakClass.VALIDATOR_FIELD_CONFIG,
    kind=RuleKind.SOURCE,
    summary="A validator taking field or config",
    rationale="v2 replaced both with info.",
)


def _write(tmp_path: Path, name: str, text: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / name
    path.write_bytes(text.encode(encoding))
    return path


def _plan_for(tmp_path: Path) -> Plan:
    return plan(_ROOT_MODEL_RULE, find_matches(_ROOT_MODEL_RULE, tmp_path))


def _only_edit(tmp_path: Path) -> str:
    result = _plan_for(tmp_path)
    assert result.is_complete, [str(s) for s in result.skipped]
    assert len(result.edits) == 1
    return result.edits[0].after


def _changed_lines(before: str, after: str) -> list[tuple[int, str, str]]:
    """Every line that differs, so a test can assert on the size of the diff."""
    old, new = before.splitlines(), after.splitlines()
    assert len(old) == len(new), "the rewrite added or removed a line"
    return [(i + 1, a, b) for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]


# ---------------------------------------------------------------------------
# The rewrite itself
# ---------------------------------------------------------------------------


def test_a_root_model_becomes_a_RootModel(tmp_path: Path) -> None:  # noqa: N802
    source = '''"""Models."""

from typing import List

from pydantic import BaseModel, Field


class Item(BaseModel):
    name: str


class Items(BaseModel):
    __root__: List[Item] = Field(..., title="every item")
'''
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "class Items(RootModel):" in after
    assert '    root: List[Item] = Field(..., title="every item")' in after
    assert "from pydantic import BaseModel, Field, RootModel" in after
    assert "__root__" not in after


def test_only_the_matched_lines_change(tmp_path: Path) -> None:
    """The guarantee that makes the output reviewable."""
    source = """# a comment that must survive
from typing import List

from pydantic import BaseModel


class Plain(BaseModel):
    #: a docstring-ish comment
    name: str = "unquoted'string"


class Items(BaseModel):
    __root__: List[Plain]
"""
    path = _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    changed = _changed_lines(path.read_text(), after)
    assert [line for line, _, _ in changed] == [4, 12, 13]
    assert changed[0][2] == "from pydantic import BaseModel, RootModel"
    assert changed[1][2] == "class Items(RootModel):"
    assert changed[2][2] == "    root: List[Plain]"


def test_the_import_is_left_alone_when_RootModel_is_already_there(tmp_path: Path) -> None:  # noqa: N802
    source = """from typing import List

from pydantic import BaseModel, RootModel


class Items(BaseModel):
    __root__: List[int]
"""
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert after.count("RootModel") == 2  # the import, and the base
    assert "class Items(RootModel):" in after


def test_an_aliased_import_is_resolved_rather_than_matched_by_name(tmp_path: Path) -> None:
    """`BaseModel as Base` binds `Base`; the rewrite has to follow the binding."""
    source = """from pydantic import BaseModel as Base


class Items(Base):
    __root__: list[int]
"""
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "class Items(RootModel):" in after
    assert "from pydantic import BaseModel as Base, RootModel" in after


def test_the_module_attribute_form_needs_no_import(tmp_path: Path) -> None:
    source = """import pydantic


class Items(pydantic.BaseModel):
    __root__: list[int]
"""
    path = _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "class Items(pydantic.RootModel):" in after
    assert [line for line, _, _ in _changed_lines(path.read_text(), after)] == [4, 5]


def test_the_unannotated_form_is_rewritten_too(tmp_path: Path) -> None:
    source = """from pydantic import BaseModel, Field


class Items(BaseModel):
    __root__ = Field(...)
"""
    _write(tmp_path, "models.py", source)
    assert "    root = Field(...)" in _only_edit(tmp_path)


# ---------------------------------------------------------------------------
# Positions, which is where a rewriter goes wrong quietly
# ---------------------------------------------------------------------------


def test_a_multibyte_character_earlier_on_the_line_does_not_shift_the_edit(
    tmp_path: Path,
) -> None:
    """`col_offset` counts bytes, not characters.

    Doing the arithmetic in characters puts the edit several columns to the left
    of where the parser said it was, and the further left it lands the more
    plausible the corrupted result looks.
    """
    source = """from pydantic import BaseModel


class Items(BaseModel):
    __root__: list[int] = None  # naïve — the accents are the point ✓
"""
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "    root: list[int] = None  # naïve — the accents are the point ✓" in after


def test_a_form_feed_does_not_shift_every_line_after_it(tmp_path: Path) -> None:
    """`str.splitlines` breaks on form feed and the parser does not.

    Using it would renumber every line below one, so the edit would land on the
    wrong statement in exactly the files old enough to contain page breaks.
    """
    source = "from pydantic import BaseModel\n\n\x0c\n\nclass Items(BaseModel):\n    __root__: list[int]\n"
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "    root: list[int]\n" in after
    assert "\x0c" in after, "the page break itself was eaten"


def test_windows_line_endings_survive(tmp_path: Path) -> None:
    source = "from pydantic import BaseModel\r\n\r\n\r\nclass Items(BaseModel):\r\n    __root__: list[int]\r\n"
    _write(tmp_path, "models.py", source)
    after = _only_edit(tmp_path)

    assert "\r\n" in after
    assert "\n" not in after.replace("\r\n", "")
    assert "    root: list[int]" in after


def test_the_file_encoding_is_carried_into_the_edit(tmp_path: Path) -> None:
    source = """# -*- coding: latin-1 -*-
from pydantic import BaseModel


class Items(BaseModel):
    __root__: list[int] = None  # r\xe9sum\xe9
"""
    _write(tmp_path, "models.py", source, encoding="latin-1")
    result = _plan_for(tmp_path)

    assert len(result.edits) == 1
    assert result.edits[0].encoding.lower().replace("_", "-") in {"latin-1", "iso-8859-1"}
    assert "r\xe9sum\xe9" in result.edits[0].after


# ---------------------------------------------------------------------------
# What it refuses to do
# ---------------------------------------------------------------------------


def test_a_root_field_on_a_class_that_is_not_a_model_is_reported_not_guessed(
    tmp_path: Path,
) -> None:
    """The scan matches `__root__` without requiring a visible BaseModel base.

    That is deliberate there -- models commonly inherit through their own
    subclasses. Here it means the base to write is a guess, and a guess is worse
    than a report.
    """
    source = """from pydantic import BaseModel


class Base(BaseModel):
    pass


class Items(Base):
    __root__: list[int]
"""
    _write(tmp_path, "models.py", source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert len(result.skipped) == 1
    assert "does not demonstrably inherit" in result.skipped[0].reason
    assert result.skipped[0].line == 9


def test_a_name_collision_stops_the_file(tmp_path: Path) -> None:
    source = """from pydantic import BaseModel


class RootModel:
    \"\"\"Something else entirely, and it got there first.\"\"\"


class Items(BaseModel):
    __root__: list[int]
"""
    _write(tmp_path, "models.py", source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "already used in this file for something else" in result.skipped[0].reason


def test_a_site_that_is_no_longer_there_is_reported(tmp_path: Path) -> None:
    """The scan and the plan are separated in time, and the file can move."""
    path = _write(tmp_path, "models.py", "from pydantic import BaseModel\n")
    stale = ScanResult(matches=(Match(path=path, line=99, excerpt="__root__: int"),), unreadable=())

    result = plan(_ROOT_MODEL_RULE, stale)

    assert result.edits == ()
    assert "not there any more" in result.skipped[0].reason


def test_a_file_that_will_not_parse_is_reported_rather_than_crashing(tmp_path: Path) -> None:
    path = _write(tmp_path, "models.py", "def (:\n")
    broken = ScanResult(matches=(Match(path=path, line=1, excerpt="?"),), unreadable=())

    result = plan(_ROOT_MODEL_RULE, broken)

    assert result.edits == ()
    assert "could not be read" in result.skipped[0].reason


def test_a_rule_with_no_rewriter_says_so_out_loud() -> None:
    """Not an empty plan.

    A plan with no edits and no explanation reads exactly like a repository that
    needed no changes, which is the one wrong answer.
    """
    with pytest.raises(UnsupportedRuleError, match="no rewriter is written"):
        plan(_VALIDATOR_RULE, ScanResult(matches=(), unreadable=()))


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def test_sites_are_counted_rather_than_files(tmp_path: Path) -> None:
    """One file holding three sites is a three-site change, not a one-file change."""
    source = """from pydantic import BaseModel


class A(BaseModel):
    __root__: list[int]


class B(BaseModel):
    __root__: list[str]


class C(BaseModel):
    __root__: dict[str, int]
"""
    _write(tmp_path, "models.py", source)
    result = _plan_for(tmp_path)

    assert len(result.edits) == 1
    assert result.rewritten == 3
    assert result.edits[0].after.count("RootModel") == 4  # the import, and three bases


# ---------------------------------------------------------------------------
# Binding, which is the difference between a rule and a search-and-replace
# ---------------------------------------------------------------------------


def test_a_base_rebound_after_the_import_is_not_treated_as_pydantic(tmp_path: Path) -> None:
    """The worst failure this module can have, so it gets the plainest test.

    Reading the import alone says `BaseModel` is pydantic's. The assignment below
    it says otherwise, and rewriting the base of a class that was never a
    pydantic model changes code that was working.
    """
    _write(
        tmp_path,
        "models.py",
        "from pydantic import BaseModel\n"
        "from mylib import Other\n"
        "\n"
        "BaseModel = Other\n"
        "\n"
        "\n"
        "class Items(BaseModel):\n"
        "    __root__: list[int]\n",
    )
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "does not demonstrably inherit" in result.skipped[0].reason


def test_a_rootmodel_rebound_after_its_import_still_counts_as_a_collision(
    tmp_path: Path,
) -> None:
    """Having been imported once is not the same as still meaning that.

    The emitted `class X(RootModel)` would inherit whatever the rebinding put
    there, which usually fails at import time and occasionally does not.
    """
    _write(
        tmp_path,
        "models.py",
        "from pydantic import BaseModel, RootModel\n"
        "from mylib import Other\n"
        "\n"
        "RootModel = Other\n"
        "\n"
        "\n"
        "class Items(BaseModel):\n"
        "    __root__: list[int]\n",
    )
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "already used in this file for something else" in result.skipped[0].reason


def test_a_name_taken_by_unpacking_is_still_a_collision(tmp_path: Path) -> None:
    """`RootModel, other = pair()` binds `RootModel` just as firmly as `=` does."""
    _write(
        tmp_path,
        "models.py",
        "from pydantic import BaseModel\n"
        "from mylib import pair\n"
        "\n"
        "RootModel, other = pair()\n"
        "\n"
        "\n"
        "class Items(BaseModel):\n"
        "    __root__: list[int]\n",
    )
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "already used in this file for something else" in result.skipped[0].reason


def test_an_import_that_does_not_run_is_not_extended(tmp_path: Path) -> None:
    """`if TYPE_CHECKING:` binds nothing at runtime.

    Adding `RootModel` to an import inside it produces a file that raises
    NameError while defining the very class this rewrite just changed.
    """
    _write(
        tmp_path,
        "models.py",
        "from typing import TYPE_CHECKING\n"
        "\n"
        "if TYPE_CHECKING:\n"
        "    from pydantic import BaseModel\n"
        "\n"
        "\n"
        "class Items(BaseModel):\n"
        "    __root__: list[int]\n",
    )
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "no plain pydantic import" in result.skipped[0].reason


def test_two_declarations_on_one_line_are_both_rewritten(tmp_path: Path) -> None:
    """The scan reports a line per site, so one line can be reported twice.

    Keeping one statement per line silently dropped the other, left the file
    half-rewritten, and still counted both as done.
    """
    _write(
        tmp_path,
        "models.py",
        "from pydantic import BaseModel\n"
        "\n"
        "\n"
        "class Items(BaseModel):\n"
        "    __root__ = 1; __root__ = 2\n",
    )
    result = _plan_for(tmp_path)

    assert result.is_complete, [str(s) for s in result.skipped]
    after = result.edits[0].after
    assert "__root__" not in after
    assert after.count("root = ") == 2
    assert result.rewritten == 2


# ---------------------------------------------------------------------------
# Class 3 -- the whole break is one word, which makes it a check on the machinery
# ---------------------------------------------------------------------------


_REGEX_RULE = Rule(
    break_class=BreakClass.REGEX_KEYWORD,
    kind=RuleKind.SOURCE,
    summary="Rename the `regex=` argument to `pattern=`",
    rationale="v2 renamed the constraint on Field and the constrained-string constructors.",
)


def _regex_plan(tmp_path: Path) -> Plan:
    return plan(_REGEX_RULE, find_matches(_REGEX_RULE, tmp_path))


def test_only_the_keyword_changes(tmp_path: Path) -> None:
    source = """from pydantic import BaseModel, Field, constr


class Account(BaseModel):
    # regex in a comment must survive, and so must the pattern text itself
    sort_code: str = Field(..., regex=r"^\\d{2}-regex-\\d{2}$")
    branch: constr(regex=r"^\\w+$") = "x"
"""
    path = _write(tmp_path, "models.py", source)
    result = _regex_plan(tmp_path)
    assert result.is_complete, [str(s) for s in result.skipped]
    after = result.edits[0].after

    changed = _changed_lines(path.read_text(), after)
    assert [line for line, _, _ in changed] == [6, 7]
    assert 'Field(..., pattern=r"^\\d{2}-regex-\\d{2}$")' in after
    assert 'constr(pattern=r"^\\w+$")' in after
    assert "# regex in a comment must survive" in after
    assert result.rewritten == 2


def test_two_on_one_line_both_change(tmp_path: Path) -> None:
    """The scan reports a line per site, so one line can be reported twice.

    Applying the same line's replacements twice would corrupt it, and reporting
    only one of them would leave the file broken in a way that looks fixed.
    """
    _write(
        tmp_path,
        "models.py",
        'from pydantic import constr\n\nx = (constr(regex=r"^a$"), constr(regex=r"^b$"))\n',
    )
    result = _regex_plan(tmp_path)

    after = result.edits[0].after
    assert after.count("pattern=") == 2
    assert "regex=" not in after


def test_a_lookalike_from_another_library_is_left_alone(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "models.py",
        'from mylib.helpers import constr\n\nx = constr(regex=r"^a$")\n',
    )
    result = _regex_plan(tmp_path)

    assert result.edits == ()
    assert result.skipped == ()


def test_a_same_line_site_that_vanished_is_not_covered_by_its_neighbour(
    tmp_path: Path,
) -> None:
    """Two sites on one line, one gone since the scan.

    Letting the survivor stand in for both reports two rewritten, writes one, and
    calls the plan complete -- the combination that looks like success.
    """
    path = _write(
        tmp_path, "models.py", 'from pydantic import constr\n\nx = constr(regex=r"^a$")\n'
    )
    scan = ScanResult(
        matches=(
            Match(path=path, line=3, excerpt="constr(regex=...)"),
            Match(path=path, line=3, excerpt="constr(regex=...)"),
        ),
        unreadable=(),
    )

    result = plan(_REGEX_RULE, scan)

    assert not result.is_complete
    assert len(result.skipped) == 1
    assert result.rewritten == 1
    assert result.edits[0].after.count("pattern=") == 1
