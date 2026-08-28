"""Turn a classified failure into a migration rule, and find where it applies.

bumpsmith emits a **rule**, not a patch. A patch says "change line 27 of this
file"; a rule says "wherever a v1 validator takes a ``field`` parameter, that is
this break, and here is every place it occurs." One failing test names one site.
The rule it implies usually names more, and the difference between those two
numbers is the part a human wants before agreeing to anything.

Matching is done over the abstract syntax tree, never over the text. That is not
a stylistic preference. ``@validator`` appears in strings, in comments, and in
documentation examples, and a library may define a decorator of its own by that
name -- one of the fixture candidates does exactly that, and a textual rewrite
would destroy it. The tree knows where a name came from; a regular expression
cannot.
"""

import ast
import os
from collections.abc import Container, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from bumpsmith.failures import BreakClass, Failure
from bumpsmith.sources import read_source

# Directories whose contents are not this project's code to change.
_SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "venv",
    }
)

# The v1 decorators that took `field` and `config`. V2 replaced both parameters
# with a single `info` argument carrying ValidationInfo.
_V1_VALIDATORS = frozenset({"validator", "root_validator"})
_V1_INFO_PARAMETERS = frozenset({"field", "config"})

_ROOT_FIELD = "__root__"


class RuleKind(Enum):
    """Whether this repository's own source is what has to change."""

    SOURCE = "source"
    """The break is in code this project can edit."""

    DEPENDENCY = "dependency"
    """Nothing in this repository's source fixes it. A dependency must move first."""


@dataclass(frozen=True, slots=True)
class Rule:
    """One migration rule, derived from a classified failure.

    ``module`` and ``name`` are set only for the removed-import class, where the
    rule is meaningless without knowing which symbol went away.
    """

    break_class: BreakClass
    kind: RuleKind
    summary: str
    rationale: str
    module: str | None = None
    name: str | None = None


class Role(Enum):
    """What a matched line *is* to the rule that found it.

    A rule points at the code to change, but that code is not always the only
    code affected by changing it. Removing an import is the clearest case: the
    import is the site, and every line that reads the name it bound is a place
    that stops working the moment the site is deleted. Reporting only the site
    is how "stop importing this" becomes a `NameError` in somebody's repository.

    The distinction lives in the type rather than in the summary text, because a
    reader who has to infer it from prose is a reader who can miss it.
    """

    SITE = "site"
    """The place the rule applies -- what a rewriter would edit."""

    USE = "use"
    """A line that reads what the site binds, and breaks if the site alone goes.

    Never edited. It exists so the count a person is shown is the number of
    places they have to think about, not the number that happen to be easy.
    """


@dataclass(frozen=True, slots=True)
class Match:
    """One place a rule applies, or one place that depends on such a place."""

    path: Path
    line: int
    excerpt: str
    role: Role = Role.SITE
    """Defaulted so that a rule which draws no distinction does not have to."""

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  {self.excerpt}"


