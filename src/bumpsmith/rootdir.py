"""Which configuration file would govern a pytest run inside a given tree.

The loop's whole claim rests on a verdict it did not produce itself: the suite
exits zero, so the edits are kept. :mod:`bumpsmith.migrate` already refuses a
verdict that came from the wrong *filesystem* -- see ``Stop.WRONG_PLACE``. This
module exists because a verdict can come from the right tree and still not be
about it.

pytest does not read its configuration from the directory it is invoked in. It
walks *upward* looking for the first file that counts as an inifile, and
whatever it finds sets ``rootdir`` and supplies ``addopts``, ``testpaths`` and
the rest. So a repository that has no pytest configuration of its own inherits
the configuration of whatever it happens to sit inside. Clone somebody's project
into a directory beneath a checkout that configures pytest, and their suite runs
under *your* settings.

That is not hypothetical here. ``python -m bumpsmith.fixtures`` clones into
``./fixtures/`` inside this checkout, and this checkout's ``pyproject.toml``
sets ``addopts = "-ra --strict-markers --strict-config"``. Of the four fixtures
only ``B`` lacks a pytest configuration of its own, and it happens to use no
markers, so nothing currently misbehaves -- which is exactly the kind of luck
that stops being true without anything failing.

Both directions are reachable and only one of them is loud:

* a stricter outside configuration turns a green suite red. Visible, and the
  worst it costs is a wasted migration attempt against a break that was never
  a pydantic break.
* an outside configuration that *deselects* -- ``addopts = "-m 'not slow'"``,
  a narrowing ``testpaths``, an ``--ignore`` -- runs fewer tests than the
  repository's own suite would. A suite that should have gone red goes green,
  and the loop keeps the edits. That is the same defect ``WRONG_PLACE`` exists
  to prevent, arriving by a different road: edits kept on the strength of a run
  that never exercised them.

What counts as an inifile is not one rule but seven, and they disagree: four
dedicated filenames count whatever they contain, while ``pyproject.toml``,
``tox.ini`` and ``setup.cfg`` count only for pytest's own section -- and
``pyproject.toml`` has two spellings that do not behave alike. All of it was
measured against the pinned pytest rather than read off a page; see
:data:`CANDIDATES`. ``pytest -c FILE`` replaces discovery outright, so the argv
is consulted too.

So it is checked rather than asked for, and the check is deliberately blunt.
Rather than decide which pytest settings are dangerous -- a list that would be
wrong the first time pytest grows an option -- an outside inifile that sets
**anything at all** is refused, and one that sets nothing is allowed through.
An empty ``[pytest]`` section is a real and useful thing: it stops the walk
without contributing a single setting, which is how a directory full of cloned
subjects keeps the host checkout's configuration out of them.
"""

import configparser
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CANDIDATES: tuple[str, ...] = (
    "pytest.toml",
    ".pytest.toml",
    "pytest.ini",
    ".pytest.ini",
    "pyproject.toml",
    "tox.ini",
    "setup.cfg",
)
"""The filenames pytest considers, in the order it considers them.

Precedence is per directory, not global: pytest tries every name in the nearest
directory before moving to its parent, so a subject's own ``setup.cfg`` beats a
``pytest.toml`` one level up.

This order and the rules below were measured against the pinned pytest, not read
off a page. ``pytest --collect-only -v`` prints ``configfile:`` and warns which
files it ignored, so it will say which of several it picked:

    configfile: pytest.toml (WARNING: ignoring pytest config in .pytest.toml,
    pytest.ini, .pytest.ini, tox.ini, setup.cfg!)

The four dedicated names arrived in pytest 9 alongside ``pytest.toml``; an
earlier version of this module knew only ``pytest.ini`` and would walk straight
past a subject that configured itself in any of the other three -- refusing a
repository for a configuration it did not have.
"""

VALUE_LIMIT = 60
"""How much of a setting's value a refusal quotes before trimming it."""


@dataclass(frozen=True, slots=True)
class Governing:
    """The inifile that would govern a run, and what it sets.

    ``settings`` is empty for a file that counts as an inifile but configures
    nothing -- a bare ``pytest.ini``, or one holding only comments. That is a
    distinct state from ``unreadable``, where the file matched and its contents
    could not be established; the two are kept apart because only the first is
    safe to ignore.

    Values are carried, not just names. "``addopts`` is set" leaves the reader
    to go and look; "``addopts = -m 'not slow'``" is the whole explanation of
    why it matters, which is the difference between a refusal somebody acts on
    and one they work around.
    """

    path: Path
    settings: tuple[tuple[str, str], ...] = ()
    unreadable: str = ""

    @property
    def keys(self) -> tuple[str, ...]:
        """The names alone, in the order the file gave them."""
        return tuple(name for name, _ in self.settings)

    @property
    def neutral(self) -> bool:
        """Whether this file changes nothing about how the suite runs."""
        return not self.settings and not self.unreadable


