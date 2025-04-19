"""Highlights command handler for the kindle2readwise CLI."""

import json
import logging
import sys

from ...config import get_config_value
from ...database import DEFAULT_DB_PATH, HighlightsDAO
from ..utils.formatters import (
    format_books_text,
    format_highlights_csv,
    format_highlights_json,
    format_highlights_text,
)

logger = logging.getLogger(__name__)


def handle_highlights(args):
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


def _handle_highlights_list(dao: HighlightsDAO, args):
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
        print(format_highlights_json(highlights, count, limit, offset))
    elif output_format == "csv":
        print(format_highlights_csv(highlights))
    else:
        print(format_highlights_text(highlights, count, limit, offset))


def _handle_highlights_books(dao: HighlightsDAO, args):
    """Handle displaying all books with highlight counts."""
    books = dao.get_books()

    # Format output based on requested format
    format_type = getattr(args, "format", "text")
    if format_type == "json":
        print(json.dumps(books, indent=2))
        return
    if format_type == "csv":
        import csv
        import sys

        writer = csv.DictWriter(sys.stdout, fieldnames=["title", "author", "highlight_count"])
        writer.writeheader()
        writer.writerows(books)
        return

    # Default text output
    print(format_books_text(books))


def _handle_highlights_delete(dao: HighlightsDAO, args):
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
