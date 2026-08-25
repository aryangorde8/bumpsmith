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
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from bumpsmith.apply import Edit
from bumpsmith.failures import BreakClass
from bumpsmith.rules import (
    Match,
    Rule,
    ScanResult,
    declares_root_field,
    module_scope_nodes,
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


def _module_bindings(tree: ast.Module) -> set[str]:
    """Every name bound at module scope, however it was bound."""
    bound: set[str] = set()
    for node in module_scope_nodes(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Assign):
            bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
    return bound


def _root_sites(tree: ast.Module) -> dict[int, tuple[ast.ClassDef, ast.stmt]]:
    """Every ``__root__`` declaration in the tree, keyed by the line it is on.

    Walks the whole tree and uses the scan's own predicate, because a site the
    scan reported has to be findable here by the same definition.
    """
    sites: dict[int, tuple[ast.ClassDef, ast.stmt]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if declares_root_field(statement):
                sites[statement.lineno] = (node, statement)
    return sites


def _field_targets(statement: ast.stmt) -> list[ast.Name]:
    """The ``__root__`` names this statement binds."""
    if isinstance(statement, ast.AnnAssign):
        return [statement.target] if isinstance(statement.target, ast.Name) else []
    if isinstance(statement, ast.Assign):
        return [t for t in statement.targets if isinstance(t, ast.Name) and t.id == _ROOT_FIELD]
    return []


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
    """
    for node in module_scope_nodes(tree):
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
    already_imported = names.direct.get(_ROOT_MODEL) == _ROOT_MODEL
    if not already_imported and _ROOT_MODEL in _module_bindings(tree):
        reason = f"the name {_ROOT_MODEL} is already used in this file for something else"
        return None, [Skipped(path, line, reason) for line in lines]

    sites = _root_sites(tree)
    # Keyed by position so that two matched sites in one class cannot each add
    # the same base replacement, which would then be applied twice.
    replacements: dict[tuple[int, int], _Replacement] = {}
    skipped: list[Skipped] = []
    needs_import = False
    rewritten = 0

    for line in lines:
        site = sites.get(line)
        if site is None:
            skipped.append(Skipped(path, line, "the site the scan reported is not there any more"))
            continue
        node, statement = site
        targets = _field_targets(statement)
        if not targets:
            skipped.append(Skipped(path, line, f"{_ROOT_FIELD} is bound in a shape not handled"))
            continue

        bases = [base for base in node.bases if pydantic_name(base, names) == _BASE_MODEL]
        if len(bases) != 1:
            skipped.append(
                Skipped(
                    path,
                    line,
                    f"{node.name} declares {_ROOT_FIELD} but does not inherit pydantic's "
                    f"{_BASE_MODEL} exactly once, so what its base should become is a guess",
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
