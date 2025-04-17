"""Database access layer for kindle2readwise using sqlite-utils."""

import hashlib
import logging
from datetime import datetime
from pathlib import Path

# Type checking imports
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from sqlite_utils import Database

logger = logging.getLogger(__name__)


class HighlightsDAO:
    """Data Access Object for managing Kindle highlights database."""

    def __init__(self, db_path: str | None = None):
        """Initialize DAO with database path.

        Args:
            db_path: Path to the SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Use default location in user data directory
            data_dir = Path.home() / ".kindle2readwise"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "highlights.db")

        self.db_path = db_path
        self.db = Database(self.db_path)
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize database tables and apply any pending migrations."""
        logger.debug(f"Initializing database at {self.db_path}")
        self._create_tables_if_not_exist()
        self._apply_migrations()

    def _create_tables_if_not_exist(self) -> None:
        """Create database tables and indexes if they don't exist."""
        # Create highlights table
        if "highlights" not in self.db.table_names():
            logger.info("Creating highlights table")
            self.db.create_table(
                "highlights",
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
            )

            # Create indexes
            self.db["highlights"].create_index(["highlight_hash"], unique=True)
            self.db["highlights"].create_index(["date_exported"])
            self.db["highlights"].create_index(["title", "author"])

        # Create export_sessions table
        if "export_sessions" not in self.db.table_names():
            logger.info("Creating export_sessions table")
            self.db.create_table(
                "export_sessions",
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
            )

    def _apply_migrations(self) -> None:
        """Apply any pending migrations using sqlite-utils capabilities."""
        # Ensure migrations table exists
        if "_migrations" not in self.db.table_names():
            logger.info("Creating _migrations table")
            self.db.create_table("_migrations", {"id": int, "name": str, "applied": str}, pk="id")

        # Define migrations as (id, name, function) tuples
        # Each migration should be a function that uses sqlite-utils methods
        migrations: list[tuple[int, str, Callable[[], None]]] = []

        # Apply any pending migrations
        for id, name, operation in migrations:
            if not self.db["_migrations"].count_where("id = ?", [id]):
                logger.info(f"Applying migration {id}: {name}")
                try:
                    operation()
                    self.db["_migrations"].insert({"id": id, "name": name, "applied": datetime.now().isoformat()})
                    logger.info(f"Migration {id} applied successfully")
                except Exception as e:
                    logger.error(f"Migration {id} failed: {e}")
                    raise

    def highlight_exists(self, title: str, author: str, text: str) -> bool:
        """Check if a highlight has already been exported.

        Args:
            title: Book title
            author: Book author
            text: Highlight text

        Returns:
            True if the highlight exists in the database, False otherwise
        """
        highlight_hash = self._generate_hash(title, author, text)
        return self.db["highlights"].count_where("highlight_hash = ?", [highlight_hash]) > 0

    def _generate_hash(self, title: str, author: str, text: str) -> str:
        """Generate a unique hash for a highlight.

        Args:
            title: Book title
            author: Book author
            text: Highlight text

        Returns:
            MD5 hash of the highlight
        """
        content = f"{title}|{author}|{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def save_highlight(self, highlight_data: dict[str, Any], export_status: str) -> int:
        """Save a highlight to the database.

        Args:
            highlight_data: Dictionary containing highlight data
            export_status: Status of the export operation ('success', 'error', etc.)

        Returns:
            ID of the inserted highlight
        """
        # Ensure highlight hash is generated
        if "highlight_hash" not in highlight_data:
            highlight_data["highlight_hash"] = self._generate_hash(
                highlight_data["title"], highlight_data["author"], highlight_data["text"]
            )

        # Add export status and timestamp
        highlight_data["status"] = export_status
        highlight_data["date_exported"] = datetime.now().isoformat()

        # Insert or replace the highlight
        return self.db["highlights"].insert(highlight_data).last_pk

    def start_export_session(self, source_file: str) -> int:
        """Start a new export session.

        Args:
            source_file: Path to the source clippings file

        Returns:
            ID of the created session
        """
        session_data = {
            "start_time": datetime.now().isoformat(),
            "source_file": source_file,
            "status": "in_progress",
            "highlights_total": 0,
            "highlights_new": 0,
            "highlights_dupe": 0,
        }
        return self.db["export_sessions"].insert(session_data).last_pk

    def complete_export_session(self, session_id: int, stats: dict[str, int], status: str = "completed") -> None:
        """Complete an export session with results.

        Args:
            session_id: ID of the export session
            stats: Dictionary with export statistics
            status: Session status (completed, error, partial)
        """
        self.db["export_sessions"].update(
            session_id,
            {
                "end_time": datetime.now().isoformat(),
                "highlights_total": stats.get("total", 0),
                "highlights_new": stats.get("new", 0),
                "highlights_dupe": stats.get("dupe", 0),
                "status": status,
            },
        )

    def get_export_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent export sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of export session records
        """
        return list(self.db["export_sessions"].rows_where(order_by="start_time desc", limit=limit))

    def get_session_by_id(self, session_id: int) -> dict[str, Any] | None:
        """Get a specific export session by ID.

        Args:
            session_id: ID of the export session

        Returns:
            Session record or None if not found
        """
        try:
            return dict(self.db["export_sessions"].get(session_id))
        except Exception:
            logger.debug(f"Session with ID {session_id} not found")
            return None

    def get_highlights_by_session(self, session_id: int) -> list[dict[str, Any]]:
        """Get highlights for a specific export session.

        Args:
            session_id: ID of the export session

        Returns:
            List of highlight records
        """
        # Get the session first to check if it exists
        session = self.get_session_by_id(session_id)
        if not session:
            return []

        # Find start and end times for the session
        start_time = session.get("start_time")
        end_time = session.get("end_time")

        if not start_time or not end_time:
            return []

        # Get highlights exported during this session's timeframe
        return list(
            self.db["highlights"].rows_where(
                "date_exported >= ? AND date_exported <= ?",
                [start_time, end_time],
                order_by="date_exported",
            )
        )

    def get_highlight_count(self) -> int:
        """Get the total number of highlights in the database.

        Returns:
            Count of highlights
        """
        return self.db["highlights"].count

    def get_highlights_by_book(self, title: str, author: str | None = None) -> list[dict[str, Any]]:
        """Get highlights for a specific book.

        Args:
            title: Book title
            author: Optional book author

        Returns:
            List of highlight records
        """
        if author:
            return list(
                self.db["highlights"].rows_where(
                    "title = ? AND author = ?", [title, author], order_by="date_highlighted"
                )
            )
        return list(self.db["highlights"].rows_where("title = ?", [title], order_by="date_highlighted"))
