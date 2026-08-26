"""Tests for removing a v1 validator's `field` and `config` parameters.

The class-1 rewriter is the first one whose edit is a *deletion*, and a deletion
has two ways to be wrong that a rename does not. It can take something with it --
the comma that belonged to the parameter before, a comment somebody wrote, the
default of the parameter next door. And it can leave behind a name the body still
reads, which turns a class that raised at import into a function that raises at
call time: a break traded for a quieter one.

So the tests here come in three groups. That the deletion is exact, that the
signature it leaves parses and means what it did, and that every shape it will
not touch is skipped with a reason rather than guessed at.

Why the rewrite is a deletion rather than the rename the error message asks for
is not decided here. `proofs/validator.py` asks a real pydantic v2 and records
the eight answers; these tests are built on that and do not re-derive it.
"""

import ast
from pathlib import Path

from bumpsmith.failures import BreakClass
from bumpsmith.rewrite import Plan, plan
from bumpsmith.rules import Rule, RuleKind, find_matches

_RULE = Rule(
    break_class=BreakClass.VALIDATOR_FIELD_CONFIG,
    kind=RuleKind.SOURCE,
    summary="Remove a v1 validator's `field` and `config` parameters",
    rationale="v2 accepts neither parameter.",
)

_HEAD = "from pydantic import BaseModel, validator\n\n\n"


def _write(tmp_path: Path, text: str, name: str = "models.py") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _plan_for(tmp_path: Path) -> Plan:
    return plan(_RULE, find_matches(_RULE, tmp_path))


def _rewritten(tmp_path: Path) -> str:
    """The one edit, having checked there is exactly one and nothing was skipped."""
    result = _plan_for(tmp_path)
    assert result.is_complete, [str(item) for item in result.skipped]
    assert len(result.edits) == 1
    return result.edits[0].after


def _signature(text: str, name: str = "check") -> str:
    """The parameter list of one function, read back out of the rewritten source.

    Read through the parser rather than by matching text, so that a rewrite which
    happens to produce the right characters in something that will not parse
    fails here rather than passing.
    """
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node.args)
    raise AssertionError(f"no function called {name} in the rewritten source")


# ---------------------------------------------------------------------------
# The deletion itself
# ---------------------------------------------------------------------------


def test_both_parameters_go_and_nothing_else_moves(tmp_path: Path) -> None:
    """The whole change, on the shape fixture B actually has."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    @classmethod\n"
        "    def check(cls, field_value, values, field, config):\n"
        "        return field_value\n"
    )
    path = _write(tmp_path, source)

    after = _rewritten(tmp_path)

    assert _signature(after) == "cls, field_value, values"
    assert after == source.replace(
        "def check(cls, field_value, values, field, config):",
        "def check(cls, field_value, values):",
    )
    assert path.read_text(encoding="utf-8") == source, "planning must not write"


def test_only_one_of_the_two_is_removed_when_only_one_is_there(tmp_path: Path) -> None:
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values"


def test_a_parameter_keeps_its_neighbours_defaults(tmp_path: Path) -> None:
    """The deletion takes the parameter's own default and no one else's."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values=None, field=None, config=None):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values=None"


