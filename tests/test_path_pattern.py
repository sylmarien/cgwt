from collections.abc import Mapping
from pathlib import Path

import pytest

from cgwt.errors import CgwtError
from cgwt.path_pattern import render_path

INPUTS: Mapping[str, str | tuple[str, ...]] = {
    "host": "gitlab.example.com",
    "remote_path": ("platform", "tools", "meta.project"),
    "project": "meta.project",
    "main_worktree": "src",
    "branch": "feature/x",
}


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("{project}/{branch}", "meta.project/feature-x"),
        (
            "{host}/{remote_path}/{branch}",
            "gitlab.example.com/platform/tools/meta.project/feature-x",
        ),
        ("{{{project}}}/{branch}", "{meta.project}/feature-x"),
    ],
)
def test_render_path_renders_inputs(pattern: str, expected: str) -> None:
    rendered = render_path(pattern, {}, INPUTS)

    assert rendered == Path(expected)
    assert not rendered.is_absolute()


@pytest.mark.parametrize(
    ("pattern", "expected_text"),
    [
        ("{project/{branch}", "{project/{branch}"),
        ("{}/{branch}", "{}"),
        ("{0}/{branch}", "{0}"),
        ("{remote_path[0]}/{branch}", "{remote_path[0]}"),
        ("{project.name}/{branch}", "{project.name}"),
        ("{project}/{branch:>8}", "{branch:>8}"),
        ("{project}/{branch!r}", "{branch!r}"),
        ("{owner}/{branch}", "{owner}"),
        ("{project}", "{project}"),
    ],
)
def test_render_path_rejects_invalid_pattern(pattern: str, expected_text: str) -> None:
    with pytest.raises(CgwtError) as error_info:
        render_path(pattern, {}, INPUTS)

    assert expected_text in error_info.value.message
    assert error_info.value.exit_code == 1


@pytest.mark.parametrize(
    ("pattern", "empty_input", "expected_text"),
    [
        ("{project}/{branch}", {"project": ""}, "{project}"),
        ("{remote_path}/{branch}", {"remote_path": ()}, "{remote_path}"),
    ],
)
def test_render_path_rejects_empty_placeholder(
    pattern: str, empty_input: Mapping[str, str | tuple[str, ...]], expected_text: str
) -> None:
    with pytest.raises(CgwtError) as error_info:
        render_path(pattern, {}, {**INPUTS, **empty_input})

    assert expected_text in error_info.value.message
    assert error_info.value.exit_code == 1


def test_render_path_ignores_unused_faulty_value() -> None:
    rendered = render_path("{project}/{branch}", {"owner": {"input": "nothing"}}, INPUTS)

    assert rendered == Path("meta.project/feature-x")
    assert not rendered.is_absolute()


def test_render_path_rejects_value_named_like_input() -> None:
    with pytest.raises(CgwtError) as error_info:
        render_path("{project}/{branch}", {"branch": {"input": "project"}}, INPUTS)

    assert "branch" in error_info.value.message
    assert error_info.value.exit_code == 1


@pytest.mark.parametrize(
    ("pattern", "values", "expected"),
    [
        (
            "{project}/{branch}/{project_parts}/{main_worktree}",
            {"project_parts": {"input": "project", "split": "."}},
            "meta.project/feature-x/meta/project/src",
        ),
        ("{owner}/{branch}", {"owner": {"input": "remote_path", "at": 0}}, "platform/feature-x"),
        (
            "{owner}/{branch}",
            {"owner": {"input": "remote_path", "at": -1}},
            "meta.project/feature-x",
        ),
        (
            "{owner}/{branch}",
            {"owner": {"input": "project", "split": ".", "at": 1}},
            "project/feature-x",
        ),
        (
            "{project}/{branch_dir}",
            {"branch_dir": {"input": "branch", "slash": "/"}},
            "meta.project/feature/x",
        ),
        (
            "{project}/{branch_dir}",
            {"branch_dir": {"input": "branch", "slash": "_"}},
            "meta.project/feature_x",
        ),
        ("{project}/{branch_dir}", {"branch_dir": {"input": "branch"}}, "meta.project/feature-x"),
        (
            "{project}/{b}",
            {"a": {"input": "branch", "slash": "_"}, "b": {"input": "a", "slash": "+"}},
            "meta.project/feature_x",
        ),
        (
            "{project}/{b}",
            {"a": {"input": "branch", "slash": "_"}, "b": {"input": "a"}},
            "meta.project/feature_x",
        ),
    ],
)
def test_render_path_resolves_values(
    pattern: str, values: Mapping[str, Mapping[str, object]], expected: str
) -> None:
    rendered = render_path(pattern, values, INPUTS)

    assert rendered == Path(expected)
    assert not rendered.is_absolute()


@pytest.mark.parametrize(
    "values",
    [
        {"owner": {"input": "nothing"}},
        {"owner": {"input": "owner"}},
        {"owner": {"input": "other"}, "other": {"input": "owner"}},
        {"owner": {"input": "project", "slash": "_"}},
        {"owner": {"input": "remote_path", "split": "."}},
        {"owner": {"input": "project", "split": ""}},
        {"owner": {"input": "project", "at": 0}},
        {"owner": {"input": "remote_path", "at": 3}},
    ],
)
def test_render_path_rejects_faulty_value(values: Mapping[str, Mapping[str, object]]) -> None:
    with pytest.raises(CgwtError) as error_info:
        render_path("{owner}/{branch}", values, INPUTS)

    assert "owner" in error_info.value.message
    assert error_info.value.exit_code == 1
