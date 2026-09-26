import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import cgwt.create
import cgwt.git
from cgwt.cli import main
from cgwt.create import resolve_branch
from cgwt.errors import CgwtError
from cgwt.git import list_worktrees
from cgwt.project import read_project


def test_branch_only_on_origin_is_tracked(git: Callable[..., str], repository: Path) -> None:
    git(repository, "branch", "feature-x")
    git(repository, "push", "origin", "feature-x")
    git(repository, "branch", "-D", "feature-x")

    assert resolve_branch(repository, "feature-x", "origin/HEAD") == "tracked"


def test_local_branch_not_checked_out_is_existing(
    git: Callable[..., str], repository: Path
) -> None:
    git(repository, "branch", "feature-local")

    assert resolve_branch(repository, "feature-local", "origin/HEAD") == "existing"


def test_branch_checked_out_in_a_worktree_is_refused(repository: Path) -> None:
    with pytest.raises(CgwtError) as error_info:
        resolve_branch(repository, "main", "origin/HEAD")

    assert error_info.value.exit_code == 5
    assert str(list_worktrees(repository)[0].path) in error_info.value.message


def test_unknown_branch_with_a_resolving_base_is_created(repository: Path) -> None:
    assert resolve_branch(repository, "feature-new", "origin/HEAD") == "created"


def test_base_that_does_not_resolve_is_refused(repository: Path) -> None:
    with pytest.raises(CgwtError) as error_info:
        resolve_branch(repository, "feature-new", "bogus")

    assert error_info.value.exit_code == 1
    assert "bogus" in error_info.value.message


def test_missing_origin_head_names_the_set_head_command(
    git: Callable[..., str], repository: Path
) -> None:
    git(repository, "remote", "set-head", "origin", "-d")

    with pytest.raises(CgwtError) as error_info:
        resolve_branch(repository, "feature-new", "origin/HEAD")

    assert error_info.value.exit_code == 1
    assert "git remote set-head origin --auto" in error_info.value.message


def test_remote_qualified_branch_is_refused(git: Callable[..., str], repository: Path) -> None:
    git(repository, "branch", "feature-x")
    git(repository, "push", "origin", "feature-x")

    with pytest.raises(CgwtError) as error_info:
        resolve_branch(repository, "origin/feature-x", "origin/HEAD")

    assert error_info.value.exit_code == 1
    assert "feature-x" in error_info.value.message


