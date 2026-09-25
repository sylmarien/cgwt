"""The project that the URL of `origin` identifies."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from cgwt.errors import CgwtError
from cgwt.git import run_git


@dataclass(frozen=True)
class Project:
    """The identifier and the name of a project, and the parts of its remote URL."""

    identifier: str
    name: str
    host: str
    remote_path: tuple[str, ...]


def parse_remote_url(url: str) -> Project:
    """Return the project of a scheme URL, an scp-like URL, or a local path."""
    if "://" in url:
        split_url = urlsplit(url)
        host = split_url.netloc.rpartition("@")[2].partition(":")[0]
        path = split_url.path
    elif ":" in url.partition("/")[0]:
        user_and_host, _, path = url.partition(":")
        host = user_and_host.rpartition("@")[2]
    else:
        host, path = "", url
    remote_path = tuple(segment for segment in path.removesuffix(".git").split("/") if segment)
    return Project(
        identifier=f"{host}/{'/'.join(remote_path)}",
        name=remote_path[-1],
        host=host,
        remote_path=remote_path,
    )


def read_project(repository: Path) -> Project:
    """Return the project of the current URL of `origin` in `repository`."""
    result = run_git(["remote", "get-url", "origin"], repository, check=False)
    if result.returncode != 0:
        raise CgwtError(f"{repository} has no origin remote. Run git remote add origin <url>.")
    return parse_remote_url(result.stdout.strip())
