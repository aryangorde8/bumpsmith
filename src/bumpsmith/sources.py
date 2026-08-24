"""Read a Python file the way Python itself reads it.

Two things in this project need this and they have to agree. A source file may
declare its own encoding through a BOM or a ``# coding:`` cookie (PEP 263), so
reading everything as UTF-8 misreads a perfectly legal file -- and, worse,
writing it back as UTF-8 after an edit would corrupt it. The encoding travels
with the text for that second reason: a reader can ignore it, but a writer
cannot.
"""

import tokenize
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Source:
    """One file's contents and the encoding they were read with."""

    text: str
    encoding: str


def read_source(path: Path) -> Source:
    """Read ``path`` with the encoding Python would use for it.

    Raises :class:`OSError` if the file cannot be read, and ``SyntaxError``,
    ``UnicodeDecodeError`` or ``ValueError`` if it cannot be decoded -- the same
    errors Python raises when it declines to import the file.
    """
    with tokenize.open(path) as handle:
        return Source(text=handle.read(), encoding=handle.encoding)
