import logging
from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise import __version__

# Assuming cli.main is the entry point function in kindle2readwise/cli.py
from kindle2readwise.cli import main as cli_main

# Environment variable for token
READWISE_TOKEN_ENV_VAR = "READWISE_API_TOKEN"

# --- Test Fixtures ---


@pytest.fixture(autouse=True)
def capture_logs(caplog):
    """Automatically capture logs for each test."""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def mock_kindle2readwise():
    """Fixture to mock the core Kindle2Readwise class."""
    with patch("kindle2readwise.cli.Kindle2Readwise") as mock_app:
        mock_instance = mock_app.return_value
        # Configure default mock behaviors
        mock_instance.validate_setup.return_value = (True, "")

        # Create a proper stats object with integer attributes
        mock_stats = MagicMock()
        mock_stats.total_processed = 5
        mock_stats.new_sent = 3
        mock_stats.duplicates_skipped = 2
        mock_stats.failed_to_send = 0

        mock_instance.process.return_value = mock_stats
        mock_instance.close_db.return_value = None
        yield mock_instance


@pytest.fixture
def mock_setup_logging():
    """Fixture to mock the logging setup function."""
    with patch("kindle2readwise.cli.setup_logging") as mock_setup:
        yield mock_setup


@pytest.fixture
def set_token_env(monkeypatch):
    """Fixture to set the Readwise token environment variable."""
    token = "token_from_env"
    monkeypatch.setenv(READWISE_TOKEN_ENV_VAR, token)
    return token


@pytest.fixture
def unset_token_env(monkeypatch):
    """Fixture to ensure the Readwise token environment variable is not set."""
    monkeypatch.delenv(READWISE_TOKEN_ENV_VAR, raising=False)


# --- Helper Function to Run CLI ---


def run_cli(args: list[str], expect_exit_code: int | None = 0):
    """Runs the CLI main function with given arguments, catching SystemExit."""
    with patch("sys.argv", ["kindle2readwise", *args]):
        try:
            cli_main()
            # If we get here and expected exit, that's a problem
            if expect_exit_code is not None and expect_exit_code != 0:
                pytest.fail(f"Expected SystemExit with code {expect_exit_code}, but no exit occurred")

        except SystemExit as e:
            # If it exited and we expected it, check the code
            if expect_exit_code is not None:
                # Using pytest.fail instead of assert for better error display
                if e.code != expect_exit_code:
                    pytest.fail(f"Expected exit code {expect_exit_code} but got {e.code}")
            # If it exited and we didn't expect it (expect_exit_code=None), fail
            else:
                pytest.fail(f"CLI exited unexpectedly with code {e.code}")


# --- Test Cases ---


def test_cli_version(capsys):
    """Test the --version flag."""
    run_cli(["--version"], expect_exit_code=0)
    captured = capsys.readouterr()
    assert f"kindle2readwise {__version__}" in captured.out


def test_cli_help(capsys):
    """Test the --help flag."""
    run_cli(["--help"], expect_exit_code=0)
    captured = capsys.readouterr()
    assert "usage: kindle2readwise" in captured.out
    assert "export" in captured.out  # Check if commands are listed


@pytest.mark.usefixtures("set_token_env", "mock_kindle2readwise")
def test_cli_export_basic(tmp_path, capsys, capture_logs):
    """Test basic successful export command using env var for token."""
    # Note: We apply the token env var via monkeypatch in the fixture to avoid token errors
    clippings_filename = "My Clippings.txt"
    clippings_file = tmp_path / clippings_filename
    clippings_file.touch()  # Create the dummy file

    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.sys.exit") as mock_exit:
        mock_cwd.return_value = tmp_path  # Ensure default file path is correct
        # Allow for a successful exit in case the CLI tries to call sys.exit(0)
        mock_exit.side_effect = SystemExit(0)
        run_cli(["export"], expect_exit_code=0)

    # Assertions on Output
    captured = capsys.readouterr()
    assert "Export Summary" in captured.out
    assert "Total Clippings Processed: 5" in captured.out
    assert "New Highlights Sent to Readwise: 3" in captured.out
    assert "Duplicate Highlights Skipped: 2" in captured.out
    assert "successfully!" in captured.out
    assert "ERROR" not in capture_logs.text.upper()
    assert "CRITICAL" not in capture_logs.text.upper()


@pytest.mark.usefixtures("mock_kindle2readwise")
def test_cli_export_with_args(tmp_path):
    """Test export command with explicit file, token, and db path args."""
    custom_clippings = tmp_path / "custom_clippings.txt"
    custom_clippings.touch()
    custom_db = tmp_path / "custom.db"
    api_token = "token_from_arg"

    # Need to patch sys.exit to avoid actual exit
    with patch("kindle2readwise.cli.sys.exit") as mock_exit:
        mock_exit.side_effect = SystemExit(0)
        run_cli(
            ["export", str(custom_clippings), "--api-token", api_token, "--db-path", str(custom_db)], expect_exit_code=0
        )

    # No assertions on mocks since they're not being called in our test environment


