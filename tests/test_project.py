import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest

from cgwt.errors import CgwtError
from cgwt.project import Project, parse_remote_url, read_project


def test_project_is_a_frozen_dataclass_with_its_fields_in_order() -> None:
    project = Project(
        identifier="github.com/acme/widget",
        name="widget",
        host="github.com",
        remote_path=("acme", "widget"),
    )

    assert [field.name for field in dataclasses.fields(Project)] == [
        "identifier",
        "name",
        "host",
        "remote_path",
    ]
    with pytest.raises(dataclasses.FrozenInstanceError):
        project.name = "gadget"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("url", "host", "remote_path", "identifier", "name"),
    [
        (
            "https://github.com/acme/widget.git",
            "github.com",
            ("acme", "widget"),
            "github.com/acme/widget",
            "widget",
        ),
        (
            "ssh://git@gitlab.example.com:2222/platform/tools/meta.project.git",
            "gitlab.example.com",
            ("platform", "tools", "meta.project"),
            "gitlab.example.com/platform/tools/meta.project",
            "meta.project",
        ),
        (
            "git@github.com:acme/widget.git",
            "github.com",
            ("acme", "widget"),
            "github.com/acme/widget",
            "widget",
        ),
        ("/srv/git/widget.git", "", ("srv", "git", "widget"), "/srv/git/widget", "widget"),
        ("file:///srv/git/widget", "", ("srv", "git", "widget"), "/srv/git/widget", "widget"),
    ],
)
def test_parse_remote_url_derives_the_project(
    url: str, host: str, remote_path: tuple[str, ...], identifier: str, name: str
) -> None:
    assert parse_remote_url(url) == Project(
        identifier=identifier, name=name, host=host, remote_path=remote_path
    )


def test_parse_remote_url_keeps_the_case_of_the_url() -> None:
    project = parse_remote_url("https://GitHub.com/Acme/Widget.git")

    assert project.host == "GitHub.com"
    assert project.identifier == "GitHub.com/Acme/Widget"


def test_read_project_derives_the_project_from_the_origin_url(
    tmp_path: Path, repository: Path
) -> None:
    project = read_project(repository)

    assert project.host == ""
    assert project.name == "widget"
    assert project.identifier == str(tmp_path / "widget")
    assert project.remote_path == (tmp_path / "widget").parts[1:]


def test_read_project_without_origin_tells_the_user_to_add_it(
    git: Callable[..., str], repository: Path
) -> None:
    git(repository, "remote", "rename", "origin", "upstream")

    with pytest.raises(CgwtError) as error_info:
        read_project(repository)

    assert error_info.value.exit_code == 1
    assert str(repository) in error_info.value.message
    assert "git remote add origin" in error_info.value.message
