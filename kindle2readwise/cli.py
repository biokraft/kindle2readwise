"""Command-line interface for kindle2readwise."""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
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
from .database import DEFAULT_DB_PATH, HighlightsDAO
from .logging_config import setup_logging
from .utils.credentials import mask_token

# Environment variable for Readwise token (optional)
READWISE_TOKEN_ENV_VAR = "READWISE_API_TOKEN"
DEFAULT_CLIPPINGS_PATH = "My Clippings.txt"

# Constants for formatting
MAX_SOURCE_FILE_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_AUTHOR_LENGTH = 20
MAX_HIGHLIGHTS_PREVIEW = 10

# Constants for UI display formatting
BOOK_TITLE_MAX_LENGTH = 37
BOOK_TITLE_TRUNCATE_LENGTH = 34
BOOK_AUTHOR_MAX_LENGTH = 27
BOOK_AUTHOR_TRUNCATE_LENGTH = 24
TABLE_WIDTH = 82

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
            dry_run=args.dry_run,
        )

        is_valid, validation_msg = app.validate_setup()
        if not is_valid:
            logger.critical("Setup validation failed: %s", validation_msg)
            sys.exit(1)

        logger.info("Setup valid. Starting export process...")
        stats = app.process()

        _print_export_summary(stats, clippings_file, args.dry_run)

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
    if args.output:
        logger.warning("Ignoring --output option (not implemented yet).")


def _print_export_summary(stats, clippings_file: Path, dry_run: bool) -> None:
    """Print export summary and handle exit codes."""
    print("\n--- Export Summary ---")
    if dry_run:
        print("[DRY RUN MODE - No highlights were actually sent to Readwise]")
    print(f"Clippings File: {clippings_file}")
    print(f"Total Clippings Processed: {stats.total_processed}")
    print(f"New Highlights {'Found' if dry_run else 'Sent to Readwise'}: {stats.new_sent}")
    print(f"Duplicate Highlights Skipped: {stats.duplicates_skipped}")
    if stats.failed_to_send > 0:
        print(f"[bold red]Highlights Failed to Send: {stats.failed_to_send}[/bold red]", file=sys.stderr)
        sys.exit(1)  # Exit with error if sends failed
    elif dry_run:
        print("Dry run completed successfully. No actual highlights were sent.")
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
    # Validate log_level values
    elif args.key == "log_level":
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if args.value.upper() not in valid_log_levels:
            logger.error(f"Invalid log level: {args.value}")
            print(f"Error: Invalid log level. Valid values are: {', '.join(valid_log_levels)}")
            sys.exit(1)
        value = args.value.upper()
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


def handle_history(args: argparse.Namespace) -> None:
    """Handle the 'history' command to display export history."""
    logger.info("Starting 'history' command.")

    # Get database path from config if not provided
    db_path = get_config_value("database_path", DEFAULT_DB_PATH)

    try:
        # Initialize the DAO
        dao = HighlightsDAO(db_path)

        # Handle specific session details if requested
        if hasattr(args, "session") and args.session:
            _show_session_details(dao, args.session, args.format)
            return

        # Get export history with specified limit
        limit = args.limit if hasattr(args, "limit") else 10
        history = dao.get_export_history(limit=limit)

        if not history:
            print("No export history found.")
            return

        # Display based on format
        if hasattr(args, "format") and args.format in ["json", "csv"]:
            _export_history_formatted(history, args.format)
        else:
            _display_history_table(history, args.details if hasattr(args, "details") else False)

    except Exception as e:
        logger.error("Error retrieving export history: %s", e, exc_info=True)
        print(f"Error retrieving export history: {e}")
        sys.exit(1)


