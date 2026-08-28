"""Turn a rule into the edits that carry it out.

:mod:`bumpsmith.rules` says what has to change and where. :mod:`bumpsmith.apply`
guarantees that a set of edits lands together or not at all. This is the part in
between: the smallest piece of text that makes each site correct.

Smallest is the point. The obvious way to rewrite Python with the standard
library is to modify the tree and hand it to :func:`ast.unparse`, and what comes
back has every comment gone, every string requoted and every line rewrapped. The
migration would be correct and the diff would be unreadable, which for a tool
whose output a person has to approve is the same as being wrong. Every edit here
is a text replacement at a position the tree reported, so a file comes back byte
for byte identical apart from the sites the rule matched.

The plan is built from the scan's own matches rather than from a second search.
A rewriter that goes looking for its own sites is a second opinion about what
the rule means, and the two drift; when they do, the edit lands somewhere the
scan never reported. Anything in the matches that cannot be rewritten is
returned as :class:`Skipped` with a reason, never dropped.

Nothing here writes to disk. The plan is edits, and :func:`bumpsmith.apply.attempt`
is what puts them on disk -- and takes them back by default.
"""

import ast
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from bumpsmith.apply import Edit
from bumpsmith.failures import BreakClass
from bumpsmith.rules import (
    LENGTH_KEYWORDS,
    Match,
    Role,
    Rule,
    ScanResult,
    declares_root_field,
    items_keyword_sites,
    pydantic_name,
    pydantic_names,
    regex_keyword_sites,
    root_validator_sites,
    validator_parameter_sites,
)
from bumpsmith.sources import read_source

_V1_REGEX = "regex"
_V2_PATTERN = "pattern"
_DYNAMIC_SCOPE = frozenset({"locals", "vars", "eval", "exec"})
"""Names whose presence means a parameter's uses cannot be read off the tree.

`locals()["field"]` is a read of `field` that is not an :class:`ast.Name` for
it, so the use detector below cannot see it and the deletion would look safe.
Anything here is a refusal rather than a puzzle to solve: whether the string
handed to `eval` names a parameter is not a question a parser answers.

Each member has to be able to reach a *local* by name, which is why `globals`
is not one. It was, briefly. A parameter is a local and the module namespace
does not hold it, so a body doing nothing dynamic but calling `globals()` was
being refused with a reason that was not true of it -- and a guard is allowed
to cost a false refusal only when the reason it gives for one is honest.
"""

_SEPARATOR = re.compile(r"^\s*,\s*$")
"""What may sit between two parameters for the first to be removable.

A comma and whitespace. Anything else there -- a comment, most of all -- is
something a person wrote that a parameter deletion has no business taking with
it, and the site is skipped instead.
"""
_ROOT_FIELD = "__root__"
_V2_ROOT_FIELD = "root"
_BASE_MODEL = "BaseModel"
_ROOT_MODEL = "RootModel"

_UNREADABLE = (OSError, UnicodeError, LookupError, SyntaxError, ValueError)
"""Everything that can go wrong between a path and a parsed tree.

``SyntaxError`` for a file this Python cannot parse, ``ValueError`` for source
containing a null byte, and the rest from reading and decoding.
"""


class RewriteError(Exception):
    """A rule could not be turned into edits."""


class UnsupportedRuleError(RewriteError):
    """No rewriter is written for this break class.

    Raised rather than returning an empty plan. A plan with no edits and no
    explanation is indistinguishable from a repository that needed no changes.
    """


@dataclass(frozen=True, slots=True)
class Skipped:
    """A site the rewriter would not touch, and why.

    Carries the same path and line the scan reported, so a reader can line the
    two lists up and see that every match was accounted for.
    """

    path: Path
    line: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}  {self.reason}"


@dataclass(frozen=True, slots=True)
class Plan:
    """Edits that carry out a rule, and the sites that were left alone."""

    edits: tuple[Edit, ...]
    skipped: tuple[Skipped, ...]
    rewritten: int
    """How many matched sites the edits cover.

    Counted in sites rather than files because the rule matched sites. One file
    holding nineteen of them is one edit, and reporting ``1`` would understate
    the change a reviewer is being asked to approve.
    """

    @property
    def is_complete(self) -> bool:
        """True when every match became an edit."""
        return not self.skipped


@dataclass(frozen=True, slots=True)
class _Replacement:
    """One stretch of text swapped for another, at a position the tree reported."""

    line: int
    """1-based, the way :mod:`ast` counts."""

    col: int
    """Byte offset into the UTF-8 encoding of that line, the way :mod:`ast` counts."""

    old: str
    """What is expected there. An insertion is the empty string."""

    new: str


