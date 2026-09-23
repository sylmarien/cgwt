import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

import cgwt.git
from cgwt.errors import CgwtError
from cgwt.git import find_repository, list_worktrees, run_git


def test_repository_fixture_has_origin_head_on_main(
    git: Callable[..., str], repository: Path
) -> None:
    assert git(repository, "rev-parse", "--abbrev-ref", "origin/HEAD") == "origin/main\n"


def test_run_git_returns_the_completed_process(repository: Path) -> None:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repository)

    assert result.returncode == 0
    assert result.stdout.strip() == "main"


def test_run_git_raises_with_the_command_and_stderr_on_failure(
    git: Callable[..., str], repository: Path
) -> None:
    with pytest.raises(subprocess.CalledProcessError) as git_failure:
        git(repository, "rev-parse", "--verify", "nope")

    with pytest.raises(CgwtError) as error_info:
        run_git(["rev-parse", "--verify", "nope"], repository)

    assert error_info.value.exit_code == 1
    assert "rev-parse" in error_info.value.message
    assert git_failure.value.stderr.strip() in error_info.value.message


def test_run_git_without_check_returns_the_failed_process(repository: Path) -> None:
    result = run_git(["rev-parse", "--verify", "nope"], repository, check=False)

    assert result.returncode != 0


def test_run_git_asks_to_install_git_when_git_is_missing(
    monkeypatch: pytest.MonkeyPatch, repository: Path, tmp_path: Path
) -> None:
    empty_directory = tmp_path / "empty"
    empty_directory.mkdir()
    monkeypatch.setenv("PATH", str(empty_directory))

    with pytest.raises(CgwtError) as error_info:
        run_git(["status"], repository)

    assert error_info.value.exit_code == 1
    assert "install git" in error_info.value.message


def test_run_git_lets_a_missing_directory_propagate(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        run_git(["status"], tmp_path / "missing")


def test_find_repository_returns_the_repository_from_its_root(repository: Path) -> None:
    assert find_repository(repository) == repository.resolve()


def test_find_repository_returns_the_repository_from_a_subdirectory(repository: Path) -> None:
    (repository / "sub").mkdir()

    assert find_repository(repository / "sub") == repository.resolve()


def test_find_repository_returns_the_repository_from_a_linked_worktree(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    git(repository, "worktree", "add", str(tmp_path / "linked"), "-b", "feature")

    assert find_repository(tmp_path / "linked") == repository.resolve()


def test_find_repository_raises_outside_a_repository(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error_info:
        find_repository(tmp_path)

    assert error_info.value.exit_code == 1
    assert str(tmp_path) in error_info.value.message


def test_list_worktrees_returns_the_main_and_linked_worktrees(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    git(repository, "worktree", "add", str(tmp_path / "linked"), "-b", "feature")

    main_entry, linked_entry = list_worktrees(repository)

    assert main_entry.path == repository.resolve()
    assert main_entry.branch == "main"
    assert not main_entry.locked
    assert main_entry.lock_reason == ""
    assert linked_entry.path == (tmp_path / "linked").resolve()
    assert linked_entry.branch == "feature"
    assert not linked_entry.locked


def test_list_worktrees_reads_the_lock_reason(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    git(repository, "worktree", "add", str(tmp_path / "linked"), "-b", "feature")
    git(repository, "worktree", "lock", "--reason", "busy now", str(tmp_path / "linked"))

    linked_entry = list_worktrees(repository)[1]

    assert linked_entry.locked
    assert linked_entry.lock_reason == "busy now"


def test_list_worktrees_reads_a_lock_without_reason(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    git(repository, "worktree", "add", str(tmp_path / "linked"), "-b", "feature")
    git(repository, "worktree", "lock", str(tmp_path / "linked"))

    linked_entry = list_worktrees(repository)[1]

    assert linked_entry.locked
    assert linked_entry.lock_reason == ""


def test_list_worktrees_leaves_the_branch_of_a_detached_worktree_empty(
    git: Callable[..., str], repository: Path, tmp_path: Path
) -> None:
    git(repository, "worktree", "add", "--detach", str(tmp_path / "linked"))

    assert list_worktrees(repository)[1].branch == ""


def test_list_worktrees_raises_on_an_unknown_label(
    monkeypatch: pytest.MonkeyPatch, repository: Path
) -> None:
    def run_git_printing_an_unknown_label(
        args: list[str], cwd: Path, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["git"], 0, "worktree /x\nmystery 1\n\n", "")

    monkeypatch.setattr(cgwt.git, "run_git", run_git_printing_an_unknown_label)

    with pytest.raises(CgwtError) as error_info:
        list_worktrees(repository)

    assert error_info.value.exit_code == 1
    assert "mystery" in error_info.value.message