def _display_history_table(history: list[dict], show_details: bool = False) -> None:
    """Display export history in a formatted table."""
    if not history:
        return

    # Print header
    print("\n--- Export History ---")
    print(f"{'ID':<5} {'Date':<20} {'Status':<10} {'Total':<8} {'New':<8} {'Dupes':<8} {'Source File':<30}")
    print("-" * 90)

    # Print each session
    for session in history:
        # Format the date for display
        start_time = session.get("start_time", "")
        if start_time:
            try:
                # Parse ISO format datetime and format for display
                dt = datetime.fromisoformat(start_time)
                formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_date = start_time
        else:
            formatted_date = "Unknown"

        # Format source file (truncate if too long)
        source_file = session.get("source_file", "")
        if len(source_file) > MAX_SOURCE_FILE_LENGTH:
            source_file = "..." + source_file[-27:]

        # Print the row
        print(
            f"{session.get('id', 0):<5} "
            f"{formatted_date:<20} "
            f"{session.get('status', ''):<10} "
            f"{session.get('highlights_total', 0):<8} "
            f"{session.get('highlights_new', 0):<8} "
            f"{session.get('highlights_dupe', 0):<8} "
            f"{source_file:<30}"
        )

    # Print summary
    total_highlights = sum(session.get("highlights_new", 0) for session in history)
    print("-" * 90)
    print(f"Total Exported: {total_highlights} highlights across {len(history)} sessions")

    # Show additional details if requested
    if show_details:
        print("\n--- Detailed Information ---")
        for session in history:
            _show_session_details_text(session)


def _show_session_details_text(session: dict) -> None:
    """Display detailed information for a session in text format."""
    # Get session fields with sensible defaults
    session_id = session.get("id", "Unknown")
    start_time = session.get("start_time", "Unknown")
    end_time = session.get("end_time", "Unknown")
    status = session.get("status", "Unknown")
    total = session.get("highlights_total", 0)
    new = session.get("highlights_new", 0)
    dupes = session.get("highlights_dupe", 0)
    source_file = session.get("source_file", "Unknown")

    # Calculate duration if both times are available
    duration = "Unknown"
    if start_time != "Unknown" and end_time != "Unknown":
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            duration = str(end_dt - start_dt)
        except (ValueError, TypeError):
            pass

    print(f"\nSession ID: {session_id}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Duration: {duration}")
    print(f"Status: {status}")
    print(f"Source File: {source_file}")
    print(f"Highlights Processed: {total}")
    print(f"New Highlights: {new}")
    print(f"Duplicate Highlights: {dupes}")


def _show_session_details(dao: HighlightsDAO, session_id: int, format_type: str = "text") -> None:
    """Show detailed information for a specific session."""
    # Get the session details
    session = dao.get_session_by_id(session_id)
    if not session:
        print(f"Session with ID {session_id} not found.")
        return

    # Get highlights for this session
    highlights = dao.get_highlights_by_session(session_id)

    # Format and display based on format type
    if format_type == "json":
        import json

        session_data = {"session": session, "highlights": highlights}
        print(json.dumps(session_data, indent=2, default=str))
    elif format_type == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write session info
        writer.writerow(["Session Information"])
        writer.writerow(["ID", "Start Time", "End Time", "Status", "Total", "New", "Duplicates"])
        writer.writerow(
            [
                session.get("id"),
                session.get("start_time"),
                session.get("end_time"),
                session.get("status"),
                session.get("highlights_total"),
                session.get("highlights_new"),
                session.get("highlights_dupe"),
            ]
        )

        # Write highlights
        if highlights:
            writer.writerow([])
            writer.writerow(["Highlights"])
            writer.writerow(["Title", "Author", "Text", "Location", "Date Highlighted", "Status"])
            for h in highlights:
                writer.writerow(
                    [
                        h.get("title"),
                        h.get("author"),
                        h.get("text"),
                        h.get("location"),
                        h.get("date_highlighted"),
                        h.get("status"),
                    ]
                )

        print(output.getvalue())
    else:
        # Text format
        _show_session_details_text(session)

        # Show highlight summary if available
        if highlights:
            print(f"\nHighlights in this session: {len(highlights)}")
            print(f"{'Title':<30} {'Author':<20} {'Status':<10}")
            print("-" * 70)

            for h in highlights[:MAX_HIGHLIGHTS_PREVIEW]:  # Show only first 10 for brevity
                title = h.get("title", "")
                if len(title) > MAX_TITLE_LENGTH:
                    title = title[:27] + "..."

                author = h.get("author", "")
                if len(author) > MAX_AUTHOR_LENGTH:
                    author = author[:17] + "..."

                print(f"{title:<30} {author:<20} {h.get('status', ''):<10}")

            if len(highlights) > MAX_HIGHLIGHTS_PREVIEW:
                print(f"... and {len(highlights) - MAX_HIGHLIGHTS_PREVIEW} more highlights")