@dataclass(frozen=True, slots=True)
class Unreadable:
    """A file the scan could not consider, and why."""

    path: Path
    reason: str


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Everything one scan found, including what it could not read.

    A file that fails to parse is reported rather than skipped in silence. A
    count that quietly excludes the files it choked on is worse than no count,
    because it looks complete.
    """

    matches: tuple[Match, ...]
    unreadable: tuple[Unreadable, ...]

    @property
    def sites(self) -> tuple[Match, ...]:
        """The places the rule applies -- what a rewriter would edit."""
        return tuple(match for match in self.matches if match.role is Role.SITE)

    @property
    def uses(self) -> tuple[Match, ...]:
        """The places that break if the sites are removed and nothing else is.

        Always in the same file as the site that bound the name: an import binds
        a module-local name, so a use of it cannot be anywhere else.
        """
        return tuple(match for match in self.matches if match.role is Role.USE)

    @property
    def count(self) -> int:
        """How many sites the rule matched.

        Sites only. A use is not a place the rule applies, and counting it as one
        would inflate the number this project puts in front of a person right
        before asking them to agree to an edit.
        """
        return len(self.sites)

    @property
    def is_complete(self) -> bool:
        """True when every candidate file was read and parsed."""
        return not self.unreadable


def write_rule(failure: Failure) -> Rule | None:
    """Derive the migration rule a failure implies, or ``None`` if none can be.

    Returns ``None`` rather than a guess. An unclassified failure, or a removed
    import whose symbol was never captured, does not narrow to one
    transformation, and a rule that names the wrong transformation is worse than
    no rule: it will match sites confidently and change them wrongly.
    """
    if failure.break_class is BreakClass.VALIDATOR_FIELD_CONFIG:
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.SOURCE,
            summary="Remove a v1 validator's `field` and `config` parameters",
            rationale=(
                "pydantic v2 dropped the per-validator `field` and `config` arguments. A "
                "validator still declaring either name raises at class-construction time, so "
                "the module fails to import and every test in it fails to collect. The error "
                "text points at `info`, and under the `@validator` shim that is not what to "
                "write: `info` belongs to v2's `@field_validator`, and the shim refuses a "
                "parameter by that name as an unsupported V1 signature. `values` is still "
                "accepted and still carries what it did, so removing the two parameters is "
                "the whole change."
            ),
        )

    if failure.break_class is BreakClass.ROOT_MODEL:
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.SOURCE,
            summary=f"Replace a `{_ROOT_FIELD}` field with pydantic.RootModel",
            rationale=(
                f"`{_ROOT_FIELD}` was v1's way of declaring a model whose whole body is one "
                "value. v2 removed it in favour of subclassing RootModel. The failure arrives "
                "as a plain TypeError from pydantic's namespace inspection, with no error code "
                "and no docs link."
            ),
        )

    if failure.break_class is BreakClass.REGEX_KEYWORD:
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.SOURCE,
            summary="Rename the `regex=` argument to `pattern=`",
            rationale=(
                "v2 renamed the constraint from `regex` to `pattern` on both `Field` and the "
                "constrained-string constructors. `Field` reports it as a PydanticUserError "
                "carrying `removed-kwargs`; `constr` never gets that far, because Python "
                "rejects the unexpected keyword while binding the arguments."
            ),
        )

    if failure.break_class is BreakClass.ITEMS_KEYWORD:
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.SOURCE,
            summary="Rename `min_items=`/`max_items=` to `min_length=`/`max_length=`",
            rationale=(
                "v2 renamed both constraints on the constrained-collection constructors, "
                "which reject the old spelling in Python's argument binding before pydantic "
                "sees the call. `Field` is not part of this: it accepts either spelling in "
                "v2 and warns, so the sites this rule reports are the ones that actually "
                "stop the suite."
            ),
        )

    if failure.break_class is BreakClass.REMOVED_INTERNAL:
        symbol = _split_symbol(failure.symbol)
        if symbol is None:
            return None
        module, name = symbol
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.SOURCE,
            summary=f"Stop importing `{name}` from `{module}`",
            rationale=(
                f"`{module}.{name}` is a pydantic internal that v2 deleted. Importing it fails "
                "at import time, so the break is not confined to the code that used it -- the "
                "whole module stops loading. Removing the import is therefore necessary and "
                "rarely sufficient: wherever the name was read, that code still expects a v1 "
                "internal to exist, and deleting only the import turns an error at import time "
                "into a `NameError` at call time. The scan lists those uses next to the import "
                "for that reason."
            ),
            module=module,
            name=name,
        )

    if failure.break_class is BreakClass.TRANSITIVE_DEPENDENCY:
        return Rule(
            break_class=failure.break_class,
            kind=RuleKind.DEPENDENCY,
            summary="A package this repository depends on is missing or unmigrated",
            rationale=(
                "The break is not in this repository's source, so no edit here removes it. "
                "A module it imports could not be found: either the environment does not "
                "have it installed, or the version that is installed is itself unmigrated. "
                "Which of those it is cannot be told from the message, and both are fixed "
                "outside this repository. "
                f"pytest reported: {failure.message or 'no message captured'}"
            ),
        )

    return None


def _split_symbol(symbol: str | None) -> tuple[str, str] | None:
    """Split pydantic's ``module:name`` symbol notation, or return ``None``.

    pydantic phrases removed imports as `` `pydantic.utils:DUNDER_ATTRIBUTES` ``.
    Anything not in that shape is not something to build a rule from.
    """
    if symbol is None:
        return None
    module, separator, name = symbol.partition(":")
    if not separator or not module or not name:
        return None
    return module, name


@dataclass(frozen=True, slots=True)
class PydanticNames:
    """The names in one module that demonstrably came from pydantic.

    This is what separates a rule from a search-and-replace. ``validator`` is an
    ordinary identifier; whether it is *pydantic's* validator depends entirely on
    what the module imported.
    """

    direct: Mapping[str, str]
    """Bound name to the pydantic name behind it.

    A mapping rather than a set because of `as`: `from pydantic import validator
    as check` binds `check`, and a rule that only knew the bound name would have
    nothing to compare against `validator`.
    """

    modules: frozenset[str]
    """Bound by `import pydantic` / `import pydantic.utils as pu`."""


_V1_COMPAT = "pydantic.v1"


def _is_pydantic_path(dotted: str) -> bool:
    """True for pydantic's v2 surface, false for its vendored v1 namespace.

    `pydantic.v1` is v2's bundled copy of the old API. Code importing from it has
    deliberately kept v1 behaviour under v2, and the signature change this rule
    is about does not apply there. Still being on the compatibility shim is a
    finding of its own -- it is just not *this* one, and counting it here would
    inflate the number with sites that are not broken.
    """
    if dotted == _V1_COMPAT or dotted.startswith(f"{_V1_COMPAT}."):
        return False
    return dotted == "pydantic" or dotted.startswith("pydantic.")


def module_scope_nodes(tree: ast.Module) -> Iterator[ast.AST]:
    """Yield every node that binds a name in the module's own namespace.

    Stops at every construct that opens a scope of its own -- functions,
    lambdas, comprehensions, and class bodies. An import inside any of them
    binds a local that module scope cannot see, so collecting it would let an
    unrelated import three functions down overrule `from mylib.decorators import
    validator` at the top of the file.

    Class bodies used to be descended into, on the reasoning that a decorator
    written inside a class resolves through the class namespace being built.
    That is true and it is not this function's job: a class body is reached by
    :func:`nodes_in_scope`, which adds its bindings on the way in. Folding them
    in here instead made `from pydantic import conlist` inside one class rename
    `min_items=` on an unrelated call at module level -- reported by review, and
    the same defect the two directions below describe.

    `try`/`except ImportError` and `if TYPE_CHECKING:` are deliberately not
    skipped. An import wrapped in either is still a module-level binding, and
    both wrappings are common enough that ignoring them would trade this false
    positive for a false negative.

    A walrus inside a module-level comprehension binds in the enclosing scope
    and this walk does not see it. That is not a hole: `_walrus_targets` reads
    the comprehension for exactly that, separately, because it wants the
    binding without wanting the comprehension's own targets.
    """
    pending: list[ast.AST] = [tree]
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (*_NESTED_SCOPES, ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(node))


def pydantic_names(tree: ast.Module) -> PydanticNames:
    """The pydantic names visible at module scope, rebindings taken off again.

    A name the module binds by any other means is dropped, whatever the order:
    `from pydantic import conlist` followed by `conlist = our_factory` leaves
    nothing of pydantic's behind, and reporting `min_items=` on the second one
    is this tool rewriting code that has nothing to do with the migration.

    Only *unconditional* rebindings count, which is the difference between the
    two idioms that look alike from here:

        from pydantic import conlist      try:
        conlist = our_factory                 from pydantic import conlist
                                          except ImportError:
                                              conlist = None

    The left one leaves nothing of pydantic's behind. The right one is the
    standard optional-dependency wrapping, the rebinding runs only when the
    import failed, and treating it as a shadow loses every site in a file that
    guards its imports -- a case this module has a named test for. So the
    rebinding scan reads the module's own body and does not descend into `try`,
    `if` or `with`, matching :func:`module_scope_nodes`, which counts an import
    inside those for the same reason in reverse.

    Order is not consulted. Deciding it properly means tracking control flow,
    and the conservative reading loses a rewrite where the aggressive one
    corrupts a file.
    """
    direct: dict[str, str] = {}
    modules: set[str] = set()
    for node in module_scope_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            # node.level > 0 is a relative import: `from .utils import validator`
            # is the project's own module, whatever it happens to be called.
            if node.level == 0 and node.module is not None and _is_pydantic_path(node.module):
                for alias in node.names:
                    direct[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_pydantic_path(alias.name):
                    continue
                # `import pydantic.utils` binds `pydantic`; with `as` it binds the alias.
                modules.add(alias.asname or alias.name.split(".")[0])
    rebound = _unconditional_rebindings(tree)
    return PydanticNames(
        direct={name: real for name, real in direct.items() if name not in rebound},
        modules=frozenset(module for module in modules if module not in rebound),
    )


_OWN_SCOPE = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _walrus_targets(statement: ast.AST) -> Iterator[str]:
    """Names one module-level statement binds with `:=`.

    Comprehensions *are* walked into, alone among the things this stops at: a
    walrus inside one binds in the enclosing scope, which is the whole reason it
    is worth looking there. Everything with a namespace of its own is skipped,
    because a walrus inside a function binds in the function.
    """
    if isinstance(statement, _OWN_SCOPE):
        return
    pending: list[ast.AST] = [statement]
    while pending:
        current = pending.pop()
        if isinstance(current, ast.NamedExpr):
            yield from _target_names(current.target)
        if isinstance(current, _OWN_SCOPE):
            continue
        pending.extend(ast.iter_child_nodes(current))


def _unconditional_rebindings(tree: ast.Module) -> set[str]:
    """Names the module body binds by something other than a pydantic import.

    Statements written directly in the module body only. Anything nested in a
    `try`, an `if` or a `with` runs on a path that may not be taken, and the
    import is the evidence actually in hand.
    """
    rebound: set[str] = set()
    for node in tree.body:
        rebound.update(_walrus_targets(node))
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None and _is_pydantic_path(node.module):
                continue
            rebound.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            rebound.update(
                alias.asname or alias.name.split(".")[0]
                for alias in node.names
                if not _is_pydantic_path(alias.name)
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            rebound.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                rebound.update(_target_names(target))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor)):
            rebound.update(_target_names(node.target))
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    rebound.update(_target_names(item.optional_vars))
    return rebound


def pydantic_name(node: ast.expr, names: PydanticNames) -> str | None:
    """Return the pydantic object this expression refers to, or ``None``.

    Handles the four shapes a decorator takes: bare, called, attribute, and
    called attribute -- `@validator`, `@validator("x")`, `@pydantic.validator`,
    `@pydantic.validator("x")`. A base class is the same question asked of a
    different position, so :mod:`bumpsmith.rewrite` resolves `BaseModel` through
    here rather than repeating the alias handling and drifting from it.
    """
    if isinstance(node, ast.Call):
        return pydantic_name(node.func, names)
    if isinstance(node, ast.Name):
        return names.direct.get(node.id)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.attr if node.value.id in names.modules else None
    return None


def validator_parameter_sites(
    tree: ast.Module,
) -> Iterator[tuple[int, ast.FunctionDef | ast.AsyncFunctionDef, tuple[ast.arg, ...]]]:
    """Yield every pydantic validator still declaring `field` or `config`.

    The function node and the offending arguments come back with the line
    because the rewrite needs their columns, and recomputing those from the line
    would mean finding the word `field` in text that may legitimately hold it
    several times -- as an annotation, a default, or another parameter's name.

    The arguments are yielded in the order they are declared, which is the order
    the deletion has to be reasoned about: what separates one from the next is
    what gets removed with it.
    """
    for node, names in functions_in_scope(tree):
        decorated = any(
            (pydantic_name(decorator, names) or "") in _V1_VALIDATORS
            for decorator in node.decorator_list
        )
        if not decorated:
            continue
        arguments = node.args
        offending = tuple(
            argument
            for argument in (
                *arguments.posonlyargs,
                *arguments.args,
                *arguments.kwonlyargs,
            )
            if argument.arg in _V1_INFO_PARAMETERS
        )
        if offending:
            yield node.lineno, node, offending


def _validator_sites(tree: ast.Module) -> Iterator[int]:
    """Yield the line of every pydantic validator still taking `field` or `config`.

    Defined in terms of the site walk rather than beside it. A scan and a rewrite
    that each decide for themselves what counts as a site drift, and when they do
    the edit lands somewhere the scan never reported.
    """
    for line, _node, _offending in validator_parameter_sites(tree):
        yield line


def _root_model_sites(tree: ast.Module) -> Iterator[int]:
    """Yield the line of every ``__root__`` field declared in a class body.

    No check that the class is a pydantic model. ``__root__`` is not a name
    Python gives meaning to and not one anybody chooses by accident; requiring a
    visible BaseModel base would miss every model that inherits through one of
    its own subclasses, which is the common case in the fixtures.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        yield from (statement.lineno for statement in node.body if declares_root_field(statement))


