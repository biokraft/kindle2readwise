import logging
from datetime import datetime
from pathlib import Path

import pytest
import sqlite_utils

from kindle2readwise.database import HighlightsDAO
from kindle2readwise.database.db_manager import generate_highlight_hash
from kindle2readwise.parser.models import KindleClipping

# Configure basic logging for tests
logging.basicConfig(level=logging.DEBUG)

# Constants
SHA256_HEX_LENGTH = 64
DEFAULT_SESSION_COUNT = 3
MIN_EXPECTED_HANDLERS = 2


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture to provide a temporary, isolated database path for each test."""
    test_db = tmp_path / "test_db.db"
    # Ensure the db file doesn't exist before the test
    if test_db.exists():
        test_db.unlink()
    return test_db


@pytest.fixture
def dao(db_path: Path) -> HighlightsDAO:
    """Fixture to provide an initialized HighlightsDAO instance for each test."""
    dao_instance = HighlightsDAO(db_path=db_path)
    yield dao_instance
    # Teardown: close the connection if needed (though sqlite-utils often manages this)
    dao_instance.close()


# --- Test HighlightsDAO Initialization and Schema ---


def test_dao_initialization(db_path: Path):
    """Test that DAO initialization creates the database file and tables."""
    # Create a new instance to test initialization
    HighlightsDAO(db_path=db_path)

    assert db_path.exists()
    db = sqlite_utils.Database(db_path)
    assert "highlights" in db.table_names()
    assert "export_sessions" in db.table_names()
    assert "_migrations" in db.table_names()


def test_dao_indexes(dao: HighlightsDAO):
    """Test that required indexes are created."""
    db = dao.db
    highlights_indexes = {idx.name for idx in db["highlights"].indexes}
    sessions_indexes = {idx.name for idx in db["export_sessions"].indexes}

    assert "idx_highlights_hash" in highlights_indexes
    assert "idx_highlights_export_date" in highlights_indexes
    assert "idx_highlights_title_author" in highlights_indexes
    assert "idx_export_sessions_start_time" in sessions_indexes


# --- Test Core DAO Functionality ---


def test_generate_highlight_hash():
    """Test the hash generation function for consistency."""
    h1 = generate_highlight_hash("Title A", "Author B", "Some text.")
    h2 = generate_highlight_hash("Title A", "Author B", "Some text.")
    h3 = generate_highlight_hash("Title A", "Author B", "Different text.")
    h4 = generate_highlight_hash("Title A", None, "Some text.")

    assert isinstance(h1, str)
    assert len(h1) == SHA256_HEX_LENGTH  # SHA-256 hex digest length
    assert h1 == h2
    assert h1 != h3
    assert h1 != h4


def test_highlight_exists_new(dao: HighlightsDAO):
    """Test highlight_exists returns False for a new highlight."""
    assert not dao.highlight_exists("Book 1", "Author 1", "Content 1")


@pytest.fixture
def sample_clipping() -> KindleClipping:
    return KindleClipping(
        title="Test Book",
        author="Test Author",
        type="highlight",
        location="100-102",
        date=datetime(2024, 1, 1, 12, 0, 0),
        content="This is a test highlight content.",
    )


def test_save_highlight_and_exists(dao: HighlightsDAO, sample_clipping: KindleClipping):
    """Test saving a highlight and then checking its existence."""
    # Arrange: Ensure highlight doesn't exist initially
    assert not dao.highlight_exists(sample_clipping.title, sample_clipping.author, sample_clipping.content)

    # Act: Save the highlight
    dao.save_highlight(sample_clipping, export_status="success")

    # Assert: Highlight should now exist
    assert dao.highlight_exists(sample_clipping.title, sample_clipping.author, sample_clipping.content)

    # Assert: Check database content directly
    db = dao.db
    highlight_hash = generate_highlight_hash(sample_clipping.title, sample_clipping.author, sample_clipping.content)
    rows = list(db["highlights"].rows_where("highlight_hash = ?", [highlight_hash]))
    assert len(rows) == 1
    saved_record = rows[0]
    assert saved_record["title"] == sample_clipping.title
    assert saved_record["author"] == sample_clipping.author
    assert saved_record["text"] == sample_clipping.content
    assert saved_record["location"] == sample_clipping.location
    assert saved_record["date_highlighted"] == sample_clipping.date.isoformat()
    assert saved_record["status"] == "success"
    assert "date_exported" in saved_record
    assert saved_record["date_exported"] is not None


def test_save_highlight_upsert(dao: HighlightsDAO, sample_clipping: KindleClipping):
    """Test that saving the same highlight again updates the record (upsert)."""
    # Arrange: Save highlight first time
    dao.save_highlight(sample_clipping, export_status="initial_success", readwise_id="123")
    db = dao.db
    highlight_hash = generate_highlight_hash(sample_clipping.title, sample_clipping.author, sample_clipping.content)
    initial_rows = list(db["highlights"].rows_where("highlight_hash = ?", [highlight_hash]))
    assert len(initial_rows) == 1
    initial_export_date = initial_rows[0]["date_exported"]

    # Act: Save the same highlight again with different status/metadata
    dao.save_highlight(sample_clipping, export_status="resent_success", readwise_id="456")

    # Assert: Still only one record, but it should be updated
    updated_rows = list(db["highlights"].rows_where("highlight_hash = ?", [highlight_hash]))
    assert len(updated_rows) == 1
    updated_record = updated_rows[0]
    assert updated_record["status"] == "resent_success"
    assert updated_record["readwise_id"] == "456"
    # Ensure date_exported was updated
    assert updated_record["date_exported"] != initial_export_date


# --- Test Export Session Tracking ---


def test_start_export_session(dao: HighlightsDAO):
    """Test starting an export session."""
    source_file = "/path/to/My Clippings.txt"
    session_id = dao.start_export_session(source_file)

    assert isinstance(session_id, int)
    assert session_id > 0

    # Check database content
    db = dao.db
    rows = list(db["export_sessions"].rows_where("id = ?", [session_id]))
    assert len(rows) == 1
    session_record = rows[0]
    assert session_record["source_file"] == source_file
    assert session_record["status"] == "started"
    assert session_record["start_time"] is not None
    assert session_record["end_time"] is None


def test_complete_export_session(dao: HighlightsDAO):
    """Test completing an export session."""
    # Arrange: Start a session
    source_file = "clippings.txt"
    session_id = dao.start_export_session(source_file)
    initial_record = next(dao.db["export_sessions"].rows_where("id = ?", [session_id]))
    assert initial_record["status"] == "started"
    assert initial_record["end_time"] is None

    # Act: Complete the session
    stats = {"total_processed": 10, "sent": 7, "duplicates": 3, "failed": 0}
    dao.complete_export_session(session_id, stats=stats, status="success")

    # Assert: Check updated record
    updated_record = next(dao.db["export_sessions"].rows_where("id = ?", [session_id]))
    assert updated_record["status"] == "success"
    assert updated_record["end_time"] is not None
    assert updated_record["highlights_total"] == stats["total_processed"]
    assert updated_record["highlights_new"] == stats["sent"]
    assert updated_record["highlights_dupe"] == stats["duplicates"]
    # Check start time hasn't changed
    assert updated_record["start_time"] == initial_record["start_time"]


def test_get_export_history(dao: HighlightsDAO):
    """Test retrieving export history."""
    # Arrange: Create a few sessions
    session_id1 = dao.start_export_session("file1.txt")
    dao.complete_export_session(session_id1, stats={"sent": 1}, status="success")

    session_id2 = dao.start_export_session("file2.txt")
    dao.complete_export_session(session_id2, stats={"sent": 5, "duplicates": 2}, status="partial")

    session_id3 = dao.start_export_session("file3.txt")  # Keep this one running

    # Act: Get history (default limit 10)
    history = dao.get_export_history()

    # Assert: Should get 3 records in reverse chronological order (by start_time)
    assert len(history) == DEFAULT_SESSION_COUNT
    assert history[0]["id"] == session_id3
    assert history[1]["id"] == session_id2
    assert history[2]["id"] == session_id1
    assert history[0]["status"] == "started"
    assert history[1]["status"] == "partial"
    assert history[2]["status"] == "success"

    # Test limit
    limited_history = dao.get_export_history(limit=1)
    assert len(limited_history) == 1
    assert limited_history[0]["id"] == session_id3


# --- Test Migration Handling (Basic) ---


def test_apply_migrations_runs(dao: HighlightsDAO):
    """Test that the migration logic runs without errors (no actual migrations defined yet)."""
    # The fixture already calls _initialize_db and _apply_migrations
    # We just need to assert that the _migrations table exists
    db = dao.db
    assert "_migrations" in db.table_names()
    # Check columns
    migration_cols = db["_migrations"].columns_dict
    assert "id" in migration_cols
    assert "name" in migration_cols
    assert "applied_at" in migration_cols
    # Check no migrations were recorded (as none are defined)
    assert db["_migrations"].count == 0
