"""Command-line interface for kindle2readwise."""

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .core import Kindle2Readwise
from .database import DEFAULT_DB_PATH
from .logging_config import setup_logging

# Environment variable for Readwise token (optional)
READWISE_TOKEN_ENV_VAR = "READWISE_API_TOKEN"
DEFAULT_CLIPPINGS_PATH = "My Clippings.txt"

logger = logging.getLogger(__name__)


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


def get_readwise_token(args: argparse.Namespace) -> str | None:
    """Get Readwise token from args, environment variable, or config (TBD)."""
    if args.api_token:
        logger.debug("Using Readwise API token from command line argument.")
        return args.api_token

    token_from_env = os.environ.get(READWISE_TOKEN_ENV_VAR)
    if token_from_env:
        logger.debug("Using Readwise API token from environment variable %s.", READWISE_TOKEN_ENV_VAR)
        return token_from_env

    # TODO: Implement reading token from a configuration file
    logger.debug("Readwise API token not found in args or environment variable.")
    return None


def handle_export(args: argparse.Namespace) -> None:
    """Handle the 'export' command."""
    logger.info("Starting 'export' command.")

    readwise_token = get_readwise_token(args)
    if not readwise_token:
        logger.critical(
            "Readwise API token not provided. Set it using the --api-token flag or the %s environment variable.",
            READWISE_TOKEN_ENV_VAR,
        )
        sys.exit(1)

    # Determine clippings file path
    clippings_file_path = Path(args.file)
    if not clippings_file_path.is_absolute():
        clippings_file_path = Path.cwd() / clippings_file_path
    clippings_file = clippings_file_path.resolve()
    logger.debug("Using clippings file: %s", clippings_file)

    # Determine database path
    db_path = Path(args.db_path).resolve() if args.db_path else DEFAULT_DB_PATH
    logger.debug("Using database path: %s", db_path)

    # TODO: Handle other export options like --force, --dry-run, --output
    if args.force:
        logger.warning("Ignoring --force option (not implemented yet).")  # Placeholder
    if args.dry_run:
        logger.warning("Ignoring --dry-run option (not implemented yet).")  # Placeholder
    if args.output:
        logger.warning("Ignoring --output option (not implemented yet).")  # Placeholder

    try:
        app = Kindle2Readwise(
            clippings_file=str(clippings_file),
            readwise_token=readwise_token,
            db_path=db_path,
        )

        is_valid, validation_msg = app.validate_setup()
        if not is_valid:
            logger.critical("Setup validation failed: %s", validation_msg)
            sys.exit(1)

        logger.info("Setup valid. Starting export process...")
        stats = app.process()

        print("\n--- Export Summary ---")
        print(f"Clippings File: {clippings_file}")
        print(f"Total Clippings Processed: {stats.total_processed}")
        print(f"New Highlights Sent to Readwise: {stats.new_sent}")
        print(f"Duplicate Highlights Skipped: {stats.duplicates_skipped}")
        if stats.failed_to_send > 0:
            print(f"[bold red]Highlights Failed to Send: {stats.failed_to_send}[/bold red]", file=sys.stderr)
            sys.exit(1)  # Exit with error if sends failed
        else:
            print("All new highlights sent successfully!")

    except FileNotFoundError as e:
        logger.critical("Error: %s", e)
        sys.exit(1)
    except Exception:
        logger.critical("An unexpected error occurred during export.", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure DB connection is closed if app object was created
        if "app" in locals() and hasattr(app, "close_db") and callable(app.close_db):
            app.close_db()


# --- Placeholder functions for other commands ---
def handle_configure(_: argparse.Namespace) -> None:
    logger.warning("'configure' command is not implemented yet.")
    print("'configure' command is not implemented yet.")


def handle_history(_: argparse.Namespace) -> None:
    logger.warning("'history' command is not implemented yet.")
    print("'history' command is not implemented yet.")


def handle_version(_: argparse.Namespace) -> None:
    print(f"kindle2readwise version {__version__}")
    # Add Python/Platform info later if needed


def main() -> None:
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Export Kindle clippings ('My Clippings.txt') to Readwise.", prog="kindle2readwise"
    )

    # --- Global Options ---
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}", help="Show program's version number and exit."
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO).",
    )
    parser.add_argument(
        "--log-file", type=str, default=None, help="Log output to a specified file in addition to the console."
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Export Command ---
    parser_export = subparsers.add_parser("export", help="Export Kindle highlights to Readwise")
    parser_export.add_argument(
        "file",
        type=str,
        nargs="?",
        default=DEFAULT_CLIPPINGS_PATH,
        help=f"Path to Kindle 'My Clippings.txt' file (default: {DEFAULT_CLIPPINGS_PATH})",
    )
    parser_export.add_argument(
        "--api-token",
        "-t",
        type=str,
        default=None,
        help=f"Readwise API token (overrides {READWISE_TOKEN_ENV_VAR} env var and config file).",
    )
    parser_export.add_argument(
        "--db-path", type=str, default=None, help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})"
    )
    # TODO: Add other export options from spec (--force, --dry-run etc.)
    parser_export.add_argument(
        "--force", "-F", action="store_true", help="Force export, ignoring duplicates (not implemented)."
    )
    parser_export.add_argument(
        "--dry-run", "-d", action="store_true", help="Parse but do not export (not implemented)."
    )
    parser_export.add_argument("--output", "-o", type=str, help="Save parsed highlights to file (not implemented).")
    parser_export.set_defaults(func=handle_export)

    # --- Configure Command (Placeholder) ---
    parser_configure = subparsers.add_parser("configure", help="Manage application configuration (not implemented).")
    # TODO: Add configure options
    parser_configure.set_defaults(func=handle_configure)

    # --- History Command (Placeholder) ---
    parser_history = subparsers.add_parser("history", help="View past export sessions (not implemented).")
    # TODO: Add history options
    parser_history.set_defaults(func=handle_history)

    args = parser.parse_args()

    # --- Setup Logging ---
    # Set up logging based on global args *before* calling command handlers
    log_file_path = Path(args.log_file) if args.log_file else None
    setup_logging(level=args.log_level, log_file=log_file_path)

    logger.debug("Parsed arguments: %s", args)

    # --- Execute Command ---
    if hasattr(args, "func"):
        args.func(args)
    else:
        # Should not happen if subparsers are required
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
