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
from dataclasses import dataclass
from pathlib import Path

CANDIDATES: tuple[str, ...] = ("pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg")
"""The filenames pytest considers, in the order it considers them.

Precedence is per directory, not global: pytest tries all four in the nearest
directory before moving to its parent. The order matters because ``pytest.ini``
wins over a ``pyproject.toml`` beside it.
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


def _pyproject(path: Path) -> Governing | None:
    """Read ``[tool.pytest.ini_options]``, or ``None`` if the table is absent."""
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return Governing(path=path, unreadable=str(exc))
    table = data.get("tool")
    if not isinstance(table, dict):
        return None
    pytest_table = table.get("pytest")
    if not isinstance(pytest_table, dict):
        return None
    options = pytest_table.get("ini_options")
    if not isinstance(options, dict):
        return None
    return Governing(
        path=path, settings=tuple((str(key), str(value)) for key, value in options.items())
    )


def _candidate(directory: Path, name: str) -> Governing | None:
    """Whether ``directory/name`` is an inifile, and what it sets."""
    path = directory / name
    if not path.is_file():
        return None
    if name == "pytest.ini":
        # pytest.ini counts even when it is completely empty. That is what makes
        # it usable as a deliberate barrier rather than only as configuration.
        return _ini_section(path, "pytest", always_matches=True)
    if name == "pyproject.toml":
        return _pyproject(path)
    if name == "tox.ini":
        return _ini_section(path, "pytest", always_matches=False)
    return _ini_section(path, "tool:pytest", always_matches=False)


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


def foreign_config(root: Path) -> Governing | None:
    """The governing inifile, but only when it is outside ``root`` and sets something.

    Args:
        root: The tree being edited.

    Returns:
        The offending :class:`Governing`, or ``None`` when the suite's
        configuration is the repository's own, absent, or present-but-neutral.
        A file *inside* ``root`` is never reported however much it sets: that is
        the repository configuring itself, which is the arrangement this check
        exists to steer people towards.
    """
    found = governing_config(root)
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
