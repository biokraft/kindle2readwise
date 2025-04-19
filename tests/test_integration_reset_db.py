from unittest.mock import patch

import pytest
import sqlite_utils

from kindle2readwise.cli.main import main as cli_main
from kindle2readwise.database import HighlightsDAO


def run_cli(args, expect_exit=0):
    """Run the CLI main function with sys.argv patched."""
    with patch("sys.argv", ["kindle2readwise", *args]):
        try:
            cli_main()
            # If we get here and expected a non-zero exit, that's a failure
            if expect_exit != 0:
                pytest.fail(f"Expected SystemExit with code {expect_exit}, but no exit occurred")
        except SystemExit as e:
            # Verify the expected exit code
            if e.code != expect_exit:
                pytest.fail(f"Expected exit code {expect_exit} but got {e.code}")


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database with some data for testing reset operation."""
    db_path = tmp_path / "test_db.db"

    # Create DAO to initialize the database
    dao = HighlightsDAO(db_path)

    # Add some test data
    session_id = dao.start_export_session("test-source.txt")
    dao.complete_export_session(session_id, stats={"total_processed": 5, "sent": 3, "duplicates": 2}, status="success")

    # Verify data was created
    assert dao.get_session_count() > 0

    # Clean up
    dao.close()

    return db_path


@pytest.fixture
def mock_input_reset(monkeypatch):
    """Mock user input to confirm database reset by returning 'RESET'."""
    monkeypatch.setattr("builtins.input", lambda _: "RESET")


@pytest.fixture
def mock_input_cancel(monkeypatch):
    """Mock user input to cancel database reset by returning something other than 'RESET'."""
    monkeypatch.setattr("builtins.input", lambda _: "cancel")


def test_reset_db_with_force(temp_db, capsys):
    """Test reset-db --force command through the CLI entry point."""
    # Verify DB exists and has data before reset
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)
    assert "export_sessions" in db.table_names()
    assert db["export_sessions"].count > 0

    # Make sure config returns our temp DB path
    with patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=temp_db):
        # Run reset command with force flag
        run_cli(["reset-db", "--force"], expect_exit=0)

    # Check console output
    captured = capsys.readouterr()
    assert "Database reset successfully" in captured.out

    # Verify database was reset (it should exist but be empty)
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)

    # Tables should exist in a fresh DB, but be empty
    assert "export_sessions" in db.table_names()
    assert db["export_sessions"].count == 0


@pytest.mark.usefixtures("mock_input_reset")
def test_reset_db_with_confirmation(temp_db, capsys):
    """Test reset-db with interactive confirmation."""
    # Verify DB exists and has data before reset
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)
    initial_count = db["export_sessions"].count
    assert initial_count > 0

    # Make sure config returns our temp DB path
    with patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=temp_db):
        # Run reset command without force flag, but with mocked input to confirm
        run_cli(["reset-db"], expect_exit=0)

    # Check console output
    captured = capsys.readouterr()
    assert "WARNING: You are about to reset the application database" in captured.out
    assert "Database reset successfully" in captured.out

    # Verify database was reset
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)
    assert "export_sessions" in db.table_names()
    assert db["export_sessions"].count == 0


@pytest.mark.usefixtures("mock_input_cancel")
def test_reset_db_cancelled(temp_db, capsys):
    """Test reset-db when user cancels the reset operation."""
    # Verify DB exists and has data before reset
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)
    initial_count = db["export_sessions"].count
    assert initial_count > 0

    # Make sure config returns our temp DB path
    with patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=temp_db):
        # Run reset command without force flag, but with mocked input to cancel
        run_cli(["reset-db"], expect_exit=0)

    # Check console output
    captured = capsys.readouterr()
    assert "WARNING: You are about to reset the application database" in captured.out
    assert "Database reset cancelled" in captured.out

    # Verify database was NOT reset (still has original data)
    assert temp_db.exists()
    db = sqlite_utils.Database(temp_db)
    assert db["export_sessions"].count == initial_count


def test_reset_nonexistent_db(tmp_path, capsys):
    """Test reset-db with a non-existent database file."""
    # Create a path to a non-existent file
    nonexistent_db = tmp_path / "does_not_exist.db"
    assert not nonexistent_db.exists()

    # Make sure config returns our non-existent path
    with patch("kindle2readwise.cli.commands.reset_db.get_config_value", return_value=nonexistent_db):
        # Run reset command
        run_cli(["reset-db"], expect_exit=0)

    # Check console output
    captured = capsys.readouterr()
    assert f"No database file found at {nonexistent_db}" in captured.out
    assert "Nothing to reset" in captured.out
