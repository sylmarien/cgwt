"""Command-line entry point."""

import argparse
import json
import sys
from importlib.metadata import version

from cgwt.errors import CgwtError


def build_parser() -> argparse.ArgumentParser:
    """Build the parser; each command binds its handler with `set_defaults(command=...)`."""
    parser = argparse.ArgumentParser(prog="cgwt", description="Manage git worktrees.")
    parser.add_argument("--version", action="version", version=f"cgwt {version('cgwt')}")
    parser.add_subparsers(required=True, metavar="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the cgwt command line."""
    args = build_parser().parse_args(argv)
    try:
        output = args.command(args)
    except CgwtError as error:
        print(f"cgwt: error: {error.message}", file=sys.stderr)
        return error.exit_code
    if args.json:
        print(json.dumps(output.value, indent=2 if sys.stdout.isatty() else None))
    elif output.text:
        print(output.text)
    return 0
