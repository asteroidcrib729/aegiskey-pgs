"""Module entry point allowing ``python -m password_generator`` and ``uv run`` execution."""

import argparse
import sys

from password_generator import __version__
from password_generator.app import run_application


def main(argv: list[str] | None = None) -> int:
    """Parse optional CLI flags and launch the AegisKey Password Generator GUI."""
    parser = argparse.ArgumentParser(
        prog="password-generator",
        description="AegisKey high-DPI Tkinter cryptographic password generator studio.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.parse_args(argv)
    return run_application()


if __name__ == "__main__":
    sys.exit(main())