def declares_root_field(statement: ast.stmt) -> bool:
    """True when this class-body statement declares ``__root__``, annotated or not.

    Public because :mod:`bumpsmith.rewrite` has to agree with the scan about what
    counts as a site. Two definitions of the same thing drift, and the one that
    drifts here would edit a line the scan never reported.
    """
    if isinstance(statement, ast.AnnAssign):
        return isinstance(statement.target, ast.Name) and statement.target.id == _ROOT_FIELD
    if isinstance(statement, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == _ROOT_FIELD
            for target in statement.targets
        )
    return False


_REGEX_CALLABLES = frozenset({"Field", "constr"})
"""The pydantic callables observed taking `regex=`.

`conint` and the rest of the constrained-type constructors never had it, so
matching on the keyword alone would report sites that were never broken.
"""


_ITEMS_CALLABLES = frozenset({"conlist", "conset", "confrozenset"})
"""The pydantic callables that *raise* on `min_items=`/`max_items=`.

`Field` is the interesting omission. It took both spellings in v1 and still
takes them in v2, where it renames them and warns -- so a `Field(min_items=1)`
is deprecated rather than broken, and rewriting it would be this tool editing
code that runs. `_REGEX_CALLABLES` includes `Field` for the opposite reason:
there it raises.
"""

