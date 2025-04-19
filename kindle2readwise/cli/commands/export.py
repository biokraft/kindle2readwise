"""Export command handler for the kindle2readwise CLI."""

import logging
import sys
from pathlib import Path

from ...config import get_config_value
from ...core import Kindle2Readwise
from ...database import DEFAULT_DB_PATH
from ..utils.common import get_default_clippings_path, get_readwise_token_cli
from ..utils.formatters import format_export_summary
from .devices import handle_devices

logger = logging.getLogger(__name__)


def handle_export(args):
    """Handle the 'export' command."""
    logger.info("Starting 'export' command.")

    # If --devices flag is provided, list devices and exit
    if hasattr(args, "devices") and args.devices:
        handle_devices(args)
        return

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
            dry_run=args.dry_run,
        )

        is_valid, validation_msg = app.validate_setup()
        if not is_valid:
            logger.critical("Setup validation failed: %s", validation_msg)
            sys.exit(1)

        logger.info("Setup valid. Starting export process...")
        stats = app.process()

        print(format_export_summary(stats, clippings_file, args.dry_run))

        # Set exit code based on failed sends
        if stats.failed_to_send > 0:
            sys.exit(1)

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


def _get_export_token(args):
    """Get Readwise token for export command."""
    readwise_token = get_readwise_token_cli(args)
    if not readwise_token:
        logger.critical(
            "Readwise API token not provided. Set it using the --api-token flag, the %s environment variable, "
            "or by running 'kindle2readwise config token'.",
            "READWISE_API_TOKEN",
        )
        sys.exit(1)
    return readwise_token


def _get_export_clippings_file(args):
    """Get clippings file path for export command."""
    # If an explicit file was provided and it exists, use it directly
    if args.file != "My Clippings.txt" and Path(args.file).exists():
        clippings_file_path = Path(args.file)
        if not clippings_file_path.is_absolute():
            clippings_file_path = Path.cwd() / clippings_file_path
        logger.debug("Using explicitly provided clippings file: %s", clippings_file_path)
        return clippings_file_path.resolve()

    # If no explicit file was provided or the default doesn't exist in current dir,
    # try to automatically detect Kindle device
    if args.file == "My Clippings.txt":
        default_path = get_default_clippings_path()
        if default_path:
            logger.info("Using automatically detected Kindle clippings file: %s", default_path)
            return Path(default_path).resolve()

    # If we get here, we'll use the provided file path even if it doesn't exist
    # (the validation will later catch the issue)
    clippings_file_path = Path(args.file)
    if not clippings_file_path.is_absolute():
        clippings_file_path = Path.cwd() / clippings_file_path

    if not clippings_file_path.exists():
        logger.warning(
            "Clippings file not found: %s. Make sure your Kindle is connected or provide the correct path.",
            clippings_file_path,
        )

    return clippings_file_path.resolve()


def _get_export_db_path(args):
    """Get database path for export command."""
    db_path = args.db_path
    if not db_path:
        db_path = get_config_value("database_path", DEFAULT_DB_PATH)
    return Path(db_path).resolve()


def _check_export_options(args):
    """Check export command options."""
    if args.force:
        logger.warning("Ignoring --force option (not implemented yet).")
    if args.output:
        logger.warning("Ignoring --output option (not implemented yet).")