def test_resolve_branch_never_fetches(
    git: Callable[..., str], repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    git(repository, "branch", "feature-x")
    git(repository, "push", "origin", "feature-x")
    git(repository, "branch", "-D", "feature-x")
    git(repository, "branch", "feature-local")
    recorded_args: list[list[str]] = []

    def run_git_recording_args(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        recorded_args.append(args)
        return cgwt.git.run_git(args, cwd, check)

    monkeypatch.setattr(cgwt.create, "run_git", run_git_recording_args)

    for branch in ["feature-x", "feature-local", "feature-new"]:
        resolve_branch(repository, branch, "origin/HEAD")

    assert recorded_args
    assert not [args for args in recorded_args if args[0] == "fetch"]


def test_create_makes_a_new_branch_from_origin_head(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "worktrees" / "widget" / "feature-new"

    assert main(["create", "feature-new", "--repo", str(repository)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"{path}\n"
    assert captured.err == f"cgwt: created feature-new from origin/HEAD at {path}\n"
    assert (path / ".git").is_file()
    assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "feature-new\n"
    assert git(path, "rev-parse", "HEAD") == git(repository, "rev-parse", "origin/HEAD")


def test_create_makes_a_new_branch_from_the_base_flag(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git(repository, "commit", "--allow-empty", "-m", "local")
    path = tmp_path / "worktrees" / "widget" / "feature-new"

    assert main(["create", "feature-new", "--base", "main", "--repo", str(repository)]) == 0

    assert capsys.readouterr().err == f"cgwt: created feature-new from main at {path}\n"
    assert git(path, "rev-parse", "HEAD") == git(repository, "rev-parse", "main")


def test_create_tracks_a_branch_that_the_fetch_brings(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed = tmp_path / "seed"
    git(seed, "branch", "feature-x")
    git(seed, "push", "origin", "feature-x")
    path = tmp_path / "worktrees" / "widget" / "feature-x"

    assert main(["create", "feature-x", "--repo", str(repository)]) == 0

    assert capsys.readouterr().err == f"cgwt: tracked origin/feature-x at {path}\n"
    assert git(path, "rev-parse", "--abbrev-ref", "@{upstream}") == "origin/feature-x\n"


def test_create_checks_out_an_existing_local_branch(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git(repository, "branch", "feature-local")
    path = tmp_path / "worktrees" / "widget" / "feature-local"

    assert main(["create", "feature-local", "--repo", str(repository)]) == 0

    assert capsys.readouterr().err == f"cgwt: existing feature-local at {path}\n"
    assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "feature-local\n"


def test_create_replaces_the_slash_of_the_branch_in_the_path(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    path = tmp_path / "worktrees" / "widget" / "feature-x"

    assert main(["create", "feature/x", "--repo", str(repository)]) == 0

    assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "feature/x\n"


def test_create_follows_the_split_layout_of_the_configuration(
    git: Callable[..., str],
    config: Callable[[str], None],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config("split-layout.toml")
    git(repository, "remote", "set-url", "origin", "git@example.com:acme/meta.project.git")
    path = tmp_path / "worktrees" / "meta.project" / "feature-x" / "meta" / "project" / "widget"

    assert main(["create", "feature-x", "--no-fetch", "--repo", str(repository)]) == 0

    assert capsys.readouterr().out == f"{path}\n"


def test_create_prints_the_worktree_and_the_outcome_as_json(
    repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "worktrees" / "widget" / "feature-new"

    assert main(["create", "feature-new", "--json", "--repo", str(repository)]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "path": str(path),
        "branch": "feature-new",
        "project": read_project(repository).identifier,
        "repository": str(repository.resolve()),
        "locked": False,
        "broken": False,
        "outcome": "created",
    }
    assert captured.err == f"cgwt: created feature-new from origin/HEAD at {path}\n"


def test_no_fetch_flag_skips_the_fetch(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git(repository, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))

    assert main(["create", "feature-new", "--no-fetch", "--repo", str(repository)]) == 0

    assert capsys.readouterr().err.startswith("cgwt: created feature-new")


def test_fetch_false_in_the_configuration_skips_the_fetch(
    git: Callable[..., str],
    config: Callable[[str], None],
    repository: Path,
    tmp_path: Path,
) -> None:
    config("no-fetch.toml")
    git(repository, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))

    assert main(["create", "feature-new", "--repo", str(repository)]) == 0


def test_repo_flag_selects_the_repository_from_outside(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["create", "feature-new", "--repo", str(repository)]) == 0

    assert (tmp_path / "worktrees" / "widget" / "feature-new" / ".git").is_file()


def test_create_outside_a_repository_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    assert main(["create", "feature-new"]) == 1

    captured = capsys.readouterr()
    assert "not inside a git repository" in captured.err
    assert captured.out == ""


def test_create_help_lists_the_arguments_and_the_exit_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["create", "--help"])

    assert exit_info.value.code == 0
    help_text = capsys.readouterr().out
    for expected_text in [
        "branch",
        "--base",
        "--no-fetch",
        "--repo",
        "--json",
        "1  failure: configuration error, missing origin, failed git command",
        "2  usage error",
        "5  the branch is checked out in another worktree",
        "6  path collision",
    ]:
        assert expected_text in help_text


def test_failed_fetch_names_the_no_fetch_flag(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git(repository, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))

    assert main(["create", "feature-new", "--repo", str(repository)]) == 1

    captured = capsys.readouterr()
    assert captured.err.startswith("cgwt: error: git fetch origin failed.")
    assert "--no-fetch" in captured.err
    assert captured.out == ""


def test_base_flag_on_an_existing_branch_is_refused(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    git(repository, "branch", "feature-local")

    assert main(["create", "feature-local", "--base", "main", "--repo", str(repository)]) == 1

    captured = capsys.readouterr()
    assert "feature-local" in captured.err
    assert "Drop --base" in captured.err
    assert captured.out == ""
    assert not (tmp_path / "worktrees").exists()


@pytest.mark.parametrize("extra_args", [[], ["--json"]])
def test_empty_directory_at_the_path_is_a_collision(
    extra_args: list[str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "worktrees" / "widget" / "feature-new"
    path.mkdir(parents=True)

    assert main(["create", "feature-new", "--repo", str(repository), *extra_args]) == 6

    captured = capsys.readouterr()
    assert captured.err == f"cgwt: error: {path}: already exists and is not a worktree\n"
    assert captured.out == ""


def test_worktree_at_the_path_is_a_collision_that_names_it(
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "worktrees" / "widget" / "feature-x"
    assert main(["create", "feature-x", "--repo", str(repository)]) == 0
    capsys.readouterr()

    assert main(["create", "feature/x", "--repo", str(repository)]) == 6

    captured = capsys.readouterr()
    assert captured.err == (
        f"cgwt: error: {path}: already used by worktree of feature-x from {repository.resolve()}\n"
    )
    assert captured.out == ""
    assert git(repository, "branch", "--list", "feature/x") == ""


def test_workforest_that_is_a_file_is_reported(
    repository: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "worktrees").write_text("")

    assert main(["create", "feature-new", "--repo", str(repository)]) == 1

    captured = capsys.readouterr()
    assert "Not a directory" in captured.err
    assert captured.out == ""


@pytest.mark.parametrize("branch_exists_before", [False, True])
def test_failed_worktree_add_is_rolled_back(
    branch_exists_before: bool,
    git: Callable[..., str],
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if branch_exists_before:
        git(repository, "branch", "feature-x")
    path = tmp_path / "worktrees" / "widget" / "feature-x"

    def run_git_failing_after_worktree_add(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = cgwt.git.run_git(args, cwd, check)
        if args[:2] == ["worktree", "add"]:
            raise CgwtError("git worktree add failed. boom")
        return result

    monkeypatch.setattr(cgwt.create, "run_git", run_git_failing_after_worktree_add)

    assert main(["create", "feature-x", "--repo", str(repository)]) == 1

    captured = capsys.readouterr()
    assert captured.err == "cgwt: error: git worktree add failed. boom\n"
    assert captured.out == ""
    assert not path.exists()
    assert str(path) not in git(repository, "worktree", "list", "--porcelain")
    assert bool(git(repository, "branch", "--list", "feature-x")) == branch_exists_before