LENGTH_KEYWORDS = {"min_items": "min_length", "max_items": "max_length"}
"""The v1 spelling of each constraint, and what v2 calls it."""


def _locally_bound(node: ast.AST) -> tuple[dict[str, str], set[str], set[str]]:
    """What one function binds in its own scope.

    Returns the pydantic names it imports, the pydantic *modules* it imports, and
    every name it binds by any means. Nested functions and class bodies are not
    descended into -- their bindings are theirs, not this scope's -- though the
    name a nested `def` or `class` introduces is bound here and is collected.
    """
    parameters: set[str] = set()
    arguments = getattr(node, "args", None)
    if isinstance(arguments, ast.arguments):
        for argument in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
            parameters.add(argument.arg)
        for extra in (arguments.vararg, arguments.kwarg):
            if extra is not None:
                parameters.add(extra.arg)

    body = getattr(node, "body", [])
    statements = list(body) if isinstance(body, list) else [body]
    direct, modules, bound = _bindings_of(statements)
    return direct, modules, bound | parameters


def _bindings_of(statements: Sequence[ast.AST]) -> tuple[dict[str, str], set[str], set[str]]:
    """What a run of statements binds, without entering a scope of their own.

    Split out of :func:`_locally_bound` so a class body can be advanced one
    statement at a time, which is how Python executes it.
    """
    direct: dict[str, str] = {}
    modules: set[str] = set()
    bound: set[str] = set()

    pending: list[ast.AST] = list(statements)
    while pending:
        child = pending.pop()
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(child.name)
            continue
        if isinstance(child, ast.Lambda):
            continue
        if isinstance(child, ast.ImportFrom):
            if child.level == 0 and child.module is not None and _is_pydantic_path(child.module):
                for alias in child.names:
                    direct[alias.asname or alias.name] = alias.name
            bound.update(alias.asname or alias.name.split(".")[0] for alias in child.names)
        elif isinstance(child, ast.Import):
            for alias in child.names:
                name = alias.asname or alias.name.split(".")[0]
                bound.add(name)
                if _is_pydantic_path(alias.name):
                    modules.add(name)
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                bound.update(_target_names(target))
        elif isinstance(
            child, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.NamedExpr)
        ):
            bound.update(_target_names(child.target))
        elif isinstance(child, ast.withitem) and child.optional_vars is not None:
            bound.update(_target_names(child.optional_vars))
        elif isinstance(child, ast.ExceptHandler) and child.name is not None:
            bound.add(child.name)
        pending.extend(ast.iter_child_nodes(child))
    return direct, modules, bound