def test_annotations_on_the_deleted_parameters_go_with_them(tmp_path: Path) -> None:
    """`arg.end_col_offset` covers an annotation, so the span has to as well.

    A deletion that stopped at the name would leave `: ModelField` behind, and
    the file would not parse -- which is the failure this asserts against.
    """
    source = (
        _HEAD + "from pydantic.fields import ModelField\n"
        "\n"
        "\n"
        "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values: dict, field: ModelField, config: type):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values: dict"


def test_a_signature_split_over_several_lines(tmp_path: Path) -> None:
    """The separator is a line ending here, which a line-at-a-time edit cannot span."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(\n"
        "        cls,\n"
        "        v,\n"
        "        values,\n"
        "        field,\n"
        "        config,\n"
        "    ):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    after = _rewritten(tmp_path)

    assert _signature(after) == "cls, v, values"
    assert "field" not in after
    assert "config" not in after
    # The parameters that stay keep the layout they had, one per line.
    assert "        values,\n    ):" in after


def test_the_rest_of_the_file_is_untouched(tmp_path: Path) -> None:
    """Byte for byte outside the signature, comments and quoting included."""
    source = (
        _HEAD + "# a comment that uses the word field\n"
        "MESSAGE = 'config'  # and a string that is one\n"
        "\n"
        "\n"
        "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values, field, config):\n"
        "        '''A docstring mentioning field and config.'''\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    after = _rewritten(tmp_path)

    assert "# a comment that uses the word field\n" in after
    assert "MESSAGE = 'config'  # and a string that is one\n" in after
    assert "'''A docstring mentioning field and config.'''" in after
    # The strongest form of the claim: the signature is the only difference.
    assert after == source.replace(
        "def check(cls, v, values, field, config):",
        "def check(cls, v, values):",
    )


def test_async_validators_are_rewritten_too(tmp_path: Path) -> None:
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    async def check(cls, v, values, field, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values"


def test_root_validators_are_rewritten_too(tmp_path: Path) -> None:
    """The rule matches `root_validator` as well, and the same deletion fixes it.

    Worth its own test because the two decorators fail differently: `@validator`
    raises at class construction and `@root_validator` does not raise until the
    validator is called. Same edit, different symptom.
    """
    source = (
        "from pydantic import BaseModel, root_validator\n\n\n"
        "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        "    @root_validator(skip_on_failure=True)\n"
        "    def check(cls, values, field, config):\n"
        "        return values\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, values"


def test_two_validators_in_one_file_are_one_edit(tmp_path: Path) -> None:
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "    name: str\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, field):\n"
        "        return v\n"
        "\n"
        '    @validator("name")\n'
        "    def check_name(cls, v, values, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert len(result.edits) == 1
    assert result.rewritten == 2
    after = result.edits[0].after
    assert _signature(after) == "cls, v"
    assert _signature(after, "check_name") == "cls, v, values"


# ---------------------------------------------------------------------------
# What it refuses
# ---------------------------------------------------------------------------


def test_a_body_that_reads_the_parameter_is_skipped(tmp_path: Path) -> None:
    """The one that matters.

    Removing a parameter the body reads turns a class that would not import into
    a function that raises NameError when it runs -- later, in somebody else's
    repository, on a path a test may not cover. Refusing is the only safe answer,
    because there is nothing in V2 to rebind the name from.
    """
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, field):\n"
        "        return v if field.name else None\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert not result.is_complete
    assert len(result.skipped) == 1
    assert "reads `field`" in result.skipped[0].reason
    assert "not defined" in result.skipped[0].reason


def test_a_body_reading_config_is_skipped_too(tmp_path: Path) -> None:
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values, config):\n"
        "        return v if config.allow_mutation else None\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "reads `config`" in result.skipped[0].reason


def test_a_nested_function_reading_the_name_counts_as_reading_it(tmp_path: Path) -> None:
    """Blunt on purpose: shadowing makes this harmless and detecting that is not
    worth the one way it could be got wrong."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, field):\n"
        "        def inner(field):\n"
        "            return field\n"
        "        return inner(v)\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "reads `field`" in result.skipped[0].reason


def test_a_keyword_only_parameter_is_skipped(tmp_path: Path) -> None:
    """Removing the last keyword-only parameter leaves a bare `*`, which will not parse."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, *, field=None):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "keyword-only" in result.skipped[0].reason


def test_a_comment_between_the_parameters_is_skipped(tmp_path: Path) -> None:
    """A deletion may remove a parameter, a comma and whitespace. Not somebody's note.

    This module's whole claim is that the diff is small enough to read. Quietly
    eating a comment while removing a parameter is the kind of edit that makes
    the claim false.
    """
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(\n"
        "        cls,\n"
        "        v,  # the value\n"
        "        field,\n"
        "    ):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert "other than a comma" in result.skipped[0].reason


def test_one_skipped_validator_does_not_stop_the_others(tmp_path: Path) -> None:
    """The plan is incomplete, and the site that could be done still is."""
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "    name: str\n"
        "\n"
        '    @validator("status")\n'
        "    def keeps_it(cls, v, field):\n"
        "        return field.name\n"
        "\n"
        '    @validator("name")\n'
        "    def drops_it(cls, v, values, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert len(result.edits) == 1
    assert not result.is_complete
    assert result.rewritten == 1
    after = result.edits[0].after
    assert _signature(after, "keeps_it") == "cls, v, field"
    assert _signature(after, "drops_it") == "cls, v, values"


def test_a_file_that_cannot_be_parsed_is_skipped_not_crashed(tmp_path: Path) -> None:
    good = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, field):\n"
        "        return v\n"
    )
    _write(tmp_path, good, "good.py")
    scan = find_matches(_RULE, tmp_path)
    _write(tmp_path, "def broken(:\n", "good.py")

    result = plan(_RULE, scan)

    assert result.edits == ()
    assert "could not be read" in result.skipped[0].reason


def test_a_site_that_moved_since_the_scan_is_skipped(tmp_path: Path) -> None:
    """A position that has drifted is a reason to write nothing."""
    good = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, field):\n"
        "        return v\n"
    )
    _write(tmp_path, good)
    scan = find_matches(_RULE, tmp_path)
    _write(tmp_path, "# the validator has gone\n")

    result = plan(_RULE, scan)

    assert result.edits == ()
    assert "not there any more" in result.skipped[0].reason


# ---------------------------------------------------------------------------
# Not our validators
# ---------------------------------------------------------------------------


def test_somebody_elses_validator_is_not_a_site(tmp_path: Path) -> None:
    """`validator` is an ordinary identifier, and this one is not pydantic's."""
    source = (
        "from mylib.decorators import validator\n\n\n"
        "class Device:\n"
        '    @validator("status")\n'
        "    def check(cls, v, values, field, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert result.skipped == ()
    assert result.rewritten == 0


def test_an_aliased_pydantic_validator_is_a_site(tmp_path: Path) -> None:
    source = (
        "from pydantic import BaseModel, validator as check_that\n\n\n"
        "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @check_that("status")\n'
        "    def check(cls, v, values, field, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values"


def test_a_validator_reached_through_the_module_is_a_site(tmp_path: Path) -> None:
    source = (
        "import pydantic\n\n\n"
        "class Device(pydantic.BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @pydantic.validator("status")\n'
        "    def check(cls, v, values, field, config):\n"
        "        return v\n"
    )
    _write(tmp_path, source)

    assert _signature(_rewritten(tmp_path)) == "cls, v, values"


def test_a_validator_with_neither_parameter_is_not_a_site(tmp_path: Path) -> None:
    source = (
        _HEAD + "class Device(BaseModel):\n"
        "    status: int\n"
        "\n"
        '    @validator("status")\n'
        "    def check(cls, v, values):\n"
        "        return v\n"
    )
    _write(tmp_path, source)
    result = _plan_for(tmp_path)

    assert result.edits == ()
    assert result.rewritten == 0
