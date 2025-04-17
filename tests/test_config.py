"""Tests for the configuration management module.

These tests verify the functionality of the configuration management system,
including loading/saving config and handling API tokens securely.
"""

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from kindle2readwise.config import (
    DEFAULT_CONFIG,
    get_config_dir,
    get_config_value,
    get_data_dir,
    get_readwise_token,
    is_configured,
    list_config,
    load_config,
    save_config,
    set_config_value,
    set_readwise_token,
)
from kindle2readwise.utils.credentials import (
    decode_token,
    encode_token,
    mask_token,
)


@pytest.fixture
def mock_config_dir():
    """Create a temporary directory for config files during tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        with (
            mock.patch("kindle2readwise.config.get_config_dir", return_value=temp_path),
            mock.patch("kindle2readwise.config.get_token_file_path", return_value=temp_path / "readwise_token"),
        ):
            yield temp_path


@pytest.fixture
def mock_config_file(mock_config_dir):
    """Create a temporary config file for testing."""
    config_file = mock_config_dir / "config.json"
    test_config = DEFAULT_CONFIG.copy()
    test_config["test_key"] = "test_value"

    with open(config_file, "w") as f:
        json.dump(test_config, f)

    return config_file


class TestConfigPaths:
    """Tests for configuration path functions."""

    def test_get_config_dir(self):
        """Test that get_config_dir returns a Path object."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)

    def test_get_data_dir(self):
        """Test that get_data_dir returns a Path object."""
        with (
            mock.patch("kindle2readwise.config.get_config_dir") as mock_config_dir,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            fake_config_dir = Path(temp_dir) / "fake_config"
            fake_config_dir.mkdir(exist_ok=True)

            mock_config_dir.return_value = fake_config_dir
            data_dir = get_data_dir()

            assert isinstance(data_dir, Path)
            assert data_dir == fake_config_dir / "data"


class TestConfigOperations:
    """Tests for configuration loading and saving functions."""

    def test_load_config_from_file(self, mock_config_file):
        """Test loading configuration from a file."""
        with mock.patch("kindle2readwise.config.get_config_file_path", return_value=mock_config_file):
            config = load_config()
            assert config["test_key"] == "test_value"
            # Ensure defaults are merged
            for key in DEFAULT_CONFIG:
                assert key in config

    def test_load_config_defaults_if_no_file(self, mock_config_dir):
        """Test loading default configuration when no file exists."""
        nonexistent_path = mock_config_dir / "nonexistent.json"
        with (
            mock.patch("kindle2readwise.config.get_config_file_path", return_value=nonexistent_path),
            mock.patch("kindle2readwise.config.get_data_dir") as mock_data_dir,
            mock.patch("kindle2readwise.config.save_config", return_value=True),
        ):
            mock_data_dir.return_value = mock_config_dir / "data"
            expected_config = DEFAULT_CONFIG.copy()
            config = load_config()

            # Only compare the keys we expect to be the same
            for key in DEFAULT_CONFIG:
                if key != "database_path":
                    assert config[key] == expected_config[key]

    def test_save_config(self, mock_config_dir):
        """Test saving configuration to a file."""
        config_file = mock_config_dir / "test_save.json"
        with mock.patch("kindle2readwise.config.get_config_file_path", return_value=config_file):
            test_config = {"key1": "value1", "key2": 42}
            result = save_config(test_config)

            assert result is True
            assert config_file.exists()

            with open(config_file) as f:
                saved_config = json.load(f)
                assert saved_config == test_config


class TestConfigValues:
    """Tests for getting and setting individual config values."""

    def test_get_config_value(self, mock_config_file):
        """Test getting a configuration value."""
        with mock.patch("kindle2readwise.config.get_config_file_path", return_value=mock_config_file):
            value = get_config_value("test_key")
            assert value == "test_value"

            # Test with default value
            value = get_config_value("nonexistent_key", "default")
            assert value == "default"

    def test_set_config_value(self, mock_config_dir):
        """Test setting a configuration value."""
        config_file = mock_config_dir / "test_set.json"

        with mock.patch("kindle2readwise.config.get_config_file_path", return_value=config_file):
            # First save a default config
            save_config(DEFAULT_CONFIG.copy())

            # Now set a value
            result = set_config_value("new_key", "new_value")
            assert result is True

            # Verify the value was saved
            config = load_config()
            assert config["new_key"] == "new_value"


class TestReadwiseToken:
    """Tests for Readwise API token management."""

    def test_set_get_readwise_token(self, mock_config_dir):
        """Test setting and retrieving a Readwise API token."""
        test_token = "test-api-token-12345"

        # Set the token
        with mock.patch("kindle2readwise.config.get_token_file_path", return_value=mock_config_dir / "readwise_token"):
            result = set_readwise_token(test_token)
            assert result is True

            # Get the token
            token = get_readwise_token()
            assert token == test_token

    def test_is_configured(self, mock_config_dir):
        """Test checking if the application is configured."""
        with mock.patch("kindle2readwise.config.get_token_file_path", return_value=mock_config_dir / "readwise_token"):
            # Initially not configured (no token)
            assert is_configured() is False

            # Set a token
            set_readwise_token("test-token")

            # Now should be configured
            assert is_configured() is True


class TestCredentials:
    """Tests for credential utilities."""

    def test_encode_decode_token(self):
        """Test encoding and decoding a token."""
        original = "test-secret-token-12345"
        encoded = encode_token(original)

        # Encoded should be different from original
        assert encoded != original

        # Decoding should match original
        decoded = decode_token(encoded)
        assert decoded == original

    def test_mask_token(self):
        """Test masking a token for display."""
        token = "abcdefghijklmnopqrstuvwxyz"
        masked = mask_token(token)

        # First 4 chars visible
        assert masked.startswith("abcd")

        # Last 4 chars visible
        assert masked.endswith("wxyz")

        # Middle chars masked
        assert "*" in masked

        # Length preserved
        assert len(masked) == len(token)


class TestConfigDisplay:
    """Tests for configuration display functions."""

    def test_list_config(self, mock_config_file, mock_config_dir):
        """Test getting displayable config with masked sensitive values."""
        with (
            mock.patch("kindle2readwise.config.get_config_file_path", return_value=mock_config_file),
            mock.patch("kindle2readwise.config.get_token_file_path", return_value=mock_config_dir / "readwise_token"),
        ):
            # Set a token
            test_token = "test-secret-token-12345"
            set_readwise_token(test_token)

            # Get displayable config
            config = list_config()

            # Token should be masked
            assert "readwise_token" in config
            assert config["readwise_token"] != test_token
            assert "*" in config["readwise_token"]