def _target_names(target: ast.expr) -> Iterator[str]:
    """The names one assignment target binds, unpacking as far as it goes."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _target_names(element)
    elif isinstance(target, ast.Starred):
        yield from _target_names(target.value)


def _without(names: PydanticNames, bound: Container[str]) -> PydanticNames:
    """The same names, minus every one this scope binds for itself."""
    return PydanticNames(
        direct={name: real for name, real in names.direct.items() if name not in bound},
        modules=frozenset(module for module in names.modules if module not in bound),
    )


def _inside(names: PydanticNames, node: ast.AST) -> PydanticNames:
    """The names in scope inside one function or class body, given those outside."""
    direct, modules, bound = _locally_bound(node)
    inherited = dict(_without(names, bound).direct)
    inherited.update(direct)
    return PydanticNames(
        direct=inherited,
        modules=frozenset(_without(names, bound).modules | modules),
    )


def _advanced(names: PydanticNames, statement: ast.stmt) -> PydanticNames:
    """The scope of a class body after one more of its statements has run."""
    direct, modules, bound = _bindings_of([statement])
    remaining = _without(names, bound)
    grown = dict(remaining.direct)
    grown.update(direct)
    return PydanticNames(direct=grown, modules=frozenset(remaining.modules | modules))


def _evaluated_outside(node: ast.AST) -> Iterator[ast.AST]:
    """The parts of a scope-opening statement evaluated where it is *written*.

    A decorator, a base class, a default and an annotation all run before the
    scope they are attached to exists. Reading them under the new scope's names
    lets a function that happens to assign `root_validator` in its own body hide
    the decorator sitting above its own `def`.
    """
    yield from getattr(node, "decorator_list", [])
    if isinstance(node, ast.ClassDef):
        yield from node.bases
        yield from node.keywords
        return
    arguments = getattr(node, "args", None)
    if isinstance(arguments, ast.arguments):
        yield from (default for default in arguments.defaults if default is not None)
        yield from (default for default in arguments.kw_defaults if default is not None)
        every = (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
            arguments.vararg,
            arguments.kwarg,
        )
        yield from (
            argument.annotation
            for argument in every
            if argument is not None and argument.annotation is not None
        )
    returns = getattr(node, "returns", None)
    if returns is not None:
        yield returns


def _comprehension_elements(node: ast.AST) -> Iterator[ast.AST]:
    """The expression a comprehension evaluates per item, one or two of them."""
    if isinstance(node, ast.DictComp):
        yield node.key
        yield node.value
    elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        yield node.elt


def nodes_in_scope(
    node: ast.AST, names: PydanticNames, functions_see: PydanticNames | None = None
) -> Iterator[tuple[ast.AST, PydanticNames]]:
    """Every node in the tree, paired with the pydantic names visible where it sits.

    One module-wide import map applied to the whole tree gets this wrong in both
    directions: it misses a pydantic import made inside a function, and -- the
    dangerous half -- it claims a *parameter* named `constr` is pydantic's and
    rewrites a call that has nothing to do with pydantic.

    ``functions_see`` is what a nested *function* inherits, which differs from
    ``names`` in exactly one place: inside a class body. Python does not put
    class scope on the lookup chain of a method, so a `from pydantic import
    conlist` written in a class body is invisible two lines further down inside
    a method -- and treating it as visible there is the same wrong edit as
    treating it as visible at module level.
    """
    inherited = names if functions_see is None else functions_see
    yield node, names

    if isinstance(node, ast.ClassDef):
        for part in _evaluated_outside(node):
            yield from nodes_in_scope(part, names, inherited)
        # Two things a class body does that a function body does not, both found
        # by review on the first version of this walk. It does not see an
        # enclosing *class* namespace -- so it starts from `inherited`, the same
        # scope a nested function gets, not from `names`. And it binds top to
        # bottom rather than treating the whole body as static locals, so an
        # import written below a call must not reach back up to it.
        body = inherited
        for statement in node.body:
            yield from nodes_in_scope(statement, body, inherited)
            body = _advanced(body, statement)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        for part in _evaluated_outside(node):
            yield from nodes_in_scope(part, names, inherited)
        body = _inside(inherited, node)
        # A lambda's body is a single expression, not a list of statements.
        statements: list[ast.AST] = list(node.body) if isinstance(node.body, list) else [node.body]
        for piece in statements:
            yield from nodes_in_scope(piece, body)
        return

    if isinstance(node, _COMPREHENSIONS):
        own = _without(inherited, _shadowed_in(node))
        for index, generator in enumerate(node.generators):
            # The outermost iterable is evaluated before the comprehension scope
            # exists, out where the comprehension is written. Every later one is
            # not, because the targets before it are bound by then.
            yield from nodes_in_scope(generator.iter, names if index == 0 else own)
            yield from nodes_in_scope(generator.target, own)
            for condition in generator.ifs:
                yield from nodes_in_scope(condition, own)
        for element in _comprehension_elements(node):
            yield from nodes_in_scope(element, own)
        return

    for child in ast.iter_child_nodes(node):
        yield from nodes_in_scope(child, names, functions_see)


def calls_in_scope(node: ast.AST, names: PydanticNames) -> Iterator[tuple[ast.Call, PydanticNames]]:
    """Every call in the tree, paired with the names actually visible where it sits."""
    for child, scope in nodes_in_scope(node, names):
        if isinstance(child, ast.Call):
            yield child, scope


def functions_in_scope(
    tree: ast.Module,
) -> Iterator[tuple[ast.FunctionDef | ast.AsyncFunctionDef, PydanticNames]]:
    """Every `def`, paired with the names visible *where its decorators run*.

    Which is the scope the `def` is written in, not the one it opens -- so a
    rule reading `node.decorator_list` gets the answer Python would give.
    """
    for node, scope in nodes_in_scope(tree, pydantic_names(tree)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node, scope


def regex_keyword_sites(tree: ast.Module) -> Iterator[tuple[int, ast.keyword]]:
    """Yield every `regex=` argument passed to one of pydantic's own callables.

    The keyword node comes back with the line because the rewrite needs the
    column too, and recomputing it from the line would mean finding the word
    `regex` in text that may legitimately contain it more than once.
    """
    for node, scope in calls_in_scope(tree, pydantic_names(tree)):
        if pydantic_name(node, scope) not in _REGEX_CALLABLES:
            continue
        for word in node.keywords:
            if word.arg == "regex":
                yield word.lineno, word


def items_keyword_sites(tree: ast.Module) -> Iterator[tuple[int, ast.keyword]]:
    """Yield every `min_items=`/`max_items=` passed to a constrained collection.

    Shaped like :func:`regex_keyword_sites`, and for the same reason: the
    keyword node carries the column the rewrite needs, and a line can hold more
    than one of these -- `conlist(int, min_items=1, max_items=3)` is two sites.
    """
    for node, scope in calls_in_scope(tree, pydantic_names(tree)):
        if pydantic_name(node, scope) not in _ITEMS_CALLABLES:
            continue
        for word in node.keywords:
            if word.arg in LENGTH_KEYWORDS:
                yield word.lineno, word


_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
"""Comprehensions run in a scope of their own, and their targets are local to it.

