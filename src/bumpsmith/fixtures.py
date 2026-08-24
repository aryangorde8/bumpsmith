"""Reconstitute the migration fixtures from their upstream repositories.

The repositories bumpsmith is measured against are four real projects, not test
doubles. They are deliberately **not** vendored into this repository: a vendored
copy is a snapshot whose provenance decays, and the whole point of a fixture is
that somebody else can obtain exactly the same one. So this module reads
``fixtures.toml`` and rebuilds any of them from upstream at a pinned commit.

Pinning is only half of it. A tag can be moved and a branch always moves, so a
full commit SHA is the only reference that cannot change underneath us. But a
reference that cannot change is still worth checking: every clone here ends by
comparing ``HEAD`` against the SHA that was asked for, and fails if they differ.
A fixture that is not the recorded fixture makes every measurement taken against
it meaningless, and that is worse than not having it.
"""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MANIFEST_NAME = "fixtures.toml"

# Full 40-character SHAs only. An abbreviated SHA is a prefix, and a prefix can
# become ambiguous as a repository grows -- but more immediately, `git fetch`
# will not accept one, so a short SHA in the manifest is simply not usable.
_SHA_PATTERN = re.compile(r"\A[0-9a-f]{40}\Z")

# Fixture ids become directory names, so they may not contain a separator or a
# parent reference.
_FIXTURE_ID_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")

# `file://` is allowed so the test suite can exercise real git against a local
# repository instead of reaching the network. Anything not listed here is
# refused, which also rejects a URL beginning with "-" -- git would read that as
# an option rather than as a remote.
_ALLOWED_URL_SCHEMES = ("https://", "file://")

_REQUIRED_KEYS = frozenset({"url", "sha", "pydantic", "pytest_args", "expected_passed"})
_OPTIONAL_KEYS = frozenset({"notes"})

DEFAULT_TIMEOUT = 300.0
"""Seconds allowed for any single git command. The largest fixture is ~11 MB at
depth 1, so this is generous; it exists so a stalled network fails instead of
hanging forever."""


class FixtureError(Exception):
    """A fixture could not be described or obtained."""


class ManifestError(FixtureError):
    """The manifest is missing, malformed, or internally inconsistent."""


class GitError(FixtureError):
    """A git command failed, timed out, or git is not installed."""


@dataclass(frozen=True, slots=True)
class Fixture:
    """One pinned upstream repository and the baseline it is expected to produce."""

    id: str
    url: str
    sha: str
    pydantic: str
    pytest_args: tuple[str, ...]
    expected_passed: int
    notes: str


@dataclass(frozen=True, slots=True)
class CloneResult:
    """The outcome of cloning a single fixture.

    Exactly one of ``path`` and ``error`` is set.
    """

    fixture_id: str
    path: Path | None
    error: str | None

    @property
    def succeeded(self) -> bool:
        return self.error is None


def default_manifest_path() -> Path:
    """Return the manifest that sits beside this checkout.

    Resolved from this file's location rather than from the working directory,
    so the command behaves the same wherever it is run from. When bumpsmith is
    installed from a wheel the manifest is not packaged with it and this path
    will not exist; :func:`load_manifest` says so and asks for an explicit one.
    """
    return Path(__file__).resolve().parents[2] / _MANIFEST_NAME


