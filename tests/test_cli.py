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
        mock_instance.process.return_value = MagicMock()
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
            if expect_exit_code is not None:
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


def test_cli_export_basic(mock_kindle2readwise, tmp_path, capsys, capture_logs):
    """Test basic successful export command using env var for token."""
    # Note: We apply the token env var via monkeypatch in the fixture, but don't need it explicitly here
    clippings_filename = "My Clippings.txt"
    clippings_file = tmp_path / clippings_filename
    clippings_file.touch()  # Create the dummy file

    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = tmp_path  # Ensure default file path is correct
        run_cli(["export"], expect_exit_code=0)

    # Assertions on Mocks
    mock_kindle2readwise.validate_setup.assert_called_once()
    mock_kindle2readwise.process.assert_called_once()
    mock_kindle2readwise.close_db.assert_called_once()

    # Assertions on Output
    captured = capsys.readouterr()
    assert "Export Summary" in captured.out
    assert "New Highlights Sent to Readwise: 3" in captured.out
    assert "Duplicate Highlights Skipped: 2" in captured.out
    assert "successfully!" in captured.out
    assert "ERROR" not in capture_logs.text.upper()
    assert "CRITICAL" not in capture_logs.text.upper()


def test_cli_export_with_args(mock_kindle2readwise, tmp_path):
    """Test export command with explicit file, token, and db path args."""
    custom_clippings = tmp_path / "custom_clippings.txt"
    custom_clippings.touch()
    custom_db = tmp_path / "custom.db"
    api_token = "token_from_arg"

    run_cli(
        ["export", str(custom_clippings), "--api-token", api_token, "--db-path", str(custom_db)], expect_exit_code=0
    )

    # Assertions on Mocks
    mock_kindle2readwise.validate_setup.assert_called_once()
    mock_kindle2readwise.process.assert_called_once()
    mock_kindle2readwise.close_db.assert_called_once()


def test_cli_export_no_token(mock_kindle2readwise, tmp_path, capsys):
    """Test export command fails if no token is provided."""
    # Note: unset_token_env fixture is applied automatically but we don't need it explicitly
    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = tmp_path
        run_cli(["export"], expect_exit_code=1)

    # Assertions
    captured = capsys.readouterr()
    assert "Readwise API token not provided" in captured.out
    # Core app should not be instantiated or called
    mock_kindle2readwise.assert_not_called()


def test_cli_export_validation_fails(mock_kindle2readwise, tmp_path, capsys):
    """Test export command fails if app setup validation fails."""
    # Arrange: Make validation fail
    mock_instance = mock_kindle2readwise
    mock_instance.validate_setup.return_value = (False, "Invalid Token Mock Message")

    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = tmp_path
        run_cli(["export"], expect_exit_code=1)

    # Assertions
    captured = capsys.readouterr()
    # Check for failure message
    assert "invalid token" in captured.out.lower()
    assert "mock message" in captured.out.lower()
    mock_kindle2readwise.assert_called_once()  # App is instantiated
    mock_instance.validate_setup.assert_called_once()  # Validation is called
    mock_instance.process.assert_not_called()  # Process should not be called
    mock_instance.close_db.assert_called_once()  # DB should still be closed in finally block


def test_cli_export_process_fails(mock_kindle2readwise, tmp_path, capsys):
    """Test export command exits correctly if app.process raises an exception."""
    # Arrange: Make process fail
    mock_instance = mock_kindle2readwise
    mock_instance.process.side_effect = ValueError("Something went wrong during process")

    clippings_file = tmp_path / "My Clippings.txt"
    clippings_file.touch()

    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.return_value = tmp_path
        run_cli(["export"], expect_exit_code=1)

    # Assertions
    captured = capsys.readouterr()
    assert "unexpected error" in captured.out.lower()
    assert "ValueError: Something went wrong during process" in captured.out  # Check traceback log
    mock_kindle2readwise.assert_called_once()
    mock_instance.validate_setup.assert_called_once()
    mock_instance.process.assert_called_once()  # Process was called
    mock_instance.close_db.assert_called_once()
    # Summary shouldn't print
    # No summary should print


def test_cli_logging_setup(mock_setup_logging, tmp_path):
    """Test that logging is configured based on CLI arguments."""
    # We need mock_kindle2readwise here to prevent the real app from running and failing
    # We also need set_token_env so the CLI doesn't exit early due to missing token

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
        mock_setup_logging.assert_called_with(level="DEBUG", log_file=log_file_path)


# --- Placeholder Tests for Other Commands ---


def test_cli_configure_placeholder(capsys):
    run_cli(["configure"], expect_exit_code=None)  # Doesn't exit yet
    captured = capsys.readouterr()
    assert "'configure' command is not implemented yet." in captured.out


def test_cli_history_placeholder(capsys):
    run_cli(["history"], expect_exit_code=None)  # Doesn't exit yet
    captured = capsys.readouterr()
    assert "'history' command is not implemented yet." in captured.out
