"""bumpsmith — migrate a repository from pydantic v1 to v2, and keep the change
only once its test suite has come back green.

Start at :mod:`bumpsmith.migrate`. It is the loop, and every other module is a
part it uses:

===========================  ===================================================
:mod:`bumpsmith.run`         where a suite runs, locally or in the harness's sandbox
:mod:`bumpsmith.remote`      running the whole loop inside that sandbox instead
:mod:`bumpsmith.fanout`      several subjects at once, each in a tree of its own
:mod:`bumpsmith.failures`    what pytest's output says the break is
:mod:`bumpsmith.rules`       which migration rule that break implies, and every site
:mod:`bumpsmith.rewrite`     the smallest edit that carries the rule out
:mod:`bumpsmith.apply`       applying it as a transaction that reverts by default
:mod:`bumpsmith.gate`        stopping before anything irreversible
:mod:`bumpsmith.publish`     the one irreversible thing, and only where somebody said
:mod:`bumpsmith.harness`     answering TrueForge's approval events with that gate
:mod:`bumpsmith.trueforge`   the transport, and the only place a socket is opened
:mod:`bumpsmith.report`      the run as a page, from the payload ``--json`` writes
:mod:`bumpsmith.rootdir`     whose pytest configuration the subject's suite runs under
:mod:`bumpsmith.sources`     one byte-exact reader, so encoding handling cannot drift
:mod:`bumpsmith.fixtures`    cloning the repositories it is measured against
===========================  ===================================================

Nothing is re-exported here. ``bumpsmith.migrate`` is both a module and the
function inside it, and a package that bound one name to both would make
``from bumpsmith import migrate`` mean different things depending on import
order.

``python -m bumpsmith`` runs the loop from a command line; see the README.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