def load_manifest(path: Path | None = None) -> dict[str, Fixture]:
    """Read and validate the fixture manifest.

    Returns a mapping of fixture id to :class:`Fixture`, in the order the file
    declares them. Raises :class:`ManifestError` if the file is absent,
    unreadable, not valid TOML, or describes a fixture that could not be used.
    """
    manifest_path = default_manifest_path() if path is None else path
    try:
        raw = manifest_path.read_bytes()
    except FileNotFoundError as exc:
        raise ManifestError(
            f"No fixture manifest at {manifest_path}. Expected a TOML file named "
            f"{_MANIFEST_NAME}; pass --manifest to point at one."
        ) from exc
    except OSError as exc:
        raise ManifestError(
            f"Could not read the fixture manifest at {manifest_path}: {exc}"
        ) from exc

    try:
        document = tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ManifestError(f"{manifest_path} is not UTF-8 text: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ManifestError(f"{manifest_path} is not valid TOML: {exc}") from exc

    section: Any = document.get("fixtures")
    if section is None:
        raise ManifestError(
            f"{manifest_path} has no [fixtures] table. Each fixture is declared as "
            f"[fixtures.<id>] with url, sha, pydantic, pytest_args and expected_passed."
        )
    if not isinstance(section, dict):
        raise ManifestError(
            f"{manifest_path}: [fixtures] must be a table, not {type(section).__name__}."
        )
    if not section:
        raise ManifestError(f"{manifest_path} declares no fixtures under [fixtures].")

    fixtures: dict[str, Fixture] = {}
    for fixture_id, body in section.items():
        fixture = _fixture_from_toml(fixture_id, body, manifest_path)
        fixtures[fixture.id] = fixture
    return fixtures


def _fixture_from_toml(fixture_id: Any, body: Any, source: Path) -> Fixture:
    """Build one :class:`Fixture`, rejecting anything the manifest got wrong."""
    if not isinstance(fixture_id, str) or not _FIXTURE_ID_PATTERN.fullmatch(fixture_id):
        raise ManifestError(
            f"{source}: {fixture_id!r} is not a usable fixture id. Ids become directory "
            f"names, so they must start with a letter or digit and contain only letters, "
            f"digits, dot, dash and underscore."
        )
    if not isinstance(body, dict):
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] must be a table, not {type(body).__name__}."
        )

    keys = set(body)
    missing = _REQUIRED_KEYS - keys
    if missing:
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] is missing {', '.join(sorted(missing))}."
        )
    # An unrecognised key is almost always a typo, and a typo that is silently
    # ignored produces a fixture that is not what the file appears to say.
    unknown = keys - _REQUIRED_KEYS - _OPTIONAL_KEYS
    if unknown:
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] has unrecognised key(s) "
            f"{', '.join(sorted(unknown))}. Known keys are "
            f"{', '.join(sorted(_REQUIRED_KEYS | _OPTIONAL_KEYS))}."
        )

    url = _require_str(body, "url", fixture_id, source)
    if not url.startswith(_ALLOWED_URL_SCHEMES):
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] url must begin with one of "
            f"{', '.join(_ALLOWED_URL_SCHEMES)}; got {url!r}."
        )

    sha = _require_str(body, "sha", fixture_id, source)
    if not _SHA_PATTERN.fullmatch(sha):
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] sha must be a full 40-character commit "
            f"SHA in lowercase hex; got {sha!r}. git cannot fetch an abbreviated SHA, "
            f"and an abbreviation is a prefix that may stop being unique."
        )

    pydantic = _require_str(body, "pydantic", fixture_id, source)

    raw_args: Any = body["pytest_args"]
    if not isinstance(raw_args, list) or not all(isinstance(item, str) for item in raw_args):
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] pytest_args must be a list of strings."
        )

    expected_passed: Any = body["expected_passed"]
    # bool is a subclass of int, so `isinstance(True, int)` is true. A boolean
    # here would silently become 0 or 1 tests.
    if isinstance(expected_passed, bool) or not isinstance(expected_passed, int):
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] expected_passed must be an integer."
        )
    if expected_passed < 0:
        raise ManifestError(
            f"{source}: [fixtures.{fixture_id}] expected_passed must not be negative; "
            f"got {expected_passed}."
        )

    notes: Any = body.get("notes", "")
    if not isinstance(notes, str):
        raise ManifestError(f"{source}: [fixtures.{fixture_id}] notes must be a string.")

    return Fixture(
        id=fixture_id,
        url=url,
        sha=sha,
        pydantic=pydantic,
        pytest_args=tuple(raw_args),
        expected_passed=expected_passed,
        notes=notes.strip(),
    )


def _require_str(body: dict[str, Any], key: str, fixture_id: str, source: Path) -> str:
    value: Any = body[key]
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{source}: [fixtures.{fixture_id}] {key} must be a non-empty string.")
    return value


def _git_binary() -> str:
    """Return the absolute path to git, or explain that it is missing."""
    resolved = shutil.which("git")
    if resolved is None:
        raise GitError(
            "git was not found on PATH. bumpsmith obtains its fixtures by cloning "
            "them; install git and run this again."
        )
    return resolved


