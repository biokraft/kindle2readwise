"""Export command handler for the kindle2readwise CLI."""

import logging
import sys
from pathlib import Path

from ...config import get_config_value
from ...core import Kindle2Readwise
from ...database import DEFAULT_DB_PATH
from ...exceptions import ProcessingError, ValidationError
from ..utils.common import get_default_clippings_path, get_readwise_token_cli
from ..utils.formatters import format_export_summary
from .devices import handle_devices

logger = logging.getLogger(__name__)


def should_detect_devices(args):
    """Check if automatic device detection should be performed.

    Args:
        args: Command arguments

    Returns:
        bool: Whether to perform device detection
    """
    # If devices flag is explicitly set, do device detection
    if hasattr(args, "devices") and args.devices:
        return True

    # If a specific file is provided, skip device detection
    if args.file:
        return False

    # If in interactive mode, we need a file, so skip device detection
    if args.interactive:
        return False

    # Default: do device detection when no file is specified
    return not args.file


def handle_export(args):
    """Handle the 'export' command."""
    logger.info("Starting 'export' command.")

    # Check if we should perform device detection
    if should_detect_devices(args):
        handle_devices(args)
        return

    # Setup part
    readwise_token = _get_export_token(args)
    clippings_file = _get_export_clippings_file(args)
    db_path = _get_export_db_path(args)
    _check_export_options(args)

    # Check if file exists
    if not clippings_file.exists():
        logger.critical(f"Clippings file not found: {clippings_file}")
        sys.exit(1)

    # Execute export
    try:
        app = Kindle2Readwise(
            clippings_file=str(clippings_file),
            readwise_token=readwise_token,
            db_path=db_path,
            dry_run=args.dry_run,
        )

        try:
            app.validate_setup()

            # Initialize stats to None
            stats = None

            # Handle interactive mode if requested
            if args.interactive:
                stats = handle_interactive_mode(app, clippings_file)
            else:
                # Regular export mode
                logger.info("Setup valid. Starting export process...")
                stats = app.process()
                print(format_export_summary(stats, clippings_file, args.dry_run))

            # Set exit code based on failed sends - only if stats is populated
            if stats is not None and stats.failed_to_send > 0:
                sys.exit(1)

        except ValidationError as e:
            logger.critical("Setup validation failed: %s", str(e))
            sys.exit(1)
        except ProcessingError as e:
            logger.critical("Processing failed: %s", str(e))
            sys.exit(1)

    except FileNotFoundError as e:
        logger.critical("Error: %s", e)
        sys.exit(1)
    except Exception:
        logger.critical("An unexpected error occurred during export.", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure DB connection is closed if app object was created
        if "app" in locals() and app:
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


def handle_interactive_mode(app, clippings_file):
    """Handle interactive mode for export.

    Args:
        app: Kindle2Readwise instance
        clippings_file: Path to the clippings file

    Returns:
        ExportStats object if export was performed, None otherwise
    """
    logger.info("Starting interactive export mode.")

    # Get highlights that would be exported
    pending_highlights = app.get_pending_highlights()

    if not pending_highlights:
        print("\nNo new highlights found to export.")
        return None

    # Display highlights for review
    print("\n=== Interactive Export Mode ===")
    print(f"Found {len(pending_highlights)} new highlights to export.\n")

    # Group highlights by book
    books = {}
    for highlight in pending_highlights:
        book_key = f"{highlight['title']} - {highlight['author']}"
        if book_key not in books:
            books[book_key] = []
        books[book_key].append(highlight)

    # Display highlights grouped by book
    for book_key, highlights in books.items():
        print(f"\n📚 {book_key}")
        print("-" * 80)

        for highlight in highlights:
            print(f"  [{highlight['id']}] {highlight['highlight'][:100]}...")
            print(f"      Location: {highlight['location']}, Date: {highlight['date']}")
            print()

    # Instructions for selection
    print("\nSelect highlights to export:")
    print("  - Enter highlight IDs separated by commas (e.g., '1,3,5')")
    print("  - Enter 'a' to select all highlights")
    print("  - Enter 'q' to quit without exporting")

    # Get user selection
    selection = input("\nYour selection: ").strip().lower()

    if selection == "q":
        print("Export cancelled.")
        return None

    selected_ids = []
    if selection == "a":
        # Select all highlights
        selected_ids = [h["id"] for h in pending_highlights]
        print(f"Selected all {len(selected_ids)} highlights.")
    else:
        # Parse the selection
        try:
            selected_ids = [int(id_str.strip()) for id_str in selection.split(",") if id_str.strip()]
            valid_ids = [id for id in selected_ids if any(h["id"] == id for h in pending_highlights)]

            if len(valid_ids) != len(selected_ids):
                invalid_ids = set(selected_ids) - set(valid_ids)
                print(f"Warning: Invalid IDs ignored: {', '.join(map(str, invalid_ids))}")

            selected_ids = valid_ids
            print(f"Selected {len(selected_ids)} highlights.")
        except ValueError:
            print("Invalid selection format. Export cancelled.")
            return None

    # Confirm export
    if selected_ids:
        confirm = input("\nProceed with export? (y/n): ").strip().lower()
        if confirm != "y":
            print("Export cancelled.")
            return None

        # Process selected highlights
        print("\nExporting selected highlights...")
        stats = app.process_selected(selected_ids=selected_ids)
        print(format_export_summary(stats, clippings_file, False))
        return stats
    print("No highlights selected. Export cancelled.")
    return None
