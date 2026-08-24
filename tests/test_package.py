"""Guard the two things the skeleton actually promises.

REVIEW.md: "A test with no assertion is a finding." These assert on behaviour
that would genuinely break a consumer -- that the package imports under the
pinned interpreter, and that it advertises itself as typed.
"""

import importlib.resources
import sys

import bumpsmith


def test_requires_python_313_or_newer() -> None:
    """The pinned floor in pyproject.toml must match the running interpreter.

    A mismatch here means CI is testing a Python the project does not claim to
    support, which makes every other green result untrustworthy.
    """
    assert sys.version_info >= (3, 13)


def test_package_is_marked_typed() -> None:
    """py.typed must ship, or mypy silently ignores this package downstream."""
    marker = importlib.resources.files(bumpsmith).joinpath("py.typed")
    assert marker.is_file()
