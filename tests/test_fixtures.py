"""Tests for the fixture loader and cloner.

No test here touches the network. `clone` runs real git, but against a
repository built in a temporary directory and reached over a `file://` URL, so
the git behaviour under test is genuine while the dependency on GitHub is not.
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from bumpsmith import fixtures as fixtures_module
from bumpsmith.fixtures import (
    BARRIER,
    BARRIER_NAME,
    CloneResult,
    Fixture,
    FixtureError,
    GitError,
    ManifestError,
    clone,
    clone_all,
    default_manifest_path,
    load_manifest,
    main,
    select,
    write_barrier,
)
from bumpsmith.rootdir import foreign_config

_MANIFEST_TEMPLATE = """
[fixtures.demo]
url = "{url}"
sha = "{sha}"
pydantic = "1.10.26"
pytest_args = ["-q"]
expected_passed = 3
"""


def _git(*args: str, cwd: Path) -> str:
    completed = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return completed.stdout.strip()


def _origin_with_two_commits(tmp_path: Path) -> tuple[Path, str, str]:
    """Build a local repository and return (path, first_sha, tip_sha).

    The two commits differ in file content, so a clone can be checked for *which*
    commit it landed on rather than merely for succeeding.
    """
    origin = tmp_path / "origin"
    origin.mkdir()
    _git("init", "--quiet", "--initial-branch", "main", ".", cwd=origin)
    _git("config", "user.email", "fixtures@example.invalid", cwd=origin)
    _git("config", "user.name", "Fixture Builder", cwd=origin)
    # GitHub serves arbitrary commit SHAs; say so here too, so the test does not
    # depend on the local git version's default.
    _git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=origin)

    (origin / "marker.txt").write_text("pinned\n")
    _git("add", "--all", cwd=origin)
    _git("commit", "--quiet", "--message", "first", cwd=origin)
    pinned = _git("rev-parse", "HEAD", cwd=origin)

    (origin / "marker.txt").write_text("moved on\n")
    _git("add", "--all", cwd=origin)
    _git("commit", "--quiet", "--message", "second", cwd=origin)
    tip = _git("rev-parse", "HEAD", cwd=origin)

    return origin, pinned, tip


def _fixture_for(origin: Path, sha: str, fixture_id: str = "demo") -> Fixture:
    return Fixture(
        id=fixture_id,
        url=f"file://{origin}",
        sha=sha,
        pydantic="1.10.26",
        pytest_args=("-q",),
        expected_passed=3,
        notes="",
    )


def _write_manifest(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "fixtures.toml"
    path.write_text(body)
    return path


# --------------------------------------------------------------------------
# The manifest this repository actually ships
# --------------------------------------------------------------------------


def test_the_default_manifest_path_finds_the_shipped_manifest() -> None:
    """The default is computed from this module's location, two directories up.

    If the module ever moves, that arithmetic goes quietly wrong and every
    caller that relies on the default starts reading nothing.
    """
    path = default_manifest_path()
    assert path.name == "fixtures.toml"
    assert path.is_file()


def test_the_shipped_manifest_is_valid() -> None:
    """The repository's own manifest must load, or nothing else here matters."""
    fixtures = load_manifest()
    assert set(fixtures) == {"A", "B", "C", "F4"}


def test_every_shipped_fixture_pins_a_full_sha() -> None:
    for fixture in load_manifest().values():
        assert len(fixture.sha) == 40, fixture.id


def test_c_and_f4_are_the_same_project_at_different_commits() -> None:
    """C is the negative control: the commit F4 was migrated *to*."""
    fixtures = load_manifest()
    assert fixtures["C"].url == fixtures["F4"].url
    assert fixtures["C"].sha != fixtures["F4"].sha


# --------------------------------------------------------------------------
# Manifest validation
# --------------------------------------------------------------------------


def test_a_missing_manifest_says_how_to_supply_one(tmp_path: Path) -> None:
    with pytest.raises(ManifestError) as caught:
        load_manifest(tmp_path / "nowhere.toml")
    assert "--manifest" in str(caught.value)


