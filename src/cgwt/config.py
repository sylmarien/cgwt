"""Locate, load, and validate the configuration file."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cgwt.errors import CgwtError

SETTING_DEFAULTS: dict[str, object] = {
    "workforest": "~/worktrees",
    "path": "{project}/{branch}",
    "fetch": True,
    "base": "origin/HEAD",
}


@dataclass
class Config:
    """The top-level settings, the values tables, and the project overrides of the file."""

    settings: dict[str, object] = field(default_factory=dict)
    values: dict[str, dict[str, object]] = field(default_factory=dict)
    projects: dict[str, dict[str, object]] = field(default_factory=dict)

    def list_workforests(self) -> list[Path]:
        """Return the top-level or default workforest, then each override workforest, once."""
        workforest_names = [self.settings.get("workforest", SETTING_DEFAULTS["workforest"])]
        workforest_names += [
            override["workforest"]
            for override in self.projects.values()
            if "workforest" in override
        ]
        return list(dict.fromkeys(Path(str(name)).expanduser() for name in workforest_names))


def locate_config_path(environ: Mapping[str, str]) -> Path:
    """Return the configuration file path under an absolute XDG_CONFIG_HOME or ~/.config."""
    xdg_config_home = environ.get("XDG_CONFIG_HOME", "")
    if xdg_config_home and Path(xdg_config_home).is_absolute():
        return Path(xdg_config_home) / "cgwt" / "config.toml"
    return Path.home() / ".config" / "cgwt" / "config.toml"


def load_config(path: Path) -> Config:
    """Read and validate the configuration file at path; a missing file is an empty Config."""
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except FileNotFoundError:
        return Config()
    except OSError as error:
        raise CgwtError(
            f"Cannot read {path}: {error.strerror}. Fix the file or remove it."
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise CgwtError(f"Cannot parse {path}: {error}. Fix the TOML syntax.") from error
    check_top_level(data, path)
    check_project_overrides(data.get("projects", {}), path)
    check_value_tables(data.get("values", {}), path)
    return Config(
        settings={key: data[key] for key in SETTING_DEFAULTS if key in data},
        values=data.get("values", {}),
        projects=data.get("projects", {}),
    )


def check_settings(table: dict[str, Any], prefix: str, path: Path) -> None:
    """Check the types of workforest, path, fetch, and base in table."""
    for key in ("workforest", "path", "base"):
        if key in table and not isinstance(table[key], str):
            raise CgwtError(f"{prefix}{key} in {path} is not a string. Set it to a string.")
    if "fetch" in table and not isinstance(table["fetch"], bool):
        raise CgwtError(f"{prefix}fetch in {path} is not a boolean. Set it to true or false.")


def check_top_level(data: dict[str, Any], path: Path) -> None:
    """Check the top-level keys of the file and their types."""
    for key in data:
        if key not in (*SETTING_DEFAULTS, "values", "projects"):
            raise CgwtError(f"Unknown key {key} in {path}. Remove it.")
    check_settings(data, "", path)
    for key in ("values", "projects"):
        if key in data and not isinstance(data[key], dict):
            raise CgwtError(f"{key} in {path} is not a table. Write it as [{key}.<name>] tables.")


def check_project_overrides(projects: dict[str, Any], path: Path) -> None:
    """Check that each project override is a table of settings."""
    for glob, override in projects.items():
        if not isinstance(override, dict):
            raise CgwtError(
                f'projects.{glob} in {path} is not a table. Write it as [projects."{glob}"].'
            )
        for key in override:
            if key not in SETTING_DEFAULTS:
                raise CgwtError(f"Unknown key projects.{glob}.{key} in {path}. Remove it.")
        check_settings(override, f"projects.{glob}.", path)


def check_value_tables(values: dict[str, Any], path: Path) -> None:
    """Check the keys and types of each values table."""
    for name, value_table in values.items():
        if not isinstance(value_table, dict):
            raise CgwtError(f"values.{name} in {path} is not a table. Write it as [values.{name}].")
        for key in value_table:
            if key not in ("input", "split", "slash", "at"):
                raise CgwtError(f"Unknown key values.{name}.{key} in {path}. Remove it.")
        if "input" not in value_table:
            raise CgwtError(
                f"values.{name}.input in {path} is missing. "
                'Add input = "<name of the value it reads>".'
            )
        for key in ("input", "split", "slash"):
            if key in value_table and not isinstance(value_table[key], str):
                raise CgwtError(
                    f"values.{name}.{key} in {path} is not a string. Set it to a string."
                )
        at_index = value_table.get("at", 0)
        if not isinstance(at_index, int) or isinstance(at_index, bool):
            raise CgwtError(f"values.{name}.at in {path} is not an integer. Set it to an integer.")
