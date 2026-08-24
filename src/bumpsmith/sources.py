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
    """Read ``path`` with the encoding Python would use for it, byte-exactly.

    Deliberately not ``tokenize.open``. That wraps the file in a TextIOWrapper
    with universal newlines, so a CRLF source is read as if it were LF -- and
    text that came back different from what was on disk cannot be written back
    to produce the original bytes. Reading the raw bytes and decoding them keeps
    ``\r\n`` intact, which is what makes a byte-for-byte revert possible.

    Raises :class:`OSError` if the file cannot be read, and ``SyntaxError``,
    ``UnicodeDecodeError`` or ``ValueError`` if it cannot be decoded -- the same
    errors Python raises when it declines to import the file.
    """
    with path.open("rb") as handle:
        encoding, _ = tokenize.detect_encoding(handle.readline)
        handle.seek(0)
        raw = handle.read()
    return Source(text=raw.decode(encoding), encoding=encoding)
