"""Reset database command handler for the kindle2readwise CLI."""

import logging
import sys
from pathlib import Path

from ...config import get_config_value
from ...database import DEFAULT_DB_PATH, HighlightsDAO

logger = logging.getLogger(__name__)


def handle_reset_db(args):
    """Handle the 'reset-db' command to reset the application database.

    This command deletes all export history and tracking data from the database.
    It requires explicit confirmation from the user unless the --force flag is used.
    """
    logger.info("Starting 'reset-db' command.")

    # Get database path from config
    db_path = get_config_value("database_path", DEFAULT_DB_PATH)
    db_path = Path(db_path)

    # Check if the database file exists
    if not db_path.exists():
        print(f"No database file found at {db_path}. Nothing to reset.")
        return

    # If not forcing, get confirmation from the user
    if not args.force:
        # First, get some database statistics to show what will be deleted
        dao = HighlightsDAO(db_path)

        # Get stats about what will be deleted
        try:
            stats = {"sessions": dao.get_session_count() or 0, "highlights": dao.get_highlight_count() or 0}
        except Exception as e:
            logger.error("Error getting database statistics: %s", e, exc_info=True)
            stats = {"sessions": "?", "highlights": "?"}

        # Show warning with confirmation prompt
        print("\n" + "=" * 80)
        print("WARNING: You are about to reset the application database.")
        print("This will permanently delete all export history and tracking information.")
        print("=" * 80 + "\n")

        print("The following data will be deleted:")
        print(f"- Export history ({stats['sessions']} sessions)")
        print(f"- Highlight tracking data ({stats['highlights']} entries)")
        print("- Cached highlight information")
        print("\nThis action cannot be undone.")

        # Ask for explicit confirmation
        confirmation = input('\nType "RESET" to confirm database reset: ')

        if confirmation != "RESET":
            print("Database reset cancelled.")
            return
    else:
        logger.info("Forced database reset requested. Skipping confirmation.")

    # Perform the database reset
    try:
        # Delete the database file
        db_path.unlink()
        logger.info("Successfully deleted database at %s", db_path)

        # Create a fresh, empty database
        HighlightsDAO(db_path)

        print("\nDatabase reset successfully. All history and tracking data has been removed.")
    except Exception as e:
        logger.error("Error resetting database: %s", e, exc_info=True)
        print(f"Error resetting database: {e}")
        sys.exit(1)