This used to say `calls_in_scope` did not need to know, "because a call is not
shadowed by an iteration variable -- a *name* is". The sentence is true about
the wrong node. A call is resolved *through* a name, and
`[conlist(str, min_items=1) for conlist in factories]` is a call whose name the
target shadows: review found it rewriting the element of that comprehension as
though it were pydantic's. `nodes_in_scope` now narrows here for the same
reason `_uses_in_scope` twenty lines down always did.
"""

_NESTED_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, *_COMPREHENSIONS)


def _scope_body_nodes(root: ast.AST) -> Iterator[ast.AST]:
    """Every node inside one scope, without entering a nested one.

    `module_scope_nodes` is this for a module. This is the same idea rooted
    anywhere, so a function body can be examined on its own terms.
    """
    pending: list[ast.AST] = list(ast.iter_child_nodes(root))
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, _NESTED_SCOPES):
            continue
        pending.extend(ast.iter_child_nodes(node))


def _bound_targets(target: ast.expr) -> Iterator[str]:
    """The names one comprehension target binds, unpacking included."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _bound_targets(element)
    elif isinstance(target, ast.Starred):
        yield from _bound_targets(target.value)


def _shadowed_in(scope: ast.AST) -> set[str]:
    """Every name this scope binds itself, and so does not inherit."""
    if isinstance(scope, _COMPREHENSIONS):
        return {name for generator in scope.generators for name in _bound_targets(generator.target)}
    return _locally_bound(scope)[2]


