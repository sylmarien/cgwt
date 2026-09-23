from collections.abc import Callable
from pathlib import Path


def test_git_is_2_38_or_later(git: Callable[..., str], tmp_path: Path) -> None:
    version_token = git(tmp_path, "--version").split()[2]
    major, minor = (int(part) for part in version_token.split(".")[:2])

    assert (major, minor) >= (2, 38)
