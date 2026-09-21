"""Command-line entry point."""

import argparse
from importlib.metadata import version


def main(argv: list[str] | None = None) -> int:
    """Run the cgwt command line."""
    parser = argparse.ArgumentParser(prog="cgwt", description="Manage git worktrees.")
    parser.add_argument("--version", action="version", version=f"cgwt {version('cgwt')}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
