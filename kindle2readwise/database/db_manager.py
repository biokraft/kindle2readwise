import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite_utils

from ..parser.models import KindleClipping
from .models import HighlightFilters

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
        """Create necessary indexes if they don't exist."""
        # For highlights table
        if "highlights" in self.db.table_names():
            self.db["highlights"].create_index(["highlight_hash"], unique=True, if_not_exists=True)
            self.db["highlights"].create_index(["date_exported"], if_not_exists=True)
            self.db["highlights"].create_index(["title", "author"], if_not_exists=True)
            logger.debug("Ensured all required indexes exist on 'highlights' table")

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
        """Record the start of an export session and return the session ID.

        Args:
            source_file: Path to the source clippings file

        Returns:
            ID of the created session
        """
        logger.debug("Starting new export session for source file: %s", source_file)
        session_data = {
            "start_time": datetime.now().isoformat(),
            "source_file": source_file,
            "status": "in_progress",
            "highlights_total": 0,
            "highlights_new": 0,
            "highlights_dupe": 0,
        }

        try:
            last_pk = self.db["export_sessions"].insert(session_data).last_pk
            logger.info("Created export session with ID: %s", last_pk)
            return last_pk
        except Exception as e:
            logger.error("Failed to create export session: %s", e, exc_info=True)
            # Still return a unique ID for recovery
            return hash(datetime.now().isoformat()) % 1000000  # Simple fallback ID

    def complete_export_session(self, session_id: int, stats: dict[str, Any], status: str = "success") -> None:
        """Update an export session with completion details.

        Args:
            session_id: ID of the session to update
            stats: Statistics about the export operation
            status: Status of the export operation
        """
        logger.debug("Completing export session %s with status: %s", session_id, status)
        try:
            self.db["export_sessions"].update(
                session_id,
                {
                    "end_time": datetime.now().isoformat(),
                    "highlights_total": stats.get("total_processed", 0),
                    "highlights_new": stats.get("sent", 0),
                    "highlights_dupe": stats.get("duplicates", 0),
                    "status": status,
                },
            )
            logger.info("Successfully updated export session %s", session_id)
        except Exception as e:
            logger.error("Failed to update export session %s: %s", session_id, e, exc_info=True)

    def get_export_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the history of export sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session records, ordered by start time (most recent first)
        """
        logger.debug("Retrieving export history (limit: %s)", limit)
        try:
            history = list(self.db["export_sessions"].rows_where(order_by="start_time desc", limit=limit))
            logger.debug("Retrieved %s export sessions", len(history))
            return history
        except Exception as e:
            logger.error("Failed to retrieve export history: %s", e, exc_info=True)
            return []

    def get_session_by_id(self, session_id: int) -> dict[str, Any] | None:
        """Get details for a specific export session.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session record or None if not found
        """
        logger.debug("Getting details for session ID: %s", session_id)
        try:
            return self.db["export_sessions"].get(session_id)
        except Exception as e:
            logger.error("Failed to retrieve session %s: %s", session_id, e)
            return None

    def get_highlights_by_session(self, session_id: int) -> list[dict[str, Any]]:
        """Get highlights for a specific export session.

        Args:
            session_id: ID of the export session

        Returns:
            List of highlight records
        """
        # Get the session first to validate it exists
        session = self.get_session_by_id(session_id)
        if not session:
            logger.debug("Session with ID %s not found", session_id)
            return []

        # Get the time range for this session
        start_time = session.get("start_time")
        end_time = session.get("end_time")

        if not start_time or not end_time:
            logger.debug("Session with ID %s has invalid time range", session_id)
            return []

        logger.debug("Finding highlights for session %s (time range: %s to %s)", session_id, start_time, end_time)

        # Find highlights exported in this time range
        try:
            highlights = list(
                self.db["highlights"].rows_where(
                    "date_exported >= ? AND date_exported <= ?", [start_time, end_time], order_by="date_exported"
                )
            )
            logger.debug("Found %d highlights for session %s", len(highlights), session_id)
            return highlights
        except Exception as e:
            logger.error("Error fetching highlights for session %s: %s", session_id, e)
            return []

    def get_books(self) -> list[dict[str, Any]]:
        """Get a list of all books in the database with their highlight counts.

        Returns:
            List of book records with title, author, and highlight count
        """
        logger.debug("Retrieving list of all books")
        try:
            # SQLite query to get distinct books with highlight counts
            query = """
            SELECT title, author, COUNT(*) as highlight_count
            FROM highlights
            GROUP BY title, author
            ORDER BY title
            """
            books = list(self.db.query(query))
            logger.debug("Retrieved %d unique books", len(books))
            return books
        except Exception as e:
            logger.error("Failed to retrieve book list: %s", e, exc_info=True)
            return []

    def get_highlights(  # noqa: PLR0913
        self,
        title: str | None = None,
        author: str | None = None,
        text_search: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "date_exported",
        sort_dir: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get highlights with optional filtering.

        Args:
            title: Filter by book title (partial match)
            author: Filter by author (partial match)
            text_search: Search in highlight text (partial match)
            limit: Maximum number of results to return
            offset: Number of results to skip (for pagination)
            sort_by: Field to sort by (date_exported, date_highlighted, title, author)
            sort_dir: Sort direction (asc, desc)

        Returns:
            List of filtered highlight records
        """
        filters = HighlightFilters(
            title=title,
            author=author,
            text_search=text_search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return self._get_highlights_with_filters(filters)

    def _get_highlights_with_filters(self, filters: HighlightFilters) -> list[dict[str, Any]]:
        """Internal implementation of retrieving highlights with filters.

        Args:
            filters: Filters for highlights

        Returns:
            List of filtered highlight records
        """
        logger.debug(
            "Retrieving highlights with filters: title=%s, author=%s, text_search=%s",
            filters.title,
            filters.author,
            filters.text_search,
        )

        # Build the WHERE clause and parameters
        where_clauses = []
        params = []

        if filters.title:
            # Handle wildcard search with * at the end (commonly used pattern)
            if filters.title.endswith("*"):
                where_clauses.append("title LIKE ?")
                params.append(f"{filters.title[:-1]}%")  # Replace * with SQL wildcard %
            else:
                # Exact match if no wildcard
                where_clauses.append("title = ?")
                params.append(filters.title)

        if filters.author:
            # Exact match for author
            where_clauses.append("author = ?")
            params.append(filters.author)

        if filters.text_search:
            # Exact substring match for text content
            where_clauses.append("text LIKE ?")
            params.append(f"%{filters.text_search}%")

        # Validate sort parameters
        valid_sort_fields = ["date_exported", "date_highlighted", "title", "author"]
        sort_by = filters.sort_by
        if sort_by not in valid_sort_fields:
            sort_by = "date_exported"

        valid_sort_dirs = ["asc", "desc"]
        sort_dir = filters.sort_dir
        if sort_dir.lower() not in valid_sort_dirs:
            sort_dir = "desc"

        order_by = f"{sort_by} {sort_dir}"

        try:
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                logger.debug("SQL where clause: %s, params: %s", where_clause, params)
                highlights = list(
                    self.db["highlights"].rows_where(
                        where_clause, params, order_by=order_by, limit=filters.limit, offset=filters.offset
                    )
                )
            else:
                highlights = list(
                    self.db["highlights"].rows_where(order_by=order_by, limit=filters.limit, offset=filters.offset)
                )

            logger.debug("Retrieved %d highlights", len(highlights))
            return highlights
        except Exception as e:
            logger.error("Failed to retrieve highlights: %s", e, exc_info=True)
            return []

    def get_highlight_count_with_filters(
        self, title: str | None = None, author: str | None = None, text_search: str | None = None
    ) -> int:
        """Get the count of highlights matching the specified filters.

        Args:
            title: Filter by book title (partial match)
            author: Filter by author (partial match)
            text_search: Search in highlight text (partial match)

        Returns:
            Count of matching highlights
        """
        # Build the WHERE clause and parameters
        where_clauses = []
        params = []

        if title:
            # Handle wildcard search with * at the end (commonly used pattern)
            if title.endswith("*"):
                where_clauses.append("title LIKE ?")
                params.append(f"{title[:-1]}%")  # Replace * with SQL wildcard %
            else:
                # Exact match if no wildcard
                where_clauses.append("title = ?")
                params.append(title)

        if author:
            # Exact match for author
            where_clauses.append("author = ?")
            params.append(author)

        if text_search:
            # Exact substring match for text content
            where_clauses.append("text LIKE ?")
            params.append(f"%{text_search}%")

        try:
            if where_clauses:
                where_clause = " AND ".join(where_clauses)
                logger.debug("Count SQL where clause: %s, params: %s", where_clause, params)
                count = self.db["highlights"].count_where(where_clause, params)
            else:
                count = self.db["highlights"].count

            return count
        except Exception as e:
            logger.error("Failed to get highlight count: %s", e, exc_info=True)
            return 0

    def delete_highlight(self, highlight_id: int) -> bool:
        """Delete a highlight by ID.

        Args:
            highlight_id: ID of the highlight to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        logger.debug("Deleting highlight with ID: %s", highlight_id)
        try:
            self.db["highlights"].delete(highlight_id)
            logger.info("Successfully deleted highlight with ID: %s", highlight_id)
            return True
        except Exception as e:
            logger.error("Failed to delete highlight with ID %s: %s", highlight_id, e, exc_info=True)
            return False

    def delete_highlights_by_book(self, title: str, author: str | None = None) -> int:
        """Delete all highlights for a specific book.

        Args:
            title: Book title (exact match)
            author: Book author (exact match, optional)

        Returns:
            Number of deleted highlights
        """
        logger.debug("Deleting highlights for book: '%s' by '%s'", title, author)
        try:
            if author:
                query = "DELETE FROM highlights WHERE title = ? AND author = ?"
                params = [title, author]
            else:
                query = "DELETE FROM highlights WHERE title = ?"
                params = [title]

            result = self.db.execute(query, params)
            affected_rows = result.rowcount if hasattr(result, "rowcount") else 0

            logger.info("Deleted %d highlights for book: '%s'", affected_rows, title)
            return affected_rows
        except Exception as e:
            logger.error("Failed to delete highlights for book '%s': %s", title, e, exc_info=True)
            return 0

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