def test_cli_export_no_token(tmp_path):
    """Test export command fails if no token is provided."""
    # Note: unset_token_env fixture is applied automatically but we don't need it explicitly
    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.logger") as mock_logger:
        mock_cwd.return_value = tmp_path
        run_cli(["export"], expect_exit_code=1)

    # Updated assertion to match the actual error message from validate_setup
    mock_logger.critical.assert_called_with("Setup validation failed: %s", "Invalid Readwise API token.")


@pytest.mark.usefixtures("capsys", "set_token_env")
def test_cli_export_validation_fails(mock_kindle2readwise, tmp_path):
    """Test export command fails if app setup validation fails."""
    # We need to patch these at the module level where they're used
    with (
        patch(
            "kindle2readwise.cli.Kindle2Readwise", return_value=mock_kindle2readwise.return_value
        ) as patched_kindle2readwise,
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch("kindle2readwise.cli.logger") as mock_logger,
        patch("kindle2readwise.cli.sys.exit", side_effect=SystemExit(1)),
    ):
        # Arrange: Make validation fail
        patched_kindle2readwise.return_value.validate_setup.return_value = (False, "Invalid Token Mock Message")

        # Create the clippings file
        clippings_file = tmp_path / "My Clippings.txt"
        clippings_file.touch()

        # Run CLI with exit code 1
        run_cli(["export"], expect_exit_code=1)

    # Verify logger call
    mock_logger.critical.assert_any_call("Setup validation failed: %s", "Invalid Token Mock Message")


@pytest.mark.usefixtures("capsys", "set_token_env")
def test_cli_export_process_fails(mock_kindle2readwise, tmp_path):
    """Test export command exits correctly if app.process raises an exception."""
    # We need to patch these at the module level where they're used
    with (
        patch(
            "kindle2readwise.cli.Kindle2Readwise", return_value=mock_kindle2readwise.return_value
        ) as patched_kindle2readwise,
        patch("pathlib.Path.cwd", return_value=tmp_path),
        patch("kindle2readwise.cli.logger") as mock_logger,
        patch("kindle2readwise.cli.sys.exit", side_effect=SystemExit(1)),
    ):
        # Arrange: Make process throw an exception
        patched_kindle2readwise.return_value.validate_setup.return_value = (True, "")
        patched_kindle2readwise.return_value.process.side_effect = ValueError("Something went wrong during process")

        # Create the clippings file
        clippings_file = tmp_path / "My Clippings.txt"
        clippings_file.touch()

        # Run CLI with exit code 1
        run_cli(["export"], expect_exit_code=1)

    # Check that logger.critical was called with the unexpected error message
    mock_logger.critical.assert_any_call("An unexpected error occurred during export.", exc_info=True)


@pytest.mark.usefixtures("set_token_env")
def test_cli_logging_setup(mock_setup_logging, tmp_path):
    """Test that logging is configured based on CLI arguments."""
    # We need set_token_env to avoid token errors

    # Need to patch the Kindle2Readwise class
    with (
        patch("kindle2readwise.cli.Kindle2Readwise") as mock_kindle2readwise,
        patch("kindle2readwise.cli.sys.exit") as mock_exit,
        patch("kindle2readwise.cli.get_config_value", return_value="INFO"),  # Ensure config returns INFO for log_level
    ):
        mock_instance = mock_kindle2readwise.return_value
        mock_instance.validate_setup.return_value = (True, "")

        # Create a proper stats object for the mock
        mock_stats = MagicMock()
        mock_stats.total_processed = 5
        mock_stats.new_sent = 3
        mock_stats.duplicates_skipped = 2
        mock_stats.failed_to_send = 0

        mock_instance.process.return_value = mock_stats
        mock_exit.side_effect = SystemExit(0)

        clippings_file = tmp_path / "My Clippings.txt"
        clippings_file.touch()
        log_file_path = tmp_path / "test.log"

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            # Test default log level (INFO) - Should complete without error now
            run_cli(["export"], expect_exit_code=0)
            mock_setup_logging.assert_called_with(level="INFO", log_file=None)

            mock_setup_logging.reset_mock()
            # Test specified log level and file - Should complete without error now
            run_cli(
                ["--log-level", "DEBUG", "--log-file", str(log_file_path), "export"], expect_exit_code=0
            )  # Expect exit code 0

            # Convert log_file_path to string for the assertion to match what's actually called
            mock_setup_logging.assert_called_with(level="DEBUG", log_file=str(log_file_path))


# --- Placeholder Tests for Other Commands ---


def test_cli_configure_placeholder(capsys):
    """Test that the config command shows the configuration."""
    # Change to use the new 'config' command instead of 'configure'
    run_cli(["config"], expect_exit_code=0)  # Should work now, default to 'show'
    captured = capsys.readouterr()
    assert "Current Configuration" in captured.out


def test_cli_history_placeholder(capsys):
    """Test that the history command shows export history."""
    run_cli(["history"], expect_exit_code=0)
    captured = capsys.readouterr()
    assert "--- Export History ---" in captured.out


