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
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from bumpsmith.apply import Edit
from bumpsmith.failures import BreakClass
from bumpsmith.rules import (
    Match,
    Rule,
    ScanResult,
    declares_root_field,
    pydantic_name,
    pydantic_names,
)
from bumpsmith.sources import read_source

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

    Applied last-first so that earlier positions are still valid, and in bytes
    because ``col_offset`` is a byte offset rather than a character index. Each
    replacement states the text it expects to find, and one that is wrong
    abandons the whole file: a position that has drifted is a reason to write
    nothing, never a reason to write a guess.
    """
    lines = _lines(text)
    for item in sorted(replacements, key=lambda r: (r.line, r.col), reverse=True):
        if not 1 <= item.line <= len(lines):
            return None
        raw = lines[item.line - 1].encode("utf-8")
        old = item.old.encode("utf-8")
        if raw[item.col : item.col + len(old)] != old:
            return None
        lines[item.line - 1] = (
            raw[: item.col] + item.new.encode("utf-8") + raw[item.col + len(old) :]
        ).decode("utf-8")
    return "".join(lines)


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


def _by_path(matches: Sequence[Match]) -> dict[Path, list[int]]:
    grouped: dict[Path, list[int]] = {}
    for match in matches:
        grouped.setdefault(match.path, []).append(match.line)
    return grouped


def plan(rule: Rule, scan: ScanResult) -> Plan:
    """Turn the sites a rule matched into the edits that carry it out.

    Raises :class:`UnsupportedRuleError` for a break class with no rewriter, so
    that "nothing to do" and "nobody has written this yet" cannot be confused.

    A scan that could not read every candidate file is still planned from what it
    did read; the incompleteness belongs to the scan and is reported there.
    """
    if rule.break_class is not BreakClass.ROOT_MODEL:
        raise UnsupportedRuleError(
            f"no rewriter is written for {rule.break_class.name}; "
            f"the rule is still the useful output, but it cannot be applied automatically"
        )

    edits: list[Edit] = []
    skipped: list[Skipped] = []
    rewritten = 0
    for path, lines in sorted(_by_path(scan.matches).items(), key=lambda item: item[0].as_posix()):
        edit, file_skipped = _plan_root_model_file(path, sorted(lines))
        skipped.extend(file_skipped)
        if edit is not None:
            edits.append(edit)
            rewritten += len(lines) - len(file_skipped)
    return Plan(edits=tuple(edits), skipped=tuple(skipped), rewritten=rewritten)
