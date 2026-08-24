# Recorded pytest output

Verbatim stdout from three real repositories after `bump-pydantic` ran on them
and left the suite broken. Captured 22 August 2026; the runs are reproducible
from the pinned SHAs in the fixture manifest.

One substitution was applied: absolute paths from the capturing machine were
replaced with `/work/repo`, `/work/.venv` and `/opt/python`. Nothing else was
edited -- not the tracebacks, not the frame ordering, not the error text.

The frame ordering matters. `F4-broken.txt` opens with a standard-library
`importlib` frame, which is neither vendored nor project code. It is kept
because it is the case that would break a naive "first non-vendored frame"
rule, and the test suite pins that behaviour.
