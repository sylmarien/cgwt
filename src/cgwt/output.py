"""The result of a command handler."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandOutput:
    """The stdout of the text mode and the object of the `--json` mode."""

    text: str
    value: object
