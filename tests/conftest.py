import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "cgwt tests")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "cgwt tests")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "tests@cgwt.invalid")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "tests@cgwt.invalid")


def run_test_git(cwd: Path, *args: str) -> str:
    """Run git without cgwt, so the tests of `run_git` do not depend on it."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def git() -> Callable[..., str]:
    return run_test_git


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    bare = tmp_path / "widget.git"
    seed = tmp_path / "seed"
    run_test_git(tmp_path, "init", "--bare", "-b", "main", str(bare))
    run_test_git(tmp_path, "clone", str(bare), str(seed))
    (seed / "README.md").write_text("widget\n")
    run_test_git(seed, "add", "README.md")
    run_test_git(seed, "commit", "-m", "Initial commit")
    run_test_git(seed, "push", "origin", "main")
    return bare


@pytest.fixture
def repository(tmp_path: Path, origin: Path) -> Path:
    clone = tmp_path / "widget"
    run_test_git(tmp_path, "clone", str(origin), str(clone))
    return clone


@pytest.fixture
def config() -> Callable[[str], None]:
    def install_config(name: str) -> None:
        target = Path(os.environ["XDG_CONFIG_HOME"]) / "cgwt" / "config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(__file__).parent / "config" / name, target)

    return install_config
