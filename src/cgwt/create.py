"""The decisions of the create command."""

from pathlib import Path
from typing import Literal

from cgwt.errors import CgwtError
from cgwt.git import list_worktrees, run_git


def _ref_resolves(repository: Path, ref: str) -> bool:
    """Return whether `ref` resolves in `repository`."""
    return (
        run_git(["rev-parse", "--verify", "--quiet", ref], repository, check=False).returncode == 0
    )


def resolve_branch(
    repository: Path, branch: str, base: str
) -> Literal["existing", "tracked", "created"]:
    """Classify `branch` from the local refs of `repository`."""
    if _ref_resolves(repository, f"refs/remotes/{branch}"):
        short_form = branch.partition("/")[2]
        raise CgwtError(f"{branch} is a remote-tracking branch. Pass {short_form} instead.")
    if _ref_resolves(repository, f"refs/heads/{branch}"):
        for entry in list_worktrees(repository):
            if entry.branch == branch:
                raise CgwtError(
                    f"{branch} is checked out at {entry.path}. "
                    "Use that worktree or pass another branch.",
                    exit_code=5,
                )
        return "existing"
    if _ref_resolves(repository, f"refs/remotes/origin/{branch}"):
        return "tracked"
    if _ref_resolves(repository, f"{base}^{{commit}}"):
        return "created"
    if base == "origin/HEAD":
        raise CgwtError(
            "origin/HEAD does not resolve to a commit. Run git remote set-head origin --auto."
        )
    raise CgwtError(
        f"{base} does not resolve to a commit. "
        "Pass a ref that exists with --base or set base in the configuration."
    )
