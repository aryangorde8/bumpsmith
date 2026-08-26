"""Apply edits as a transaction that can always be taken back.

Reverting is the **default**. A caller earns a change by saying :meth:`keep`
after checking that it helped; an exception, an early return, or simply
forgetting all land in the same place -- the tree exactly as it was. That
ordering is the whole design. A tool that edits a repository and decides
afterwards whether that was a good idea has already done the irreversible part.

What the default covers, exactly
--------------------------------
Anything that unwinds the stack, because a ``finally`` block is the mechanism
and that is the limit of what one covers. A ``SIGKILL``, an ``os._exit``, a
segfault in an extension module, or the power going out leave the edits on disk:
nothing runs afterwards to take them back, and there is no journal to recover
from at the next start. This paragraph exists because the word "a crash" used to
stand here, and it covered the case this module handles and the case it does not
with the same word.

Nothing here decides *what* to change. It takes edits somebody else produced and
guarantees the same three things about any of them: all of them land or none do,
nothing outside the root is touched, and the originals come back byte for byte
-- unless something outside this transaction changed a file after it was
written, in which case that file is **left alone** and :class:`RevertError` says
which and why. Reverting is supposed to cost nothing, and overwriting somebody
else's work is not nothing. It is the one outcome where the tree is left in a
state nobody chose, so it is raised rather than returned.
"""

import codecs
import os
import stat
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from bumpsmith.sources import read_source

# Writing text can fail in three ways that all mean the same thing here: OSError
# from the filesystem, UnicodeError when the text will not encode, and
# LookupError when the codec name is not a codec. Only the first is an OSError,
# and treating it as the only one let the other two escape rollback entirely.
_WRITE_FAILED = (OSError, UnicodeError, LookupError)


def _canonical(encoding: str) -> str:
    """The one name a codec answers to.

    `latin-1` and `iso-8859-1` are the same codec, and `tokenize.detect_encoding`
    does not always return the spelling the caller used. Comparing the two as
    strings rejects an edit for being written correctly, so every comparison of
    encodings in this module goes through here.

    Raises :class:`LookupError` if the name is not a codec at all.
    """
    return codecs.lookup(encoding).name


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

    ``before`` is not decoration. It is checked against what is on disk twice --
    once across the whole set before anything is written, and again immediately
    before this file is written -- so an edit planned against content that has
    since changed is refused rather than used to overwrite the change.
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
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
        # mkstemp creates 0600. Renaming that over the original would quietly
        # change the file's permissions as a side effect of editing it.
        temporary.chmod(mode)
        temporary.replace(path)
    except _WRITE_FAILED:
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

        if edit.path.is_symlink():
            raise ApplyError(
                f"Refusing to edit {edit.path}: it is a symlink. The write renames a "
                f"temporary file over the path, which would replace the link itself "
                f"with a regular file and leave the file it points at untouched -- so "
                f"the content checked and the object changed would not be the same "
                f"thing."
            )

        try:
            wanted = _canonical(edit.encoding)
        except LookupError as exc:
            raise ApplyError(
                f"Cannot edit {edit.path}: {edit.encoding!r} is not a known codec."
            ) from exc
        if _canonical(current.encoding) != wanted:
            raise ApplyError(
                f"{edit.path} reads as {current.encoding} but this edit was written for "
                f"{edit.encoding}. Applying it would write different bytes than the "
                f"file holds, and reverting it would not restore the original."
            )

        for text, label in ((edit.before, "before"), (edit.after, "after")):
            try:
                text.encode(edit.encoding)
            except UnicodeError as exc:
                raise ApplyError(
                    f"Cannot edit {edit.path}: its {label} text does not encode as "
                    f"{edit.encoding} ({exc}). Refused here rather than discovered "
                    f"halfway through writing."
                ) from exc

        if current.text != edit.before:
            raise ApplyError(
                f"{edit.path} has changed since this edit was planned. Refusing to "
                f"apply it: the edit was written against different content, so "
                f"applying it now would overwrite whatever changed, and reverting it "
                f"would restore the wrong thing."
            )


def _restore(applied: Sequence[Edit]) -> None:
    """Put every applied edit's original contents back, unless something else got there first.

    Every file is checked before it is written. :func:`_apply` re-reads
    immediately before writing so that a change made between the check and the
    write is refused rather than overwritten, and this is the same care applied
    on the way out: a file that no longer holds what this transaction put there
    has been changed by something else, and that change is not ours to discard.
    Reverting is supposed to cost nothing, and destroying somebody's work is not
    nothing.

    The window is not theoretical. :mod:`bumpsmith.migrate` holds a
    transaction open across every later run of the test suite, so "between apply
    and revert" is minutes of a suite executing against the same checkout, not
    the few milliseconds a ``with`` block suggests.

    Every file is attempted even after one fails, because stopping at the first
    failure would leave more of the tree changed than continuing does.
    """
    unrestored: list[str] = []
    for edit in applied:
        try:
            current = read_source(edit.path)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
            unrestored.append(f"{edit.path}: could not be read to check it before restoring: {exc}")
            continue

        if current.text != edit.after or _canonical(current.encoding) != _canonical(edit.encoding):
            unrestored.append(
                f"{edit.path}: changed after this edit was applied, so it was left alone. "
                f"It holds somebody else's work and this edit is still in it."
            )
            continue

        try:
            _write(edit.path, edit.before, edit.encoding)
        except _WRITE_FAILED as exc:
            unrestored.append(f"{edit.path}: could not be written: {exc}")
    if unrestored:
        raise RevertError(
            "Applied edits could not be taken back, and the working tree is in a "
            "state nobody chose. Deal with these by hand or from version control:\n"
            + "\n".join(f"  {item}" for item in unrestored)
        )


def _apply(edits: Sequence[Edit]) -> list[Edit]:
    applied: list[Edit] = []
    for edit in edits:
        # Re-read immediately before writing. _verify checked every file up
        # front so a bad set fails before anything is touched, but that check
        # and this write are not the same moment, and anything that changed in
        # between would be silently overwritten.
        try:
            current = read_source(edit.path)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as exc:
            _restore(applied)
            raise ApplyError(
                f"Could not re-read {edit.path} before writing it: {exc}. The "
                f"{len(applied)} edit(s) already applied were taken back."
            ) from exc

        # _verify has already established both names are codecs.
        if current.text != edit.before or _canonical(current.encoding) != _canonical(edit.encoding):
            _restore(applied)
            raise ApplyError(
                f"{edit.path} changed between being checked and being written. "
                f"Refusing to overwrite that change. The {len(applied)} edit(s) "
                f"already applied were taken back, so nothing has changed."
            )

        try:
            _write(edit.path, edit.after, edit.encoding)
        except _WRITE_FAILED as exc:
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
