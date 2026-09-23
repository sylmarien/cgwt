"""The calls cgwt makes to git."""

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cgwt.errors import CgwtError

SKIPPED_WORKTREE_LABELS = {"HEAD", "bare", "detached", "prunable"}


@dataclass(frozen=True)
class WorktreeEntry:
    """One record of `git worktree list --porcelain`."""

    path: Path
    branch: str = ""
    locked: bool = False
    lock_reason: str = ""


def run_git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run git with `args` in `cwd`. `args` does not include `git`."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as error:
        if error.filename != "git":
            raise
        raise CgwtError(
            "git is not on PATH. cgwt needs git 2.38 or later: install git and retry."
        ) from error
    if check and result.returncode != 0:
        raise CgwtError(f"{shlex.join(['git', *args])} failed. {result.stderr.strip()}")
    return result


def find_repository(cwd: Path) -> Path:
    """Return the main worktree of the repository that contains `cwd`."""
    result = run_git(["rev-parse", "--git-common-dir"], cwd, check=False)
    if result.returncode != 0:
        raise CgwtError(f"{cwd} is not inside a git repository. Run cgwt from inside a repository.")
    return (cwd / result.stdout.strip()).resolve().parent


def list_worktrees(repository: Path) -> list[WorktreeEntry]:
    """Return the worktrees of `repository` in the order git lists them."""
    result = run_git(["worktree", "list", "--porcelain"], repository)
    entries = []
    fields: dict[str, Any] = {}
    for line in result.stdout.splitlines():
        label, _, value = line.partition(" ")
        if label == "":
            entries.append(WorktreeEntry(**fields))
            fields = {}
        elif label == "worktree":
            fields["path"] = Path(value)
        elif label == "branch":
            fields["branch"] = value.removeprefix("refs/heads/")
        elif label == "locked":
            fields["locked"] = True
            fields["lock_reason"] = value
        elif label not in SKIPPED_WORKTREE_LABELS:
            raise CgwtError(f"git worktree list printed an unknown label: {label}. Upgrade cgwt.")
    return entries
