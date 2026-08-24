"""Tests for the fixture loader and cloner.

No test here touches the network. `clone` runs real git, but against a
repository built in a temporary directory and reached over a `file://` URL, so
the git behaviour under test is genuine while the dependency on GitHub is not.
"""

import subprocess
from pathlib import Path

import pytest

from bumpsmith.fixtures import (
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
)

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
    """A failure whose cause was discarded costs more than the call it saved."""
    origin, _, _ = _origin_with_two_commits(tmp_path)
    absent = "0" * 40

    with pytest.raises(GitError) as caught:
        clone(_fixture_for(origin, absent), tmp_path / "work")

    message = str(caught.value)
    assert "git fetch" in message
    assert "git wrote nothing to stderr" not in message


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