_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def _lines(text: str) -> list[str]:
    """Split the way the parser counts lines, keeping the endings.

    Not :meth:`str.splitlines`, which also breaks on form feed, vertical tab and
    several Unicode separators. Those are legal inside Python source and the
    parser does not count them as line breaks, so using it would shift every line
    number after the first one and put edits somewhere nobody asked for.
    """
    out: list[str] = []
    start = 0
    for match in _LINE_BREAK.finditer(text):
        out.append(text[start : match.end()])
        start = match.end()
    out.append(text[start:])
    return out


def _replace(text: str, replacements: Iterable[_Replacement]) -> str | None:
    """Apply every replacement, or return ``None`` if any position does not hold.

    Positions arrive as a line and a byte offset into that line, the way
    :mod:`ast` reports them, and are resolved here to one offset into the whole
    encoded source. Resolving them is what lets ``old`` cross a line ending,
    which a deletion has to: the parameter being removed and the comma that
    joined it to what came before are not always on the same line.

    In bytes throughout, because ``col_offset`` is a byte offset rather than a
    character index. Applied last-first so that earlier offsets are still valid.
    Each replacement states the text it expects to find, and one that is wrong
    abandons the whole file: a position that has drifted is a reason to write
    nothing, never a reason to write a guess.
    """
    data = text.encode("utf-8")
    lines = [line.encode("utf-8") for line in _lines(text)]
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    resolved: list[tuple[int, int, bytes]] = []
    for item in replacements:
        if not 1 <= item.line <= len(lines):
            return None
        # Bounded to its own line before being used as an offset into the whole
        # text. Without this a column past the end of a short line would run on
        # into the next one and could match there, which is a position that has
        # drifted reading as a position that holds.
        if item.col > len(lines[item.line - 1]):
            return None
        start = starts[item.line - 1] + item.col
        old = item.old.encode("utf-8")
        if data[start : start + len(old)] != old:
            return None
        resolved.append((start, len(old), item.new.encode("utf-8")))

    for start, length, new in sorted(resolved, key=lambda item: item[0], reverse=True):
        data = data[:start] + new + data[start + length :]
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Only reachable from a position landing inside a multi-byte character,
        # which is the same drift the checks above exist for and gets the same
        # answer: write nothing.
        return None


def _own_namespace_nodes(tree: ast.Module) -> Iterator[ast.AST]:
    """Yield every node that can bind a name in the module's own namespace.

    Narrower than :func:`bumpsmith.rules.module_scope_nodes`, deliberately. That
    one descends into class bodies, because for *counting* sites an import is
    evidence about the file whatever block it sits in. A class body has its own
    namespace, so an import inside one binds an attribute rather than a module
    name. Fine to notice; wrong to extend, and wrong to trust for a name about to
    be written into a base class.
    """
    pending: list[ast.AST] = [tree]
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        pending.extend(ast.iter_child_nodes(node))


def _targets(target: ast.expr) -> Iterator[str]:
    """The names one assignment target binds, unpacking as far as it goes.

    `RootModel, other = pair()` binds `RootModel`. Reading only bare
    :class:`ast.Name` targets misses it, and a missed binding is a name this
    module believes it owns when it does not.
    """
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _targets(element)
    elif isinstance(target, ast.Starred):
        yield from _targets(target.value)


def _bindings(tree: ast.Module) -> dict[str, list[ast.AST]]:
    """Every module-scope binding of every name, keyed by name.

    A list rather than a set because the count is the point. One binding can be
    checked; two mean something rebound the name, and which one is live where the
    class is defined is not a question this can answer by reading imports.
    """
    found: dict[str, list[ast.AST]] = {}

    def note(name: str, node: ast.AST) -> None:
        found.setdefault(name, []).append(node)

    for node in _own_namespace_nodes(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            note(node.name, node)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                note(alias.asname or alias.name.split(".")[0], node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name in _targets(target):
                    note(name, node)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.NamedExpr)):
            for name in _targets(node.target):
                note(name, node)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for name in _targets(node.optional_vars):
                note(name, node)
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            note(node.name, node)
    return found


def _bound_only_by_pydantic(bindings: dict[str, list[ast.AST]], bound: str, real: str) -> bool:
    """Whether ``bound`` is this module's name for pydantic's ``real``, and only that.

    Two bindings is a refusal, not a tie-break. `from pydantic import BaseModel`
    followed by `BaseModel = Other` leaves a name that reads as pydantic's and is
    not, and rewriting the base of a class that was never a pydantic model is the
    exact search-and-replace failure the rule machinery exists to avoid.
    """
    found = bindings.get(bound, [])
    if len(found) != 1:
        return False
    node = found[0]
    return (
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "pydantic"
        and any(
            (alias.asname or alias.name) == bound and alias.name == real for alias in node.names
        )
    )


