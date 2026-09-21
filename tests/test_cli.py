from importlib.metadata import version

import pytest

from cgwt.cli import main


def test_version_flag_prints_the_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"cgwt {version('cgwt')}\n"


def test_unknown_argument_prints_usage_and_exits_with_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--unknown"])

    assert exit_info.value.code == 2
    assert "usage: cgwt" in capsys.readouterr().err


def test_no_argument_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: cgwt" in capsys.readouterr().out