def _uses_in_scope(
    scope: ast.AST, module: str, name: str, inherited: frozenset[str]
) -> Iterator[tuple[int, Role]]:
    """Sites and uses in one scope, then in each scope nested inside it.

    ``inherited`` is the set of names bound to the removed import that are
    visible on the way in. A scope that binds one of those names by any other
    means -- a parameter, an assignment, a nested `def` -- takes it out of that
    set for itself and for everything under it, because a load there reads the
    local binding and would survive the import being deleted.
    """
    shadowed = _shadowed_in(scope)

    here: set[str] = set()
    for node in _scope_body_nodes(scope):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == module:
            for alias in node.names:
                if alias.name == name:
                    here.add(alias.asname or alias.name)
                    yield node.lineno, Role.SITE

    # Subtract before adding: `shadowed` includes the names this scope's own
    # import binds, and those are exactly the ones that must survive.
    visible = frozenset({bound for bound in inherited if bound not in shadowed} | here)

    # An optimisation, not a guard: the test below is `node.id in visible`, so an
    # empty set already yields nothing. It is here because most scopes in a scan
    # never see this name, and it skips a second walk of every one of them --
    # measured at 12.6ms -> 5.9ms on a 400-function module.
    if visible:
        for node in _scope_body_nodes(scope):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in visible:
                yield node.lineno, Role.USE

    for node in _scope_body_nodes(scope):
        if isinstance(node, _NESTED_SCOPES):
            if isinstance(node, _COMPREHENSIONS) and node.generators:
                # The outermost iterable is evaluated out here, before the target
                # it is about to bind exists. Reading it under the comprehension's
                # own names would lose a real use to a name that shadows it only
                # afterwards.
                yield from _loads_under(node.generators[0].iter, visible)
            yield from _uses_in_scope(node, module, name, visible)


def _loads_under(node: ast.AST, visible: frozenset[str]) -> Iterator[tuple[int, Role]]:
    """Every load of a visible name in one expression, scopes inside it aside."""
    if not visible:
        return
    for child in (node, *_scope_body_nodes(node)):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id in visible:
            yield child.lineno, Role.USE