def _export_history_formatted(history: list[dict], format_type: str) -> None:
    """Export history in the specified format (JSON or CSV)."""
    if format_type == "json":
        import json

        print(json.dumps(history, indent=2, default=str))
    elif format_type == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Start Time",
                "End Time",
                "Status",
                "Total Highlights",
                "New Highlights",
                "Duplicate Highlights",
                "Source File",
            ]
        )

        # Write rows
        for session in history:
            writer.writerow(
                [
                    session.get("id"),
                    session.get("start_time"),
                    session.get("end_time"),
                    session.get("status"),
                    session.get("highlights_total"),
                    session.get("highlights_new"),
                    session.get("highlights_dupe"),
                    session.get("source_file"),
                ]
            )

        print(output.getvalue())


def handle_version(_: argparse.Namespace) -> None:
    print(f"kindle2readwise version {__version__}")
    # Add Python/Platform info later if needed


def handle_highlights(args: argparse.Namespace) -> None:
    """Handle the 'highlights' command to list and search highlights."""
    logger.info("Starting 'highlights' command.")

    # Get database path from config if not provided
    db_path = get_config_value("database_path", DEFAULT_DB_PATH)

    try:
        # Initialize the DAO
        dao = HighlightsDAO(db_path)

        # Process different sub-commands
        if hasattr(args, "highlights_command"):
            if args.highlights_command == "list":
                _handle_highlights_list(dao, args)
            elif args.highlights_command == "books":
                _handle_highlights_books(dao, args)
            elif args.highlights_command == "delete":
                _handle_highlights_delete(dao, args)
            else:
                print("Unknown subcommand. Use 'kindle2readwise highlights --help' for usage information.")
        else:
            # Default: list highlights with no filters
            _handle_highlights_list(dao, args)

    except Exception as e:
        logger.error("Error processing highlights command: %s", e, exc_info=True)
        print(f"Error processing highlights command: {e}")
        sys.exit(1)


def _handle_highlights_list(dao: HighlightsDAO, args: argparse.Namespace) -> None:
    """Handle listing highlights with optional filters."""
    # Extract filter parameters
    title = getattr(args, "title", None)
    author = getattr(args, "author", None)
    text = getattr(args, "text", None)
    limit = getattr(args, "limit", 20)
    offset = getattr(args, "offset", 0)
    sort_by = getattr(args, "sort", "date_exported")
    sort_dir = getattr(args, "order", "desc")
    output_format = getattr(args, "format", None)

    # Get the count first for the summary info
    count = dao.get_highlight_count_with_filters(title=title, author=author, text_search=text)

    # Get filtered highlights
    highlights = dao.get_highlights(
        title=title, author=author, text_search=text, limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir
    )

    if not highlights:
        print("No highlights found with the specified filters.")
        return

    # Handle different output formats
    if output_format == "json":
        _output_highlights_json(highlights, count, limit, offset)
    elif output_format == "csv":
        _output_highlights_csv(highlights)
    else:
        _output_highlights_text(highlights, count, limit, offset)


def _output_highlights_text(highlights: list[dict], count: int, limit: int, offset: int) -> None:
    """Display highlights in formatted text."""
    # Print summary
    print(f"\nFound {count} highlights total")
    if count > limit:
        print(f"Displaying {len(highlights)} highlights (offset: {offset}, limit: {limit})")

    print("\n" + "=" * 80)

    # Print each highlight
    for h in highlights:
        title = h.get("title", "Unknown Title")
        author = h.get("author", "Unknown Author")
        text = h.get("text", "")
        date_highlighted = h.get("date_highlighted", "Unknown")
        location = h.get("location", "Unknown")

        # Format date if available
        if date_highlighted and date_highlighted != "Unknown":
            try:
                dt = datetime.fromisoformat(date_highlighted)
                date_highlighted = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Location: {location}")
        print(f"Date: {date_highlighted}")
        print(f"Text: {text}")
        print("-" * 80)


