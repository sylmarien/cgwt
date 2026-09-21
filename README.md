# cgwt

CLI tool to manage git worktrees, with a behavior that is modifiable with a configuration file.

## Install

```sh
uv tool install cgwt
```

`pipx install cgwt` works too. cgwt requires Python 3.12 or later.

## Development

[uv](https://docs.astral.sh/uv/) manages the environment.

```sh
uv sync
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
```

pytest fails when line or branch coverage is below 100%.

## Release

The version lives in `pyproject.toml`. To release, run the Release workflow from the Actions tab and choose the version part to bump. The workflow bumps the version, tags the commit, publishes to PyPI, and creates a GitHub release.