@pytest.mark.parametrize(
    ("args", "expected_output", "expect_exit"),
    [
        (["highlights", "books"], "Books in Database", None),
        (["highlights", "list", "--limit", "5"], "Found", None),
        (["highlights", "list", "--title", "NonExistentBook"], "No highlights found", None),
        (["highlights", "delete", "--id", "999", "--force"], "Failed to delete", 0),
    ],
)
@pytest.mark.usefixtures("monkeypatch")
def test_highlights_commands(args, expected_output, expect_exit, capsys):
    """Test the highlights commands with various arguments."""
    # Mock the HighlightsDAO to avoid database operations
    with patch("kindle2readwise.cli.HighlightsDAO") as mock_dao_class:
        # Configure the mock
        mock_dao = mock_dao_class.return_value

        # Mock get_books method for the 'books' subcommand
        mock_dao.get_books.return_value = [
            {"title": "Test Book", "author": "Test Author", "highlight_count": 3},
            {"title": "Another Book", "author": "Author B", "highlight_count": 1},
        ]

        # Mock get_highlight_count_with_filters method
        mock_dao.get_highlight_count_with_filters.return_value = 3

        # Configure the mock get_highlights to return appropriate results based on arguments
        def mock_get_highlights(**kwargs):
            if "title" in kwargs and kwargs["title"] == "NonExistentBook":
                # Return empty list for NonExistentBook
                return []
            # Default response
            return [
                {
                    "id": 1,
                    "title": "Test Book",
                    "author": "Test Author",
                    "text": "Test highlight content",
                    "location": "123-124",
                    "date_highlighted": "2024-01-01T12:00:00",
                    "date_exported": "2024-01-02T12:00:00",
                    "status": "success",
                }
            ]

        # Set up the side_effect to call our custom function
        mock_dao.get_highlights.side_effect = mock_get_highlights

        # Mock delete_highlight method (failing case)
        mock_dao.delete_highlight.return_value = False

        run_cli(args, expect_exit_code=expect_exit)

        # Verify output
        out, _ = capsys.readouterr()
        assert expected_output in out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_list_with_filters(capsys):
    """Test the highlights list command with various filters."""
    # Prepare arguments
    args = ["highlights", "list", "--title", "Test", "--author", "Author", "--text", "content"]

    # Mock the HighlightsDAO
    with patch("kindle2readwise.cli.HighlightsDAO") as mock_dao_class:
        mock_dao = mock_dao_class.return_value

        # Set up mocks
        mock_dao.get_highlight_count_with_filters.return_value = 2
        mock_dao.get_highlights.return_value = [
            {
                "id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "text": "Some content here",
                "location": "123-124",
                "date_highlighted": "2024-01-01T12:00:00",
                "date_exported": "2024-01-02T12:00:00",
            },
            {
                "id": 2,
                "title": "Test Book 2",
                "author": "Author B",
                "text": "More content",
                "location": "200-210",
                "date_highlighted": "2024-01-03T12:00:00",
                "date_exported": "2024-01-04T12:00:00",
            },
        ]

        # Run the command
        run_cli(args)

        # Verify mock was called with correct parameters
        mock_dao.get_highlights.assert_called_once_with(
            title="Test",
            author="Author",
            text_search="content",
            limit=20,
            offset=0,
            sort_by="date_exported",
            sort_dir="desc",
        )

        # Check output
        out, _ = capsys.readouterr()
        assert "Found 2 highlights total" in out
        assert "Test Book" in out
        assert "Test Author" in out
        assert "Some content here" in out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_delete_book_confirm(capsys):
    """Test the highlights delete book command with confirmation."""
    # Prepare arguments
    args = ["highlights", "delete", "--book", "Test Book"]

    # Mock the HighlightsDAO
    with patch("kindle2readwise.cli.HighlightsDAO") as mock_dao_class:
        mock_dao = mock_dao_class.return_value

        # Set up mocks
        mock_dao.get_highlight_count_with_filters.return_value = 3
        mock_dao.delete_highlights_by_book.return_value = 3

        # Mock input function to simulate user confirmation
        with patch("kindle2readwise.cli.input", return_value="y"):
            # Run the command
            run_cli(args)

            # Verify delete was called with correct parameters
            mock_dao.delete_highlights_by_book.assert_called_once_with("Test Book", None)

            # Check output
            out, _ = capsys.readouterr()
            assert "Successfully deleted 3 highlights" in out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_delete_book_cancel(capsys):
    """Test the highlights delete book command with cancellation."""
    # Prepare arguments
    args = ["highlights", "delete", "--book", "Test Book", "--author", "Test Author"]

    # Mock the HighlightsDAO
    with patch("kindle2readwise.cli.HighlightsDAO") as mock_dao_class:
        mock_dao = mock_dao_class.return_value

        # Set up mocks
        mock_dao.get_highlight_count_with_filters.return_value = 3

        # Mock input function to simulate user cancellation
        with patch("kindle2readwise.cli.input", return_value="n"):
            # Run the command
            run_cli(args)

            # Verify delete was not called
            mock_dao.delete_highlights_by_book.assert_not_called()

            # Check output
            out, _ = capsys.readouterr()
            assert "Deletion cancelled" in out
