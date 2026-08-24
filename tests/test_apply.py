"""Tests for the apply-and-revert transaction.

Most of these assert that the tree is unchanged. That is the point: the module
exists to make "we tried something and it did not help" cost nothing.
"""

import stat
from pathlib import Path

import pytest

from bumpsmith import apply as apply_module
from bumpsmith.apply import ApplyError, Edit, attempt
from bumpsmith.sources import read_source


def _file(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _edit(path: Path, after: str) -> Edit:
    source = read_source(path)
    return Edit(path=path, before=source.text, after=after, encoding=source.encoding)


# --------------------------------------------------------------------------
# Reverting is the default
# --------------------------------------------------------------------------


def test_edits_are_taken_back_when_the_caller_says_nothing(tmp_path: Path) -> None:
    """Forgetting to keep a change is not a way to keep it."""
    path = _file(tmp_path, "model.py", "original\n")

    with attempt([_edit(path, "changed\n")], tmp_path):
        assert path.read_text() == "changed\n"

    assert path.read_text() == "original\n"


def test_edits_survive_when_the_caller_keeps_them(tmp_path: Path) -> None:
    path = _file(tmp_path, "model.py", "original\n")

    with attempt([_edit(path, "changed\n")], tmp_path) as session:
        session.keep()

    assert path.read_text() == "changed\n"


def test_an_exception_inside_the_block_reverts_and_still_raises(tmp_path: Path) -> None:
    """The failure has to reach the caller, and the tree has to come back."""
    path = _file(tmp_path, "model.py", "original\n")

    with (
        pytest.raises(RuntimeError, match="suite went red"),
        attempt([_edit(path, "changed\n")], tmp_path),
    ):
        raise RuntimeError("suite went red")

    assert path.read_text() == "original\n"


def test_the_revert_is_byte_for_byte(tmp_path: Path) -> None:
    """Trailing whitespace, blank lines and a missing final newline all survive."""
    original = "a = 1\n\n\n   \nb = 2"
    path = _file(tmp_path, "fussy.py", original)

    with attempt([_edit(path, "totally different")], tmp_path):
        pass

    assert path.read_bytes() == original.encode()


def test_a_declared_encoding_survives_the_round_trip(tmp_path: Path) -> None:
    """Reading honours PEP 263, so writing has to as well.

    Writing a latin-1 source back as UTF-8 would corrupt it, and the corruption
    would be the *revert*, which is the one operation that must be exact.
    """
    original = "# -*- coding: latin-1 -*-\nNOTE = 'caf\xe9'\n"
    path = tmp_path / "latin.py"
    path.write_bytes(original.encode("latin-1"))

    with attempt([_edit(path, "# -*- coding: latin-1 -*-\nNOTE = 'th\xe9'\n")], tmp_path) as s:
        assert path.read_bytes().decode("latin-1").endswith("'th\xe9'\n")
        s.keep()

    assert path.read_bytes().decode("latin-1") == "# -*- coding: latin-1 -*-\nNOTE = 'th\xe9'\n"


def test_a_crlf_file_reverts_to_the_same_bytes(tmp_path: Path) -> None:
    """Byte-for-byte has to mean bytes, including the ones that end lines.

    Reading through a TextIOWrapper normalised CRLF to LF, so the revert wrote
    back different bytes than it found -- in the one operation that must be
    exact. The read is raw now, and the write does not translate either.
    """
    original = b"a = 1\r\nb = 2\r\n"
    path = tmp_path / "crlf.py"
    path.write_bytes(original)

    with attempt([_edit(path, "a = 9\r\nb = 2\r\n")], tmp_path):
        assert path.read_bytes() == b"a = 9\r\nb = 2\r\n"

    assert path.read_bytes() == original


def test_a_byte_order_mark_survives_the_round_trip(tmp_path: Path) -> None:
    """A BOM is bytes on disk. detect_encoding reports utf-8-sig, and encoding
    back with it puts the mark where it was."""
    path = tmp_path / "bom.py"
    path.write_bytes(b"\xef\xbb\xbfx = 1\n")

    with attempt([_edit(path, "x = 2\n")], tmp_path) as session:
        session.keep()

    assert path.read_bytes() == b"\xef\xbb\xbfx = 2\n"


def test_a_codec_alias_is_not_a_different_encoding(tmp_path: Path) -> None:
    """`latin-1` and `iso-8859-1` name one codec.

    detect_encoding does not always return the spelling the caller used, and
    comparing the two as strings rejected an edit for being written correctly.
    """
    path = tmp_path / "latin.py"
    path.write_bytes("# -*- coding: latin-1 -*-\nx = 'caf\xe9'\n".encode("latin-1"))
    edit = Edit(
        path=path,
        before=read_source(path).text,
        after="# -*- coding: latin-1 -*-\nx = 'th\xe9'\n",
        encoding="latin-1",
    )

    with attempt([edit], tmp_path) as session:
        session.keep()

    assert path.read_bytes().decode("latin-1").endswith("'th\xe9'\n")


def test_an_unknown_codec_is_refused(tmp_path: Path) -> None:
    path = _file(tmp_path, "model.py", "x = 1\n")
    nonsense = Edit(path=path, before="x = 1\n", after="x = 2\n", encoding="not-a-codec")

    with pytest.raises(ApplyError, match="not a known codec"), attempt([nonsense], tmp_path):
        pass

    assert path.read_text() == "x = 1\n"


def test_a_symlink_is_refused_and_both_files_are_left_alone(tmp_path: Path) -> None:
    """Renaming over a symlink replaces the link, not what it points at.

    The check read through the link and the write would have replaced the link
    itself with a regular file -- so the content verified and the object changed
    would not have been the same thing.
    """
    target = _file(tmp_path, "real.py", "target = 1\n")
    link = tmp_path / "link.py"
    link.symlink_to(target)

    with (
        pytest.raises(ApplyError, match="symlink"),
        attempt([_edit(link, "target = 2\n")], tmp_path),
    ):
        pass

    assert link.is_symlink()
    assert target.read_text() == "target = 1\n"


def test_text_that_will_not_encode_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    """UnicodeEncodeError is a ValueError, not an OSError.

    Catching only OSError let it escape rollback, leaving earlier edits applied
    while the caller saw a failure. It is refused up front now instead.
    """
    first = _file(tmp_path, "a.py", "first\n")
    latin = tmp_path / "b.py"
    latin.write_bytes("# -*- coding: latin-1 -*-\nx = 1\n".encode("latin-1"))

    unencodable = Edit(
        path=latin,
        before=read_source(latin).text,
        after="# -*- coding: latin-1 -*-\nx = '\u4e2d\u6587'\n",
        encoding="latin-1",
    )

    with (
        pytest.raises(ApplyError, match="does not encode"),
        attempt([_edit(first, "first changed\n"), unencodable], tmp_path),
    ):
        pass

    assert first.read_text() == "first\n"


def test_an_edit_written_for_the_wrong_encoding_is_refused(tmp_path: Path) -> None:
    """Same text, different bytes. The revert would not restore the original."""
    path = _file(tmp_path, "model.py", "x = 1\n")
    mismatched = Edit(path=path, before="x = 1\n", after="x = 2\n", encoding="latin-1")

    with pytest.raises(ApplyError, match="reads as"), attempt([mismatched], tmp_path):
        pass

    assert path.read_text() == "x = 1\n"


def test_a_file_that_changes_between_checking_and_writing_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifying and writing are not the same moment.

    Checking every file up front makes a bad set fail before anything is
    touched, but it leaves a gap: anything that changes in between would have
    been silently overwritten. Each file is now re-read immediately before it is
    written.
    """
    first = _file(tmp_path, "a.py", "first\n")
    second = _file(tmp_path, "b.py", "second\n")
    edits = [_edit(first, "first changed\n"), _edit(second, "second changed\n")]
    real_write = apply_module._write

    def meddling_write(path: Path, text: str, encoding: str) -> None:
        real_write(path, text, encoding)
        if path == first:
            second.write_text("somebody else got here\n")

    monkeypatch.setattr(apply_module, "_write", meddling_write)

    with pytest.raises(ApplyError, match="changed between being checked"), attempt(edits, tmp_path):
        pass

    assert first.read_text() == "first\n"
    assert second.read_text() == "somebody else got here\n"


# --------------------------------------------------------------------------
# Refusing before anything is written
# --------------------------------------------------------------------------


def test_an_edit_outside_the_root_is_refused(tmp_path: Path) -> None:
    outside = _file(tmp_path, "outside.py", "untouched\n")
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(ApplyError, match="outside"), attempt([_edit(outside, "x\n")], root):
        pass

    assert outside.read_text() == "untouched\n"


def test_an_edit_planned_against_stale_content_is_refused(tmp_path: Path) -> None:
    """Something else changed the file. Applying now would overwrite that."""
    path = _file(tmp_path, "model.py", "original\n")
    planned = _edit(path, "changed\n")
    path.write_text("somebody else got here first\n")

    with pytest.raises(ApplyError, match="has changed since"), attempt([planned], tmp_path):
        pass

    assert path.read_text() == "somebody else got here first\n"


def test_two_edits_to_one_file_are_refused(tmp_path: Path) -> None:
    """Which one wins would depend on order, and revert would restore one."""
    path = _file(tmp_path, "model.py", "original\n")
    first = _edit(path, "one\n")
    second = _edit(path, "two\n")

    with pytest.raises(ApplyError, match="two edits"), attempt([first, second], tmp_path):
        pass

    assert path.read_text() == "original\n"


def test_a_missing_file_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    """One bad edit must not let the good ones land first."""
    good = _file(tmp_path, "good.py", "original\n")
    good_edit = _edit(good, "changed\n")
    missing = Edit(path=tmp_path / "gone.py", before="", after="x\n")

    with pytest.raises(ApplyError, match="Cannot edit"), attempt([good_edit, missing], tmp_path):
        pass

    assert good.read_text() == "original\n"


# --------------------------------------------------------------------------
# Partial failure
# --------------------------------------------------------------------------


def test_a_write_that_fails_halfway_rolls_the_others_back(tmp_path: Path) -> None:
    """All of them land or none do."""
    first = _file(tmp_path, "writable/a.py", "first\n")
    second = _file(tmp_path, "locked/b.py", "second\n")
    first_edit = _edit(first, "first changed\n")
    second_edit = _edit(second, "second changed\n")

    locked = tmp_path / "locked"
    locked.chmod(stat.S_IRUSR | stat.S_IXUSR)  # readable, not writable
    try:
        with (
            pytest.raises(ApplyError, match="taken back"),
            attempt([first_edit, second_edit], tmp_path),
        ):
            pass
    finally:
        locked.chmod(stat.S_IRWXU)

    assert first.read_text() == "first\n"
    assert second.read_text() == "second\n"


# --------------------------------------------------------------------------
# Details that would be side effects if nobody checked
# --------------------------------------------------------------------------


def test_file_permissions_are_not_changed_by_editing(tmp_path: Path) -> None:
    """The temporary file is created 0600. Renaming it over the original
    would silently narrow the original's permissions."""
    path = _file(tmp_path, "script.py", "original\n")
    path.chmod(0o755)

    with attempt([_edit(path, "changed\n")], tmp_path) as session:
        session.keep()

    assert stat.S_IMODE(path.stat().st_mode) == 0o755


def test_an_edit_that_changes_nothing_is_not_written(tmp_path: Path) -> None:
    """A rule can match a site already in its target state."""
    path = _file(tmp_path, "model.py", "already correct\n")
    before = path.stat().st_mtime_ns

    with attempt([_edit(path, "already correct\n")], tmp_path) as session:
        assert session.edits == ()
        session.keep()

    assert path.stat().st_mtime_ns == before


def test_several_files_revert_together(tmp_path: Path) -> None:
    paths = [_file(tmp_path, f"pkg/m{index}.py", f"original {index}\n") for index in range(5)]

    with attempt([_edit(path, "changed\n") for path in paths], tmp_path):
        assert all(path.read_text() == "changed\n" for path in paths)

    assert [path.read_text() for path in paths] == [f"original {index}\n" for index in range(5)]