def test_a_manifest_that_is_not_toml_is_reported_as_such(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "this is not = = toml\n")
    with pytest.raises(ManifestError, match="not valid TOML"):
        load_manifest(path)


def test_a_manifest_without_a_fixtures_table_is_refused(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path, "[something_else]\nkey = 1\n")
    with pytest.raises(ManifestError, match=r"\[fixtures\]"):
        load_manifest(path)


def test_an_abbreviated_sha_is_refused(tmp_path: Path) -> None:
    """git cannot fetch a short SHA, so accepting one only defers the failure."""
    path = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha="1c595e4")
    )
    with pytest.raises(ManifestError, match="40-character"):
        load_manifest(path)


def test_an_uppercase_sha_is_refused(tmp_path: Path) -> None:
    """git prints lowercase; a mixed-case pin would never equal what HEAD reports."""
    sha = "1C595E4806022CB80748000E37CD52C413C248A5"
    path = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha)
    )
    with pytest.raises(ManifestError, match="40-character"):
        load_manifest(path)


def test_a_url_git_would_read_as_an_option_is_refused(tmp_path: Path) -> None:
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    path = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url="--upload-pack=touch /tmp/x", sha=sha)
    )
    with pytest.raises(ManifestError, match="must begin with"):
        load_manifest(path)


def test_an_ssh_url_is_refused(tmp_path: Path) -> None:
    """A fixture a judge cannot clone anonymously is not a reproducible fixture."""
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    path = _write_manifest(
        tmp_path,
        _MANIFEST_TEMPLATE.format(url="git@github.com:emnify/emnify-sdk-python.git", sha=sha),
    )
    with pytest.raises(ManifestError, match="must begin with"):
        load_manifest(path)


def test_a_missing_key_is_named(tmp_path: Path) -> None:
    path = _write_manifest(
        tmp_path,
        '[fixtures.demo]\nurl = "https://x.invalid/r.git"\n'
        'sha = "1c595e4806022cb80748000e37cd52c413c248a5"\n',
    )
    with pytest.raises(ManifestError, match="expected_passed"):
        load_manifest(path)


def test_a_mistyped_key_is_refused_rather_than_ignored(tmp_path: Path) -> None:
    """A silently ignored typo produces a fixture that is not what the file says."""
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    body = _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha) + 'note = "typo"\n'
    path = _write_manifest(tmp_path, body)
    with pytest.raises(ManifestError, match="unrecognised key"):
        load_manifest(path)


def test_a_boolean_expected_passed_is_refused(tmp_path: Path) -> None:
    """bool subclasses int, so an unguarded check would read true as one test."""
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    body = _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha).replace(
        "expected_passed = 3", "expected_passed = true"
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(ManifestError, match="must be an integer"):
        load_manifest(path)


def test_a_negative_expected_passed_is_refused(tmp_path: Path) -> None:
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    body = _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha).replace(
        "expected_passed = 3", "expected_passed = -1"
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(ManifestError, match="negative"):
        load_manifest(path)


def test_a_fixture_id_containing_a_path_separator_is_refused(tmp_path: Path) -> None:
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    body = _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha).replace(
        "[fixtures.demo]", '[fixtures."../escape"]'
    )
    path = _write_manifest(tmp_path, body)
    with pytest.raises(ManifestError, match="usable fixture id"):
        load_manifest(path)


def test_notes_are_optional(tmp_path: Path) -> None:
    sha = "1c595e4806022cb80748000e37cd52c413c248a5"
    path = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url="https://x.invalid/r.git", sha=sha)
    )
    assert load_manifest(path)["demo"].notes == ""


# --------------------------------------------------------------------------
# Cloning
# --------------------------------------------------------------------------


def test_clone_checks_out_the_pinned_commit_and_not_the_tip(tmp_path: Path) -> None:
    """The point of the whole module: a pin must actually pin."""
    origin, pinned, tip = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"

    destination = clone(_fixture_for(origin, pinned), root)

    assert _git("rev-parse", "HEAD", cwd=destination) == pinned
    assert _git("rev-parse", "HEAD", cwd=destination) != tip
    assert (destination / "marker.txt").read_text() == "pinned\n"


