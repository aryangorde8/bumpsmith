"""Which configuration would govern a suite run, and when that is a refusal.

The module under test encodes a piece of pytest's behaviour rather than any of
this project's, so the tests that matter most are the ones that check the two
against each other. `test_pytest_agrees_about_the_barrier` is that check: it
runs a real pytest and asserts it does what this module predicted.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from bumpsmith.fixtures import BARRIER_NAME, write_barrier
from bumpsmith.rootdir import (
    CANDIDATES,
    Governing,
    config_argument,
    describe,
    foreign_config,
    governing_config,
    runs_pytest,
)

CONFIGURING = '[tool.pytest.ini_options]\naddopts = "-q"\ntestpaths = ["tests"]\n'
NEUTRAL = "# nothing here\n[pytest]\n"


def _tree(tmp_path: Path) -> tuple[Path, Path]:
    """A repository inside an outer directory, with nothing configured yet."""
    outer = tmp_path / "outer"
    root = outer / "repo"
    root.mkdir(parents=True)
    return outer, root


# --------------------------------------------------------------------------
# Which file wins
# --------------------------------------------------------------------------


def test_a_configuring_file_above_the_repository_is_what_governs_it(tmp_path: Path) -> None:
    """The case the whole module exists for: a subject inheriting its container."""
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == outer / "pyproject.toml"
    assert set(found.keys) == {"addopts", "testpaths"}
    assert foreign_config(root) == found


def test_the_repository_configuring_itself_is_never_foreign(tmp_path: Path) -> None:
    """However much it sets. That is the arrangement this check steers people to."""
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\naddopts = --strict-markers\n", encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == root / "pytest.ini"
    assert found.keys == ("addopts",)
    assert foreign_config(root) is None


def test_the_nearest_configuration_wins_not_the_outermost(tmp_path: Path) -> None:
    """pytest stops at the first match walking up, and so does this."""
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "--outermost"\n', encoding="utf-8"
    )
    (outer / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "--nearest"\n', encoding="utf-8"
    )

    found = governing_config(root)

    assert found is not None
    assert found.path == outer / "pyproject.toml"


def test_pytest_ini_beats_a_pyproject_beside_it(tmp_path: Path) -> None:
    """Precedence is per directory, and `pytest.ini` is the highest of the four."""
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (outer / "pytest.ini").write_text("[pytest]\naddopts = --from-the-ini\n", encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == outer / "pytest.ini"
    assert found.keys == ("addopts",)


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("pyproject.toml", '[project]\nname = "something"\n'),
        ("tox.ini", "[tox]\nenvlist = py313\n"),
        ("setup.cfg", "[metadata]\nname = something\n"),
    ],
)
def test_a_file_without_the_pytest_section_does_not_count(
    tmp_path: Path, name: str, text: str
) -> None:
    """Three of the four names only count when they carry pytest's own section.

    Getting this wrong in the permissive direction would refuse almost every
    repository on earth, since a `pyproject.toml` two levels up is the normal
    state of a Python checkout.
    """
    outer, root = _tree(tmp_path)
    (outer / name).write_text(text, encoding="utf-8")

    assert governing_config(root) is None
    assert foreign_config(root) is None


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("pyproject.toml", '[tool.pytest.ini_options]\naddopts = "-q"\n'),
        ("tox.ini", "[pytest]\naddopts = -q\n"),
        ("setup.cfg", "[tool:pytest]\naddopts = -q\n"),
    ],
)
def test_each_of_the_other_three_names_counts_when_it_carries_the_section(
    tmp_path: Path, name: str, text: str
) -> None:
    """The same three, the other way round."""
    outer, root = _tree(tmp_path)
    (outer / name).write_text(text, encoding="utf-8")

    found = foreign_config(root)

    assert found is not None
    assert found.path == outer / name
    assert found.keys == ("addopts",)


# --------------------------------------------------------------------------
# Neutral, and why it is a state of its own
# --------------------------------------------------------------------------


def test_an_empty_pytest_ini_counts_as_a_barrier_and_configures_nothing(tmp_path: Path) -> None:
    """The two halves that make the barrier work, asserted separately.

    It has to *stop the walk* -- otherwise the checkout above is still reached --
    and it has to *set nothing* -- otherwise stopping the walk is no improvement
    on what it stopped.
    """
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (outer / "pytest.ini").write_text(NEUTRAL, encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == outer / "pytest.ini", "the walk did not stop at the barrier"
    assert found.keys == ()
    assert found.neutral
    assert foreign_config(root) is None


def test_a_completely_empty_pytest_ini_is_still_a_barrier(tmp_path: Path) -> None:
    """Zero bytes -- no section, no comment, nothing.

    `test_an_empty_pytest_ini_counts_as_a_barrier_and_configures_nothing` uses a
    file that still carries `[pytest]`, so it passes whether or not the name is
    treated as always counting. Breaking that flag on purpose was caught by
    nothing, which is how this case was found: pytest honours a `pytest.ini`
    whatever is in it, and only this test says so.
    """
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (outer / "pytest.ini").write_text("", encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == outer / "pytest.ini", "an empty pytest.ini did not stop the walk"
    assert found.neutral
    assert foreign_config(root) is None


def test_only_pytest_ini_counts_while_empty(tmp_path: Path) -> None:
    """An empty `tox.ini` is not a barrier, and believing it was would be silent.

    pytest treats `pytest.ini` as an inifile whatever it contains; the other
    three only count when their section is present. A barrier built on the wrong
    filename would let the walk straight through.
    """
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (outer / "tox.ini").write_text("", encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == tmp_path / "pyproject.toml"
    assert foreign_config(root) is not None


def test_the_barrier_bumpsmith_writes_reads_as_neutral_to_bumpsmith(tmp_path: Path) -> None:
    """The two modules have to agree, and they are written apart.

    `fixtures.write_barrier` produces the file and `rootdir` judges it. If the
    barrier ever gained a setting -- or the judgement ever stopped recognising an
    empty section -- every cloned fixture would start being refused, or worse,
    silently stop being protected.
    """
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")

    written = write_barrier(outer)

    assert written == outer / BARRIER_NAME
    found = governing_config(root)
    assert found is not None
    assert found.path == written
    assert found.neutral
    assert foreign_config(root) is None


# --------------------------------------------------------------------------
# Files that cannot be read
# --------------------------------------------------------------------------


def test_a_configuration_that_cannot_be_parsed_is_refused_not_ignored(tmp_path: Path) -> None:
    """Unreadable is not the same as empty, and only one of them is safe.

    A file that exists and cannot be read is not evidence that it sets nothing.
    """
    outer, root = _tree(tmp_path)
    (outer / "pytest.ini").write_text("[pytest\nthis is not ini\n", encoding="utf-8")

    found = foreign_config(root)

    assert found is not None
    assert found.keys == ()
    assert found.unreadable
    assert not found.neutral
    assert "could not be read" in describe(found)


def test_a_percent_sign_in_a_value_is_not_a_parse_error(tmp_path: Path) -> None:
    """configparser interpolates `%` by default; pytest does not.

    `filterwarnings` and log-format settings carry `%` routinely, so a reader
    that raised on them would report perfectly ordinary configuration as
    unreadable -- and refuse for the wrong reason.

    This only bites because the values are read. While `Governing` carried names
    alone, `interpolation=None` was unreachable and this test passed with the
    guard removed; the break run is what showed it.
    """
    outer, root = _tree(tmp_path)
    (outer / "pytest.ini").write_text(
        "[pytest]\nlog_format = %(asctime)s %(message)s\n", encoding="utf-8"
    )

    found = foreign_config(root)

    assert found is not None
    assert not found.unreadable
    assert found.keys == ("log_format",)
    assert found.settings == (("log_format", "%(asctime)s %(message)s"),)
    assert "%(asctime)s" in describe(found)


# --------------------------------------------------------------------------
# The message
# --------------------------------------------------------------------------


def test_the_description_names_the_file_and_what_it_sets(tmp_path: Path) -> None:
    """The remedy is one line in the subject, so the reader has to know which line."""
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")

    found = foreign_config(root)

    assert found is not None
    described = describe(found)
    assert str(outer / "pyproject.toml") in described
    assert "addopts = -q" in described
    assert "testpaths" in described


def test_a_long_setting_is_trimmed_rather_than_spilled_into_the_message(tmp_path: Path) -> None:
    """An `addopts` can be a paragraph, and a refusal is one line.

    Trimmed rather than dropped: the reader still sees which setting and enough
    of it to recognise, and the file is named for the rest.
    """
    outer, root = _tree(tmp_path)
    (outer / "pytest.ini").write_text(f"[pytest]\naddopts = {'-x ' * 80}\n", encoding="utf-8")

    found = foreign_config(root)

    assert found is not None
    described = describe(found)
    assert "\u2026" in described
    assert len(described) < 200


def test_the_keys_are_listed_in_a_stable_order() -> None:
    """Two runs of the same refusal produce the same sentence.

    `keys` arrives in file order; the message sorts it. A refusal whose wording
    depended on how somebody happened to arrange their ini is one nobody can
    grep for twice.
    """
    one = Governing(
        path=Path("/x/pyproject.toml"), settings=(("testpaths", "tests"), ("addopts", "-q"))
    )
    other = Governing(
        path=Path("/x/pyproject.toml"), settings=(("addopts", "-q"), ("testpaths", "tests"))
    )

    assert describe(one) == describe(other)


# --------------------------------------------------------------------------
# Against pytest itself
# --------------------------------------------------------------------------


def test_pytest_agrees_about_the_barrier(tmp_path: Path) -> None:
    """The claim this module makes, checked against the program it makes it about.

    Everything above tests what `rootdir.py` believes. This one runs pytest twice
    over the same subject -- once inheriting a strict configuration from above,
    once behind the barrier -- and asserts pytest behaves as predicted both
    times. Without it the module could be internally consistent and wrong.
    """
    outer, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "--strict-markers"\n', encoding="utf-8"
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_marked.py").write_text(
        "import pytest\n\n\n@pytest.mark.unregistered\ndef test_one() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    inherited = _run()
    assert foreign_config(root) is not None, "predicted: governed from outside"
    assert inherited.returncode != 0
    assert "unregistered" in inherited.stdout + inherited.stderr

    write_barrier(outer)

    behind_barrier = _run()
    assert foreign_config(root) is None, "predicted: the barrier stops the walk"
    assert behind_barrier.returncode == 0, behind_barrier.stdout + behind_barrier.stderr


# --------------------------------------------------------------------------
# The four dedicated filenames pytest 9 added
# --------------------------------------------------------------------------

_ALL_SEVEN: tuple[tuple[str, str, str], ...] = (
    ("pytest.toml", "", '[pytest]\naddopts = ["-q"]\n'),
    (".pytest.toml", "", '[pytest]\naddopts = ["-q"]\n'),
    ("pytest.ini", "", "[pytest]\naddopts = -q\n"),
    (".pytest.ini", "", "[pytest]\naddopts = -q\n"),
    ("pyproject.toml", "", '[tool.pytest.ini_options]\naddopts = "-q"\n'),
    ("tox.ini", "", "[pytest]\naddopts = -q\n"),
    ("setup.cfg", "", "[tool:pytest]\naddopts = -q\n"),
)
"""Every name pytest reads, with an empty spelling and a configured one.

