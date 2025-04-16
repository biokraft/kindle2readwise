"""Core functionality for kindle2readwise application."""

import logging
from pathlib import Path

from .database import ExportStats, HighlightsDAO
from .parser import KindleClipping, KindleClippingsParser
from .readwise import ReadwiseAPIClient

logger = logging.getLogger(__name__)


class Kindle2Readwise:
    """Main application class for kindle2readwise."""

    def __init__(self, clippings_file: str, readwise_token: str, db_path: str | None = None):
        """Initialize the application.

        Args:
            clippings_file: Path to the Kindle clippings file
            readwise_token: Readwise API token
            db_path: Path to the SQLite database file (optional)
        """
        self.clippings_file = Path(clippings_file)
        self.parser = KindleClippingsParser(clippings_file)
        self.readwise_client = ReadwiseAPIClient(readwise_token)
        self.db = HighlightsDAO(db_path)

    def validate_setup(self) -> tuple[bool, str]:
        """Validate the application setup.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if clippings file exists
        if not self.clippings_file.exists():
            return False, f"Clippings file not found: {self.clippings_file}"

        # Validate Readwise API token
        if not self.readwise_client.validate_token():
            return False, "Invalid Readwise API token"

        return True, ""

    def process(self) -> ExportStats:
        """Process Kindle clippings and export them to Readwise.

        Returns:
            ExportStats with the results of the export
        """
        logger.info(f"Processing clippings from {self.clippings_file}")

        # Parse clippings file
        clippings = self.parser.parse()
        logger.info(f"Found {len(clippings)} clippings")

        # Initialize stats
        stats = ExportStats(total=len(clippings), new=0, dupe=0)

        # Start export session
        session_id = self.db.start_export_session(str(self.clippings_file))

        # Filter out duplicates
        new_clippings, duplicate_count = self._filter_duplicates(clippings)
        stats.dupe = duplicate_count
        stats.new = len(new_clippings)

        # Export to Readwise if there are new clippings
        if new_clippings:
            logger.info(f"Exporting {len(new_clippings)} new clippings to Readwise")
            result = self.readwise_client.send_highlights(new_clippings)

            # Save successfully exported highlights to database
            if result["sent"] > 0:
                self._save_exported_highlights(new_clippings)

        # Update export session with final stats
        self.db.complete_export_session(session_id, {"total": stats.total, "new": stats.new, "dupe": stats.dupe})

        logger.info(f"Export completed: {stats.total} total, {stats.new} new, {stats.dupe} duplicates")
        return stats

    def _filter_duplicates(self, clippings: list[KindleClipping]) -> tuple[list[KindleClipping], int]:
        """Filter out clippings that have already been exported.

        Args:
            clippings: List of KindleClipping objects

        Returns:
            Tuple of (new_clippings, duplicate_count)
        """
        new_clippings = []
        duplicate_count = 0

        for clipping in clippings:
            # Skip clippings that are not highlights or notes
            if clipping.type not in ["highlight", "note"]:
                continue

            # Check if the highlight already exists in the database
            if self.db.highlight_exists(clipping.title, clipping.author or "", clipping.content):
                duplicate_count += 1
                continue

            new_clippings.append(clipping)

        return new_clippings, duplicate_count

    def _save_exported_highlights(self, clippings: list[KindleClipping]) -> None:
        """Save successfully exported highlights to the database.

        Args:
            clippings: List of KindleClipping objects that were exported
        """
        for clipping in clippings:
            highlight_data = {
                "title": clipping.title,
                "author": clipping.author or "",
                "text": clipping.content,
                "location": clipping.location,
                "date_highlighted": clipping.date.isoformat() if clipping.date else None,
                "readwise_id": None,  # We don't have this information
                "status": "success",
            }

            self.db.save_highlight(highlight_data, "success")