def test_clone_places_the_fixture_in_a_directory_named_for_its_id(tmp_path: Path) -> None:
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"

    destination = clone(_fixture_for(origin, pinned, fixture_id="B"), root)

    assert destination == (root / "B").resolve()


def test_clone_refuses_a_non_empty_destination_without_touching_it(tmp_path: Path) -> None:
    """Nothing in this module deletes. Removing a previous clone is the caller's call."""
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"
    occupied = root / "demo"
    occupied.mkdir(parents=True)
    keepsake = occupied / "please-do-not-delete.txt"
    keepsake.write_text("still here\n")

    with pytest.raises(FixtureError, match="not empty"):
        clone(_fixture_for(origin, pinned), root)

    assert keepsake.read_text() == "still here\n"


def test_clone_refuses_when_the_destination_is_a_file(tmp_path: Path) -> None:
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"
    root.mkdir()
    (root / "demo").write_text("i am not a directory\n")

    with pytest.raises(FixtureError, match="not a directory"):
        clone(_fixture_for(origin, pinned), root)


def test_clone_refuses_an_id_that_would_escape_the_root(tmp_path: Path) -> None:
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"
    root.mkdir()

    with pytest.raises(FixtureError, match="not directly inside"):
        clone(_fixture_for(origin, pinned, fixture_id="../escape"), root)


def test_a_git_failure_carries_gits_own_explanation(tmp_path: Path) -> None:
    """A failure whose cause was discarded costs more than the call it saved.

    An unreachable remote fails both the single-commit fetch and the fallback,
    which is the case where git's own words are all the caller has to go on.
    """
    missing_origin = tmp_path / "no-such-repository"

    with pytest.raises(GitError) as caught:
        clone(_fixture_for(missing_origin, "0" * 40), tmp_path / "work")

    message = str(caught.value)
    assert "single commit" in message
    assert "every branch and tag" in message
    assert "git wrote nothing to stderr" not in message


def test_a_sha_on_no_branch_or_tag_says_so(tmp_path: Path) -> None:
    """The remote answers, and simply does not have the commit.

    git would report this as a pathspec that did not match. The fixture-level
    explanation -- force-pushed away, or the manifest is wrong -- is the one the
    caller can act on.
    """
    origin, _, _ = _origin_with_two_commits(tmp_path)

    with pytest.raises(GitError, match="on any branch or tag"):
        clone(_fixture_for(origin, "0" * 40), tmp_path / "work")


