import logging
from collections.abc import Generator
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

# Constants for expected values in tests
TOTAL_BOOK_COUNT = 3
BOOK_ONE_HIGHLIGHT_COUNT = 2
BOOK_TWO_HIGHLIGHT_COUNT = 3
ANOTHER_BOOK_HIGHLIGHT_COUNT = 1

TOTAL_HIGHLIGHTS_COUNT = 6
HIGHLIGHTS_WITH_BOOK_TITLE_COUNT = 5
HIGHLIGHTS_WITH_AUTHOR_A_COUNT = 3
HIGHLIGHTS_WITH_TEXT_2_COUNT = 4
HIGHLIGHTS_AFTER_DELETE_COUNT = 5
HIGHLIGHTS_AFTER_BOOK_DELETE_COUNT = 3
HIGHLIGHTS_AFTER_BOOK_WITHOUT_AUTHOR_DELETE_COUNT = 4

MIN_SAMPLE_HIGHLIGHT_COUNT = 3


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """Fixture to provide a temporary, isolated database path for each test."""
    test_db = tmp_path / "test_db.db"
    # Ensure the db file doesn't exist before the test
    if test_db.exists():
        test_db.unlink()
    return test_db


@pytest.fixture
def dao(db_path: Path) -> Generator[HighlightsDAO, None, None]:
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
    # Get the indexes by columns they index
    highlight_indexes = [list(idx.columns) for idx in db["highlights"].indexes]

    # Check if the required indexes exist by their columns
    assert ["highlight_hash"] in highlight_indexes
    assert ["date_exported"] in highlight_indexes
    assert ["title", "author"] in highlight_indexes


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
    assert session_record["status"] == "in_progress"
    assert session_record["start_time"] is not None
    assert session_record["end_time"] is None


def test_complete_export_session(dao: HighlightsDAO):
    """Test completing an export session."""
    # Arrange: Start a session
    source_file = "clippings.txt"
    session_id = dao.start_export_session(source_file)
    initial_record = next(dao.db["export_sessions"].rows_where("id = ?", [session_id]))
    assert initial_record["status"] == "in_progress"
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
    assert history[0]["status"] == "in_progress"
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


# --- Test Phase 5 Features: Enhanced Database Management ---


@pytest.fixture
def populate_sample_highlights(dao: HighlightsDAO) -> list[int]:
    """Fixture to populate the database with sample highlights for testing."""
    sample_data = [
        ("Book One", "Author A", "Highlight 1-1"),
        ("Book One", "Author A", "Highlight 1-2"),
        ("Book Two", "Author B", "Highlight 2-1"),
        ("Book Two", "Author B", "Highlight 2-2"),
        ("Book Two", "Author B", "Highlight 2-3"),
        ("Another Book", "Author A", "Highlight 3-1"),
    ]

    highlight_ids = []

    for title, author, text in sample_data:
        clipping = KindleClipping(
            title=title,
            author=author,
            type="highlight",
            location=f"{len(text)}-{len(text) + 10}",
            date=datetime(2024, 1, 1, 12, 0, 0),
            content=text,
        )
        dao.save_highlight(clipping)

        # Get the ID of the saved highlight
        highlight_hash = generate_highlight_hash(title, author, text)
        rows = list(dao.db["highlights"].rows_where("highlight_hash = ?", [highlight_hash]))
        if rows:
            highlight_ids.append(rows[0]["id"])

    return highlight_ids


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_books(dao: HighlightsDAO):
    """Test listing all books with highlight counts."""
    books = dao.get_books()

    assert len(books) == TOTAL_BOOK_COUNT  # Three unique books

    # Books should be returned in alphabetical order by title
    assert books[0]["title"] == "Another Book"
    assert books[0]["author"] == "Author A"
    assert books[0]["highlight_count"] == ANOTHER_BOOK_HIGHLIGHT_COUNT

    assert books[1]["title"] == "Book One"
    assert books[1]["author"] == "Author A"
    assert books[1]["highlight_count"] == BOOK_ONE_HIGHLIGHT_COUNT

    assert books[2]["title"] == "Book Two"
    assert books[2]["author"] == "Author B"
    assert books[2]["highlight_count"] == BOOK_TWO_HIGHLIGHT_COUNT


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_no_filters(dao: HighlightsDAO):
    """Test retrieving highlights with no filters."""
    highlights = dao.get_highlights()

    assert len(highlights) == TOTAL_HIGHLIGHTS_COUNT  # Total number of sample highlights

    # By default, should be sorted by date_exported in descending order
    # Since they were all added in sequence, the first highlight should have the most recent export date
    first_highlight = highlights[0]
    last_highlight = highlights[-1]
    assert first_highlight["date_exported"] >= last_highlight["date_exported"]


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_with_title_filter(dao: HighlightsDAO):
    """Test retrieving highlights filtered by title."""
    highlights = dao.get_highlights(title="Book*")

    assert len(highlights) == HIGHLIGHTS_WITH_BOOK_TITLE_COUNT  # "Book One" (2) + "Book Two" (3)

    # All should match the title filter
    for h in highlights:
        assert "Book" in h["title"]


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_with_author_filter(dao: HighlightsDAO):
    """Test retrieving highlights filtered by author."""
    highlights = dao.get_highlights(author="Author A")

    assert len(highlights) == HIGHLIGHTS_WITH_AUTHOR_A_COUNT  # "Book One" (2) + "Another Book" (1)

    # All should match the author filter
    for h in highlights:
        assert h["author"] == "Author A"


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_with_text_search(dao: HighlightsDAO):
    """Test retrieving highlights filtered by text content."""
    # When searching for "2", we get any highlight containing "2"
    highlights = dao.get_highlights(text_search="2")

    # Check that we found the right number of highlights
    assert len(highlights) == HIGHLIGHTS_WITH_TEXT_2_COUNT

    # All should match the text filter
    for h in highlights:
        assert "2" in h["text"]

    # Filter with more specific text to get only specific highlight
    specific_highlights = dao.get_highlights(text_search="2-2")
    assert len(specific_highlights) == 1

    for h in specific_highlights:
        assert "2-2" in h["text"]


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_with_multiple_filters(dao: HighlightsDAO):
    """Test retrieving highlights with multiple filters applied."""
    # Using more specific text search to get just one result
    highlights = dao.get_highlights(title="Book One", author="Author A", text_search="1-1")

    assert len(highlights) == 1  # Only "Book One" by "Author A" containing "1-1" matches all filters
    assert highlights[0]["title"] == "Book One"
    assert highlights[0]["author"] == "Author A"
    assert "1-1" in highlights[0]["text"]


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlights_with_sorting(dao: HighlightsDAO):
    """Test retrieving highlights with custom sorting."""
    # Sort by title, ascending order
    highlights = dao.get_highlights(sort_by="title", sort_dir="asc")

    assert len(highlights) == TOTAL_HIGHLIGHTS_COUNT
    assert highlights[0]["title"] <= highlights[-1]["title"]

    # Sort by author, descending order
    highlights = dao.get_highlights(sort_by="author", sort_dir="desc")

    assert len(highlights) == TOTAL_HIGHLIGHTS_COUNT
    assert highlights[0]["author"] >= highlights[-1]["author"]


