"""Command-line interface for kindle2readwise."""

import argparse
import sys


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Export Kindle highlights to Readwise",
        prog="kindle2readwise",
    )
    parser.add_argument("--version", action="store_true", help="Display version information")

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export Kindle clippings to Readwise")
    export_parser.add_argument("-f", "--clippings-file", help="Path to My Clippings.txt file")
    export_parser.add_argument("-t", "--api-token", help="Readwise API token")

    args = parser.parse_args()

    if args.version:
        from . import __version__

        print(f"kindle2readwise v{__version__}")
        return 0

    if args.command == "export":
        print("Export feature not yet implemented.")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
