"""Command-line interface for kindle2readwise."""

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .core import Kindle2Readwise


def get_default_clippings_path() -> str | None:
    """Get the default path to the Kindle clippings file.

    Returns:
        Path to the clippings file if found, None otherwise
    """
    # Common paths where Kindle gets mounted
    common_paths = [
        # macOS
        Path("/Volumes/Kindle/documents/My Clippings.txt"),
        # Linux
        Path("/media/Kindle/documents/My Clippings.txt"),
        # Windows
        Path("E:/documents/My Clippings.txt"),
        Path("F:/documents/My Clippings.txt"),
    ]

    # Check current directory first
    current_dir = Path.cwd() / "My Clippings.txt"
    if current_dir.exists():
        return str(current_dir)

    # Check common paths
    for path in common_paths:
        if path.exists():
            return str(path)

    return None


def get_api_token_from_env() -> str | None:
    """Get the Readwise API token from environment variables.

    Returns:
        API token if found, None otherwise
    """
    return os.environ.get("READWISE_API_TOKEN")


def configure_logging(verbose: bool = False) -> None:
    """Configure logging for the application.

    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Export Kindle highlights to Readwise",
        prog="kindle2readwise",
    )
    parser.add_argument("--version", action="store_true", help="Display version information")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    # Add subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export Kindle clippings to Readwise")
    export_parser.add_argument("-f", "--clippings-file", help="Path to My Clippings.txt file")
    export_parser.add_argument("-t", "--api-token", help="Readwise API token (or set READWISE_API_TOKEN env var)")
    export_parser.add_argument("-d", "--db-path", help="Path to SQLite database file (optional)")
    export_parser.add_argument("--dry-run", action="store_true", help="Parse clippings but don't export to Readwise")

    args = parser.parse_args()

    # Configure logging
    configure_logging(args.verbose)

    if args.version:
        print(f"kindle2readwise v{__version__}")
        return 0

    if args.command == "export":
        return handle_export_command(args)

    parser.print_help()
    return 0


def validate_export_args(args):
    """Validate export command arguments.

    Args:
        args: Command line arguments

    Returns:
        Tuple of (is_valid, error_message, clippings_file, api_token)
    """
    # Get clippings file path
    clippings_file = args.clippings_file
    if not clippings_file:
        clippings_file = get_default_clippings_path()
        if not clippings_file:
            return False, "No Kindle clippings file found. Please specify with --clippings-file.", None, None

    # Get API token if we're not doing a dry run
    api_token = args.api_token
    if not api_token:
        api_token = get_api_token_from_env()
        if not api_token and not args.dry_run:
            error_msg = "No Readwise API token found. Please use --api-token or set READWISE_API_TOKEN."
            return False, error_msg, None, None

    # For dry runs, use a dummy token if none provided
    if args.dry_run:
        api_token = api_token or "dry_run_token"

    return True, "", clippings_file, api_token


def handle_export_command(args):
    """Handle the export command.

    Args:
        args: Command line arguments

    Returns:
        Exit code
    """
    # Validate arguments
    is_valid, error_msg, clippings_file, api_token = validate_export_args(args)
    if not is_valid:
        print(f"Error: {error_msg}")
        return 1

    try:
        # Initialize app
        app = Kindle2Readwise(clippings_file=clippings_file, readwise_token=api_token, db_path=args.db_path)

        if args.dry_run:
            # Dry run - just parse and count
            print(f"Dry run: Processing clippings from {clippings_file}...")
            clippings = app.parser.parse()
            print(f"Found {len(clippings)} clippings:")

            # Group by book
            books = {}
            for clip in clippings:
                book_key = f"{clip.title} - {clip.author or 'Unknown'}"
                if book_key not in books:
                    books[book_key] = {"highlights": 0, "notes": 0}

                if clip.type == "highlight":
                    books[book_key]["highlights"] += 1
                elif clip.type == "note":
                    books[book_key]["notes"] += 1

            # Print summary by book
            for book, counts in books.items():
                print(f"  {book}: {counts['highlights']} highlights, {counts['notes']} notes")
            return 0

        # Regular run - validate and process
        is_valid, error = app.validate_setup()
        if not is_valid:
            print(f"Error: {error}")
            return 1

        # Process clippings
        print(f"Processing clippings from {clippings_file}...")
        stats = app.process()

        print("Export completed:")
        print(f"  Total clippings: {stats.total}")
        print(f"  New clippings: {stats.new}")
        print(f"  Duplicate clippings: {stats.dupe}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
