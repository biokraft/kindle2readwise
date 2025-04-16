import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal

from rich.logging import RichHandler

# Define standard log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Define logger for this module
logger = logging.getLogger(__name__)

# Define default log file path relative to the project root
DEFAULT_LOG_DIR = Path.cwd() / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "kindle2readwise.log"


def setup_logging(
    level: LogLevel = "INFO",
    log_file: Path = DEFAULT_LOG_FILE,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """Configure logging for the application.

    Sets up logging to both console (with rich formatting) and a rotating file.

    Args:
        level: The minimum logging level to capture.
        log_file: The path to the log file.
        max_bytes: The maximum size of the log file before rotation.
        backup_count: The number of backup log files to keep.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Ensure log directory exists only if a log file path is provided
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Basic configuration - sets the root logger level
    # Handlers will filter based on their own levels if set lower
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.NullHandler()],  # Prevent default handler if root is configured
    )

    root_logger = logging.getLogger()
    # Ensure root logger level is set correctly (basicConfig might be called elsewhere)
    root_logger.setLevel(log_level)

    # Remove existing handlers attached to the root logger to avoid duplication
    for handler in root_logger.handlers[:]:
        # Keep NullHandler to prevent default stderr handler if no other handlers added
        if not isinstance(handler, logging.NullHandler):
            root_logger.removeHandler(handler)

    # --- Console Handler (Rich) ---
    console_handler = RichHandler(
        level=log_level,
        show_time=True,
        show_level=True,
        show_path=False,  # Keep output cleaner, module name is in format
        rich_tracebacks=True,
        tracebacks_suppress=[],  # Add libraries to suppress here if needed
        markup=True,  # Enable Rich markup in log messages
    )
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # Create root logger instance and add handlers
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    # --- File Handler (Rotating) - Add only if log_file is specified ---
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                filename=log_file,  # log_file is confirmed Path object here
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
            root_logger.addHandler(file_handler)
            logger.debug("Added RotatingFileHandler for file: %s", log_file)
        except Exception:
            # Log error if file handler setup fails, but continue with console logging
            logging.getLogger(__name__).error("Failed to set up file logging to %s", log_file, exc_info=True)
    else:
        logging.getLogger(__name__).debug("File logging skipped as no log_file was provided.")


# Example usage for direct script execution (optional)
if __name__ == "__main__":
    setup_logging(level="DEBUG")
    logger = logging.getLogger("logging_config_test")
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
    try:
        # Using result variable to prevent B018 linter warning
        result = 1 / 0
        print(result)  # Never executed
    except ZeroDivisionError:
        logger.exception("Caught an exception.")  # Automatically includes traceback

    print(f"Log file created at: {DEFAULT_LOG_FILE.resolve()}")
