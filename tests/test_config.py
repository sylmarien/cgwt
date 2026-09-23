import tomllib
from pathlib import Path

import pytest

from cgwt.config import SETTING_DEFAULTS, Config, load_config, locate_config_path
from cgwt.errors import CgwtError


def test_locate_config_path_uses_an_absolute_xdg_config_home() -> None:
    assert locate_config_path({"XDG_CONFIG_HOME": "/abs"}) == Path("/abs/cgwt/config.toml")


@pytest.mark.parametrize("environ", [{}, {"XDG_CONFIG_HOME": ""}, {"XDG_CONFIG_HOME": "relative"}])
def test_locate_config_path_falls_back_to_the_home_config(environ: dict[str, str]) -> None:
    assert locate_config_path(environ) == Path.home() / ".config" / "cgwt" / "config.toml"


def test_setting_defaults_hold_the_four_setting_defaults() -> None:
    assert SETTING_DEFAULTS == {
        "workforest": "~/worktrees",
        "path": "{project}/{branch}",
        "fetch": True,
        "base": "origin/HEAD",
    }


def test_config_defaults_to_empty_tables() -> None:
    config = Config()

    assert (config.settings, config.values, config.projects) == ({}, {}, {})


def test_list_workforests_defaults_to_the_expanded_default_workforest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert Config().list_workforests() == [tmp_path / "worktrees"]


def test_list_workforests_lists_the_top_level_then_the_override_workforests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config = Config(
        settings={"workforest": "~/top"},
        projects={"a/*": {"workforest": "~/first"}, "b/*": {"workforest": "/second"}},
    )

    assert config.list_workforests() == [tmp_path / "top", tmp_path / "first", Path("/second")]


def test_list_workforests_drops_duplicates() -> None:
    config = Config(settings={"workforest": "/top"}, projects={"a/*": {"workforest": "/top"}})

    assert config.list_workforests() == [Path("/top")]


def test_list_workforests_skips_overrides_without_a_workforest() -> None:
    config = Config(settings={"workforest": "/top"}, projects={"a/*": {"base": "main"}})

    assert config.list_workforests() == [Path("/top")]


def load_toml(tmp_path: Path, text: str) -> Config:
    config_file = tmp_path / "config.toml"
    config_file.write_text(text)
    return load_config(config_file)


def test_load_config_returns_an_empty_config_for_a_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = load_config(tmp_path / "missing.toml")

    assert config == Config()
    assert capsys.readouterr() == ("", "")


def test_load_config_reports_a_file_that_cannot_be_read(tmp_path: Path) -> None:
    with pytest.raises(IsADirectoryError) as os_error:
        tmp_path.open("rb")

    with pytest.raises(CgwtError) as error:
        load_config(tmp_path)

    assert error.value.exit_code == 1
    assert str(tmp_path) in error.value.message
    assert str(os_error.value.strerror) in error.value.message


def test_load_config_reports_invalid_toml(tmp_path: Path) -> None:
    with pytest.raises(tomllib.TOMLDecodeError) as decode_error:
        tomllib.loads("a =")

    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, "a =")

    assert error.value.exit_code == 1
    assert str(tmp_path / "config.toml") in error.value.message
    assert str(decode_error.value) in error.value.message


def test_load_config_rejects_an_unknown_top_level_key(tmp_path: Path) -> None:
    with pytest.raises(CgwtError, match="color"):
        load_toml(tmp_path, 'color = "red"')


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("workforest = 1", "workforest"),
        ("path = 1", "path"),
        ("base = 1", "base"),
        ("fetch = 1", "fetch"),
        ('fetch = "yes"', "fetch"),
        ("values = 1", "values"),
        ("projects = 1", "projects"),
    ],
)
def test_load_config_rejects_a_top_level_key_of_the_wrong_type(
    tmp_path: Path, text: str, key: str
) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, text)

    assert error.value.exit_code == 1
    assert error.value.message.startswith(f"{key} in ")


def test_load_config_returns_the_tables_of_a_valid_file(tmp_path: Path) -> None:
    config = load_toml(
        tmp_path,
        'workforest = "~/w"\n'
        "fetch = false\n"
        "[values.name]\n"
        'input = "project"\n'
        '[projects."github.com/*"]\n'
        'base = "main"\n',
    )

    assert config.settings == {"workforest": "~/w", "fetch": False}
    assert config.values == {"name": {"input": "project"}}
    assert config.projects == {"github.com/*": {"base": "main"}}


def test_load_config_returns_an_empty_config_for_an_empty_file(tmp_path: Path) -> None:
    assert load_toml(tmp_path, "") == Config()


def test_load_config_rejects_a_project_override_that_is_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, '[projects]\n"github.com/x" = 1\n')

    assert error.value.message.startswith("projects.github.com/x in ")


def test_load_config_rejects_an_unknown_project_override_key(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, '[projects."github.com/x"]\ncolor = "red"\n')

    assert error.value.message.startswith("Unknown key projects.github.com/x.color in ")


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("workforest = 1", "workforest"),
        ("path = 1", "path"),
        ("base = 1", "base"),
        ("fetch = 1", "fetch"),
        ('fetch = "yes"', "fetch"),
    ],
)
def test_load_config_rejects_a_project_override_key_of_the_wrong_type(
    tmp_path: Path, text: str, key: str
) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, f'[projects."github.com/x"]\n{text}\n')

    assert error.value.message.startswith(f"projects.github.com/x.{key} in ")


def test_load_config_returns_a_valid_project_override(tmp_path: Path) -> None:
    config = load_toml(
        tmp_path,
        '[projects."github.com/x"]\n'
        'workforest = "~/w"\n'
        'path = "{branch}"\n'
        "fetch = false\n"
        'base = "main"\n',
    )

    assert config.projects["github.com/x"] == {
        "workforest": "~/w",
        "path": "{branch}",
        "fetch": False,
        "base": "main",
    }


def test_load_config_rejects_a_value_that_is_not_a_table(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, "[values]\nfirst = 1\n")

    assert error.value.message.startswith("values.first in ")


def test_load_config_rejects_a_value_without_input(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, '[values.first]\nsplit = "/"\n')

    assert error.value.message.startswith("values.first.input in ")


def test_load_config_rejects_an_unknown_value_key(tmp_path: Path) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, '[values.first]\ninput = "project"\ncolor = "red"\n')

    assert error.value.message.startswith("Unknown key values.first.color in ")


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("input = 1", "input"),
        ('input = "project"\nsplit = 1', "split"),
        ('input = "project"\nslash = 1', "slash"),
        ('input = "project"\nat = true', "at"),
        ('input = "project"\nat = "1"', "at"),
    ],
)
def test_load_config_rejects_a_value_key_of_the_wrong_type(
    tmp_path: Path, text: str, key: str
) -> None:
    with pytest.raises(CgwtError) as error:
        load_toml(tmp_path, f"[values.first]\n{text}\n")

    assert error.value.message.startswith(f"values.first.{key} in ")


def test_load_config_returns_a_valid_value_table(tmp_path: Path) -> None:
    config = load_toml(
        tmp_path,
        '[values.first]\ninput = "project"\nsplit = "/"\nat = -1\nslash = "-"\n',
    )

    assert config.values["first"] == {"input": "project", "split": "/", "at": -1, "slash": "-"}
