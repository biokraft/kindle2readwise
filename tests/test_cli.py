import logging
from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise import __version__

# Update import to use the new CLI structure
from kindle2readwise.cli.main import main as cli_main
from kindle2readwise.exceptions import ProcessingError, ValidationError

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
    # Update to use the correct path to core class in export module
    with patch("kindle2readwise.cli.commands.export.Kindle2Readwise") as mock_app:
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

        yield mock_app


@pytest.fixture
def mock_setup_logging():
    """Fixture to mock the logging setup function."""
    # Update path to use main module
    with patch("kindle2readwise.cli.main.setup_logging") as mock_setup:
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


@pytest.mark.usefixtures("set_token_env")
def test_cli_export_basic(tmp_path, mock_kindle2readwise):
    """Test basic successful export command using env var for token."""
    # Note: We apply the token env var via monkeypatch in the fixture to avoid token errors
    clippings_filename = "My Clippings.txt"
    clippings_file = tmp_path / clippings_filename
    clippings_file.touch()  # Create the dummy file

    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.main.sys.exit") as mock_exit:
        mock_cwd.return_value = tmp_path
        mock_exit.side_effect = SystemExit(0)  # Success exit

        # Run the CLI with basic export command
        run_cli(["export"])

        # Check that app was constructed with expected args
        mock_kindle2readwise.assert_called_once()

        # Validate
        mock_instance = mock_kindle2readwise.return_value
        mock_instance.validate_setup.assert_called_once()
        mock_instance.process.assert_called_once()


def test_cli_export_with_args(tmp_path, mock_kindle2readwise):
    """Test export command with explicit file, token, and db path args."""
    custom_clippings = tmp_path / "custom_clippings.txt"
    custom_clippings.touch()
    custom_db = tmp_path / "custom.db"
    api_token = "token_from_arg"

    # Need to patch sys.exit to avoid actual exit
    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.main.sys.exit") as mock_exit:
        mock_cwd.return_value = tmp_path
        mock_exit.side_effect = SystemExit(0)  # Success exit

        # Run CLI with explicit args - use the correct parameter names
        run_cli(
            [
                "export",
                str(custom_clippings),  # The file is a positional argument
                "--api-token",
                api_token,
                "--db-path",
                str(custom_db),
            ]
        )

        # Get the call args
        args, kwargs = mock_kindle2readwise.call_args

        # Validate args were passed correctly - compare as strings to avoid PosixPath vs str mismatch
        assert str(kwargs["clippings_file"]) == str(custom_clippings)
        assert kwargs["readwise_token"] == api_token
        assert str(kwargs["db_path"]) == str(custom_db)


def test_cli_export_no_token(tmp_path):
    """Test export command fails if no token is provided."""
    # Note: unset_token_env fixture is applied automatically but we don't need it explicitly
    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.commands.export.logger") as mock_logger:
        mock_cwd.return_value = tmp_path
        run_cli(["export"], expect_exit_code=1)

    # Updated assertion to match the actual error message from validate_setup
    mock_logger.critical.assert_called_with("Setup validation failed: %s", "Invalid Readwise API token.")


@pytest.mark.usefixtures("set_token_env")
def test_cli_export_validation_fails(tmp_path, mock_kindle2readwise):
    """Test export command when validation fails."""
    # Create a dummy file
    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    # Setup the mock to trigger a validation error
    mock_app = mock_kindle2readwise.return_value
    mock_app.validate_setup.side_effect = ValidationError("Validation failed")

    # Patch cwd to return tmp_path and sys.exit to prevent real exit
    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.main.sys.exit") as mock_exit:
        mock_cwd.return_value = tmp_path
        mock_exit.side_effect = SystemExit(1)  # Error exit

        # Run the export command, expect failure
        run_cli(["export"], expect_exit_code=1)  # Expect exit code 1 for validation failure

        # Validate that validate_setup was called
        mock_app.validate_setup.assert_called_once()
        # Process should not be called after validation failure
        mock_app.process.assert_not_called()


