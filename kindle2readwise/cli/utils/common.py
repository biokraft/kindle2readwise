"""Common utility functions for CLI commands."""

import logging
import os
from pathlib import Path

from ...config import get_readwise_token

# Environment variable for Readwise token (optional)
READWISE_TOKEN_ENV_VAR = "READWISE_API_TOKEN"
DEFAULT_CLIPPINGS_PATH = "My Clippings.txt"

logger = logging.getLogger(__name__)


def get_api_token_from_env() -> str | None:
    """Get the Readwise API token from environment variables.

    Returns:
        API token if found, None otherwise
    """
    return os.environ.get(READWISE_TOKEN_ENV_VAR)


def get_readwise_token_cli(args) -> str | None:
    """Get Readwise token from args, environment variable, or config."""
    # First try command line argument
    if hasattr(args, "api_token") and args.api_token:
        logger.debug("Using Readwise API token from command line argument.")
        return args.api_token

    # Then try environment variable
    token_from_env = os.environ.get(READWISE_TOKEN_ENV_VAR)
    if token_from_env:
        logger.debug("Using Readwise API token from environment variable %s.", READWISE_TOKEN_ENV_VAR)
        return token_from_env

    # Finally try configured token
    token_from_config = get_readwise_token()
    if token_from_config:
        logger.debug("Using Readwise API token from configuration.")
        return token_from_config

    logger.debug("Readwise API token not found in args, environment variable, or configuration.")
    return None


def get_default_clippings_path() -> str | None:
    """Get the default path to the Kindle clippings file.

    Returns:
        Path to the clippings file if found, None otherwise
    """
    # First try to automatically detect connected Kindle devices
    from ...utils.device_detection import find_kindle_clippings

    kindle_clippings = find_kindle_clippings()
    if kindle_clippings:
        logger.info("Automatically detected Kindle clippings file: %s", kindle_clippings)
        return str(kindle_clippings)

    # Check current directory as fallback
    current_dir = Path.cwd() / "My Clippings.txt"
    if current_dir.exists():
        logger.debug("Found clippings file in current directory: %s", current_dir)
        return str(current_dir)

    logger.debug("No Kindle clippings file found automatically")
    return None
