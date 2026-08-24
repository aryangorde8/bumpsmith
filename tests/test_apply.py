"""Tests for the apply-and-revert transaction.

Most of these assert that the tree is unchanged. That is the point: the module
exists to make "we tried something and it did not help" cost nothing.
"""

import stat
from pathlib import Path

import pytest

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