@pytest.mark.usefixtures("set_token_env")
def test_cli_export_process_fails(tmp_path, mock_kindle2readwise):
    """Test export command when processing fails."""
    # Create a dummy file
    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    # Setup the mock to trigger a processing error
    mock_app = mock_kindle2readwise.return_value
    mock_app.process.side_effect = ProcessingError("Processing failed")

    # Patch cwd to return tmp_path and sys.exit to prevent real exit
    with patch("pathlib.Path.cwd") as mock_cwd, patch("kindle2readwise.cli.main.sys.exit") as mock_exit:
        mock_cwd.return_value = tmp_path
        mock_exit.side_effect = SystemExit(1)  # Error exit

        # Run the export command, expect failure
        run_cli(["export"], expect_exit_code=1)  # Expect exit code 1 for processing failure

        # Validate that both methods were called
        mock_app.validate_setup.assert_called_once()
        mock_app.process.assert_called_once()


@pytest.mark.usefixtures("set_token_env")
def test_cli_logging_setup(mock_setup_logging, tmp_path):
    """Test that logging is set up correctly."""
    # Need to patch the Kindle2Readwise class
    with (
        patch("kindle2readwise.cli.commands.export.Kindle2Readwise") as mock_kindle2readwise,
        patch("kindle2readwise.cli.main.sys.exit") as mock_exit,
        patch("kindle2readwise.config.get_config_value", return_value="INFO"),  # Ensure config returns INFO
    ):
        # Create a dummy clippings file
        clippings_file = tmp_path / "My Clippings.txt"
        clippings_file.touch()

        # Configure the mock
        inst = mock_kindle2readwise.return_value
        inst.validate_setup.return_value = (True, "")
        inst.process.return_value = MagicMock(total_processed=5, new_sent=3, duplicates_skipped=2, failed_to_send=0)
        mock_exit.side_effect = SystemExit(0)

        # Run with custom log level
        run_cli(["--log-level", "DEBUG", "export"], expect_exit_code=0)

    # Check that log setup was called with DEBUG level
    mock_setup_logging.assert_called_with(level="DEBUG", log_file=None)


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
    with patch("kindle2readwise.cli.commands.highlights.HighlightsDAO") as mock_dao_class:
        mock_dao = mock_dao_class.return_value

        # Configure the mock based on the command
        if "books" in args:
            # Mock get_books method
            mock_dao.get_books.return_value = [
                {"title": "Book 1", "author": "Author 1", "highlight_count": 10},
                {"title": "Book 2", "author": "Author 2", "highlight_count": 5},
            ]
        elif "list" in args:
            # Mock get_highlight_count_with_filters
            mock_dao.get_highlight_count_with_filters.return_value = 15

            # Different behaviors based on title filter
            if "--title" in args and args[args.index("--title") + 1] == "NonExistentBook":
                mock_dao.get_highlights.return_value = []  # No highlights found
            else:
                # Mock get_highlights for normal case - accept any kwargs
                def mock_get_highlights(**kwargs):  # noqa: ARG001 - kwargs is intentionally unused
                    return [
                        {
                            "id": 1,
                            "title": "Test Book",
                            "author": "Test Author",
                            "text": "This is a test highlight.",
                            "location": "123",
                            "date_highlighted": "2023-01-01T12:00:00",
                            "date_exported": "2023-01-02T12:00:00",
                        }
                    ]

                mock_dao.get_highlights.side_effect = mock_get_highlights
        elif "delete" in args:
            # Mock delete_highlight that returns False (failed)
            mock_dao.delete_highlight.return_value = False

        # Run the command
        run_cli(args, expect_exit_code=expect_exit)

        # Check output
        captured = capsys.readouterr()
        assert expected_output in captured.out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_list_with_filters(capsys):
    """Test the highlights list command with various filters."""
    # Prepare arguments
    args = ["highlights", "list", "--title", "Test", "--author", "Author", "--text", "content"]

    # Mock the HighlightsDAO
    with patch("kindle2readwise.cli.commands.highlights.HighlightsDAO") as mock_dao_class:
        mock_dao = mock_dao_class.return_value

        # Mock get_highlight_count_with_filters
        mock_dao.get_highlight_count_with_filters.return_value = 3

        # Mock get_highlights
        mock_dao.get_highlights.return_value = [
            {
                "id": 1,
                "title": "Test Book",
                "author": "Test Author",
                "text": "This is some content to test with.",
                "location": "123-125",
                "date_highlighted": "2023-01-01T12:00:00",
                "date_exported": "2023-01-02T12:00:00",
            }
        ]

        # Run the command
        run_cli(args, expect_exit_code=None)

        # Check that get_highlights was called with the correct filter parameters
        mock_dao.get_highlights.assert_called_with(
            title="Test",
            author="Author",
            text_search="content",
            limit=20,  # Default limit
            offset=0,  # Default offset
            sort_by="date_exported",  # Default sort field
            sort_dir="desc",  # Default sort direction
        )

        # Verify output has expected strings
        captured = capsys.readouterr()
        assert "Found 3 highlights total" in captured.out
        assert "Test Book" in captured.out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_delete_book_confirm(capsys):
    """Test the highlights delete book command with confirmation."""
    # Prepare arguments
    args = ["highlights", "delete", "--book", "Test Book"]

    # Mock the HighlightsDAO
    with (
        patch("kindle2readwise.cli.commands.highlights.HighlightsDAO") as mock_dao_class,
        patch("kindle2readwise.cli.commands.highlights.input", return_value="y") as mock_input,
    ):
        mock_dao = mock_dao_class.return_value

        # Mock get_highlight_count_with_filters to return 5 highlights
        mock_dao.get_highlight_count_with_filters.return_value = 5

        # Mock delete_highlights_by_book to return 5 deleted
        mock_dao.delete_highlights_by_book.return_value = 5

        # Run the command
        run_cli(args, expect_exit_code=None)

        # Check that the confirmation prompt was shown
        mock_input.assert_called_once()
        assert "Test Book" in mock_input.call_args[0][0]
        assert "5 highlights" in mock_input.call_args[0][0]

        # Check that delete_highlights_by_book was called with the correct parameters
        mock_dao.delete_highlights_by_book.assert_called_once_with("Test Book", None)

        # Verify output has success message
        captured = capsys.readouterr()
        assert "Successfully deleted 5 highlights" in captured.out


@pytest.mark.usefixtures("monkeypatch")
def test_highlights_delete_book_cancel(capsys):
    """Test the highlights delete book command with cancellation."""
    # Prepare arguments
    args = ["highlights", "delete", "--book", "Test Book", "--author", "Test Author"]

    # Mock the HighlightsDAO
    with (
        patch("kindle2readwise.cli.commands.highlights.HighlightsDAO") as mock_dao_class,
        patch("kindle2readwise.cli.commands.highlights.input", return_value="n") as mock_input,
    ):
        mock_dao = mock_dao_class.return_value

        # Mock get_highlight_count_with_filters to return 3 highlights
        mock_dao.get_highlight_count_with_filters.return_value = 3

        # Run the command
        run_cli(args, expect_exit_code=None)

        # Check that the confirmation prompt was shown
        mock_input.assert_called_once()
        assert "Test Book" in mock_input.call_args[0][0]
        assert "Test Author" in mock_input.call_args[0][0]

        # Check that delete_highlights_by_book was NOT called
        mock_dao.delete_highlights_by_book.assert_not_called()

        # Verify output has cancellation message
        captured = capsys.readouterr()
        assert "Deletion cancelled" in captured.out
