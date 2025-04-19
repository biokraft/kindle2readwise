"""Test suite for the reset-db command."""

from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise.cli.commands.reset_db import handle_reset_db
from kindle2readwise.database import HighlightsDAO


@pytest.fixture
def mock_input_reset(monkeypatch):
    """Mock user input to return "RESET" to confirm database reset."""
    monkeypatch.setattr("builtins.input", lambda _: "RESET")


@pytest.fixture
def mock_input_cancel(monkeypatch):
    """Mock user input to return anything but "RESET" to cancel database reset."""
    monkeypatch.setattr("builtins.input", lambda _: "no")


@pytest.fixture
def mock_db_path(tmp_path):
    """Create a mock database file that exists."""
    db_path = tmp_path / "test_db.db"
    db_path.touch()  # Create the empty file
    return db_path


@pytest.fixture
def mock_missing_db_path(tmp_path):
    """Return a path to a non-existent database file."""
    return tmp_path / "nonexistent_db.db"


@pytest.fixture
def mock_args_force():
    """Mock command line arguments with force flag."""
    args = MagicMock()
    args.force = True
    return args


@pytest.fixture
def mock_args_no_force():
    """Mock command line arguments with no force flag."""
    args = MagicMock()
    args.force = False
    return args


@pytest.fixture
def mock_dao_stats():
    """Mock DAO with statistics."""
    mock_dao = MagicMock(spec=HighlightsDAO)
    mock_dao.get_session_count.return_value = 5
    mock_dao.get_highlight_count.return_value = 152
    return mock_dao


def test_reset_db_no_db_file(mock_missing_db_path, mock_args_no_force, capsys):
    """Test reset-db when database file doesn't exist."""
    with patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_missing_db_path):
        handle_reset_db(mock_args_no_force)

    # Check for the expected output message
    captured = capsys.readouterr()
    assert f"No database file found at {mock_missing_db_path}" in captured.out
    assert "Nothing to reset" in captured.out


@pytest.mark.usefixtures("mock_input_reset")
def test_reset_db_with_confirmation(mock_db_path, mock_args_no_force, capsys):
    """Test reset-db with user confirmation."""
    with (
        patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_db_path),
        patch("kindle2readwise.cli.commands.reset_db.HighlightsDAO") as mock_dao_class,
    ):
        # Setup the mock DAO
        mock_dao_instance = mock_dao_class.return_value
        mock_dao_instance.get_session_count.return_value = 5
        mock_dao_instance.get_highlight_count.return_value = 152

        # Call the handler
        handle_reset_db(mock_args_no_force)

    # Verify messages and file handling
    captured = capsys.readouterr()
    assert "WARNING: You are about to reset the application database" in captured.out
    assert "Database reset successfully" in captured.out
    assert not mock_db_path.exists()  # File should be deleted


@pytest.mark.usefixtures("mock_input_cancel")
def test_reset_db_canceled(mock_db_path, mock_args_no_force, capsys):
    """Test reset-db when user cancels the operation."""
    with (
        patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_db_path),
        patch("kindle2readwise.cli.commands.reset_db.HighlightsDAO") as mock_dao_class,
    ):
        # Setup the mock DAO
        mock_dao_instance = mock_dao_class.return_value
        mock_dao_instance.get_session_count.return_value = 5
        mock_dao_instance.get_highlight_count.return_value = 152

        # Call the handler
        handle_reset_db(mock_args_no_force)

    # Verify messages and file handling
    captured = capsys.readouterr()
    assert "WARNING: You are about to reset the application database" in captured.out
    assert "Database reset cancelled" in captured.out
    assert mock_db_path.exists()  # File should still exist


def test_reset_db_with_force(mock_db_path, mock_args_force, capsys):
    """Test reset-db with --force flag to skip confirmation."""
    with (
        patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_db_path),
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Call the handler with force flag
        handle_reset_db(mock_args_force)

    # Verify behavior with force flag
    captured = capsys.readouterr()
    assert "Database reset successfully" in captured.out
    mock_unlink.assert_called_once()  # Check that unlink was called
    # No confirmation prompt should appear
    assert "Are you absolutely sure" not in captured.out


def test_reset_db_error_handling(mock_db_path, mock_args_force, capsys):
    """Test error handling during database reset."""
    with (
        patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_db_path),
        patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")),
        patch("sys.exit") as mock_exit,
    ):
        # Call the handler
        handle_reset_db(mock_args_force)

    # Verify error handling
    captured = capsys.readouterr()
    assert "Error resetting database" in captured.out
    mock_exit.assert_called_once_with(1)  # Should exit with error code


def test_reset_db_dao_creation_after_reset(mock_db_path, mock_args_force):
    """Test that a new DAO is created after database reset."""
    with (
        patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=mock_db_path),
        patch("kindle2readwise.cli.commands.reset_db.HighlightsDAO") as mock_dao_class,
    ):
        # Call the handler
        handle_reset_db(mock_args_force)

    # The DAO should be instantiated twice:
    # 1. When checking stats (this doesn't happen with --force)
    # 2. After resetting to create a fresh database
    # Since we're using --force, it should be called exactly once
    mock_dao_class.assert_called_once_with(mock_db_path)
