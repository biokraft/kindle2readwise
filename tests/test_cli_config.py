"""Tests for the CLI configuration commands.

These tests verify that the CLI commands for configuration management work correctly.
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from kindle2readwise.cli import handle_config_paths, handle_config_set, handle_config_show, handle_config_token, main
from kindle2readwise.config import DEFAULT_CONFIG


@pytest.fixture
def mock_config_dir():
    """Create a temporary directory for config files during tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with (
            mock.patch("kindle2readwise.config.get_config_dir", return_value=temp_path),
            mock.patch("kindle2readwise.config.get_token_file_path", return_value=temp_path / "readwise_token"),
        ):
            # Create data directory to avoid FileNotFoundError
            data_dir = temp_path / "data"
            data_dir.mkdir(exist_ok=True)
            yield temp_path


@pytest.fixture
def mock_config_file(mock_config_dir):
    """Create a temporary config file for testing."""
    config_file = mock_config_dir / "config.json"
    test_config = DEFAULT_CONFIG.copy()
    test_config["test_key"] = "test_value"

    with open(config_file, "w") as f:
        json.dump(test_config, f)

    with mock.patch("kindle2readwise.config.get_config_file_path", return_value=config_file):
        yield config_file


class CaptureStdout:
    """Context manager to capture stdout."""

    def __init__(self):
        self.stdout = StringIO()
        self._old_stdout = None

    def __enter__(self):
        """Enter the context and capture stdout."""
        self._old_stdout = sys.stdout
        sys.stdout = self.stdout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore stdout."""
        sys.stdout = self._old_stdout

    def get_output(self):
        return self.stdout.getvalue()


class TestConfigCommands:
    """Test CLI configuration commands."""

    @pytest.mark.usefixtures("mock_config_file")
    def test_handle_config_show(self):
        """Test showing current configuration."""
        # Mock args
        args = mock.MagicMock()

        # Call the function and capture stdout
        with CaptureStdout() as captured:
            handle_config_show(args)
            output = captured.get_output()

        # Check output
        assert "Current Configuration" in output
        assert "test_key: test_value" in output
        assert "Configuration directory" in output
        assert "Data directory" in output

    def test_handle_config_token_arg(self, mock_config_dir):
        """Test setting token via command line argument."""
        # Mock args with token
        args = mock.MagicMock()
        args.token = "test-token-12345"

        # Call the function and capture stdout
        with CaptureStdout() as captured:
            handle_config_token(args)
            output = captured.get_output()

        # Check output
        assert "Readwise API token" in output
        assert "successfully saved" in output

        # Token should be saved
        token_file = mock_config_dir / "readwise_token"
        assert token_file.exists()

    def test_handle_config_token_interactive(self, mock_config_dir):
        """Test setting token interactively."""
        # Mock args without token
        args = mock.MagicMock()
        args.token = None

        # Mock getpass to return a token
        with mock.patch("getpass.getpass", return_value="interactive-token-12345"), CaptureStdout() as captured:
            handle_config_token(args)
            output = captured.get_output()

        # Check output
        assert "Readwise API token" in output
        assert "successfully saved" in output

        # Token should be saved
        token_file = mock_config_dir / "readwise_token"
        assert token_file.exists()

    @pytest.mark.usefixtures("mock_config_dir")
    def test_handle_config_token_interactive_empty(self):
        """Test handling empty token input."""
        # Mock args without token
        args = mock.MagicMock()
        args.token = None

        # Mock getpass to return empty string
        with mock.patch("getpass.getpass", return_value=""), CaptureStdout() as captured:
            handle_config_token(args)
            output = captured.get_output()

        # Check output
        assert "No token provided" in output
        assert "Operation cancelled" in output

    @pytest.mark.usefixtures("mock_config_dir")
    def test_handle_config_token_interactive_cancel(self):
        """Test cancelling token input."""
        # Mock args without token
        args = mock.MagicMock()
        args.token = None

        # Mock getpass to raise KeyboardInterrupt
        with mock.patch("getpass.getpass", side_effect=KeyboardInterrupt), CaptureStdout() as captured:
            handle_config_token(args)
            output = captured.get_output()

        # Check output
        assert "Operation cancelled" in output

    def test_handle_config_set_valid(self, mock_config_file):
        """Test setting a valid configuration value."""
        # Mock args
        args = mock.MagicMock()
        args.key = "export_format"
        args.value = "json"

        # Call the function
        with CaptureStdout() as captured:
            handle_config_set(args)
            output = captured.get_output()

        # Check output
        assert "Configuration updated" in output
        assert "export_format = json" in output

        # Check config file was updated
        with open(mock_config_file) as f:
            config = json.load(f)
            assert config["export_format"] == "json"

    def test_handle_config_set_boolean(self, mock_config_file):
        """Test setting a boolean configuration value."""
        # Mock args
        args = mock.MagicMock()
        args.key = "auto_confirm"
        args.value = "true"

        # Call the function
        with CaptureStdout() as captured:
            handle_config_set(args)
            output = captured.get_output()

        # Check output
        assert "Configuration updated" in output

        # Check config file was updated with boolean value (not string)
        with open(mock_config_file) as f:
            config = json.load(f)
            assert config["auto_confirm"] is True
            assert not isinstance(config["auto_confirm"], str)

    def test_handle_config_set_invalid_key(self, mock_config_file):
        """Test setting an invalid configuration key."""
        # Mock args
        args = mock.MagicMock()
        args.key = "invalid_key"
        args.value = "some_value"

        # Call the function and expect system exit
        with pytest.raises(SystemExit), CaptureStdout():
            handle_config_set(args)

        # Check error message directly
        # Since the output is captured before the exit, we need to read the file manually
        sys.stdout = sys.__stdout__  # Restore stdout
        with open(mock_config_file) as f:
            config = json.load(f)
            # Config should not have the invalid key
            assert "invalid_key" not in config

    def test_handle_config_set_invalid_boolean(self, mock_config_file):
        """Test setting an invalid boolean value."""
        # Mock args
        args = mock.MagicMock()
        args.key = "auto_confirm"
        args.value = "not_a_boolean"

        # Call the function and expect system exit
        with pytest.raises(SystemExit), CaptureStdout():
            handle_config_set(args)

        # Check error message manually
        sys.stdout = sys.__stdout__  # Restore stdout
        with open(mock_config_file) as f:
            config = json.load(f)
            # auto_confirm should not be the invalid value
            assert config.get("auto_confirm") != "not_a_boolean"

    @pytest.mark.usefixtures("mock_config_dir")
    def test_handle_config_paths(self):
        """Test showing configuration paths."""
        # Mock args
        args = mock.MagicMock()

        # Call the function
        with CaptureStdout() as captured:
            handle_config_paths(args)
            output = captured.get_output()

        # Check output
        assert "Application Paths" in output
        assert "Configuration directory" in output
        assert "Data directory" in output
        assert "Database path" in output
        assert "Detected platform" in output

    def test_handle_config_set_valid_log_level(self, mock_config_file):
        """Test setting a valid log level."""
        # Test each valid log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_log_levels:
            # Mock args
            args = mock.MagicMock()
            args.key = "log_level"
            args.value = level

            # Call the function
            with CaptureStdout() as captured:
                handle_config_set(args)
                output = captured.get_output()

            # Check output
            assert f"Configuration updated: log_level = {level}" in output

            # Check config file was updated correctly
            with open(mock_config_file) as f:
                config = json.load(f)
                assert config["log_level"] == level

    def test_handle_config_set_valid_log_level_lowercase(self, mock_config_file):
        """Test setting a valid log level with lowercase input."""
        # Mock args
        args = mock.MagicMock()
        args.key = "log_level"
        args.value = "debug"  # lowercase

        # Call the function
        with CaptureStdout() as captured:
            handle_config_set(args)
            output = captured.get_output()

        # Check output
        assert "Configuration updated: log_level = DEBUG" in output

        # Check config file was updated with uppercase value
        with open(mock_config_file) as f:
            config = json.load(f)
            assert config["log_level"] == "DEBUG"  # Should be stored in uppercase

    def test_handle_config_set_invalid_log_level(self, mock_config_file):
        """Test setting an invalid log level."""
        # Mock args
        args = mock.MagicMock()
        args.key = "log_level"
        args.value = "INVALID_LEVEL"

        # Call the function and expect system exit
        with pytest.raises(SystemExit):
            handle_config_set(args)

        # After SystemExit, check that the config wasn't changed
        with open(mock_config_file) as f:
            config = json.load(f)
            # log_level should not be the invalid value
            assert config.get("log_level") != "INVALID_LEVEL"


class TestLogLevelValidation:
    """Test validation of log level values."""

    def test_valid_log_levels(self, mock_config_file):
        """Test that valid log levels are accepted."""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_log_levels:
            # Mock command line args
            test_args = ["config", "set", "log_level", level]
            with (
                mock.patch("sys.argv", ["kindle2readwise", *test_args]),
                pytest.raises(SystemExit, code=0),
                CaptureStdout(),
            ):
                main()

            # Verify config was updated correctly
            with open(mock_config_file) as f:
                config = json.load(f)
                assert config["log_level"] == level

    def test_invalid_log_level(self, mock_config_file):
        """Test that invalid log levels are rejected."""
        # Set a known initial log level
        with open(mock_config_file) as f:
            config = json.load(f)
        initial_level = config.get("log_level", "INFO")

        # Test with an invalid log level
        test_args = ["config", "set", "log_level", "INVALID"]
        with (
            mock.patch("sys.argv", ["kindle2readwise", *test_args]),
            pytest.raises(SystemExit, code=1),
            CaptureStdout(),
        ):
            main()

        # Verify config was not changed
        with open(mock_config_file) as f:
            config = json.load(f)
            assert config["log_level"] == initial_level
            assert config["log_level"] != "INVALID"