_ALWAYS_TOML: frozenset[str] = frozenset({"pytest.toml", ".pytest.toml"})
"""TOML files that count as configuration whatever they contain, even empty."""

_ALWAYS_INI: frozenset[str] = frozenset({"pytest.ini", ".pytest.ini"})
"""INI files that count as configuration whatever they contain, even empty."""


def _settings_from(table: object) -> tuple[tuple[str, str], ...]:
    """A TOML table's entries as name/value pairs, or nothing if it is not one."""
    if not isinstance(table, dict):
        return ()
    return tuple((str(key), str(value)) for key, value in table.items())


def _load_toml(path: Path) -> tuple[dict[str, object] | None, str]:
    """Parse ``path`` as TOML. Returns the document, or the reason it could not be."""
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle), ""
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, str(exc)


def _ini_section(path: Path, section: str, *, always_matches: bool) -> Governing | None:
    """Read ``[section]`` from an ini-style file, or ``None`` if it has none.

    Interpolation is switched off because pytest ini values routinely contain
    ``%`` -- a ``filterwarnings`` line or a log format string -- and configparser
    would raise on text pytest itself reads without complaint. That only bites
    once the values are read rather than only their names; an earlier version
    read names alone, which made this argument true and the line that carried it
    unreachable.
    """
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeDecodeError, configparser.Error) as exc:
        # A file that exists and cannot be read is not evidence of absence. If
        # this name always counts as an inifile, pytest will use it and we
        # cannot say what it sets; if it only counts when a section is present,
        # we cannot say whether that section is there either. Both are reported
        # rather than guessed.
        return Governing(path=path, unreadable=str(exc))
    if not parser.has_section(section):
        return Governing(path=path) if always_matches else None
    return Governing(path=path, settings=tuple(parser.items(section)))


def _pytest_toml(path: Path) -> Governing:
    """Read a ``pytest.toml``, whose settings live under a ``[pytest]`` table.

    Always a match. pytest honours these two filenames whether or not the table
    is there, which is what makes an empty one usable as a barrier.
    """
    document, unreadable = _load_toml(path)
    if document is None:
        return Governing(path=path, unreadable=unreadable)
    return Governing(path=path, settings=_settings_from(document.get("pytest")))


def _pyproject(path: Path) -> Governing | None:
    """Read a ``pyproject.toml``, which counts only for pytest's own tables.

    Two spellings, and they do not behave alike. ``[tool.pytest.ini_options]``
    counts as configuration by being present, empty or not. The newer native
    ``[tool.pytest]`` counts only when it holds something -- an empty one is
    walked straight past, which was measured rather than assumed.
    """
    document, unreadable = _load_toml(path)
    if document is None:
        return Governing(path=path, unreadable=unreadable)
    tool = document.get("tool")
    if not isinstance(tool, dict):
        return None
    pytest_table = tool.get("pytest")
    if not isinstance(pytest_table, dict):
        return None
    options = pytest_table.get("ini_options")
    if isinstance(options, dict):
        return Governing(path=path, settings=_settings_from(options))
    native = _settings_from(pytest_table)
    return Governing(path=path, settings=native) if native else None


def _candidate(directory: Path, name: str) -> Governing | None:
    """Whether ``directory/name`` is an inifile, and what it sets."""
    path = directory / name
    if not path.is_file():
        return None
    if name in _ALWAYS_TOML:
        return _pytest_toml(path)
    if name in _ALWAYS_INI:
        return _ini_section(path, "pytest", always_matches=True)
    if name == "pyproject.toml":
        return _pyproject(path)
    if name == "tox.ini":
        return _ini_section(path, "pytest", always_matches=False)
    return _ini_section(path, "tool:pytest", always_matches=False)


_PYTEST_NAMES: frozenset[str] = frozenset({"pytest", "py.test"})
"""What pytest is called when it is the program being run."""

_CONFIG_FLAGS: tuple[str, ...] = ("--config-file", "-c")
"""pytest's own options for naming a configuration file instead of finding one.

Longest first, so ``--config-file`` is never matched by the ``-c`` prefix rule.
"""