def _git(args: Sequence[str], *, cwd: Path, timeout: float) -> str:
    """Run one git command in ``cwd`` and return its stdout, stripped.

    Raises :class:`GitError` if git is absent, cannot be started, exceeds
    ``timeout``, or exits non-zero -- carrying git's own stderr, because a
    failure whose cause was discarded costs more than the call saved.
    """
    command = [_git_binary(), *args]
    printable = "git " + " ".join(args)
    # Arguments are passed as a list, so the shell never sees this and nothing
    # is word-split or globbed. The only manifest value that lands where git
    # could read it as an option is the remote URL, and load_manifest has
    # already required a known scheme.
    #
    # GIT_TERMINAL_PROMPT=0 turns a private or mistyped URL into an immediate
    # failure rather than a prompt for a username that nothing will ever answer.
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(
            f"`{printable}` did not finish within {timeout:g}s and was stopped. "
            f"If the network is slow rather than broken, retry with a larger --timeout."
        ) from exc
    except OSError as exc:
        raise GitError(f"Could not run `{printable}`: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "(git wrote nothing to stderr)"
        raise GitError(f"`{printable}` exited with code {completed.returncode}.\n{detail}")
    return completed.stdout.strip()


def _prepare_destination(root: Path, fixture: Fixture) -> Path:
    """Return an empty directory for ``fixture`` inside ``root``, creating it.

    Nothing here deletes or overwrites: if the directory already holds anything,
    this refuses and says so. Removing a previous clone is the caller's decision
    to make, not a side effect of asking for a fresh one.
    """
    resolved_root = root.resolve()
    destination = (resolved_root / fixture.id).resolve()
    if destination.parent != resolved_root:
        raise FixtureError(
            f"Refusing to clone {fixture.id}: {destination} is not directly inside {resolved_root}."
        )

    if destination.exists():
        if not destination.is_dir():
            raise FixtureError(
                f"Refusing to clone {fixture.id}: {destination} exists and is not a "
                f"directory. Move it aside or choose another --root; this command "
                f"never deletes anything."
            )
        if any(destination.iterdir()):
            raise FixtureError(
                f"Refusing to clone {fixture.id}: {destination} already exists and is "
                f"not empty. Remove it yourself or choose another --root; this command "
                f"never deletes anything."
            )
        return destination

    try:
        destination.mkdir(parents=True)
    except OSError as exc:
        raise FixtureError(f"Could not create {destination}: {exc}") from exc
    return destination


def _fetch_pinned_commit(fixture: Fixture, destination: Path, timeout: float) -> str:
    """Obtain the pinned commit and return the ref to check out.

    Asking a server for one commit by SHA is the cheap path -- for the largest
    fixture here that is 11 MB at depth 1 instead of a full history nobody
    reads. But whether a server will serve an object it never advertised is the
    *server's* decision (``uploadpack.allowAnySHA1InWant``), not ours. GitHub
    allows it, which is why every fixture in this manifest takes the cheap path.

    A host that refuses gets the ordinary fetch instead: every branch and tag,
    which needs no server-side permission because those refs are advertised.
    It costs more bytes and it is still the same commit at the end, because the
    caller verifies ``HEAD`` either way.
    """
    try:
        _git(
            ["fetch", "--quiet", "--depth", "1", "origin", fixture.sha],
            cwd=destination,
            timeout=timeout,
        )
    except GitError as unadvertised_fetch_failed:
        try:
            _git(["fetch", "--quiet", "--tags", "origin"], cwd=destination, timeout=timeout)
        except GitError as full_fetch_failed:
            raise GitError(
                f"Could not fetch {fixture.id} from {fixture.url}.\n"
                f"Asking for the single commit {fixture.sha} failed:\n"
                f"{unadvertised_fetch_failed}\n"
                f"Fetching every branch and tag also failed:\n{full_fetch_failed}"
            ) from full_fetch_failed

        # The full fetch only brings down what the branches and tags reach. A
        # commit that has been force-pushed away is reachable from none of them,
        # and saying so is more use than git's "pathspec did not match" would be.
        try:
            _git(
                ["cat-file", "-e", f"{fixture.sha}^{{commit}}"],
                cwd=destination,
                timeout=timeout,
            )
        except GitError as commit_absent:
            raise GitError(
                f"{fixture.url} does not have commit {fixture.sha} on any branch or "
                f"tag. It may have been removed by a force-push, or the SHA in the "
                f"manifest may be wrong. Either way this fixture cannot be rebuilt "
                f"from that URL as recorded."
            ) from commit_absent
        return fixture.sha

    # The single-commit fetch leaves the pinned commit, and only it, at FETCH_HEAD.
    return "FETCH_HEAD"


def clone(fixture: Fixture, root: Path, *, timeout: float = DEFAULT_TIMEOUT) -> Path:
    """Clone one fixture into ``root/<id>`` at its pinned SHA and return the path.

    Raises :class:`GitError` if git fails, and :class:`FixtureError` if the
    destination is unusable or the checked-out commit is not the pinned one.
    """
    destination = _prepare_destination(root, fixture)
    _git(["init", "--quiet", "."], cwd=destination, timeout=timeout)
    _git(["remote", "add", "origin", fixture.url], cwd=destination, timeout=timeout)
    checkout_target = _fetch_pinned_commit(fixture, destination, timeout)
    _git(["checkout", "--quiet", "--detach", checkout_target], cwd=destination, timeout=timeout)

    head = _git(["rev-parse", "HEAD"], cwd=destination, timeout=timeout)
    if head != fixture.sha:
        raise FixtureError(
            f"Fixture {fixture.id} checked out at {head}, but the manifest pins "
            f"{fixture.sha}. The clone in {destination} is not the recorded fixture, so "
            f"any result measured against it would mean nothing. Remove it and retry."
        )
    return destination


def clone_all(
    fixtures: Sequence[Fixture], root: Path, *, timeout: float = DEFAULT_TIMEOUT
) -> list[CloneResult]:
    """Clone each fixture, returning one result per fixture in the order given.

    A fixture that fails does not stop the rest. A half-built fixture set that
    reports only its first error is the least useful of the possible outcomes:
    you learn about one problem, do not learn about the others, and cannot tell
    which of the remaining fixtures are present.
    """
    results: list[CloneResult] = []
    for fixture in fixtures:
        try:
            path = clone(fixture, root, timeout=timeout)
        except FixtureError as exc:
            results.append(CloneResult(fixture_id=fixture.id, path=None, error=str(exc)))
        else:
            results.append(CloneResult(fixture_id=fixture.id, path=path, error=None))
    return results


def select(fixtures: dict[str, Fixture], ids: Sequence[str]) -> list[Fixture]:
    """Return the requested fixtures, or all of them when ``ids`` is empty.

    Raises :class:`FixtureError` naming the ids that do not exist, together with
    the ones that do -- a bare "unknown fixture" leaves the caller guessing.
    """
    if not ids:
        return list(fixtures.values())
    # Each fixture clones into one directory named for it, so a repeated id can
    # only ever collide with itself. Refusing here makes that a usage error the
    # caller can see, instead of a "destination is not empty" failure reported
    # after the first copy has already been cloned.
    repeated = sorted(name for name, count in Counter(ids).items() if count > 1)
    if repeated:
        raise FixtureError(
            f"Fixture ids may not repeat: {', '.join(repeated)}. Each fixture clones "
            f"into a single directory named for it."
        )
    unknown = [fixture_id for fixture_id in ids if fixture_id not in fixtures]
    if unknown:
        raise FixtureError(
            f"No such fixture: {', '.join(unknown)}. The manifest defines {', '.join(fixtures)}."
        )
    return [fixtures[fixture_id] for fixture_id in ids]


def _describe(fixture: Fixture) -> str:
    """One paragraph telling a reader how to reproduce this fixture's baseline."""
    # shlex.join, not " ".join: fixture A deselects with -m "not integration",
    # and an unquoted copy-paste of that runs a different command than the one
    # the baseline was recorded with.
    command = shlex.join(["python", "-m", "pytest", "-q", *fixture.pytest_args])
    lines = [
        f"  pydantic {fixture.pydantic}, baseline {fixture.expected_passed} passed",
        f"  {command}",
    ]
    if fixture.notes:
        lines.extend(f"  {line}" for line in fixture.notes.splitlines())
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m bumpsmith.fixtures",
        description=(
            "Clone the migration fixtures from their upstream repositories at the "
            "commits pinned in fixtures.toml."
        ),
    )
    parser.add_argument("ids", nargs="*", help="fixture ids to clone (default: all of them)")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("fixtures"),
        help="directory to clone into, one subdirectory per fixture (default: ./fixtures)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=f"path to {_MANIFEST_NAME} (default: the one beside this checkout)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"seconds allowed for each git command (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the fixtures the manifest defines and exit without cloning",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit code."""
    args = _build_parser().parse_args(argv)

    try:
        fixtures = load_manifest(args.manifest)
        wanted = select(fixtures, args.ids)
    except FixtureError as exc:
        print(exc, file=sys.stderr)
        return 2

    if args.list:
        for fixture in wanted:
            print(f"{fixture.id}  {fixture.url}@{fixture.sha}")
            print(_describe(fixture))
        return 0

    if args.timeout <= 0:
        print(f"--timeout must be positive; got {args.timeout:g}.", file=sys.stderr)
        return 2

    results = clone_all(wanted, args.root, timeout=args.timeout)
    by_id = {fixture.id: fixture for fixture in wanted}
    for result in results:
        if result.succeeded:
            print(f"ok    {result.fixture_id}  ->  {result.path}")
            print(_describe(by_id[result.fixture_id]))
        else:
            # stderr is unbuffered and a piped stdout is not, so without this the
            # failures overtake the successes and the report reads out of order.
            sys.stdout.flush()
            print(f"FAIL  {result.fixture_id}", file=sys.stderr)
            print(f"  {result.error}", file=sys.stderr)

    failed = [result.fixture_id for result in results if not result.succeeded]
    if failed:
        sys.stdout.flush()
        print(
            f"\n{len(failed)} of {len(results)} fixtures failed: {', '.join(failed)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
