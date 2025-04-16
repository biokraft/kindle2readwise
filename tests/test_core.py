"""Tests for the core kindle2readwise functionality."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise.core import Kindle2Readwise
from kindle2readwise.parser import KindleClipping

# Constants to replace magic numbers
TOTAL_CLIPPINGS = 3
CLIPPINGS_NEW = 3
CLIPPINGS_DUPE = 0
TWO_CLIPPINGS = 2
ONE_CLIPPING = 1


@pytest.fixture
def sample_clippings():
    """Fixture providing sample Kindle clippings."""
    return [
        KindleClipping(
            title="Test Book",
            author="Test Author",
            type="highlight",
            location="123-124",
            date=datetime(2025, 4, 15, 22, 16, 21),
            content="This is a test highlight",
        ),
        KindleClipping(
            title="Test Book",
            author="Test Author",
            type="note",
            location="125",
            date=datetime(2025, 4, 15, 22, 17, 30),
            content="This is a test note",
        ),
        KindleClipping(
            title="Another Book",
            author="Another Author",
            type="highlight",
            location="456-457",
            date=datetime(2025, 4, 16, 10, 30, 0),
            content="This is another test highlight",
        ),
    ]


@pytest.fixture
def mock_app(sample_clippings):
    """Fixture providing a mocked Kindle2Readwise app."""
    # Create actual mocks instead of patching
    mock_parser = MagicMock()
    mock_parser.parse.return_value = sample_clippings

    mock_client = MagicMock()
    mock_client.validate_token.return_value = True
    mock_client.send_highlights.return_value = {"sent": len(sample_clippings), "failed": 0}

    mock_dao = MagicMock()
    mock_dao.highlight_exists.return_value = False
    mock_dao.start_export_session.return_value = 1

    # Create a Kindle2Readwise instance but replace its components with mocks
    with patch("pathlib.Path.exists", return_value=True):
        app = Kindle2Readwise(clippings_file="test_clippings.txt", readwise_token="test_token", db_path=":memory:")

    # Replace the real components with mocks
    app.parser = mock_parser
    app.readwise_client = mock_client
    app.db = mock_dao

    # Mock the _filter_duplicates method to simplify testing
    original_filter_duplicates = app._filter_duplicates

    def mocked_filter_duplicates(clippings):
        """Mocked version that respects the mock DAO's highlight_exists."""
        new_clippings = []
        duplicate_count = 0

        for clipping in clippings:
            if app.db.highlight_exists(clipping.title, clipping.author or "", clipping.content):
                duplicate_count += 1
            else:
                new_clippings.append(clipping)

        return new_clippings, duplicate_count

    app._filter_duplicates = mocked_filter_duplicates

    yield app, mock_parser, mock_client, mock_dao

    # Restore original method
    app._filter_duplicates = original_filter_duplicates


@patch("pathlib.Path.exists", return_value=True)
def test_validate_setup_success(mock_path_exists, mock_app):  # noqa: ARG001
    """Test successful validation of setup."""
    app, _, client_mock, _ = mock_app

    # Ensure the client returns True for token validation
    client_mock.validate_token.return_value = True

    is_valid, error = app.validate_setup()

    assert is_valid is True
    assert error == ""


@patch("pathlib.Path.exists", return_value=False)
def test_validate_setup_missing_file(mock_path_exists, mock_app):  # noqa: ARG001
    """Test validation with missing clippings file."""
    app, _, _, _ = mock_app

    is_valid, error = app.validate_setup()

    assert is_valid is False
    assert "not found" in error


@patch("pathlib.Path.exists", return_value=True)
def test_validate_setup_invalid_token(mock_path_exists, mock_app):  # noqa: ARG001
    """Test validation with invalid token."""
    app, _, client_mock, _ = mock_app

    # Configure token validation to fail
    client_mock.validate_token.return_value = False

    is_valid, error = app.validate_setup()

    assert is_valid is False
    assert "Invalid Readwise API token" in error


def test_process_new_highlights(mock_app):
    """Test processing new highlights."""
    app, parser_mock, client_mock, dao_mock = mock_app

    # Configure DAO to indicate no duplicates
    dao_mock.highlight_exists.return_value = False

    stats = app.process()

    # Verify the results
    assert stats.total == TOTAL_CLIPPINGS
    assert stats.new == CLIPPINGS_NEW
    assert stats.dupe == CLIPPINGS_DUPE

    # Verify parser was called
    parser_mock.parse.assert_called_once()

    # Verify client was called with all highlights
    client_mock.send_highlights.assert_called_once()

    # Verify DAO was called to save highlights
    assert dao_mock.save_highlight.call_count == TOTAL_CLIPPINGS

    # Verify export session was created and completed
    dao_mock.start_export_session.assert_called_once()
    dao_mock.complete_export_session.assert_called_once()


def test_process_duplicate_highlights(mock_app):
    """Test processing with duplicate highlights."""
    app, parser_mock, client_mock, dao_mock = mock_app

    # Configure DAO to indicate all highlights are duplicates
    dao_mock.highlight_exists.return_value = True

    stats = app.process()

    # Verify the results
    assert stats.total == TOTAL_CLIPPINGS
    assert stats.new == CLIPPINGS_DUPE
    assert stats.dupe == TOTAL_CLIPPINGS

    # Verify parser was called
    parser_mock.parse.assert_called_once()

    # Verify client was not called since all highlights are duplicates
    client_mock.send_highlights.assert_not_called()

    # Verify no highlights were saved
    dao_mock.save_highlight.assert_not_called()

    # Verify export session was created and completed
    dao_mock.start_export_session.assert_called_once()
    dao_mock.complete_export_session.assert_called_once()


def test_process_mixed_highlights(mock_app):
    """Test processing with mix of new and duplicate highlights."""
    app, parser_mock, client_mock, dao_mock = mock_app

    # Configure DAO to indicate some duplicates
    # First highlight is a duplicate, others are new
    dao_mock.highlight_exists.side_effect = [True, False, False]

    stats = app.process()

    # Verify the results
    assert stats.total == TOTAL_CLIPPINGS
    assert stats.new == TWO_CLIPPINGS
    assert stats.dupe == ONE_CLIPPING

    # Verify parser was called
    parser_mock.parse.assert_called_once()

    # Verify client was called with new highlights
    client_mock.send_highlights.assert_called_once()
    assert len(client_mock.send_highlights.call_args[0][0]) == TWO_CLIPPINGS

    # Verify new highlights were saved
    assert dao_mock.save_highlight.call_count == TWO_CLIPPINGS

    # Verify export session was created and completed
    dao_mock.start_export_session.assert_called_once()
    dao_mock.complete_export_session.assert_called_once()

    # Verify the sent stats match what's passed to complete_export_session
    exported_stats = dao_mock.complete_export_session.call_args[0][1]
    assert exported_stats["total"] == TOTAL_CLIPPINGS
    assert exported_stats["new"] == TWO_CLIPPINGS
    assert exported_stats["dupe"] == ONE_CLIPPING
