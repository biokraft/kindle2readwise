"""Output formatting utilities for CLI commands."""

import csv
import io
import json
from datetime import datetime

# Constants for UI display formatting
BOOK_TITLE_MAX_LENGTH = 37
BOOK_TITLE_TRUNCATE_LENGTH = 34
BOOK_AUTHOR_MAX_LENGTH = 27
BOOK_AUTHOR_TRUNCATE_LENGTH = 24
TABLE_WIDTH = 82
MAX_SOURCE_FILE_LENGTH = 30
MAX_TITLE_LENGTH = 30
MAX_AUTHOR_LENGTH = 20
MAX_HIGHLIGHTS_PREVIEW = 10


def format_export_summary(stats, clippings_file, dry_run: bool) -> str:
    """Format the export summary for display."""
    output = ["\n--- Export Summary ---"]
    if dry_run:
        output.append("[DRY RUN MODE - No highlights were actually sent to Readwise]")
    output.append(f"Clippings File: {clippings_file}")
    output.append(f"Total Clippings Processed: {stats.total_processed}")
    output.append(f"New Highlights {'Found' if dry_run else 'Sent to Readwise'}: {stats.new_sent}")
    output.append(f"Duplicate Highlights Skipped: {stats.duplicates_skipped}")

    if stats.failed_to_send > 0:
        output.append(f"Highlights Failed to Send: {stats.failed_to_send}")
    elif dry_run:
        output.append("Dry run completed successfully. No actual highlights were sent.")
    else:
        output.append("All new highlights sent successfully!")

    return "\n".join(output)


def format_history_table(history: list[dict]) -> str:
    """Display export history in a formatted table."""
    if not history:
        return "No export history found."

    output = ["\n--- Export History ---"]
    output.append(f"{'ID':<5} {'Date':<20} {'Status':<10} {'Total':<8} {'New':<8} {'Dupes':<8} {'Source File':<30}")
    output.append("-" * 90)

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

        # Format the row
        output.append(
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
    output.append("-" * 90)
    output.append(f"Total Exported: {total_highlights} highlights across {len(history)} sessions")

    return "\n".join(output)


def format_session_details(session: dict) -> str:
    """Format detailed information for a session in text format."""
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

    output = [f"\nSession ID: {session_id}"]
    output.append(f"Start Time: {start_time}")
    output.append(f"End Time: {end_time}")
    output.append(f"Duration: {duration}")
    output.append(f"Status: {status}")
    output.append(f"Source File: {source_file}")
    output.append(f"Highlights Processed: {total}")
    output.append(f"New Highlights: {new}")
    output.append(f"Duplicate Highlights: {dupes}")

    return "\n".join(output)


def format_highlights_text(highlights: list[dict], count: int, limit: int, offset: int) -> str:
    """Format highlights in text format."""
    output = [f"\nFound {count} highlights total"]
    if count > limit:
        output.append(f"Displaying {len(highlights)} highlights (offset: {offset}, limit: {limit})")

    output.append("\n" + "=" * 80)

    # Format each highlight
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

        output.append(f"Title: {title}")
        output.append(f"Author: {author}")
        output.append(f"Location: {location}")
        output.append(f"Date: {date_highlighted}")
        output.append(f"Text: {text}")
        output.append("-" * 80)

    return "\n".join(output)


def format_highlights_json(highlights: list[dict], count: int, limit: int, offset: int) -> str:
    """Format highlights as JSON."""
    result = {"count": count, "limit": limit, "offset": offset, "highlights": highlights}
    return json.dumps(result, indent=2, default=str)


def format_highlights_csv(highlights: list[dict]) -> str:
    """Format highlights as CSV."""
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

    return output.getvalue()


def format_books_text(books: list[dict]) -> str:
    """Format books list as text."""
    output = ["\n--- Books in Database ---"]
    output.append(f"{'Title':<40} {'Author':<30} {'Highlights':<10}")
    output.append("-" * TABLE_WIDTH)

    for book in books:
        title = book.get("title", "Unknown")
        if len(title) > BOOK_TITLE_MAX_LENGTH:
            title = title[:BOOK_TITLE_TRUNCATE_LENGTH] + "..."

        author = book.get("author", "Unknown")
        if len(author) > BOOK_AUTHOR_MAX_LENGTH:
            author = author[:BOOK_AUTHOR_TRUNCATE_LENGTH] + "..."

        count = book.get("highlight_count", 0)

        output.append(f"{title:<40} {author:<30} {count:<10}")

    output.append("-" * TABLE_WIDTH)
    output.append(f"Total: {len(books)} books, {sum(book.get('highlight_count', 0) for book in books)} highlights")

    return "\n".join(output)
