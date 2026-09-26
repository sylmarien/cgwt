import dataclasses
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from cgwt.errors import CgwtError
from cgwt.project import read_project
from cgwt.worktrees import Worktree, find_worktrees, read_worktree


@pytest.fixture
def workforest(tmp_path: Path) -> Path:
    workforest = tmp_path / "workforest"
    workforest.mkdir()
    return workforest


def test_worktree_is_a_frozen_dataclass_with_its_fields_in_order() -> None:
    worktree = Worktree(
        path=Path("/forest/feature"),
        branch="feature",
        project="github.com/acme/widget",
        repository=Path("/code/widget"),
        locked=False,
        broken=False,
        lock_reason="",
    )

    assert [field.name for field in dataclasses.fields(Worktree)] == [
        "path",
        "branch",
        "project",
        "repository",
        "locked",
        "broken",
        "lock_reason",
    ]
    with pytest.raises(dataclasses.FrozenInstanceError):
        worktree.branch = "main"  # type: ignore[misc]


def test_to_dict_holds_the_six_keys_of_the_worktree_object() -> None:
    worktree = Worktree(
        path=Path("/forest/feature"),
        branch="feature",
        project="github.com/acme/widget",
        repository=Path("/code/widget"),
        locked=True,
        broken=False,
        lock_reason="busy now",
    )

    assert list(worktree.to_dict().items()) == [
        ("path", "/forest/feature"),
        ("branch", "feature"),
        ("project", "github.com/acme/widget"),
        ("repository", "/code/widget"),
        ("locked", True),
        ("broken", False),
    ]


def test_read_worktree_describes_a_worktree(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "feature"), "-b", "feature")

    assert read_worktree(workforest / "feature") == Worktree(
        path=workforest / "feature",
        branch="feature",
        project=read_project(repository).identifier,
        repository=repository.resolve(),
        locked=False,
        broken=False,
        lock_reason="",
    )


def test_read_worktree_reports_the_lock_and_its_reason(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "feature"), "-b", "feature")
    git(repository, "worktree", "lock", "--reason", "busy now", str(workforest / "feature"))

    worktree = read_worktree(workforest / "feature")

    assert worktree.locked
    assert worktree.lock_reason == "busy now"


def test_read_worktree_marks_a_worktree_whose_repository_is_gone_as_broken(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "feature"), "-b", "feature")
    shutil.rmtree(repository)

    assert read_worktree(workforest / "feature") == Worktree(
        path=workforest / "feature",
        branch="",
        project="",
        repository=repository.resolve(),
        locked=False,
        broken=True,
        lock_reason="",
    )


def test_read_worktree_without_origin_tells_the_user_to_add_it(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "feature"), "-b", "feature")
    git(repository, "remote", "rename", "origin", "upstream")

    with pytest.raises(CgwtError) as error_info:
        read_worktree(workforest / "feature")

    assert "git remote add origin" in error_info.value.message


def test_find_worktrees_lists_every_worktree_sorted_by_path(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "zeta"), "-b", "zeta")
    git(repository, "worktree", "lock", "--reason", "busy now", str(workforest / "zeta"))
    git(repository, "worktree", "add", str(workforest / "nested" / "deep"), "-b", "deep")
    git(repository, "worktree", "add", str(workforest / "alpha"), "-b", "alpha")
    project = read_project(repository).identifier

    assert find_worktrees([workforest]) == [
        Worktree(
            path=workforest / "alpha",
            branch="alpha",
            project=project,
            repository=repository.resolve(),
            locked=False,
            broken=False,
            lock_reason="",
        ),
        Worktree(
            path=workforest / "nested" / "deep",
            branch="deep",
            project=project,
            repository=repository.resolve(),
            locked=False,
            broken=False,
            lock_reason="",
        ),
        Worktree(
            path=workforest / "zeta",
            branch="zeta",
            project=project,
            repository=repository.resolve(),
            locked=True,
            broken=False,
            lock_reason="busy now",
        ),
    ]


def test_find_worktrees_skips_a_repository_in_the_workforest(
    git: Callable[..., str], tmp_path: Path, origin: Path, workforest: Path
) -> None:
    git(tmp_path, "clone", str(origin), str(workforest / "clone"))

    assert find_worktrees([workforest]) == []


def test_find_worktrees_does_not_follow_a_symlink_to_a_worktree(
    git: Callable[..., str], tmp_path: Path, repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(tmp_path / "outside"), "-b", "outside")
    (workforest / "link").symlink_to(tmp_path / "outside")

    assert find_worktrees([workforest]) == []


def test_find_worktrees_of_a_missing_workforest_is_empty(tmp_path: Path) -> None:
    assert find_worktrees([tmp_path / "missing"]) == []


def test_find_worktrees_lists_a_broken_worktree(
    git: Callable[..., str], repository: Path, workforest: Path
) -> None:
    git(repository, "worktree", "add", str(workforest / "feature"), "-b", "feature")
    shutil.rmtree(repository)

    worktrees = find_worktrees([workforest])

    assert [(worktree.path, worktree.broken) for worktree in worktrees] == [
        (workforest / "feature", True)
    ]
