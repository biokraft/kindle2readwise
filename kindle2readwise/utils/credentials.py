"""Utilities for secure handling of API tokens and credentials.

This module provides a more secure way to handle API tokens and credentials
than storing them in plain text in configuration files. In a future version,
this could be enhanced to use platform-specific keyring implementations.
"""

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def encode_token(token: str) -> str:
    """Encode a token with base64 encoding.

    This is not secure encryption, but provides a basic level of obfuscation.

    Args:
        token: The token to encode

    Returns:
        str: The encoded token
    """
    if not token:
        return ""
    try:
        return base64.b64encode(token.encode()).decode()
    except Exception as e:
        logger.error(f"Error encoding token: {e}")
        return ""


def decode_token(encoded_token: str) -> str:
    """Decode a token from base64 encoding.

    Args:
        encoded_token: The encoded token

    Returns:
        str: The decoded token or empty string if error
    """
    if not encoded_token:
        return ""
    try:
        return base64.b64decode(encoded_token.encode()).decode()
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return ""


def save_token_to_file(token: str, file_path: Path) -> bool:
    """Save an API token to a file with basic encoding.

    Args:
        token: The API token to save
        file_path: Path to save the token to

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Encode and save token
        encoded_token = encode_token(token)
        with open(file_path, "w") as f:
            f.write(encoded_token)

        # Set restrictive permissions on Unix-like systems
        if os.name == "posix":
            os.chmod(file_path, 0o600)  # Owner read/write only

        logger.debug(f"Token saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving token to file: {e}")
        return False


def load_token_from_file(file_path: Path) -> str:
    """Load an API token from a file and decode it.

    Args:
        file_path: Path to the token file

    Returns:
        str: The decoded token or empty string if error or file not found
    """
    if not file_path.exists():
        logger.debug(f"Token file not found: {file_path}")
        return ""

    try:
        with open(file_path) as f:
            encoded_token = f.read().strip()

        if not encoded_token:
            return ""

        decoded_token = decode_token(encoded_token)
        logger.debug(f"Token loaded from {file_path}")
        return decoded_token
    except Exception as e:
        logger.error(f"Error loading token from file: {e}")
        return ""


def mask_token(token: str) -> str:
    """Mask a token for display or logging.

    Args:
        token: The token to mask

    Returns:
        str: The masked token (first 4 + last 4 characters visible)
    """
    if not token:
        return ""

    min_token_length_for_partial_mask = 8
    if len(token) <= min_token_length_for_partial_mask:
        return "*" * len(token)

    visible_chars = 4
    return token[:visible_chars] + "*" * (len(token) - 2 * visible_chars) + token[-visible_chars:]
