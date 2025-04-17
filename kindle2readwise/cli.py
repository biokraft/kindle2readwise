"""Command-line interface for kindle2readwise."""

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .config import (
    get_config_dir,
    get_config_value,
    get_data_dir,
    get_readwise_token,
    is_configured,
    list_config,
    set_config_value,
    set_readwise_token,
)
from .core import Kindle2Readwise
from .database import DEFAULT_DB_PATH
from .logging_config import setup_logging
from .utils.credentials import mask_token

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


def get_readwise_token_cli(args: argparse.Namespace) -> str | None:
    """Get Readwise token from args, environment variable, or config."""
    # First try command line argument
    if args.api_token:
        logger.debug("Using Readwise API token from command line argument.")
        return args.api_token

    # Then try environment variable
    token_from_env = os.environ.get(READWISE_TOKEN_ENV_VAR)
    if token_from_env:
        logger.debug("Using Readwise API token from environment variable %s.", READWISE_TOKEN_ENV_VAR)
        return token_from_env

    # Finally try configured token
    token_from_config = get_readwise_token()
    if token_from_config:
        logger.debug("Using Readwise API token from configuration.")
        return token_from_config

    logger.debug("Readwise API token not found in args, environment variable, or configuration.")
    return None


def handle_export(args: argparse.Namespace) -> None:
    """Handle the 'export' command."""
    logger.info("Starting 'export' command.")

    # Setup part
    readwise_token = _get_export_token(args)
    clippings_file = _get_export_clippings_file(args)
    db_path = _get_export_db_path(args)

    # Check export options
    _check_export_options(args)

    # Execute export
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

        _print_export_summary(stats, clippings_file)

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


def _get_export_token(args: argparse.Namespace) -> str:
    """Get Readwise token for export command."""
    readwise_token = get_readwise_token_cli(args)
    if not readwise_token:
        logger.critical(
            "Readwise API token not provided. Set it using the --api-token flag, the %s environment variable, "
            "or by running 'kindle2readwise config token'.",
            READWISE_TOKEN_ENV_VAR,
        )
        sys.exit(1)
    return readwise_token


def _get_export_clippings_file(args: argparse.Namespace) -> Path:
    """Get clippings file path for export command."""
    clippings_file_path = Path(args.file)
    if not clippings_file_path.is_absolute():
        clippings_file_path = Path.cwd() / clippings_file_path
    return clippings_file_path.resolve()


def _get_export_db_path(args: argparse.Namespace) -> Path:
    """Get database path for export command."""
    db_path = args.db_path
    if not db_path:
        db_path = get_config_value("database_path", DEFAULT_DB_PATH)
    return Path(db_path).resolve()


def _check_export_options(args: argparse.Namespace) -> None:
    """Check export command options."""
    if args.force:
        logger.warning("Ignoring --force option (not implemented yet).")
    if args.dry_run:
        logger.warning("Ignoring --dry-run option (not implemented yet).")
    if args.output:
        logger.warning("Ignoring --output option (not implemented yet).")


def _print_export_summary(stats, clippings_file: Path) -> None:
    """Print export summary and handle exit codes."""
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


def handle_configure(args: argparse.Namespace) -> None:
    """Handle the 'config' command and its subcommands."""
    if not hasattr(args, "config_command") or not args.config_command:
        # Default to 'show' if no subcommand specified
        args.config_command = "show"

    if args.config_command == "show":
        handle_config_show(args)
    elif args.config_command == "token":
        handle_config_token(args)
    elif args.config_command == "set":
        handle_config_set(args)
    elif args.config_command == "paths":
        handle_config_paths(args)
    else:
        logger.error(f"Unknown config subcommand: {args.config_command}")
        sys.exit(1)


def handle_config_show(_: argparse.Namespace) -> None:
    """Show current configuration."""
    logger.info("Showing current configuration")
    config = list_config()

    print("\n--- Current Configuration ---")
    for key, value in config.items():
        print(f"{key}: {value}")

    print(f"\nConfiguration directory: {get_config_dir()}")
    print(f"Data directory: {get_data_dir()}")

    if is_configured():
        print("\nApplication is properly configured.")
    else:
        print("\nWARNING: Application is not fully configured.")
        if not get_readwise_token():
            print("Missing Readwise API token. Set it with 'kindle2readwise config token'.")