def _output_highlights_json(highlights: list[dict], count: int, limit: int, offset: int) -> None:
    """Output highlights as JSON."""
    import json

    result = {"count": count, "limit": limit, "offset": offset, "highlights": highlights}

    print(json.dumps(result, indent=2, default=str))


def _output_highlights_csv(highlights: list[dict]) -> None:
    """Output highlights as CSV."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(["ID", "Title", "Author", "Text", "Location", "Date Highlighted", "Date Exported"])

    # Write data
    for h in highlights:
        writer.writerow(
            [
                h.get("id", ""),
                h.get("title", ""),
                h.get("author", ""),
                h.get("text", ""),
                h.get("location", ""),
                h.get("date_highlighted", ""),
                h.get("date_exported", ""),
            ]
        )

    print(output.getvalue())


def _handle_highlights_books(dao: HighlightsDAO, args: argparse.Namespace) -> None:
    """Handle displaying all books with highlight counts."""
    books = dao.get_books()

    # Format output based on requested format
    format_type = getattr(args, "format", "text")
    if format_type == "json":
        print(json.dumps(books, indent=2))
        return
    if format_type == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=["title", "author", "highlight_count"])
        writer.writeheader()
        writer.writerows(books)
        return

    # Default text output
    print("\n--- Books in Database ---")
    print(f"{'Title':<40} {'Author':<30} {'Highlights':<10}")
    print("-" * TABLE_WIDTH)

    for book in books:
        title = book.get("title", "Unknown")
        if len(title) > BOOK_TITLE_MAX_LENGTH:
            title = title[:BOOK_TITLE_TRUNCATE_LENGTH] + "..."

        author = book.get("author", "Unknown")
        if len(author) > BOOK_AUTHOR_MAX_LENGTH:
            author = author[:BOOK_AUTHOR_TRUNCATE_LENGTH] + "..."

        count = book.get("highlight_count", 0)

        print(f"{title:<40} {author:<30} {count:<10}")

    print("-" * TABLE_WIDTH)
    print(f"Total: {len(books)} books, {sum(book.get('highlight_count', 0) for book in books)} highlights")


def _handle_highlights_delete(dao: HighlightsDAO, args: argparse.Namespace) -> None:
    """Handle deleting highlights."""
    # Check which delete option was specified
    if hasattr(args, "id") and args.id:
        # Delete a single highlight by ID
        highlight_id = args.id
        if not args.force:
            confirm = input(f"Are you sure you want to delete highlight with ID {highlight_id}? (y/N): ")
            if confirm.lower() != "y":
                print("Deletion cancelled.")
                return

        success = dao.delete_highlight(highlight_id)
        if success:
            print(f"Successfully deleted highlight with ID {highlight_id}.")
        else:
            print(f"Failed to delete highlight with ID {highlight_id}.")

    elif hasattr(args, "book") and args.book:
        # Delete highlights for a specific book
        title = args.book
        author = args.author if hasattr(args, "author") else None

        # Get count of highlights to be deleted
        count = dao.get_highlight_count_with_filters(title=title, author=author)

        if count == 0:
            print(f"No highlights found for book '{title}'{f' by {author}' if author else ''}.")
            return

        if not args.force:
            confirm = input(
                f"Are you sure you want to delete {count} highlights for '{title}'"
                f"{f' by {author}' if author else ''}? (y/N): "
            )
            if confirm.lower() != "y":
                print("Deletion cancelled.")
                return

        deleted = dao.delete_highlights_by_book(title, author)
        if deleted > 0:
            print(f"Successfully deleted {deleted} highlights.")
        else:
            print("No highlights were deleted.")

    else:
        print("No delete options specified. Use --id or --book to specify what to delete.")


def _setup_global_options(parser):
    """Set up global options for the CLI."""
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


def _setup_export_command(subparsers):
    """Set up the export command and its options."""
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


def _setup_config_command(subparsers):
    """Set up the config command and its subcommands."""
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


def _setup_history_command(subparsers):
    """Set up the history command and its options."""
    parser_history = subparsers.add_parser("history", help="View export history")
    parser_history.add_argument("--session", type=str, help="Show details for a specific session")
    parser_history.add_argument("--format", type=str, choices=["json", "csv"], help="Output format for history")
    parser_history.add_argument("--details", action="store_true", help="Show detailed session details")
    parser_history.add_argument("--limit", type=int, help="Limit the number of history entries to display")
    parser_history.set_defaults(func=handle_history)


def _setup_highlights_command(subparsers):
    """Set up the highlights command and its subcommands."""
    parser_highlights = subparsers.add_parser("highlights", help="Manage stored highlights")
    highlights_subparsers = parser_highlights.add_subparsers(
        dest="highlights_command", help="Highlight management commands"
    )

    # Highlights list subcommand
    parser_highlights_list = highlights_subparsers.add_parser("list", help="List and search highlights in the database")
    parser_highlights_list.add_argument("--title", type=str, help="Filter by book title (partial match)")
    parser_highlights_list.add_argument("--author", type=str, help="Filter by author (partial match)")
    parser_highlights_list.add_argument("--text", type=str, help="Search in highlight text (partial match)")
    parser_highlights_list.add_argument("--limit", type=int, default=20, help="Maximum number of results (default: 20)")
    parser_highlights_list.add_argument(
        "--offset", type=int, default=0, help="Results offset for pagination (default: 0)"
    )
    parser_highlights_list.add_argument(
        "--sort",
        type=str,
        default="date_exported",
        choices=["date_exported", "date_highlighted", "title", "author"],
        help="Field to sort by (default: date_exported)",
    )
    parser_highlights_list.add_argument(
        "--order", type=str, default="desc", choices=["asc", "desc"], help="Sort direction (default: desc)"
    )
    parser_highlights_list.add_argument(
        "--format", type=str, choices=["text", "json", "csv"], help="Output format (default: text)"
    )

    # Highlights books subcommand
    parser_highlights_books = highlights_subparsers.add_parser("books", help="List all books with highlight counts")
    parser_highlights_books.add_argument(
        "--format", type=str, choices=["text", "json", "csv"], help="Output format (default: text)"
    )

    # Highlights delete subcommand
    parser_highlights_delete = highlights_subparsers.add_parser("delete", help="Delete highlights or books")
    delete_group = parser_highlights_delete.add_mutually_exclusive_group(required=True)
    delete_group.add_argument("--id", type=int, help="Delete a single highlight by ID")
    delete_group.add_argument("--book", type=str, help="Delete all highlights for a specific book")
    parser_highlights_delete.add_argument("--author", type=str, help="Author name (when deleting by book)")
    parser_highlights_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")

    # Set default handler for the main highlights command
    parser_highlights.set_defaults(func=handle_highlights)


def main() -> None:
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Export Kindle clippings ('My Clippings.txt') to Readwise.", prog="kindle2readwise"
    )

    # --- Global Options ---
    _setup_global_options(parser)

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Export Command ---
    _setup_export_command(subparsers)

    # --- Config Command ---
    _setup_config_command(subparsers)

    # --- History Command ---
    _setup_history_command(subparsers)

    # --- Highlights Command ---
    _setup_highlights_command(subparsers)

    # --- Version Command ---
    parser_version = subparsers.add_parser("version", help="Show version information")
    parser_version.set_defaults(func=handle_version)

    # Parse arguments and set up logging
    args = parser.parse_args()

    # Configure logging based on arguments
    # Convert numeric log level back to string name for setup_logging
    level_name = args.log_level  # This already has the name as a string
    setup_logging(level=level_name, log_file=args.log_file)

    # Call the appropriate function
    try:
        args.func(args)
    except Exception as e:
        logger.error("Unhandled exception: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