def test_the_full_fetch_recovers_when_a_single_commit_fetch_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Serving an object it never advertised is the server's decision.

    GitHub allows it and every fixture in the manifest takes that cheap path, so
    the refusal cannot be produced against a real remote here. It is simulated
    instead: the point under test is our recovery, not git's negotiation.
    """
    origin, pinned, tip = _origin_with_two_commits(tmp_path)
    real_git = fixtures_module._git
    refusals: list[str] = []

    def refusing_git(args: Sequence[str], *, cwd: Path, timeout: float) -> str:
        if list(args[:3]) == ["fetch", "--quiet", "--depth"]:
            refusals.append(" ".join(args))
            raise GitError("Server does not allow request for unadvertised object")
        return real_git(args, cwd=cwd, timeout=timeout)

    monkeypatch.setattr(fixtures_module, "_git", refusing_git)
    destination = clone(_fixture_for(origin, pinned), tmp_path / "work")

    assert refusals, "the cheap single-commit fetch should be tried first"
    assert _git("rev-parse", "HEAD", cwd=destination) == pinned
    assert _git("rev-parse", "HEAD", cwd=destination) != tip
    assert (destination / "marker.txt").read_text() == "pinned\n"


def test_clone_all_reports_every_fixture_even_when_one_fails(tmp_path: Path) -> None:
    """Partial failure in a batch is reported per item, never as a single abort."""
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    root = tmp_path / "work"
    fixtures = [
        _fixture_for(origin, pinned, fixture_id="good-one"),
        _fixture_for(origin, "0" * 40, fixture_id="bad"),
        _fixture_for(origin, pinned, fixture_id="good-two"),
    ]

    results = clone_all(fixtures, root)

    assert [result.fixture_id for result in results] == ["good-one", "bad", "good-two"]
    assert [result.succeeded for result in results] == [True, False, True]
    assert (root / "good-two" / "marker.txt").read_text() == "pinned\n"


def test_a_clone_result_carries_a_path_or_an_error_but_never_both() -> None:
    ok = CloneResult(fixture_id="demo", path=Path("/work/demo"), error=None)
    bad = CloneResult(fixture_id="demo", path=None, error="it broke")
    assert ok.succeeded
    assert not bad.succeeded


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------


def test_select_with_no_ids_returns_everything() -> None:
    fixtures = load_manifest()
    assert len(select(fixtures, [])) == len(fixtures)


def test_select_preserves_the_order_asked_for() -> None:
    fixtures = load_manifest()
    assert [fixture.id for fixture in select(fixtures, ["F4", "B"])] == ["F4", "B"]


def test_select_refuses_a_repeated_id(tmp_path: Path) -> None:
    """A repeated id can only collide with itself, so it is a usage error.

    Before this was checked, `fixtures B B` cloned B and then reported that the
    destination was not empty -- a clone failure for what is a typo.
    """
    fixtures = load_manifest()
    with pytest.raises(FixtureError, match="may not repeat"):
        select(fixtures, ["B", "B"])
    assert not (tmp_path / "B").exists()


def test_select_names_the_available_ids_when_one_is_unknown() -> None:
    fixtures = load_manifest()
    with pytest.raises(FixtureError) as caught:
        select(fixtures, ["B", "nope"])
    message = str(caught.value)
    assert "nope" in message
    assert "F4" in message


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def test_list_describes_the_fixtures_without_cloning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "work"

    exit_code = main(["--list", "--root", str(root)])

    assert exit_code == 0
    assert not root.exists()
    printed = capsys.readouterr().out
    assert "connect-eaas-core" in printed
    assert "347 passed" in printed


def test_the_printed_command_quotes_arguments_containing_spaces(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fixture A deselects with -m "not integration". Printed bare, a paste of
    that line runs a different command than the one the baseline came from."""
    assert main(["--list", "A"]) == 0
    assert "-m 'not integration'" in capsys.readouterr().out


def test_an_unknown_fixture_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list", "nope"]) == 2
    assert "nope" in capsys.readouterr().err


def test_repeated_ids_exit_two_without_cloning_anything(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "work"

    assert main(["B", "B", "--root", str(root)]) == 2

    assert not root.exists()
    assert "may not repeat" in capsys.readouterr().err


def test_a_non_positive_timeout_is_a_usage_error(tmp_path: Path) -> None:
    assert main(["B", "--root", str(tmp_path / "work"), "--timeout", "0"]) == 2


def test_main_clones_and_reports_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    origin, pinned, _ = _origin_with_two_commits(tmp_path)
    manifest = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url=f"file://{origin}", sha=pinned)
    )
    root = tmp_path / "work"

    exit_code = main(["--manifest", str(manifest), "--root", str(root)])

    assert exit_code == 0
    assert (root / "demo" / "marker.txt").read_text() == "pinned\n"
    assert "ok    demo" in capsys.readouterr().out


def test_main_returns_one_when_a_clone_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    origin, _, _ = _origin_with_two_commits(tmp_path)
    manifest = _write_manifest(
        tmp_path, _MANIFEST_TEMPLATE.format(url=f"file://{origin}", sha="0" * 40)
    )

    exit_code = main(["--manifest", str(manifest), "--root", str(tmp_path / "work")])

    assert exit_code == 1
    assert "FAIL  demo" in capsys.readouterr().err


# --------------------------------------------------------------------------
# The barrier that keeps this checkout out of the clones
# --------------------------------------------------------------------------


