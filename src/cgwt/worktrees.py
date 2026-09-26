"""The worktrees found in the workforests."""

import os
from dataclasses import dataclass
from pathlib import Path

from cgwt.git import find_repository, list_worktrees
from cgwt.project import read_project


@dataclass(frozen=True)
class Worktree:
    """A worktree found in a workforest and the repository it belongs to."""

    path: Path
    branch: str
    project: str
    repository: Path
    locked: bool
    broken: bool
    lock_reason: str

    def to_dict(self) -> dict[str, str | bool]:
        """Return the six keys of the worktree object."""
        return {
            "path": str(self.path),
            "branch": self.branch,
            "project": self.project,
            "repository": str(self.repository),
            "locked": self.locked,
            "broken": self.broken,
        }


def read_worktree(path: Path) -> Worktree:
    """Describe the worktree at `path`, a directory that holds a `.git` file."""
    gitdir = Path((path / ".git").read_text().removeprefix("gitdir: ").strip())
    if not gitdir.is_dir():
        # The gitdir is `<repository>/.git/worktrees/<name>`.
        return Worktree(
            path=path,
            branch="",
            project="",
            repository=gitdir.parents[2],
            locked=False,
            broken=True,
            lock_reason="",
        )
    repository = find_repository(path)
    resolved_path = path.resolve()
    entry = next(entry for entry in list_worktrees(repository) if entry.path == resolved_path)
    return Worktree(
        path=path,
        branch=entry.branch,
        project=read_project(repository).identifier,
        repository=repository,
        locked=entry.locked,
        broken=False,
        lock_reason=entry.lock_reason,
    )


def find_worktrees(workforests: list[Path]) -> list[Worktree]:
    """Return the worktrees below `workforests`, sorted by path, without following symlinks."""
    worktrees = []
    for workforest in workforests:
        for dirpath, dirnames, filenames in os.walk(workforest):
            if ".git" in filenames:
                worktrees.append(read_worktree(Path(dirpath)))
                dirnames.clear()
            elif ".git" in dirnames:
                dirnames.clear()
    return sorted(worktrees, key=lambda worktree: str(worktree.path))
