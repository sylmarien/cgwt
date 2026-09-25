import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import cgwt.create
import cgwt.git
from cgwt.create import resolve_branch
from cgwt.errors import CgwtError
from cgwt.git import list_worktrees


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