def runs_pytest(command: Sequence[str]) -> bool:
    """Whether this argv recognisably runs pytest.

    Deliberately narrow, and narrow in a specific way: pytest has to be in a
    position where it could be *the program*. Either the command itself, or the
    module argument to an interpreter. An earlier version matched the word
    anywhere in the argv, which made ``make pytest`` -- a perfectly ordinary way
    to spell a suite command -- into a refusal nobody could act on, contradicting
    the paragraph directly above it.

    That earlier version also made the ``-m`` branch look dead, because the bare
    word matched one iteration later regardless. Removing the branch changed no
    answer and was recorded as such; narrowing the scan is what made it load
    bearing again. A test can only find dead code that is dead for good.

    Commands this cannot recognise -- ``tox``, ``uv run pytest``, a shell
    wrapper -- are left alone rather than refused on a guess. Under-recognising
    costs a check that does not happen; over-recognising costs a tool that
    cannot be used.
    """
    if command and PurePosixPath(command[0]).name in _PYTEST_NAMES:
        return True
    for index, argument in enumerate(command[1:], start=1):
        if argument == "-m" and index + 1 < len(command) and command[index + 1] == "pytest":
            return True
        if argument == "-mpytest":
            return True
    return False


def config_argument(command: Sequence[str]) -> str | None:
    """The configuration file this argv explicitly selects, if it selects one.

    ``pytest -c FILE`` replaces discovery outright: pytest reads that file and
    puts ``rootdir`` beside it, wherever it is. A guard that walked upward from
    the repository would then be judging a file the run never opens.

    Only meaningful for a command :func:`runs_pytest` has already accepted --
    ``python -c "code"`` is the interpreter's option, not pytest's, and this
    would read the code as a filename.

    Returns ``None`` when no such option is present, and when one is present with
    nothing after it -- that is a broken command line, which pytest will reject
    on its own terms.
    """
    for index, argument in enumerate(command):
        for flag in _CONFIG_FLAGS:
            if argument == flag:
                following = command[index + 1 : index + 2]
                return following[0] if following else None
            if argument.startswith(f"{flag}="):
                return argument[len(flag) + 1 :]
            if flag == "-c" and argument.startswith("-c") and len(argument) > 2:
                return argument[2:]
    return None


def _named_config(selected: str, root: Path) -> Governing | None:
    """Read the file an argv named, or ``None`` if it is not there to read.

    A named file that does not exist is not this module's problem: pytest exits
    before running anything, which the loop already reports as a suite that could
    not be run. Refusing here would put a configuration complaint in front of a
    plain typo.

    The suffix picks the reader because that is what pytest does with the name.
    """
    path = (
        (root / selected).resolve() if not PurePosixPath(selected).is_absolute() else Path(selected)
    )
    if not path.is_file():
        return None
    if path.suffix == ".toml":
        return _pytest_toml(path)
    return _ini_section(path, "pytest", always_matches=True)


def governing_config(root: Path) -> Governing | None:
    """The inifile pytest would use for a suite run at ``root``.

    Args:
        root: The directory the suite is run from -- for this package, the tree
            being edited.

    Returns:
        The nearest inifile at or above ``root``, or ``None`` if there is none
        anywhere up to the filesystem root. ``None`` is not a failure: pytest
        falls back to its own defaults, which is the situation this module is
        trying to preserve.

    The walk stops at the first match, which is what pytest does, so the result
    is the file that actually wins rather than every file that could have.
    """
    directory = root.resolve()
    for candidate_dir in (directory, *directory.parents):
        for name in CANDIDATES:
            found = _candidate(candidate_dir, name)
            if found is not None:
                return found
    return None


def foreign_config(root: Path, command: Sequence[str] = ()) -> Governing | None:
    """The governing inifile, but only when it is outside ``root`` and sets something.

    Args:
        root: The tree being edited.
        command: The argv that will run the suite. Only consulted for an explicit
            ``-c``/``--config-file``, which replaces discovery; without one the
            walk from ``root`` is what pytest would do.

    Returns:
        The offending :class:`Governing`, or ``None`` when the suite's
        configuration is the repository's own, absent, or present-but-neutral.
        A file *inside* ``root`` is never reported however much it sets: that is
        the repository configuring itself, which is the arrangement this check
        exists to steer people towards.
    """
    selected = config_argument(command)
    found = _named_config(selected, root) if selected is not None else governing_config(root)
    if found is None or found.neutral:
        return None
    if found.path.is_relative_to(root.resolve()):
        return None
    return found


def _trim(value: str) -> str:
    """One setting's value, short enough to sit inside a sentence."""
    flattened = " ".join(value.split())
    if len(flattened) <= VALUE_LIMIT:
        return flattened
    return flattened[: VALUE_LIMIT - 1] + "\u2026"


def describe(found: Governing) -> str:
    """One line naming the file and what it contributes, for a refusal message.

    Sorted by name so the same refusal reads the same way twice. The order
    inside an ini file is the author's, and a message somebody cannot grep for
    reliably is one they stop reading.
    """
    if found.unreadable:
        return f"{found.path}, which could not be read ({found.unreadable})"
    listed = ", ".join(f"{name} = {_trim(value)}" for name, value in sorted(found.settings))
    return f"{found.path}, which sets {listed}"