def _bound_only_by_importing_pydantic(bindings: dict[str, list[ast.AST]], bound: str) -> bool:
    """Whether ``bound`` is this module's name for the pydantic module itself."""
    found = bindings.get(bound, [])
    if len(found) != 1:
        return False
    node = found[0]
    return isinstance(node, ast.Import) and any(
        (alias.asname or alias.name.split(".")[0]) == bound and _is_pydantic_module(alias.name)
        for alias in node.names
    )


def _is_pydantic_module(dotted: str) -> bool:
    return dotted == "pydantic" or dotted.startswith("pydantic.")


def _root_sites(tree: ast.Module) -> dict[int, list[tuple[ast.ClassDef, ast.stmt]]]:
    """Every ``__root__`` declaration in the tree, keyed by the line it is on.

    Walks the whole tree and uses the scan's own predicate, because a site the
    scan reported has to be findable here by the same definition.
    """
    sites: dict[int, list[tuple[ast.ClassDef, ast.stmt]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if declares_root_field(statement):
                sites.setdefault(statement.lineno, []).append((node, statement))
    return sites


def _field_targets(statement: ast.stmt) -> list[ast.Name]:
    """The ``__root__`` names this statement binds."""
    if isinstance(statement, ast.AnnAssign):
        return [statement.target] if isinstance(statement.target, ast.Name) else []
    if isinstance(statement, ast.Assign):
        return [t for t in statement.targets if isinstance(t, ast.Name) and t.id == _ROOT_FIELD]
    return []


def _base_is_certain(base: ast.expr, bindings: dict[str, list[ast.AST]]) -> bool:
    """Whether this base demonstrably *is* pydantic's BaseModel where it is written.

    `pydantic_name` answers what the imports imply, which is the right question
    for counting sites. Changing a base class needs the stronger one: that no
    later statement rebound the name out from under the import.
    """
    if isinstance(base, ast.Name):
        return _bound_only_by_pydantic(bindings, base.id, _BASE_MODEL)
    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
        return _bound_only_by_importing_pydantic(bindings, base.value.id)
    return False


def _base_replacement(base: ast.expr) -> _Replacement | None:
    """Swap ``BaseModel`` for ``RootModel`` wherever this base names it.

    Two shapes reach here: a bare name, whatever it was imported as, and an
    attribute on the module. The attribute form needs no import added, so only
    the name form is reported back as needing one.
    """
    if isinstance(base, ast.Name):
        return _Replacement(base.lineno, base.col_offset, base.id, _ROOT_MODEL)
    if isinstance(base, ast.Attribute) and base.end_lineno is not None:
        # `pydantic.BaseModel` -- only the attribute changes, and its position is
        # the end of the expression walked back by the length of the name.
        col = base.end_col_offset
        if col is None:
            return None
        return _Replacement(
            base.end_lineno, col - len(base.attr.encode("utf-8")), base.attr, _ROOT_MODEL
        )
    return None


def _import_replacement(tree: ast.Module) -> _Replacement | None:
    """Add ``RootModel`` to an existing ``from pydantic import ...``.

    Appended after the last name rather than rebuilt, so a parenthesised import
    spanning several lines keeps its shape and a one-line import keeps its line.

    Only a direct child of the module body qualifies. An import nested in a class
    body binds an attribute, and one under `if TYPE_CHECKING:` binds nothing at
    all at runtime -- extending either produces a file that raises `NameError`
    while defining the class this rewrite just changed.
    """
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 0 or node.module != "pydantic":
            continue
        if not node.names or any(alias.name == "*" for alias in node.names):
            continue
        last = node.names[-1]
        if last.end_lineno is None or last.end_col_offset is None:
            continue
        return _Replacement(last.end_lineno, last.end_col_offset, "", f", {_ROOT_MODEL}")
    return None


_GONE = "the site the scan reported is not there any more"

_MOVED = (
    "the line holds more sites than the scan reported, so which of them it "
    "meant cannot be told apart from the ones that arrived since"
)
"""Why a line that *gained* sites is left alone entirely.

A line that lost one was already handled: the survivors are rewritten and the
difference is reported skipped. A line that gained one was not, and review found
the gap -- the planner took the first `wanted` of whatever the fresh parse
returned, which on a line whose new site sorts first means rewriting a keyword
the scan never saw and calling the plan complete.

The remaining case is a site replaced by another at the same count, and nothing
in `(path, line)` can tell those apart: the scan would have to carry the column,
which is a wider change than the window it closes. That window needs a writer
editing the tree between the scan and the plan of one run, and inside one run
the file does not move. Both leftovers stay honest for the same reason: the
finder re-ran, so anything rewritten is a real site, and a suite that goes red
reverts the edit byte-for-byte regardless.
"""


def _plan_root_model_file(path: Path, lines: Sequence[int]) -> tuple[Edit | None, list[Skipped]]:
    """Build one file's edit from the sites the scan reported in it."""
    try:
        source = read_source(path)
        tree = ast.parse(source.text)
    except _UNREADABLE as exc:
        return None, [Skipped(path, line, f"could not be read: {exc!r}") for line in lines]

    names = pydantic_names(tree)
    bindings = _bindings(tree)

    # `RootModel` is about to be written into this file, so the question is not
    # whether it was imported once but whether the name still means what the
    # import said. An import followed by a rebinding is a name that reads as
    # pydantic's and is not.
    already_imported = _bound_only_by_pydantic(bindings, _ROOT_MODEL, _ROOT_MODEL)
    if not already_imported and _ROOT_MODEL in bindings:
        reason = f"the name {_ROOT_MODEL} is already used in this file for something else"
        return None, [Skipped(path, line, reason) for line in lines]

    sites = _root_sites(tree)
    # Keyed by position so that two matched sites in one class cannot each add
    # the same base replacement, which would then be applied twice.
    replacements: dict[tuple[int, int], _Replacement] = {}
    skipped: list[Skipped] = []
    needs_import = False
    rewritten = 0

    # A line can hold more than one declaration -- `__root__: int = 1; x: int = 2`
    # is one line and two statements -- and the scan reports a line per site, so
    # the same line can also arrive twice. Both are handled by working through
    # every statement on a reported line and counting each statement once.
    seen: set[tuple[int, int]] = set()
    for line in lines:
        found = sites.get(line)
        if not found:
            skipped.append(Skipped(path, line, "the site the scan reported is not there any more"))
            continue

        for node, statement in found:
            here = (statement.lineno, statement.col_offset)
            if here in seen:
                continue
            seen.add(here)

            targets = _field_targets(statement)
            if not targets:
                skipped.append(
                    Skipped(path, line, f"{_ROOT_FIELD} is bound in a shape not handled")
                )
                continue

            bases = [
                base
                for base in node.bases
                if pydantic_name(base, names) == _BASE_MODEL and _base_is_certain(base, bindings)
            ]
            if len(bases) != 1:
                skipped.append(
                    Skipped(
                        path,
                        line,
                        f"{node.name} declares {_ROOT_FIELD} but does not demonstrably inherit "
                        f"pydantic's {_BASE_MODEL} exactly once, so what its base should become "
                        f"is a guess",
                    )
                )
                continue

            base_replacement = _base_replacement(bases[0])
            if base_replacement is None:
                skipped.append(Skipped(path, line, f"{node.name}'s base is in a shape not handled"))
                continue

            for target in targets:
                replacements[(target.lineno, target.col_offset)] = _Replacement(
                    target.lineno, target.col_offset, _ROOT_FIELD, _V2_ROOT_FIELD
                )
            replacements[(base_replacement.line, base_replacement.col)] = base_replacement
            needs_import = needs_import or isinstance(bases[0], ast.Name)
            rewritten += 1

    if not replacements:
        return None, skipped

    if needs_import and not already_imported:
        added = _import_replacement(tree)
        if added is None:
            reason = f"{_ROOT_MODEL} has to be imported and there is no plain pydantic import to add it to"
            return None, [Skipped(path, line, reason) for line in lines]
        replacements[(added.line, added.col)] = added

    after = _replace(source.text, replacements.values())
    if after is None:
        reason = "the source moved under the positions the parser reported"
        return None, [Skipped(path, line, reason) for line in lines]

    edit = Edit(path=path, before=source.text, after=after, encoding=source.encoding)
    return (edit if edit.changes_anything else None), skipped


def _positional_defaults(
    arguments: ast.arguments,
) -> list[tuple[ast.arg, ast.expr | None]]:
    """Pair every positional parameter with its default, or with ``None``.

    :attr:`ast.arguments.defaults` is a bare list that aligns to the *end* of
    ``posonlyargs + args``, so the pairing has to be counted from the right. The
    default matters because it is part of the parameter: removing ``field`` from
    ``field=None`` and leaving the ``=None`` behind is a syntax error.
    """
    positional = [*arguments.posonlyargs, *arguments.args]
    offset = len(positional) - len(arguments.defaults)
    paired: list[tuple[ast.arg, ast.expr | None]] = []
    for index, argument in enumerate(positional):
        default = arguments.defaults[index - offset] if index >= offset else None
        paired.append((argument, default))
    return paired


def _element_span(argument: ast.arg, default: ast.expr | None) -> tuple[int, int, int, int]:
    """Where one parameter starts and ends, counting its annotation and default.

    ``arg.end_col_offset`` already covers an annotation. A default is a sibling
    node rather than a child, so it has to be reached for separately.
    """
    end_line = argument.end_lineno if argument.end_lineno is not None else argument.lineno
    end_col = (
        argument.end_col_offset if argument.end_col_offset is not None else argument.col_offset
    )
    if (
        default is not None
        and default.end_lineno is not None
        and default.end_col_offset is not None
        and (default.end_lineno, default.end_col_offset) > (end_line, end_col)
    ):
        end_line, end_col = default.end_lineno, default.end_col_offset
    return argument.lineno, argument.col_offset, end_line, end_col


def _names_used(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Every name this function reads or writes anywhere inside itself.

    Parameters are :class:`ast.arg` nodes rather than :class:`ast.Name`, so a
    parameter that is never used contributes nothing here -- which is the whole
    question being asked. ``global`` and ``nonlocal`` carry their names as plain
    strings and would otherwise be invisible.

    Deliberately blunt: a nested function with its own ``field`` parameter
    registers a use that shadowing makes harmless. Reading it as a use costs a
    skip with a reason on it; missing a real one costs a NameError at runtime in
    somebody else's repository.

    What it cannot see is a name reached without being written -- ``locals()``,
    ``eval`` and the rest of :data:`_DYNAMIC_SCOPE`. Those are not detected here
    because they are not uses of the parameter; they are evidence that uses may
    exist which this function is not able to find. :func:`_drop_parameters`
    treats them as such.
    """
    used: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Name):
            used.add(inner.id)
        elif isinstance(inner, (ast.Global, ast.Nonlocal)):
            used.update(inner.names)
    return used


def _drop_parameters(
    source: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    offending: Sequence[ast.arg],
) -> tuple[list[_Replacement], str | None]:
    """Delete ``field`` and ``config`` from a validator's signature.

    That deletion is the whole fix, and it is worth saying why it is not the
    rename the rule's name suggests. Under V2's ``@validator`` shim a parameter
    called ``info`` is refused outright -- "Unsupported signature for V1 style
    validator" -- because ``info`` belongs to ``@field_validator``, the V2
    decorator. ``values`` is still accepted and still carries what it did. So the
    smallest text that makes the site correct is the removal, and a rewrite to
    ``info`` would trade one raised error for another.

    Each deletion spans from the end of the parameter before it to the end of
    itself, which is what takes the separating comma with it. Returns the
    replacements, or a reason nothing can be written.
    """
    used = _names_used(node)
    # Asked before the parameter names are, because it is a different question.
    # The check below finds uses; this one establishes whether finding them is
    # possible at all. A body holding `locals()["field"]` reads the parameter
    # without ever naming it in a way the tree records, so a clean answer from
    # the use check would be an absence of evidence read as evidence of absence.
    dynamic = sorted(used & _DYNAMIC_SCOPE)
    if dynamic:
        names = " and ".join(f"`{name}`" for name in dynamic)
        return [], (
            f"{node.name} calls {names}, so what it reads cannot be settled by "
            f"reading it; a parameter removed here could still be reached by name "
            f"at runtime"
        )

    reading = sorted({argument.arg for argument in offending} & used)
    if reading:
        names = " and ".join(f"`{name}`" for name in reading)
        return [], (
            f"{node.name} reads {names} somewhere inside itself, and V2 passes "
            f"nothing to rebind it from; removing the parameter would leave a "
            f"name that is not defined"
        )

    positional = _positional_defaults(node.args)
    deletable = {id(argument) for argument, _ in positional}
    elsewhere = [argument.arg for argument in offending if id(argument) not in deletable]
    if elsewhere:
        names = " and ".join(f"`{name}`" for name in sorted(elsewhere))
        return [], (
            f"{node.name} declares {names} keyword-only or positional-only, and "
            f"removing it there can leave a bare `*` or `/` that will not parse"
        )

    spans = [_element_span(argument, default) for argument, default in positional]
    wanted = {id(argument) for argument in offending}
    encoded = source.encode("utf-8")
    lines = [line.encode("utf-8") for line in _lines(source)]
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line)

    def at(line: int, col: int) -> int:
        return starts[line - 1] + col

    replacements: list[_Replacement] = []
    for index, (argument, _default) in enumerate(positional):
        if id(argument) not in wanted:
            continue
        if index == 0:
            # No parameter before it to attach the comma to. A pydantic
            # validator always has `cls` first, so this is unreachable in the
            # shapes that reach here -- and a deletion that guessed which side
            # the comma was on is not worth writing on the strength of that.
            return [], (
                f"{node.name} declares `{argument.arg}` first, where there is no "
                f"separator to remove with it"
            )
        _, _, previous_line, previous_col = spans[index - 1]
        start_line, start_col, end_line, end_col = spans[index]
        start = at(previous_line, previous_col)
        boundary = at(start_line, start_col)
        end = at(end_line, end_col)
        separator = encoded[start:boundary].decode("utf-8")
        removed = encoded[start:end].decode("utf-8")
        if not _SEPARATOR.fullmatch(separator) or "#" in removed:
            return [], (
                f"{node.name}'s `{argument.arg}` is separated from what comes "
                f"before it by something other than a comma, so removing it "
                f"would take that with it"
            )
        replacements.append(_Replacement(previous_line, previous_col, removed, ""))
    return replacements, None


def _plan_validator_file(path: Path, lines: Sequence[int]) -> tuple[Edit | None, list[Skipped]]:
    """Remove `field` and `config` from the validators the scan reported.

    The signature is the only thing that changes. A validator body that used
    either name is not rewritten at all -- see :func:`_drop_parameters` for why
    the alternative is a name that is not defined.
    """
    try:
        source = read_source(path)
        tree = ast.parse(source.text)
    except _UNREADABLE as exc:
        return None, [Skipped(path, line, f"could not be read: {exc!r}") for line in lines]

    by_line: dict[
        int, list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, tuple[ast.arg, ...]]]
    ] = {}
    for line, node, offending in validator_parameter_sites(tree):
        by_line.setdefault(line, []).append((node, offending))

    replacements: dict[tuple[int, int], _Replacement] = {}
    skipped: list[Skipped] = []
    # A `def` line holds one function, so unlike the other rewriters this cannot
    # see the same line twice from distinct sites -- but the scan can still
    # report a line twice, and counting one function once is what keeps
    # `rewritten` honest when it does.
    seen: set[tuple[int, int]] = set()
    for line in sorted(set(lines)):
        found = by_line.get(line)
        if not found:
            skipped.append(Skipped(path, line, "the site the scan reported is not there any more"))
            continue
        for node, offending in found:
            here = (node.lineno, node.col_offset)
            if here in seen:
                continue
            seen.add(here)
            dropped, reason = _drop_parameters(source.text, node, offending)
            if reason is not None:
                skipped.append(Skipped(path, line, reason))
                continue
            for item in dropped:
                replacements[(item.line, item.col)] = item

    if not replacements:
        return None, skipped

    after = _replace(source.text, replacements.values())
    if after is None:
        reason = "the source moved under the positions the parser reported"
        return None, [Skipped(path, line, reason) for line in lines]

    edit = Edit(path=path, before=source.text, after=after, encoding=source.encoding)
    return (edit if edit.changes_anything else None), skipped


def _plan_keyword_rename(
    path: Path,
    lines: Sequence[int],
    finder: Callable[[ast.Module], Iterator[tuple[int, ast.keyword]]],
    rename: Mapping[str, str],
) -> tuple[Edit | None, list[Skipped]]:
    """Rename keyword arguments in place, at the sites the scan reported.

    Two break classes are this and nothing else -- `regex=` to `pattern=`, and
    `min_items=`/`max_items=` to their `_length` spellings. They differ only in
    which call the finder looks inside and what each keyword is renamed to, so
    they share the part that is easy to get subtly wrong: matching reported
    lines to keyword nodes when a line can hold more than one.

    The whole break is one word per site, which is what makes it a good check on
    the machinery: if the diff is bigger than that, the machinery is wrong.
    """
    try:
        source = read_source(path)
        tree = ast.parse(source.text)
    except _UNREADABLE as exc:
        return None, [Skipped(path, line, f"could not be read: {exc!r}") for line in lines]

    # Grouped rather than keyed one-to-one: two renamable arguments can share a
    # line, and the scan reports a line per site, so the mapping is not unique.
    by_line: dict[int, list[ast.keyword]] = {}
    for line, word in finder(tree):
        by_line.setdefault(line, []).append(word)

    replacements: dict[tuple[int, int], _Replacement] = {}
    skipped: list[Skipped] = []
    # Matched one occurrence to one keyword rather than line to line. Two sites
    # can share a line, and if one of them has gone since the scan the other must
    # not quietly stand in for it: that reports two rewritten, writes one, and
    # calls the plan complete.
    for line in sorted(set(lines)):
        wanted = lines.count(line)
        words = by_line.get(line, [])
        if len(words) > wanted:
            skipped.extend(Skipped(path, line, _MOVED) for _ in range(wanted))
            continue
        for word in words[:wanted]:
            # `arg` is None for `**kwargs`, which has no name to rename. The
            # finders never yield one -- they match on the name -- so this
            # skips nothing today; it is here because the type says it can
            # happen and a rewriter is the wrong place to be sure it cannot.
            name = word.arg
            if name is None:
                continue
            replacements[(word.lineno, word.col_offset)] = _Replacement(
                word.lineno, word.col_offset, name, rename[name]
            )
        for _ in range(wanted - len(words)):
            skipped.append(Skipped(path, line, _GONE))

    if not replacements:
        return None, skipped

    after = _replace(source.text, replacements.values())
    if after is None:
        reason = "the source moved under the positions the parser reported"
        return None, [Skipped(path, line, reason) for line in lines]

    edit = Edit(path=path, before=source.text, after=after, encoding=source.encoding)
    return (edit if edit.changes_anything else None), skipped


def _plan_regex_file(path: Path, lines: Sequence[int]) -> tuple[Edit | None, list[Skipped]]:
    """Rename `regex=` to `pattern=` at the sites the scan reported in one file."""
    return _plan_keyword_rename(path, lines, regex_keyword_sites, {_V1_REGEX: _V2_PATTERN})


def _plan_items_file(path: Path, lines: Sequence[int]) -> tuple[Edit | None, list[Skipped]]:
    """Rename `min_items=`/`max_items=` to their v2 spellings in one file."""
    return _plan_keyword_rename(path, lines, items_keyword_sites, LENGTH_KEYWORDS)


_SKIP_ON_FAILURE = "skip_on_failure=True"

_EMPTY_CALL = re.compile(r"(?P<name>[\w.]+)\(\s*\)")
_PLAIN_NAME = re.compile(r"[\w.]+")


def _span(text: str, node: ast.expr) -> str | None:
    """The source of one expression, when it lies on a single line.

    Read out of the file rather than reconstructed from the tree. `ast.unparse`
    would give a normalised spelling, and the whole contract of
    :class:`_Replacement` is that `old` is what is actually there.
    """
    if node.end_lineno is None or node.end_col_offset is None or node.lineno != node.end_lineno:
        return None
    lines = [line.encode("utf-8") for line in _lines(text)]
    if not 1 <= node.lineno <= len(lines):
        return None
    try:
        return lines[node.lineno - 1][node.col_offset : node.end_col_offset].decode("utf-8")
    except UnicodeDecodeError:
        return None


def _skip_on_failure(text: str, node: ast.expr) -> _Replacement | None:
    """How to give one `@root_validator` the argument v2 demands, or ``None``.

    Three shapes, and the third is an insertion rather than a substitution:
    `@root_validator` grows a call, `@root_validator()` gains an argument
    between its parentheses, and `@root_validator(allow_reuse=True)` gains one
    after the last it already has.
    """
    if not isinstance(node, ast.Call):
        span = _span(text, node)
        if span is None or _PLAIN_NAME.fullmatch(span) is None:
            return None
        return _Replacement(node.lineno, node.col_offset, span, f"{span}({_SKIP_ON_FAILURE})")

    if not node.args and not node.keywords:
        span = _span(text, node)
        match = _EMPTY_CALL.fullmatch(span) if span is not None else None
        if span is None or match is None:
            return None
        return _Replacement(
            node.lineno, node.col_offset, span, f"{match['name']}({_SKIP_ON_FAILURE})"
        )

    # After the last argument, wherever that is. Written as an insertion so the
    # existing arguments keep their own spelling -- reformatting somebody's
    # decorator is not this rule's business.
    ends = [
        (item.end_lineno, item.end_col_offset)
        for item in (*node.args, *(word.value for word in node.keywords))
        if item.end_lineno is not None and item.end_col_offset is not None
    ]
    if not ends:
        return None
    line, col = max(ends)
    return _Replacement(line, col, "", f", {_SKIP_ON_FAILURE}")


def _plan_root_validator_file(
    path: Path, lines: Sequence[int]
) -> tuple[Edit | None, list[Skipped]]:
    """Add `skip_on_failure=True` to the root validators v2 refuses, in one file."""
    try:
        source = read_source(path)
        tree = ast.parse(source.text)
    except _UNREADABLE as exc:
        return None, [Skipped(path, line, f"could not be read: {exc!r}") for line in lines]

    by_line: dict[int, list[tuple[ast.expr, bool]]] = {}
    for line, node, rewritable in root_validator_sites(tree):
        by_line.setdefault(line, []).append((node, rewritable))

    replacements: dict[tuple[int, int], _Replacement] = {}
    skipped: list[Skipped] = []
    for line in sorted(set(lines)):
        wanted = lines.count(line)
        found = by_line.get(line, [])
        for node, rewritable in found[:wanted]:
            if not rewritable:
                skipped.append(
                    Skipped(
                        path,
                        line,
                        "`pre` or `skip_on_failure` is passed as something this cannot read, "
                        "so whether v2 already accepts this decorator is not decidable here",
                    )
                )
                continue
            made = _skip_on_failure(source.text, node)
            if made is None:
                skipped.append(
                    Skipped(path, line, "the decorator is not written in a shape this can extend")
                )
                continue
            replacements[(made.line, made.col)] = made
        for _ in range(wanted - len(found[:wanted])):
            skipped.append(Skipped(path, line, "the site the scan reported is not there any more"))

    if not replacements:
        return None, skipped

    after = _replace(source.text, replacements.values())
    if after is None:
        reason = "the source moved under the positions the parser reported"
        return None, [Skipped(path, line, reason) for line in lines]

    edit = Edit(path=path, before=source.text, after=after, encoding=source.encoding)
    return (edit if edit.changes_anything else None), skipped


_USES_LISTED = 5
"""How many use sites the refusal names before it summarises the rest.

A refusal a person cannot read is a refusal they will skip. The full list is in
the scan either way.
"""


_PLANNERS = {
    BreakClass.VALIDATOR_FIELD_CONFIG: _plan_validator_file,
    BreakClass.ROOT_MODEL: _plan_root_model_file,
    BreakClass.REGEX_KEYWORD: _plan_regex_file,
    BreakClass.ITEMS_KEYWORD: _plan_items_file,
    BreakClass.ROOT_VALIDATOR_SKIP: _plan_root_validator_file,
}
"""The break classes that can be carried out, not the ones that can be named.

A rule is useful output on its own -- it says what is wrong and where, and a
person can act on it. Only some of them reduce to an edit safe enough to write
without asking.
"""


def has_rewriter(break_class: BreakClass) -> bool:
    """Whether this class reduces to an edit, rather than to a rule and a stop.

    Public because the answer is documented -- the README's taxonomy table has a
    rewriter column -- and a documented fact should be derivable rather than
    retyped. :mod:`tests.test_docs` reads it.
    """
    return break_class in _PLANNERS


def _by_path(matches: Sequence[Match]) -> dict[Path, list[int]]:
    """Group the lines to edit by file.

    Sites only. A scan may also report *uses* -- lines that break if a site is
    removed and nothing else is -- and those are for a person to read, never for
    a planner to rewrite. Filtering here rather than in each planner means a
    rewriter written later cannot forget to.
    """
    grouped: dict[Path, list[int]] = {}
    for match in matches:
        if match.role is not Role.SITE:
            continue
        grouped.setdefault(match.path, []).append(match.line)
    return grouped


def plan(rule: Rule, scan: ScanResult) -> Plan:
    """Turn the sites a rule matched into the edits that carry it out.

    Raises :class:`UnsupportedRuleError` for a break class with no rewriter, so
    that "nothing to do" and "nobody has written this yet" cannot be confused.

    A scan that could not read every candidate file is still planned from what it
    did read; the incompleteness belongs to the scan and is reported there.
    """
    planner = _PLANNERS.get(rule.break_class)
    if planner is None:
        # The uses belong in this message and not only in the report. This is the
        # sentence a person reads at the moment they are told to do it by hand,
        # and "stop importing X" acted on alone is what produces a `NameError`.
        where = ""
        if scan.uses:
            listed = ", ".join(
                f"{use.path.as_posix()}:{use.line}" for use in scan.uses[:_USES_LISTED]
            )
            more = len(scan.uses) - _USES_LISTED
            if more > 0:
                listed += f", and {more} more"
            where = (
                f"; the name is still read at {listed}, so removing the "
                f"{'sites' if len(scan.sites) != 1 else 'site'} alone would replace this "
                f"error with a NameError"
            )
        raise UnsupportedRuleError(
            f"no rewriter is written for {rule.break_class.name}; "
            f"the rule is still the useful output, but it cannot be applied automatically"
            f"{where}"
        )

    edits: list[Edit] = []
    skipped: list[Skipped] = []
    rewritten = 0
    for path, lines in sorted(_by_path(scan.matches).items(), key=lambda item: item[0].as_posix()):
        edit, file_skipped = planner(path, sorted(lines))
        skipped.extend(file_skipped)
        if edit is not None:
            edits.append(edit)
            rewritten += len(lines) - len(file_skipped)
    return Plan(edits=tuple(edits), skipped=tuple(skipped), rewritten=rewritten)