def handle_config_token(args: argparse.Namespace) -> None:
    """Configure the Readwise API token."""
    if args.token:
        # Set the token from the command line argument
        token = args.token
        if set_readwise_token(token):
            logger.info("Readwise API token successfully saved.")
            print(f"Readwise API token {mask_token(token)} successfully saved.")
        else:
            logger.error("Failed to save Readwise API token.")
            print("Failed to save Readwise API token.")
            sys.exit(1)
    else:
        # Interactive mode - prompt for token
        try:
            import getpass

            token = getpass.getpass("Enter your Readwise API token: ")
            if not token:
                print("No token provided. Operation cancelled.")
                return

            if set_readwise_token(token):
                logger.info("Readwise API token successfully saved.")
                print(f"Readwise API token {mask_token(token)} successfully saved.")
            else:
                logger.error("Failed to save Readwise API token.")
                print("Failed to save Readwise API token.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return


def handle_config_set(args: argparse.Namespace) -> None:
    """Set a configuration value."""
    if not args.key or not args.value:
        logger.error("Both key and value must be specified.")
        print("Error: Both key and value must be specified.")
        print("Usage: kindle2readwise config set KEY VALUE")
        sys.exit(1)

    # Validate key is a known configuration option
    valid_keys = ["export_format", "auto_confirm", "log_level", "database_path"]
    if args.key not in valid_keys:
        logger.error(f"Unknown configuration key: {args.key}")
        print(f"Error: Unknown configuration key: {args.key}")
        print(f"Valid keys are: {', '.join(valid_keys)}")
        sys.exit(1)

    # Special handling for boolean values
    if args.key == "auto_confirm":
        if args.value.lower() in ("true", "yes", "1", "on"):
            value = True
        elif args.value.lower() in ("false", "no", "0", "off"):
            value = False
        else:
            logger.error(f"Invalid boolean value for {args.key}: {args.value}")
            print("Error: Invalid boolean value. Use 'true' or 'false'.")
            sys.exit(1)
    else:
        value = args.value

    if set_config_value(args.key, value):
        logger.info(f"Configuration value set: {args.key} = {value}")
        print(f"Configuration updated: {args.key} = {value}")
    else:
        logger.error(f"Failed to set configuration value: {args.key}")
        print("Error: Failed to update configuration.")
        sys.exit(1)


def handle_config_paths(_: argparse.Namespace) -> None:
    """Show configuration and data paths."""
    print("\n--- Application Paths ---")
    print(f"Configuration directory: {get_config_dir()}")
    print(f"Data directory: {get_data_dir()}")
    print(f"Database path: {get_config_value('database_path')}")

    # Detect platform
    system = sys.platform
    if system.startswith("darwin"):
        platform_name = "macOS"
    elif system.startswith("win"):
        platform_name = "Windows"
    elif system.startswith("linux"):
        platform_name = "Linux"
    else:
        platform_name = system

    print(f"Detected platform: {platform_name}")


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
        default="WARNING",
        help="Set the logging level (default: WARNING).",
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
        help=f"Path to the 'My Clippings.txt' file (default: {DEFAULT_CLIPPINGS_PATH})",
    )
    parser_export.add_argument(
        "--api-token", "-t", type=str, help="Readwise API token (or use the READWISE_API_TOKEN environment variable)."
    )
    parser_export.add_argument(
        "--db-path",
        type=str,
        help=f"Path to the SQLite database (default: from config or {DEFAULT_DB_PATH}).",
    )
    parser_export.add_argument("--force", "-f", action="store_true", help="Force export of all highlights.")
    parser_export.add_argument(
        "--dry-run", "-d", action="store_true", help="Simulate export without sending to Readwise."
    )
    parser_export.add_argument("--output", "-o", type=str, help="Output highlights to a file instead of Readwise.")
    parser_export.set_defaults(func=handle_export)

    # --- Config Command ---
    parser_config = subparsers.add_parser("config", help="Configure the application")
    config_subparsers = parser_config.add_subparsers(dest="config_command", help="Configuration commands")

    # Config show subcommand
    parser_config_show = config_subparsers.add_parser("show", help="Show current configuration")
    parser_config_show.set_defaults(func=handle_configure)

    # Config token subcommand
    parser_config_token = config_subparsers.add_parser("token", help="Set the Readwise API token")
    parser_config_token.add_argument(
        "token", nargs="?", type=str, help="The Readwise API token (omit for interactive prompt)"
    )
    parser_config_token.set_defaults(func=handle_configure)

    # Config set subcommand
    parser_config_set = config_subparsers.add_parser("set", help="Set a configuration value")
    parser_config_set.add_argument("key", type=str, help="Configuration key to set")
    parser_config_set.add_argument("value", type=str, help="Value to set")
    parser_config_set.set_defaults(func=handle_configure)

    # Config paths subcommand
    parser_config_paths = config_subparsers.add_parser("paths", help="Show configuration and data paths")
    parser_config_paths.set_defaults(func=handle_configure)

    parser_config.set_defaults(func=handle_configure)

    # --- History Command ---
    parser_history = subparsers.add_parser("history", help="View export history")
    parser_history.set_defaults(func=handle_history)

    # --- Version Command ---
    parser_version = subparsers.add_parser("version", help="Show version information")
    parser_version.set_defaults(func=handle_version)

    # Parse arguments and call the appropriate handler
    args = parser.parse_args()

    # Set up logging
    setup_logging(level=args.log_level, log_file=args.log_file)

    # Call the appropriate handler function
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
