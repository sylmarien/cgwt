import argparse
import sys
from collections.abc import Callable
from importlib.metadata import version

import pytest

import cgwt.cli
from cgwt.cli import build_parser, main
from cgwt.errors import CgwtError
from cgwt.output import CommandOutput


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


def test_no_argument_prints_usage_and_exits_with_2(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])

    captured = capsys.readouterr()
    assert exit_info.value.code == 2
    assert "usage: cgwt" in captured.err
    assert captured.out == ""


def test_parser_has_no_global_flag_other_than_version_and_help() -> None:
    option_strings = {
        option for action in build_parser()._actions for option in action.option_strings
    }

    assert option_strings == {"-h", "--help", "--version"}


def bind_fake_command(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[argparse.Namespace], CommandOutput]
) -> None:
    """Make `main` parse with a parser that binds `handler` to the `fake` command."""
    parser = build_parser()
    subparsers = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    fake_parser = subparsers.add_parser("fake")
    fake_parser.add_argument("--json", action="store_true")
    fake_parser.set_defaults(command=handler)
    monkeypatch.setattr(cgwt.cli, "build_parser", lambda: parser)


def return_hi(args: argparse.Namespace) -> CommandOutput:
    return CommandOutput("hi", {"a": 1})


def test_cgwt_error_prints_one_stderr_line_and_returns_its_exit_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(args: argparse.Namespace) -> CommandOutput:
        raise CgwtError("boom. Run x.", 4)

    bind_fake_command(monkeypatch, fail)

    assert main(["fake"]) == 4
    captured = capsys.readouterr()
    assert captured.err == "cgwt: error: boom. Run x.\n"
    assert captured.out == ""


def test_other_exception_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def crash(args: argparse.Namespace) -> CommandOutput:
        raise RuntimeError

    bind_fake_command(monkeypatch, crash)

    with pytest.raises(RuntimeError):
        main(["fake"])


def test_text_output_prints_the_text(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bind_fake_command(monkeypatch, return_hi)

    assert main(["fake"]) == 0
    assert capsys.readouterr().out == "hi\n"


def test_json_output_prints_one_line_when_stdout_is_not_a_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bind_fake_command(monkeypatch, return_hi)

    assert main(["fake", "--json"]) == 0
    assert capsys.readouterr().out == '{"a": 1}\n'


def test_json_output_is_indented_when_stdout_is_a_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bind_fake_command(monkeypatch, return_hi)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    assert main(["fake", "--json"]) == 0
    assert capsys.readouterr().out == '{\n  "a": 1\n}\n'


def test_empty_text_output_prints_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    bind_fake_command(monkeypatch, lambda args: CommandOutput("", {}))

    assert main(["fake"]) == 0
    assert capsys.readouterr().out == ""


def test_cgwt_error_holds_its_message_and_exit_code() -> None:
    error = CgwtError("boom. Run x.", 4)

    assert error.message == "boom. Run x."
    assert error.exit_code == 4


def test_cgwt_error_exit_code_defaults_to_1() -> None:
    assert CgwtError("x").exit_code == 1


def test_command_output_holds_its_text_and_value() -> None:
    output = CommandOutput("hi", {"a": 1})

    assert output.text == "hi"
    assert output.value == {"a": 1}