def _removed_symbol_sites(tree: ast.Module, module: str, name: str) -> Iterator[tuple[int, Role]]:
    """Yield every ``from <module> import <name>``, and every use of what it bound.

    Only the import form is a site. Attribute access on an imported module reaches
    the same symbol, but no recorded run breaks that way, and `failures.py` already
    declines to write classifiers for signatures nobody has observed.

    The uses are the reason this is not called ``_removed_import_sites`` any more.
    `pydantic.utils:DUNDER_ATTRIBUTES` is deleted in v2, so the rule says to stop
    importing it -- and in the fixture that actually carries this break, the name
    is *used* two lines further down. Deleting the import on that advice alone was
    measured: it turns a `PydanticImportError` at import time into a `NameError` at
    call time. Reporting the import and staying quiet about the use is how a
    correct rule produces a broken repository.

    The bound name is `asname` when the import renames it, because that is the
    name the rest of the file actually reads.

    Scope is followed rather than assumed. A module-wide set of bound names gets
    this wrong in both directions -- the same two directions `calls_in_scope`
    documents -- and the dangerous one is a parameter that happens to share the
    spelling: the refusal would name that line and claim removing the import
    causes a `NameError` there, which is a specific and checkable false statement
    about somebody's code. Over-reporting is the safe direction for a list that is
    read rather than edited, but only while what is said about each line is true.
    """
    seen: set[int] = set()
    for line, role in _uses_in_scope(tree, module, name, frozenset()):
        if role is Role.SITE:
            yield line, role
        elif line not in seen:
            # One line may read the name more than once (`X or default_for(X)`),
            # and that is one line to go and look at, not two.
            seen.add(line)
            yield line, role


def _sites(rule: Rule, tree: ast.Module) -> Iterator[tuple[int, Role]]:
    """Yield every line this rule has something to say about, and in what role.

    Most break classes report sites and nothing else, so they say so once here
    rather than each threading a constant through its own finder.
    """
    if rule.break_class is BreakClass.VALIDATOR_FIELD_CONFIG:
        return ((line, Role.SITE) for line in _validator_sites(tree))
    if rule.break_class is BreakClass.ROOT_MODEL:
        return ((line, Role.SITE) for line in _root_model_sites(tree))
    if rule.break_class is BreakClass.REGEX_KEYWORD:
        return ((line, Role.SITE) for line, _ in regex_keyword_sites(tree))
    if rule.break_class is BreakClass.ITEMS_KEYWORD:
        return ((line, Role.SITE) for line, _ in items_keyword_sites(tree))
    if rule.break_class is BreakClass.REMOVED_INTERNAL and rule.module and rule.name:
        return _removed_symbol_sites(tree, rule.module, rule.name)
    return iter(())


def _candidate_files(root: Path) -> Iterator[Path]:
    """Yield this project's Python files, in a deterministic order.

    Pruned at the directory level rather than filtered afterwards: descending
    into a virtualenv only to discard every file inside it is work with a
    known-zero yield. Measured on a tree carrying 8,000 vendored files,
    discovery falls from 59ms to 6ms.
    """
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories if name not in _SKIP_DIRECTORIES)
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                yield Path(directory) / filename


def find_matches(rule: Rule, root: Path) -> ScanResult:
    """Find every site under ``root`` where ``rule`` applies.

    A dependency rule matches nothing here, and that is the answer rather than a
    gap: the count says out loud that no edit in this repository fixes it.

    Files that cannot be read or parsed are collected in
    :attr:`ScanResult.unreadable` and do not stop the scan.
    """
    if rule.kind is RuleKind.DEPENDENCY:
        return ScanResult(matches=(), unreadable=())

    matches: list[Match] = []
    unreadable: list[Unreadable] = []
    for path in _candidate_files(root):
        try:
            # read_source honours a BOM or a `# coding:` cookie, so a valid
            # non-UTF-8 source is read rather than written off as unreadable.
            source = read_source(path).text
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
            unreadable.append(Unreadable(path=path, reason=f"could not read: {exc}"))
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, ValueError) as exc:
            unreadable.append(Unreadable(path=path, reason=f"could not parse: {exc}"))
            continue

        lines = source.splitlines()
        for line, role in _sites(rule, tree):
            excerpt = lines[line - 1].strip() if 0 < line <= len(lines) else ""
            matches.append(Match(path=path, line=line, excerpt=excerpt, role=role))

    # ast.walk is documented to yield "in no specified order". Sorting makes the
    # output of two runs comparable, which matters because it is read in a diff.
    matches.sort(key=lambda match: (match.path.as_posix(), match.line, match.role.value))
    return ScanResult(matches=tuple(matches), unreadable=tuple(unreadable))
