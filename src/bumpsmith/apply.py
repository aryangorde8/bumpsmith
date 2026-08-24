"""Apply edits as a transaction that can always be taken back.

Reverting is the **default**. A caller earns a change by saying :meth:`keep`
after checking that it helped; an exception, a crash, or simply forgetting all
land in the same place -- the tree exactly as it was. That ordering is the whole
design. A tool that edits a repository and decides afterwards whether that was a
good idea has already done the irreversible part.

Nothing here decides *what* to change. It takes edits somebody else produced and
guarantees the same three things about any of them: all of them land or none
do, the originals come back byte for byte, and nothing outside the root is
touched.
"""

import os
import stat
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from bumpsmith.sources import read_source


class ApplyError(Exception):
    """An edit could not be applied, or could not be applied safely."""


class RevertError(ApplyError):
    """An edit was applied and could not be taken back.

    Separate from :class:`ApplyError` because it is the one failure this module
    exists to prevent. It means the working tree is in a state nobody chose.
    """


@dataclass(frozen=True, slots=True)
class Edit:
    """One file's before and after, in the encoding both are written in.

    ``before`` is not decoration. It is checked against what is on disk at the
    moment of applying, so an edit planned against content that has since
    changed is refused rather than used to overwrite the change.
    """

    path: Path
    before: str
    after: str
    encoding: str = "utf-8"

    @property
    def changes_anything(self) -> bool:
        return self.before != self.after


@dataclass(slots=True)
class Attempt:
    """A set of edits that are currently on disk and will be taken back."""

    edits: tuple[Edit, ...]
    _kept: bool = field(default=False, repr=False)

    def keep(self) -> None:
        """Keep these edits. Without this call they are reverted on the way out."""
        self._kept = True

    @property
    def kept(self) -> bool:
        return self._kept


def _write(path: Path, text: str, encoding: str) -> None:
    """Replace ``path``'s contents atomically, preserving its permissions.

    Written to a temporary file in the same directory and renamed over the
    original, so a reader never sees a half-written file and a crash mid-write
    leaves the original intact. The rename is atomic within one filesystem,
    which a sibling temporary file guarantees.
    """
    mode = stat.S_IMODE(path.stat().st_mode)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".bumpsmith"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding) as handle:
            handle.write(text)
        # mkstemp creates 0600. Renaming that over the original would quietly
        # change the file's permissions as a side effect of editing it.
        temporary.chmod(mode)
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def _verify(edits: Sequence[Edit], root: Path) -> None:
    """Refuse the whole set unless every edit is safe to apply.

    Checked before anything is written, so a set containing one bad edit does
    not apply the good ones first and discover the problem afterwards.
    """
    resolved_root = root.resolve()
    seen: set[Path] = set()
    for edit in edits:
        resolved = edit.path.resolve()
        if not resolved.is_relative_to(resolved_root):
            raise ApplyError(
                f"Refusing to edit {resolved}: it is outside {resolved_root}. Every "
                f"edit has to land inside the tree being migrated."
            )
        if resolved in seen:
            raise ApplyError(
                f"Refusing to apply two edits to {resolved} in one attempt. Which one "
                f"wins would depend on their order, and reverting would restore only "
                f"one of them."
            )
        seen.add(resolved)

        try:
            current = read_source(edit.path)
        except OSError as exc:
            raise ApplyError(f"Cannot edit {edit.path}: {exc}") from exc
        except (UnicodeDecodeError, SyntaxError, ValueError) as exc:
            raise ApplyError(f"Cannot read {edit.path} to check it before editing: {exc}") from exc

        if current.text != edit.before:
            raise ApplyError(
                f"{edit.path} has changed since this edit was planned. Refusing to "
                f"apply it: the edit was written against different content, so "
                f"applying it now would overwrite whatever changed, and reverting it "
                f"would restore the wrong thing."
            )


def _restore(applied: Sequence[Edit]) -> None:
    """Put every applied edit's original contents back.

    Every file is attempted even after one fails, because stopping at the first
    failure would leave more of the tree changed than continuing does.
    """
    unrestored: list[str] = []
    for edit in applied:
        try:
            _write(edit.path, edit.before, edit.encoding)
        except OSError as exc:
            unrestored.append(f"{edit.path}: {exc}")
    if unrestored:
        raise RevertError(
            "Applied edits could not be taken back, and the working tree is in a "
            "state nobody chose. Restore these by hand or from version control:\n"
            + "\n".join(f"  {item}" for item in unrestored)
        )


def _apply(edits: Sequence[Edit]) -> list[Edit]:
    applied: list[Edit] = []
    for edit in edits:
        try:
            _write(edit.path, edit.after, edit.encoding)
        except OSError as exc:
            _restore(applied)
            raise ApplyError(
                f"Could not write {edit.path}: {exc}. The {len(applied)} edit(s) "
                f"already applied were taken back, so nothing has changed."
            ) from exc
        applied.append(edit)
    return applied


@contextmanager
def attempt(edits: Sequence[Edit], root: Path) -> Iterator[Attempt]:
    """Apply ``edits`` for the duration of the block, then take them back.

    The caller keeps them by calling :meth:`Attempt.keep` before the block ends,
    which it should do only once it has evidence the change was an improvement.
    Anything else -- an early return, an exception, a forgotten call -- reverts.

    Edits that change nothing are dropped rather than written, so a rule that
    matched a site already in its target state does not rewrite the file and
    does not appear in the attempt.

    Raises :class:`ApplyError` before touching anything if any edit is unsafe,
    and :class:`RevertError` if edits were applied and could not be undone.
    """
    real = [edit for edit in edits if edit.changes_anything]
    _verify(real, root)
    applied = _apply(real)
    session = Attempt(edits=tuple(real))
    try:
        yield session
    finally:
        if not session.kept:
            _restore(applied)
