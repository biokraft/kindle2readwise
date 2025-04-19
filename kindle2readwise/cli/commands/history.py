"""History command handler for the kindle2readwise CLI."""

import csv
import json
import logging
import sys

from ...config import get_config_value
from ...database import DEFAULT_DB_PATH, HighlightsDAO
from ..utils.formatters import (
    MAX_HIGHLIGHTS_PREVIEW,
    format_history_table,
    format_session_details,
)

logger = logging.getLogger(__name__)

# Constants for string truncation
MAX_TITLE_LENGTH = 30
MAX_AUTHOR_LENGTH = 20
TRUNCATION_SUFFIX = "..."


def handle_history(args):
    """Handle the 'history' command to display export history."""
    logger.info("Starting 'history' command.")

    # Get database path from config if not provided
    db_path = get_config_value("database_path", DEFAULT_DB_PATH)

    try:
        # Initialize the DAO
        dao = HighlightsDAO(db_path)

        # Handle specific session details if requested
        if hasattr(args, "session") and args.session:
            _show_session_details(dao, args.session, args.format if hasattr(args, "format") else "text")
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
            # Display the history table
            print(format_history_table(history))

            # Show details if requested
            if hasattr(args, "details") and args.details:
                print("\n--- Detailed Information ---")
                for session in history:
                    print(format_session_details(session))

    except Exception as e:
        logger.error("Error retrieving export history: %s", e, exc_info=True)
        print(f"Error retrieving export history: {e}")
        sys.exit(1)


def _show_session_details(dao: HighlightsDAO, session_id: int, format_type: str = "text"):
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
        session_data = {"session": session, "highlights": highlights}
        print(json.dumps(session_data, indent=2, default=str))
    elif format_type == "csv":
        _output_session_csv(session, highlights)
    else:
        # Text format
        print(format_session_details(session))

        # Show highlight summary if available
        if highlights:
            print(f"\nHighlights in this session: {len(highlights)}")
            print(f"{'Title':<30} {'Author':<20} {'Status':<10}")
            print("-" * 70)

            for h in highlights[:MAX_HIGHLIGHTS_PREVIEW]:  # Show only first few for brevity
                title = h.get("title", "")
                if len(title) > MAX_TITLE_LENGTH:
                    title = title[:27] + TRUNCATION_SUFFIX

                author = h.get("author", "")
                if len(author) > MAX_AUTHOR_LENGTH:
                    author = author[:17] + TRUNCATION_SUFFIX

                print(f"{title:<30} {author:<20} {h.get('status', ''):<10}")

            if len(highlights) > MAX_HIGHLIGHTS_PREVIEW:
                print(f"... and {len(highlights) - MAX_HIGHLIGHTS_PREVIEW} more highlights")


def _output_session_csv(session, highlights):
    """Output session details as CSV."""
    output = _create_csv_writer()
    writer = output["writer"]

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

    print(output["stream"].getvalue())


def _export_history_formatted(history: list[dict], format_type: str):
    """Export history in the specified format (JSON or CSV)."""
    if format_type == "json":
        print(json.dumps(history, indent=2, default=str))
    elif format_type == "csv":
        output = _create_csv_writer()
        writer = output["writer"]

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

        print(output["stream"].getvalue())


def _create_csv_writer():
    """Create a CSV writer with a StringIO stream."""
    import io

    stream = io.StringIO()
    writer = csv.writer(stream)
    return {"stream": stream, "writer": writer}
