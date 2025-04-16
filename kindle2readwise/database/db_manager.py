import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite_utils

from ..parser.models import KindleClipping

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.cwd() / "data" / "kindle2readwise.db"


def generate_highlight_hash(title: str, author: str | None, text: str) -> str:
    """Generate a unique SHA-256 hash for a highlight based on its core content."""
    hash_input = f"{title or ''}|{author or ''}|{text}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


class HighlightsDAO:
    """Data Access Object for managing exported highlights in the SQLite database."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        """Initialize the DAO and ensure the database is set up."""
        # Ensure db_path is a Path object
        self.db_path = Path(db_path) if isinstance(db_path, str) else db_path

        # Special handling for in-memory database (doesn't need directory creation)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure data directory exists
            logger.info("Initializing HighlightsDAO with database at: %s", self.db_path)
        else:
            logger.info("Initializing HighlightsDAO with in-memory database.")

        self.db = sqlite_utils.Database(self.db_path)
        self._initialize_db()
        # Apply migrations after ensuring tables exist
        self._apply_migrations()

    def _initialize_db(self) -> None:
        """Create database tables and indexes if they don't exist."""
        created_tables = []
        if "highlights" not in self.db.table_names():
            logger.debug("Creating 'highlights' table.")
            self.db["highlights"].create(
                {
                    "id": int,
                    "highlight_hash": str,
                    "title": str,
                    "author": str,
                    "text": str,
                    "location": str,
                    "date_highlighted": str,
                    "date_exported": str,
                    "readwise_id": str,
                    "status": str,
                },
                pk="id",
                if_not_exists=True,
            )
            created_tables.append("highlights")

        if "export_sessions" not in self.db.table_names():
            logger.debug("Creating 'export_sessions' table.")
            self.db["export_sessions"].create(
                {
                    "id": int,
                    "start_time": str,
                    "end_time": str,
                    "highlights_total": int,
                    "highlights_new": int,
                    "highlights_dupe": int,
                    "source_file": str,
                    "status": str,
                },
                pk="id",
                if_not_exists=True,
            )
            created_tables.append("export_sessions")

        if created_tables:
            logger.info("Created database tables: %s", ", ".join(created_tables))

        # Create indexes
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Ensure required indexes exist on the tables."""
        indexes_to_create = {
            "highlights": [
                ("idx_highlights_hash", ["highlight_hash"], True),  # Unique index
                ("idx_highlights_export_date", ["date_exported"], False),
                ("idx_highlights_title_author", ["title", "author"], False),
            ],
            "export_sessions": [("idx_export_sessions_start_time", ["start_time"], False)],
        }

        for table_name, indexes in indexes_to_create.items():
            if table_name in self.db.table_names():
                existing_indexes = {idx.name for idx in self.db[table_name].indexes}
                for index_name, columns, unique in indexes:
                    if index_name not in existing_indexes:
                        logger.debug(
                            "Creating index '%s' on table '%s' for columns %s.", index_name, table_name, columns
                        )
                        try:
                            self.db[table_name].create_index(columns, index_name, unique=unique, if_not_exists=True)
                            logger.info("Successfully created index '%s' on table '%s'.", index_name, table_name)
                        except Exception as e:
                            logger.error(
                                "Failed to create index '%s' on table '%s'. Error: %s", index_name, table_name, e
                            )
                    else:
                        logger.debug("Index '%s' already exists on table '%s'.", index_name, table_name)

    def highlight_exists(self, title: str, author: str | None, text: str) -> bool:
        """Check if a highlight with the same content already exists in the database."""
        highlight_hash = generate_highlight_hash(title, author, text)
        logger.debug("Checking existence for highlight hash: %s", highlight_hash)
        exists = self.db["highlights"].count_where("highlight_hash = ?", [highlight_hash]) > 0
        logger.debug("Highlight with hash %s %s.", highlight_hash, "exists" if exists else "does not exist")
        return exists

    def save_highlight(
        self,
        clipping: KindleClipping,
        export_status: str = "success",
        readwise_id: str | None = None,
    ) -> None:
        """Record an exported highlight in the database."""
        highlight_hash = generate_highlight_hash(clipping.title, clipping.author, clipping.content)
        logger.debug("Saving highlight with hash: %s, Status: %s", highlight_hash, export_status)

        record = {
            "highlight_hash": highlight_hash,
            "title": clipping.title,
            "author": clipping.author,
            "text": clipping.content,
            "location": clipping.location,
            "date_highlighted": clipping.date.isoformat() if clipping.date else None,
            "date_exported": datetime.now().isoformat(),
            "readwise_id": readwise_id,
            "status": export_status,
        }

        try:
            # Use upsert to insert or update based on hash
            self.db["highlights"].upsert(record, hash_id="highlight_hash", alter=True)
            logger.info("Successfully saved/updated highlight: Title='%s', Hash=%s", clipping.title, highlight_hash[:8])
        except Exception:
            logger.error(
                "Failed to save highlight: Title='%s', Hash=%s",
                clipping.title,
                highlight_hash[:8],
                exc_info=True,
            )

    def start_export_session(self, source_file: str) -> int:
        """Record the start of an export session and return its ID."""
        logger.info("Starting new export session for file: %s", source_file)
        session_data = {
            "start_time": datetime.now().isoformat(),
            "source_file": source_file,
            "status": "started",
            # Initialize counts to 0 or None
            "highlights_total": 0,
            "highlights_new": 0,
            "highlights_dupe": 0,
        }
        try:
            result = self.db["export_sessions"].insert(session_data)
            session_id = result.last_pk
            logger.info("Export session started with ID: %d", session_id)
            return session_id
        except Exception:
            logger.error("Failed to start export session for file: %s", source_file, exc_info=True)
            raise  # Re-raise the exception as session start is critical

    def complete_export_session(self, session_id: int, stats: dict[str, Any], status: str = "success") -> None:
        """Update an export session record with completion details and statistics."""
        logger.info("Completing export session ID: %d with status: %s", session_id, status)
        logger.debug("Completion stats for session %d: %s", session_id, stats)

        update_data = {
            "end_time": datetime.now().isoformat(),
            "highlights_total": stats.get("total_processed", 0),
            "highlights_new": stats.get("sent", 0),  # Assuming 'sent' corresponds to new
            "highlights_dupe": stats.get("duplicates", 0),
            "status": status,
        }
        try:
            self.db["export_sessions"].update(session_id, update_data)
            logger.info("Successfully completed export session ID: %d", session_id)
        except Exception:
            logger.error("Failed to complete export session ID: %d", session_id, exc_info=True)

    def get_export_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve the most recent export session records."""
        logger.debug("Fetching last %d export session records.", limit)
        try:
            history = list(self.db["export_sessions"].rows_where(order_by="start_time DESC", limit=limit))
            logger.debug("Retrieved %d export history records.", len(history))
            return history
        except Exception:
            logger.error("Failed to retrieve export history.", exc_info=True)
            return []

    # --- Migration Handling ---
    def _apply_migrations(self) -> None:
        """Apply any pending database migrations."""
        logger.debug("Checking for and applying database migrations...")
        # Ensure migrations table exists
        if "_migrations" not in self.db.table_names():
            logger.info("Creating '_migrations' table for tracking schema changes.")
            self.db.create_table(
                "_migrations", {"id": int, "name": str, "applied_at": str}, pk="id", if_not_exists=True
            )

        # Define migrations as a list of tuples: (id, name, function)
        # Add future migrations here. Lambdas are fine for simple sqlite-utils calls.
        migrations: list[tuple[int, str, callable]] = [
            # Future migrations will be added here
        ]

        applied_migration_ids = {row["id"] for row in self.db["_migrations"].rows}
        applied_count = 0

        for mig_id, mig_name, mig_operation in migrations:
            if mig_id not in applied_migration_ids:
                logger.info("Applying migration ID %d: '%s'...", mig_id, mig_name)
                try:
                    # Execute the migration function
                    mig_operation()

                    # Record the migration
                    self.db["_migrations"].insert(
                        {"id": mig_id, "name": mig_name, "applied_at": datetime.now().isoformat()}, pk="id"
                    )
                    logger.info("Successfully applied migration ID %d: '%s'.", mig_id, mig_name)
                    applied_count += 1
                except Exception as e:
                    logger.error("Failed to apply migration ID %d: '%s'. Error: %s", mig_id, mig_name, e, exc_info=True)
                    # Decide on error handling: stop or continue? Currently stopping.
                    raise RuntimeError(f"Migration {mig_id} ('{mig_name}') failed.") from e
            else:
                logger.debug("Migration ID %d: '%s' already applied.", mig_id, mig_name)

        if applied_count > 0:
            logger.info("Applied %d new database migrations.", applied_count)
        else:
            logger.debug("No new database migrations to apply.")

    def close(self) -> None:
        """Close the database connection."""
        if self.db:
            logger.info("Closing database connection to: %s", self.db_path)
            self.db = None  # Allow garbage collection


# Example Usage (for testing or direct script run)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_db_path = Path.cwd() / "data" / "test_kindle2readwise.db"
    if test_db_path.exists():
        test_db_path.unlink()

    dao = HighlightsDAO(db_path=test_db_path)

    # Test highlight check
    print(f"Exists? {dao.highlight_exists('Test Book', 'Test Author', 'This is a test highlight.')}")

    # Test save highlight
    test_clipping = KindleClipping(
        title="Test Book",
        author="Test Author",
        type="highlight",
        location="100-102",
        date=datetime.now(),
        content="This is a test highlight.",
    )
    dao.save_highlight(test_clipping)
    print(f"Exists after save? {dao.highlight_exists('Test Book', 'Test Author', 'This is a test highlight.')}")

    # Test session tracking
    session_id = dao.start_export_session(source_file="test_clippings.txt")
    print(f"Started session ID: {session_id}")
    dao.complete_export_session(session_id, stats={"sent": 5, "duplicates": 2, "total_processed": 7}, status="success")
    print("Completed session.")

    # Test history
    history = dao.get_export_history()
    print("Export History:")
    for session in history:
        print(session)

    dao.close()
    print(f"Test database created/updated at: {test_db_path.resolve()}")

    # Database is kept for manual inspection
