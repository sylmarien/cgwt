"""The create command."""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Literal

from cgwt.config import load_config, locate_config_path, resolve_settings
from cgwt.errors import CgwtError
from cgwt.git import find_repository, list_worktrees, run_git
from cgwt.output import CommandOutput
from cgwt.path_pattern import render_path
from cgwt.project import read_project
from cgwt.worktrees import read_worktree


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


def create_command(args: argparse.Namespace) -> CommandOutput:
    """Claim the path the configuration computes for `args.branch` and add a worktree there."""
    repository = find_repository(Path(args.repo) if args.repo else Path.cwd())
    project = read_project(repository)
    config = load_config(locate_config_path(os.environ))
    flags: dict[str, object] = {}
    if args.base is not None:
        flags["base"] = args.base
    if args.no_fetch:
        flags["fetch"] = False
    settings = resolve_settings(config, project.identifier, flags)
    run_git(["worktree", "prune"], repository)
    if settings.fetch:
        result = run_git(["fetch", "origin"], repository, check=False)
        if result.returncode != 0:
            raise CgwtError(
                f"git fetch origin failed. {result.stderr.strip()} "
                "Pass --no-fetch to skip the fetch."
            )
    outcome = resolve_branch(repository, args.branch, settings.base)
    if args.base is not None and outcome != "created":
        raise CgwtError(
            f"{args.branch} already exists, so --base does not apply. "
            "Drop --base to use the branch as it is."
        )
    inputs = {
        "host": project.host,
        "remote_path": project.remote_path,
        "project": project.name,
        "main_worktree": repository.name,
        "branch": args.branch,
    }
    path = settings.workforest / render_path(settings.path, config.values, inputs)
    _claim_path(path)
    _add_worktree(repository, path, args.branch, outcome, settings.base)
    if outcome == "created":
        print(f"cgwt: created {args.branch} from {settings.base} at {path}", file=sys.stderr)
    elif outcome == "tracked":
        print(f"cgwt: tracked origin/{args.branch} at {path}", file=sys.stderr)
    else:
        print(f"cgwt: existing {args.branch} at {path}", file=sys.stderr)
    return CommandOutput(
        text=str(path), value={**read_worktree(path).to_dict(), "outcome": outcome}
    )


def _claim_path(path: Path) -> None:
    """Create the directory at `path`, which must not exist yet."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()
    except FileExistsError as error:
        if (path / ".git").is_file():
            worktree = read_worktree(path)
            raise CgwtError(
                f"{path}: already used by worktree of {worktree.branch} from {worktree.repository}",
                exit_code=6,
            ) from error
        raise CgwtError(f"{path}: already exists and is not a worktree", exit_code=6) from error
    except OSError as error:
        raise CgwtError(
            f"Cannot create {path}: {error.strerror}. "
            "Fix the workforest directory or set workforest in the configuration."
        ) from error


def _add_worktree(
    repository: Path,
    path: Path,
    branch: str,
    outcome: Literal["existing", "tracked", "created"],
    base: str,
) -> None:
    """Add the worktree of `branch` at `path` in the way `outcome` requires."""
    if outcome == "existing":
        git_args = ["worktree", "add", str(path), branch]
    elif outcome == "tracked":
        git_args = ["worktree", "add", "--track", "-b", branch, str(path), f"origin/{branch}"]
    else:
        git_args = ["worktree", "add", "--no-track", "-b", branch, str(path), base]
    try:
        run_git(git_args, repository)
    except CgwtError:
        shutil.rmtree(path)
        run_git(["worktree", "prune"], repository)
        if outcome == "created":
            run_git(["branch", "-D", branch], repository, check=False)
        raise
