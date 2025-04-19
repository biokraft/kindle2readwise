from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise.cli.commands.export import handle_export


@pytest.fixture
def mock_kindle2readwise():
    """Fixture to mock the core Kindle2Readwise class."""
    with patch("kindle2readwise.cli.commands.export.Kindle2Readwise") as mock_app:
        mock_instance = mock_app.return_value
        # Configure default mock behaviors
        mock_instance.validate_setup.return_value = None  # Returns None instead of tuple

        # Mock the get_pending_highlights method
        mock_highlights = [
            {
                "id": 1,
                "title": "Test Book 1",
                "author": "Author 1",
                "highlight": "This is highlight 1",
                "location": "100",
                "date": "2023-01-01",
            },
            {
                "id": 2,
                "title": "Test Book 2",
                "author": "Author 2",
                "highlight": "This is highlight 2",
                "location": "200",
                "date": "2023-01-02",
            },
        ]
        mock_instance.get_pending_highlights.return_value = mock_highlights

        # Create a proper stats object with integer attributes
        mock_stats = MagicMock()
        mock_stats.total_processed = 5
        mock_stats.new_sent = 3
        mock_stats.duplicates_skipped = 2
        mock_stats.failed_to_send = 0

        mock_instance.process.return_value = mock_stats
        mock_instance.process_selected.return_value = mock_stats
        mock_instance.close_db.return_value = None

        yield mock_app


@pytest.fixture
def mock_input():
    """Fixture to mock input function."""
    with patch("kindle2readwise.cli.commands.export.input") as mock_in:
        yield mock_in


@pytest.fixture
def mock_device_detection():
    """Fixture to mock device detection functions."""
    with patch("kindle2readwise.cli.commands.export.should_detect_devices") as mock_detect:
        # Disable automatic device detection
        mock_detect.return_value = False
        yield mock_detect


@pytest.fixture
def mock_sys_exit():
    """Fixture to mock sys.exit."""
    with patch("kindle2readwise.cli.commands.export.sys.exit") as mock_exit:
        mock_exit.side_effect = lambda _: None  # Don't actually exit
        yield mock_exit


@pytest.fixture
def interactive_args():
    """Fixture to create args for interactive mode."""
    args = MagicMock()
    args.interactive = True
    args.force = False
    args.dry_run = False
    args.api_token = "test_token"
    args.file = "My Clippings.txt"
    args.db_path = None
    args.output = None
    # Explicitly set devices to False to avoid device detection
    args.devices = False
    return args


# Define constants for test data
EXPECTED_HIGHLIGHT_COUNT = 2
FIRST_HIGHLIGHT_ID = 1
SECOND_HIGHLIGHT_ID = 2


def test_interactive_mode_basic(interactive_args, mock_kindle2readwise, mock_input, capsys):
    """Test basic interactive mode functionality."""
    # Setup mock input to select all highlights
    mock_input.side_effect = ["a", "y"]  # 'a' to select all, 'y' to confirm

    # Run the export command with interactive mode
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.is_file") as mock_is_file:
        mock_exists.return_value = True
        mock_is_file.return_value = True
        handle_export(interactive_args)

    # Check that the mocked instance methods were called correctly
    mock_instance = mock_kindle2readwise.return_value
    mock_instance.validate_setup.assert_called_once()
    mock_instance.get_pending_highlights.assert_called_once()
    mock_instance.process_selected.assert_called_once()

    # Verify the selected highlights were passed to process_selected
    args, kwargs = mock_instance.process_selected.call_args
    assert len(kwargs["selected_ids"]) == EXPECTED_HIGHLIGHT_COUNT  # Both highlights should be selected
    assert kwargs["selected_ids"] == [FIRST_HIGHLIGHT_ID, SECOND_HIGHLIGHT_ID]  # IDs should match our mock data

    # Check the console output
    captured = capsys.readouterr()
    assert "Interactive Export Mode" in captured.out
    assert "Test Book 1" in captured.out
    assert "Test Book 2" in captured.out


def test_interactive_mode_selective(interactive_args, mock_kindle2readwise, mock_input, capsys):
    """Test interactive mode with selective highlight choice."""
    # Setup mock input to select only the first highlight
    mock_input.side_effect = ["1", "y"]  # '1' to select first highlight, 'y' to confirm

    # Run the export command with interactive mode
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.is_file") as mock_is_file:
        mock_exists.return_value = True
        mock_is_file.return_value = True
        handle_export(interactive_args)

    # Check that the mocked instance methods were called correctly
    mock_instance = mock_kindle2readwise.return_value
    mock_instance.validate_setup.assert_called_once()
    mock_instance.get_pending_highlights.assert_called_once()
    mock_instance.process_selected.assert_called_once()

    # Verify only the first highlight was passed to process_selected
    args, kwargs = mock_instance.process_selected.call_args
    assert len(kwargs["selected_ids"]) == 1
    assert kwargs["selected_ids"] == [FIRST_HIGHLIGHT_ID]

    # Check the console output
    captured = capsys.readouterr()
    assert "Interactive Export Mode" in captured.out
    assert "Test Book 1" in captured.out
    assert "Test Book 2" in captured.out


def test_interactive_mode_cancel(interactive_args, mock_kindle2readwise, mock_input, capsys):
    """Test interactive mode with user cancellation."""
    # Setup mock input to select highlights but cancel the export
    mock_input.side_effect = ["a", "n"]  # 'a' to select all, 'n' to cancel

    # Run the export command with interactive mode
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.is_file") as mock_is_file:
        mock_exists.return_value = True
        mock_is_file.return_value = True
        handle_export(interactive_args)

    # Check that the mocked instance methods were called correctly
    mock_instance = mock_kindle2readwise.return_value
    mock_instance.validate_setup.assert_called_once()
    mock_instance.get_pending_highlights.assert_called_once()

    # Verify process_selected was NOT called (export was cancelled)
    mock_instance.process_selected.assert_not_called()

    # Check the console output
    captured = capsys.readouterr()
    assert "Interactive Export Mode" in captured.out
    assert "Export cancelled" in captured.out


def test_interactive_mode_no_highlights(interactive_args, mock_kindle2readwise, capsys):
    """Test interactive mode when no highlights are available."""
    # Setup mock to return no highlights
    mock_instance = mock_kindle2readwise.return_value
    mock_instance.get_pending_highlights.return_value = []

    # Run the export command with interactive mode
    with patch("pathlib.Path.exists") as mock_exists, patch("pathlib.Path.is_file") as mock_is_file:
        mock_exists.return_value = True
        mock_is_file.return_value = True
        handle_export(interactive_args)

    # Verify process_selected was NOT called (no highlights to export)
    mock_instance.process_selected.assert_not_called()

    # Check the console output
    captured = capsys.readouterr()
    assert "No new highlights found to export" in captured.out
