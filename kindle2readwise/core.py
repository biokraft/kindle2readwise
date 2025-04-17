"""Core functionality for kindle2readwise application."""

import logging

# Define a simple structure for results (can be expanded)
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Use TYPE_CHECKING to avoid circular imports for type hints if models grow complex
# Use the DAO and default path from the database module
from .database import DEFAULT_DB_PATH, HighlightsDAO
from .parser import KindleClipping, KindleClippingsParser
from .readwise import ReadwiseAPIClient

logger = logging.getLogger(__name__)


@dataclass
class ExportStats:
    """Statistics for an export session."""

    total_processed: int = 0
    new_sent: int = 0
    duplicates_skipped: int = 0
    failed_to_send: int = 0


class Kindle2Readwise:
    """Main application class for kindle2readwise."""

    def __init__(self, clippings_file: str, readwise_token: str, db_path: Path | None = None, dry_run: bool = False):
        """Initialize the application."""
        self.clippings_file = Path(clippings_file)
        # Use default DB path if none provided
        self.db_path = db_path if db_path else DEFAULT_DB_PATH
        logger.info("Using database at: %s", self.db_path)
        self.dry_run = dry_run

        # Initialize components
        self.parser = KindleClippingsParser(clippings_file)
        self.readwise_client = ReadwiseAPIClient(readwise_token)
        self.db = HighlightsDAO(self.db_path)  # Pass the Path object
        logger.info("Kindle2Readwise initialized. Dry run mode: %s", self.dry_run)

    def validate_setup(self) -> tuple[bool, str]:
        """Validate the application setup (file existence, API token)."""
        logger.info("Validating setup...")
        # Check if clippings file exists
        if not self.clippings_file.exists():
            msg = f"Clippings file not found: {self.clippings_file}"
            logger.error(msg)
            return False, msg
        logger.debug("Clippings file found: %s", self.clippings_file)

        # Skip Readwise API token validation in dry-run mode
        if self.dry_run:
            logger.info("Dry run mode active - skipping Readwise API token validation.")
            return True, "Setup validated successfully (token validation skipped in dry-run mode)."

        # Validate Readwise API token
        if not self.readwise_client.validate_token():
            msg = "Invalid Readwise API token."
            logger.error(msg)
            return False, msg
        logger.debug("Readwise API token validated successfully.")

        logger.info("Setup validation successful.")
        return True, "Setup validated successfully."

    def process(self) -> ExportStats:
        """Process Kindle clippings and export them to Readwise."""
        logger.info("Starting processing for clippings file: %s", self.clippings_file)
        if self.dry_run:
            logger.info("DRY RUN MODE: No highlights will be sent to Readwise.")
        start_time = datetime.now()

        # Start export session tracking in the database - only if not in dry-run mode
        session_id = None
        if not self.dry_run:
            session_id = self.db.start_export_session(str(self.clippings_file))

        stats = ExportStats()
        session_status = "success"  # Assume success initially
        status_ref = [session_status]  # Use a list to reference the status

        try:
            # Parse and filter clippings
            all_clippings = self.parser.parse()
            stats.total_processed = len(all_clippings)
            logger.info("Parsed %d total clippings.", stats.total_processed)

            # Process clippings and update stats
            self._process_clippings(all_clippings, stats, status_ref)
            session_status = status_ref[0]  # Get updated status after processing
        except Exception:
            logger.error("An error occurred during processing.", exc_info=True)
            session_status = "error"
            # Ensure stats reflect the failure state if possible
            stats.failed_to_send = len(all_clippings) if "all_clippings" in locals() else stats.total_processed
            stats.new_sent = 0
        finally:
            self._complete_process(session_id, stats, session_status, start_time)

        return stats

    def _process_clippings(
        self, all_clippings: list[KindleClipping], stats: ExportStats, status_ref: list[str]
    ) -> None:
        """Process filtered clippings and update the stats."""
        # Filter out duplicates using the database
        new_clippings, duplicate_count = self._filter_duplicates(all_clippings)
        stats.duplicates_skipped = duplicate_count
        stats.new_sent = len(new_clippings)  # Initialize with the count after filtering
        logger.info(
            "Found %d new clippings after checking %d duplicates.",
            len(new_clippings),
            stats.duplicates_skipped,
        )

        # Export new clippings to Readwise if any exist
        if new_clippings:
            if self.dry_run:
                self._handle_dry_run_export(new_clippings, stats)
            else:
                self._handle_real_export(new_clippings, stats, status_ref)
        else:
            logger.info("No new clippings to export.")
            stats.new_sent = 0

    def _handle_dry_run_export(self, new_clippings: list[KindleClipping], stats: ExportStats) -> None:
        """Handle export in dry run mode."""
        logger.info(
            "DRY RUN: Would have sent %d new clippings to Readwise. Skipping actual API call.",
            len(new_clippings),
        )
        # In dry run mode, we assume all highlights would have been sent successfully
        stats.new_sent = len(new_clippings)
        stats.failed_to_send = 0

    def _handle_real_export(
        self, new_clippings: list[KindleClipping], stats: ExportStats, status_ref: list[str]
    ) -> None:
        """Handle real export to Readwise."""
        logger.info("Attempting to export %d new clippings to Readwise...", len(new_clippings))
        export_result = self.readwise_client.send_highlights(new_clippings)
        # Update based on what was actually sent
        sent_count = export_result.get("sent", 0)
        stats.new_sent = sent_count  # This will be the actual number successfully sent
        stats.failed_to_send = export_result.get("failed", 0)
        logger.info("Readwise export result: Sent=%d, Failed=%d", stats.new_sent, stats.failed_to_send)

        if stats.failed_to_send > 0:
            # Mark as partial success if some failed
            status_ref[0] = "partial"  # Update the status by reference
            logger.warning("%d highlights failed to send to Readwise.", stats.failed_to_send)

        # Save successfully exported highlights to the database
        # We assume Readwise API handles its own duplicates, so we save all *sent* ones.
        # Filter the *original* new_clippings list based on which ones were successfully sent.
        # NOTE: Readwise API currently doesn't return IDs of successful highlights easily in bulk.
        # For now, assume all `sent` were the first ones in the batch and save them.
        # A more robust approach would need individual success tracking if the API supported it.
        successfully_sent_clippings = new_clippings[:sent_count]
        if successfully_sent_clippings:
            self._save_exported_highlights(successfully_sent_clippings)

    def _complete_process(
        self, session_id: int | None, stats: ExportStats, session_status: str, start_time: datetime
    ) -> None:
        """Complete the process and log results."""
        # Complete the export session tracking - only if not in dry-run mode
        if not self.dry_run and session_id is not None:
            final_stats_dict = {
                "total_processed": stats.total_processed,
                "sent": stats.new_sent,
                "duplicates": stats.duplicates_skipped,
                "failed": stats.failed_to_send,
                # Add other relevant stats if needed
            }
            self.db.complete_export_session(session_id, stats=final_stats_dict, status=session_status)

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(
            "Processing finished in %.2f seconds. Status: %s. Results: %s",
            duration.total_seconds(),
            "dry_run" if self.dry_run else session_status,
            stats,
        )

    def _filter_duplicates(self, clippings: list[KindleClipping]) -> tuple[list[KindleClipping], int]:
        """Filter out clippings that already exist in the database."""
        logger.debug("Filtering %d clippings for duplicates...", len(clippings))
        new_clippings = []
        duplicate_count = 0

        for clipping in clippings:
            # Basic check: ignore clippings without content, though parser might already do this
            if not clipping.content:
                logger.debug(
                    "Skipping clipping with no content: Title='%s', Loc='%s'", clipping.title, clipping.location
                )
                continue

            # Check database for duplicates based on hash
            if self.db.highlight_exists(clipping.title, clipping.author or "", clipping.content):
                logger.debug("Duplicate found: Title='%s', Loc='%s'", clipping.title, clipping.location)
                duplicate_count += 1
            else:
                # Only add non-duplicates to the list to be sent
                new_clippings.append(clipping)

        logger.debug("Filtering complete. Found %d duplicates.", duplicate_count)
        return new_clippings, duplicate_count

    def _save_exported_highlights(self, successfully_sent_clippings: list[KindleClipping]) -> None:
        """Save successfully exported highlights to the database."""
        if not successfully_sent_clippings:
            return

        logger.info("Saving %d successfully exported highlights to the database...", len(successfully_sent_clippings))
        saved_count = 0
        for clipping in successfully_sent_clippings:
            try:
                # Pass the whole KindleClipping object to the DAO method
                self.db.save_highlight(clipping, export_status="success")
                saved_count += 1
            except Exception:
                # Log error but continue saving others if possible
                logger.error(
                    "Failed to save exported highlight to DB: Title='%s', Loc='%s'",
                    clipping.title,
                    clipping.location,
                    exc_info=True,
                )
        logger.info("Finished saving %d highlights to the database.", saved_count)

    def close_db(self) -> None:
        """Close the database connection explicitly if needed."""
        if self.db:
            self.db.close()