def test_cloning_writes_the_barrier_beside_the_fixture(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A fixture arrives already protected from the checkout it was cloned into.

    Writing it separately would be a step somebody forgets, and forgetting it is
    silent: the fixture runs, it just runs under the wrong settings.
    """
    origin, sha, _ = _origin_with_two_commits(tmp_path)
    manifest = _write_manifest(tmp_path, _MANIFEST_TEMPLATE.format(url=f"file://{origin}", sha=sha))
    root = tmp_path / "work"

    assert main(["--manifest", str(manifest), "--root", str(root)]) == 0
    capsys.readouterr()

    barrier = root / BARRIER_NAME
    assert barrier.is_file()
    assert foreign_config(root / "demo") is None


def test_the_barrier_is_never_written_over_something_that_is_already_there(
    tmp_path: Path,
) -> None:
    """It may be somebody's deliberate configuration for that directory.

    Replacing it would be the same class of surprise the barrier exists to
    prevent, arriving from the other direction.
    """
    root = tmp_path / "work"
    root.mkdir()
    mine = root / BARRIER_NAME
    mine.write_text("[pytest]\naddopts = --mine\n", encoding="utf-8")

    assert write_barrier(root) == mine
    assert mine.read_text(encoding="utf-8") == "[pytest]\naddopts = --mine\n"


def test_the_barrier_is_a_pytest_ini_because_the_others_do_not_count_when_empty() -> None:
    """The filename is load-bearing, and nothing else about the file is.

    `pytest.ini` is the one name pytest treats as configuration whatever it
    contains. Written as `tox.ini` or `setup.cfg` the same empty file would not
    stop the walk at all.
    """
    assert BARRIER_NAME == "pytest.ini"
    assert "[pytest]" in BARRIER


def test_a_directory_in_the_barriers_place_is_refused_not_accepted(tmp_path: Path) -> None:
    """pytest reads configuration from files, so a directory stops nothing.

    Asking only whether the path *existed* reported a barrier that was not there
    and let every clone inherit the checkout's settings in silence -- the worst
    available failure for a guard, which is to appear to be working.
    """
    root = tmp_path / "work"
    root.mkdir()
    (root / BARRIER_NAME).mkdir()

    with pytest.raises(FixtureError, match="is not a file"):
        write_barrier(root)


def test_a_barrier_that_cannot_be_written_fails_that_fixture_not_the_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`clone_all` converts `FixtureError` per fixture; an `OSError` would escape.

    A permission or disk-full error ended the whole command in a traceback, so
    the fixtures that would have worked were never attempted.

    The failure here is a dangling symlink rather than a permission bit: it is
    deterministic, needs no `chmod` that a root-owned CI would ignore, and lands
    on the *write* rather than on the "not a file" check above -- which is the
    point. A first version of this test used a directory, which tripped the other
    guard and left this one covered by nothing.
    """
    origin, sha, _ = _origin_with_two_commits(tmp_path)
    manifest = _write_manifest(tmp_path, _MANIFEST_TEMPLATE.format(url=f"file://{origin}", sha=sha))
    root = tmp_path / "work"
    root.mkdir()
    (root / BARRIER_NAME).symlink_to(root / "no-such-directory" / "target.ini")

    exit_code = main(["--manifest", str(manifest), "--root", str(root)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "FAIL  demo" in captured.err
    assert "Could not write the pytest barrier" in captured.err


def test_a_directory_in_the_barriers_place_fails_that_fixture_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same routing, for the other of the two ways the barrier can be refused."""
    origin, sha, _ = _origin_with_two_commits(tmp_path)
    manifest = _write_manifest(tmp_path, _MANIFEST_TEMPLATE.format(url=f"file://{origin}", sha=sha))
    root = tmp_path / "work"
    root.mkdir()
    (root / BARRIER_NAME).mkdir()

    exit_code = main(["--manifest", str(manifest), "--root", str(root)])

    assert exit_code == 1
    assert "is not a file" in capsys.readouterr().err
