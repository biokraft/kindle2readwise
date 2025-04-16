import logging
from pathlib import Path

import pytest
from rich.logging import RichHandler

from kindle2readwise.logging_config import DEFAULT_LOG_FILE, setup_logging

# Constants
MIN_EXPECTED_HANDLERS = 2


@pytest.fixture(autouse=True)
def isolate_logging():
    """Fixture to isolate logging setup for each test."""
    # Get the root logger
    root_logger = logging.getLogger()
    # Store original handlers and level
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level

    # Monkeypatch basicConfig to prevent it from adding handlers globally
    # monkeypatch.setattr(logging, \"basicConfig\", lambda **kwargs: None)

    yield  # Run the test

    # Restore original state
    root_logger.handlers[:] = original_handlers
    root_logger.setLevel(original_level)
    # Clean up potentially created log file
    if DEFAULT_LOG_FILE.exists():
        try:
            DEFAULT_LOG_FILE.unlink()
            DEFAULT_LOG_FILE.parent.rmdir()  # Remove logs dir if empty
        except OSError:
            pass  # Ignore if dir not empty or other issues


def test_setup_logging_default(tmp_path):
    """Test setup_logging with default settings."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "kindle2readwise.log"

    setup_logging(log_file=log_file)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO

    # Check handler types and levels
    assert len(root_logger.handlers) >= MIN_EXPECTED_HANDLERS  # Allow for potential NullHandler

    rich_handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

    assert len(rich_handlers) == 1
    assert rich_handlers[0].level == logging.INFO

    assert len(file_handlers) == 1
    assert file_handlers[0].level == logging.INFO
    assert Path(file_handlers[0].baseFilename).resolve() == log_file.resolve()
    assert log_file.exists()


def test_setup_logging_debug_level(tmp_path):
    """Test setup_logging with DEBUG level."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "test_debug.log"

    setup_logging(level="DEBUG", log_file=log_file)

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    rich_handlers = [h for h in root_logger.handlers if isinstance(h, RichHandler)]
    file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]

    assert rich_handlers[0].level == logging.DEBUG
    assert file_handlers[0].level == logging.DEBUG
    assert log_file.exists()


def test_setup_logging_creates_directory(tmp_path):
    """Test that setup_logging creates the log directory if it doesn't exist."""
    log_dir = tmp_path / "new_log_dir"
    log_file = log_dir / "app.log"

    assert not log_dir.exists()
    setup_logging(log_file=log_file)
    assert log_dir.exists()
    assert log_dir.is_dir()
    assert log_file.exists()


def test_logging_output_to_file(tmp_path):
    """Test that log messages are written to the file."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "output_test.log"

    setup_logging(level="INFO", log_file=log_file)

    test_message = "This is a test log message."
    logger = logging.getLogger("test_output")
    logger.info(test_message)

    # Close handlers to ensure file is flushed
    for handler in logging.getLogger().handlers:
        handler.close()

    assert log_file.exists()
    with open(log_file) as f:
        content = f.read()
        assert test_message in content
        assert "INFO" in content
        assert "test_output" in content