@pytest.mark.usefixtures("populate_sample_highlights")
def test_get_highlight_count_with_filters(dao: HighlightsDAO):
    """Test counting highlights with filters."""
    # No filters
    assert dao.get_highlight_count_with_filters() == TOTAL_HIGHLIGHTS_COUNT

    # Title filter
    assert dao.get_highlight_count_with_filters(title="Book One") == BOOK_ONE_HIGHLIGHT_COUNT

    # Author filter
    assert dao.get_highlight_count_with_filters(author="Author A") == HIGHLIGHTS_WITH_AUTHOR_A_COUNT

    # Text filter - all highlights containing "1" (should be 4: three with "1-" and one with "3-1")
    assert dao.get_highlight_count_with_filters(text_search="1") == HIGHLIGHTS_WITH_TEXT_2_COUNT

    # Text filter - more specific to get just highlights with "1-1"
    assert dao.get_highlight_count_with_filters(text_search="1-1") == 1

    # Multiple filters - exact title match with text search
    assert dao.get_highlight_count_with_filters(title="Book Two", text_search="2-2") == 1


def test_delete_highlight(dao: HighlightsDAO, populate_sample_highlights):
    """Test deleting a highlight by ID."""
    highlight_ids = populate_sample_highlights
    assert len(highlight_ids) >= MIN_SAMPLE_HIGHLIGHT_COUNT

    # Check that all highlights exist initially
    all_highlights = dao.get_highlights()
    assert len(all_highlights) == TOTAL_HIGHLIGHTS_COUNT

    # Delete a highlight
    highlight_id_to_delete = highlight_ids[0]
    success = dao.delete_highlight(highlight_id_to_delete)

    assert success is True

    # Check that the highlight was deleted
    remaining_highlights = dao.get_highlights()
    assert len(remaining_highlights) == HIGHLIGHTS_AFTER_DELETE_COUNT

    # Make sure the deleted highlight is no longer in the database
    for h in remaining_highlights:
        assert h["id"] != highlight_id_to_delete


@pytest.mark.usefixtures("populate_sample_highlights")
def test_delete_highlights_by_book_with_author(dao: HighlightsDAO):
    """Test deleting all highlights for a specific book with author."""
    # Verify initial state
    assert dao.get_highlight_count_with_filters() == TOTAL_HIGHLIGHTS_COUNT

    # Delete all highlights for a specific book and author
    deleted_count = dao.delete_highlights_by_book("Book Two", "Author B")

    assert deleted_count == BOOK_TWO_HIGHLIGHT_COUNT

    # Check that only the specified book's highlights were deleted
    remaining_highlights = dao.get_highlights()
    assert len(remaining_highlights) == HIGHLIGHTS_AFTER_BOOK_DELETE_COUNT

    # Verify that no highlights for the deleted book remain
    for h in remaining_highlights:
        assert not (h["title"] == "Book Two" and h["author"] == "Author B")

    # Verify that other books' highlights still exist
    assert dao.get_highlight_count_with_filters(title="Book One") == BOOK_ONE_HIGHLIGHT_COUNT
    assert dao.get_highlight_count_with_filters(title="Another Book") == ANOTHER_BOOK_HIGHLIGHT_COUNT


@pytest.mark.usefixtures("populate_sample_highlights")
def test_delete_highlights_by_book_without_author(dao: HighlightsDAO):
    """Test deleting all highlights for a specific book without specifying author."""
    # Delete all highlights for a book title regardless of author
    deleted_count = dao.delete_highlights_by_book("Book One")

    assert deleted_count == BOOK_ONE_HIGHLIGHT_COUNT

    # Check that only the specified book's highlights were deleted
    remaining_highlights = dao.get_highlights()
    assert len(remaining_highlights) == HIGHLIGHTS_AFTER_BOOK_WITHOUT_AUTHOR_DELETE_COUNT

    # Verify that no highlights for the deleted book remain
    for h in remaining_highlights:
        assert h["title"] != "Book One"
