"""Configuration management for kindle2readwise.

This module handles reading and writing configuration settings,
including secure storage of API tokens and user preferences.
"""

import json
import logging
import os
import platform
from functools import lru_cache
from pathlib import Path
from typing import Any

from kindle2readwise.utils.credentials import load_token_from_file, mask_token, save_token_to_file

logger = logging.getLogger(__name__)

# Default configuration settings
DEFAULT_CONFIG = {
    "export_format": "default",
    "auto_confirm": False,
    "log_level": "INFO",
    "database_path": "",  # Will be auto-populated based on config_dir
}


def get_config_dir() -> Path:
    """Get the platform-specific configuration directory."""
    system = platform.system()
    home = Path.home()

    if system == "Darwin":  # macOS
        config_dir = home / "Library" / "Application Support" / "kindle2readwise"
    elif system == "Windows":
        config_dir = Path(os.getenv("APPDATA", str(home / "AppData" / "Roaming"))) / "kindle2readwise"
    else:  # Linux and others
        config_dir = home / ".config" / "kindle2readwise"

    # Create the config directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_dir() -> Path:
    """Get the platform-specific data directory."""
    config_dir = get_config_dir()
    data_dir = config_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_credentials_dir() -> Path:
    """Get the directory for storing credentials."""
    config_dir = get_config_dir()
    creds_dir = config_dir / "credentials"
    creds_dir.mkdir(exist_ok=True)
    return creds_dir


def get_token_file_path() -> Path:
    """Get the path to the Readwise API token file."""
    return get_credentials_dir() / "readwise_token"


@lru_cache(maxsize=1)
def get_config_file_path() -> Path:
    """Get the path to the configuration file."""
    return get_config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    """Load configuration from file or create with defaults if not exists."""
    config_file = get_config_file_path()

    # If config file exists, load it
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
            logger.debug(f"Loaded configuration from {config_file}")

            # Merge with defaults to ensure all keys exist
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config)
            return merged_config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration instead")
            return DEFAULT_CONFIG.copy()

    # Create new config with defaults
    config = DEFAULT_CONFIG.copy()

    # Set default database path if not set
    if not config["database_path"]:
        config["database_path"] = str(get_data_dir() / "kindle2readwise.db")

    # Save the new config
    save_config(config)
    return config


def save_config(config: dict[str, Any]) -> bool:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save

    Returns:
        bool: True if successful, False otherwise
    """
    config_file = get_config_file_path()
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        logger.debug(f"Saved configuration to {config_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return False


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value by key.

    Args:
        key: The configuration key to retrieve
        default: Default value to return if key not found

    Returns:
        The configuration value or default if not found
    """
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any) -> bool:
    """Set a configuration value.

    Args:
        key: The configuration key to set
        value: The value to set

    Returns:
        bool: True if successful, False otherwise
    """
    config = load_config()
    config[key] = value
    return save_config(config)


def set_readwise_token(token: str) -> bool:
    """Store the Readwise API token securely.

    Saves the token to a separate file with basic encoding for improved security.

    Args:
        token: The Readwise API token

    Returns:
        bool: True if stored successfully, False otherwise
    """
    token_file = get_token_file_path()

    if not token:
        logger.warning("Attempting to store empty API token")
        return False

    logger.info(f"Storing Readwise API token {mask_token(token)}")
    return save_token_to_file(token, token_file)


def get_readwise_token() -> str:
    """Retrieve the stored Readwise API token.

    Returns:
        str: The stored token or empty string if not set
    """
    token_file = get_token_file_path()
    token = load_token_from_file(token_file)

    if token:
        logger.debug(f"Retrieved Readwise API token: {mask_token(token)}")
    else:
        logger.debug("No Readwise API token found")

    return token


def get_database_path() -> str:
    """Get the path to the SQLite database file.

    Returns:
        str: Path to the database file
    """
    path = get_config_value("database_path", "")
    if not path:
        # Set default path if not configured
        path = str(get_data_dir() / "kindle2readwise.db")
        set_config_value("database_path", path)
    return path


def is_configured() -> bool:
    """Check if the application has been configured with required settings.

    Returns:
        bool: True if configured, False otherwise
    """
    # Currently, only checks if Readwise token is set
    token = get_readwise_token()
    return bool(token)


def list_config() -> dict[str, Any]:
    """Get a dictionary of all configuration values for display.

    This masks sensitive values like API tokens.

    Returns:
        Dict[str, Any]: Configuration values safe for display
    """
    config = load_config()
    display_config = config.copy()

    # Add the token (masked) for display
    token = get_readwise_token()
    if token:
        display_config["readwise_token"] = mask_token(token)
    else:
        display_config["readwise_token"] = "[Not Set]"

    return display_config