The order is pytest's own precedence, measured with `--collect-only -v`, which
prints `configfile:` and warns which files it ignored.
"""


def test_the_candidate_list_is_pytests_own_order() -> None:
    """Ordering is not cosmetic: it decides which of several files wins."""
    assert tuple(name for name, _, _ in _ALL_SEVEN) == CANDIDATES


@pytest.mark.parametrize(("name", "_empty", "configured"), _ALL_SEVEN)
def test_every_name_pytest_reads_is_seen_as_configuration(
    tmp_path: Path, name: str, _empty: str, configured: str
) -> None:
    """A configured file above the subject is foreign whichever name it uses.

    The dangerous direction. Missing a name means missing a configuration that
    really does govern the suite, and the refusal never fires.
    """
    outer, root = _tree(tmp_path)
    (outer / name).write_text(configured, encoding="utf-8")

    found = foreign_config(root)

    assert found is not None, f"{name} was not recognised as configuration"
    assert found.path == outer / name
    assert found.keys == ("addopts",)


@pytest.mark.parametrize("name", ["pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini"])
def test_the_four_dedicated_names_count_while_completely_empty(tmp_path: Path, name: str) -> None:
    """All four are barriers, not just `pytest.ini`.

    The other direction, and the one that bit: a subject configuring itself in
    `pytest.toml` was walked straight past and refused for a configuration that
    was not governing it.
    """
    _, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (root / name).write_text("", encoding="utf-8")

    found = governing_config(root)

    assert found is not None
    assert found.path == root / name, f"an empty {name} did not stop the walk"
    assert found.neutral
    assert foreign_config(root) is None


def test_the_nearest_name_wins_across_all_seven(tmp_path: Path) -> None:
    """With every name present, the winner is the first in pytest's order.

    Removed one at a time, the next in line takes over -- which is how the order
    was established rather than assumed.
    """
    outer, root = _tree(tmp_path)
    for name, _, configured in _ALL_SEVEN:
        (outer / name).write_text(configured, encoding="utf-8")

    for name, _, _ in _ALL_SEVEN:
        found = governing_config(root)
        assert found is not None
        assert found.path == outer / name, f"expected {name} to win"
        (outer / name).unlink()

    assert governing_config(root) is None


def test_the_native_pyproject_table_counts_only_when_it_holds_something(
    tmp_path: Path,
) -> None:
    """`[tool.pytest]` and `[tool.pytest.ini_options]` do not behave alike.

    An empty `ini_options` counts as configuration; an empty `[tool.pytest]` is
    walked straight past. Measured, not assumed, because the asymmetry is the
    sort of thing a reasonable person would get backwards.
    """
    outer, root = _tree(tmp_path)

    (outer / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")
    assert governing_config(root) is None, "an empty [tool.pytest] should not count"

    (outer / "pyproject.toml").write_text('[tool.pytest]\naddopts = ["-q"]\n', encoding="utf-8")
    found = governing_config(root)
    assert found is not None
    assert found.keys == ("addopts",)

    (outer / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    empty = governing_config(root)
    assert empty is not None, "an empty [tool.pytest.ini_options] does count"
    assert empty.neutral


# --------------------------------------------------------------------------
# A command that names its own configuration
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (("pytest", "-c", "custom.ini"), "custom.ini"),
        (("pytest", "-c=custom.ini"), "custom.ini"),
        (("pytest", "-ccustom.ini"), "custom.ini"),
        (("pytest", "--config-file", "custom.ini"), "custom.ini"),
        (("pytest", "--config-file=custom.ini"), "custom.ini"),
        (("pytest", "-q"), None),
        (("pytest", "-c"), None),
    ],
)
def test_the_config_option_is_read_in_every_spelling(
    command: tuple[str, ...], expected: str | None
) -> None:
    """argparse accepts all five, so a reader that knew one would miss four.

    `-c` with nothing after it returns nothing: that is a broken command line,
    and pytest rejects it on its own terms rather than ours.
    """
    assert config_argument(command) == expected


def test_a_named_configuration_outside_the_tree_is_refused(tmp_path: Path) -> None:
    """`-c` replaces discovery, so the walk's answer is not the one that governs.

    The subject has its own barrier here. Walking would find it and allow the
    run; pytest would ignore it entirely and read the named file instead.
    """
    outer, root = _tree(tmp_path)
    (root / "pytest.ini").write_text("", encoding="utf-8")
    (outer / "custom.ini").write_text("[pytest]\naddopts = -m 'not slow'\n", encoding="utf-8")

    assert foreign_config(root) is None, "the walk alone sees the subject's own barrier"

    found = foreign_config(root, ("pytest", "-c", "../custom.ini"))

    assert found is not None
    assert found.path == outer / "custom.ini"
    assert "not slow" in describe(found)


def test_a_named_configuration_inside_the_tree_is_allowed(tmp_path: Path) -> None:
    """And the other way round: naming your own config is the remedy, not the offence."""
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (root / "mine.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")

    assert foreign_config(root) is not None, "the walk alone finds the outer configuration"
    assert foreign_config(root, ("pytest", "-c", "mine.ini")) is None


def test_a_named_configuration_that_is_not_there_is_not_our_complaint(
    tmp_path: Path,
) -> None:
    """pytest exits before running anything, which the loop already reports.

    Refusing here would put a configuration complaint in front of a plain typo.
    """
    outer, root = _tree(tmp_path)
    (outer / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")

    assert foreign_config(root, ("pytest", "-c", "nope.ini")) is None


# --------------------------------------------------------------------------
# Which commands are pytest at all
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        ("pytest", "-q"),
        ("py.test", "-q"),
        ("/somewhere/else/bin/pytest",),
        ("python", "-m", "pytest"),
        ("./venv/bin/python", "-m", "pytest", "-q"),
        ("python3.13", "-mpytest"),
        ("python", "-m", "coverage", "run", "-m", "pytest"),
    ],
)
def test_pytest_in_a_position_where_it_could_be_the_program(command: tuple[str, ...]) -> None:
    """Each of these is how somebody actually writes it on a command line."""
    assert runs_pytest(command)


@pytest.mark.parametrize(
    "command",
    [
        ("make", "pytest"),
        ("python", "script.py", "pytest"),
        ("python", "-c", "print('ok')", "pytest"),
        ("tox", "-e", "py313"),
        ("./run-tests.sh",),
        (),
    ],
)
def test_the_word_pytest_somewhere_in_the_argv_is_not_a_pytest_run(
    command: tuple[str, ...],
) -> None:
    """`make pytest` is an ordinary way to spell a suite command.

    Refusing it would be a refusal nobody could act on, and the recognizer's own
    docstring promises otherwise. An earlier version scanned every position and
    broke that promise for all five of these.
    """
    assert not runs_pytest(command)


@pytest.mark.parametrize("barrier", ["pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini"])
def test_pytest_agrees_which_names_are_barriers(tmp_path: Path, barrier: str) -> None:
    """Each of the four, checked against the program the claim is about.

    `test_pytest_agrees_about_the_barrier` covers `pytest.ini` end to end. This
    asks the narrower question for all four names at once, by reading back the
    `configfile:` pytest prints -- which is pytest stating outright which file it
    chose, rather than us inferring it from behaviour.
    """
    _, root = _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(CONFIGURING, encoding="utf-8")
    (root / barrier).write_text("", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text("def test_one() -> None:\n    assert True\n", encoding="utf-8")

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "--collect-only", "-v"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert f"configfile: {barrier}" in result.stdout, result.stdout
    found = governing_config(root)
    assert found is not None
    assert found.path == root / barrier, "pytest and this module disagree about the file"
    assert foreign_config(root) is None


def test_pytest_agrees_about_an_explicitly_named_configuration(tmp_path: Path) -> None:
    """`-c` really does override a barrier the subject already has.

    The premise finding 2 rests on. Without this the `-c` handling could be
    guarding against something pytest does not do.
    """
    outer, root = _tree(tmp_path)
    (root / "pytest.ini").write_text("", encoding="utf-8")
    (outer / "custom.ini").write_text("[pytest]\naddopts = --strict-markers\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text(
        "import pytest\n\n\n@pytest.mark.unregistered\ndef test_one() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    def _run(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, "-m", "pytest", "-q", *extra],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    assert _run().returncode == 0, "the subject's own barrier governs an ordinary run"
    assert foreign_config(root) is None

    named = _run("-c", "../custom.ini")

    assert named.returncode != 0, "-c did not override the barrier"
    assert "unregistered" in named.stdout + named.stderr
    assert foreign_config(root, ("pytest", "-c", "../custom.ini")) is not None
