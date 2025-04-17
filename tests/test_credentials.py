"""Tests for the credentials utility module.

These tests verify that the credentials utility functions work correctly
for securely storing and retrieving API tokens and other credentials.
"""

import os
import tempfile
from pathlib import Path

import pytest

from kindle2readwise.utils.credentials import (
    decode_token,
    encode_token,
    load_token_from_file,
    mask_token,
    save_token_to_file,
)


class TestTokenEncoding:
    """Tests for token encoding and decoding."""

    def test_encode_decode_token(self):
        """Test encoding and decoding a token."""
        original = "test-secret-token-123456"
        encoded = encode_token(original)

        # Ensure encoded is different from original
        assert encoded != original

        # Decoding should match original
        decoded = decode_token(encoded)
        assert decoded == original

    def test_encode_empty_token(self):
        """Test encoding an empty token."""
        encoded = encode_token("")
        assert encoded == ""

    def test_decode_empty_token(self):
        """Test decoding an empty token."""
        decoded = decode_token("")
        assert decoded == ""

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        decoded = decode_token("not-valid-base64@!")
        assert decoded == ""  # Should handle error and return empty string


class TestTokenFileOperations:
    """Tests for token file operations."""

    def test_save_and_load_token(self):
        """Test saving and loading a token from a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "test_token"
            test_token = "test-secret-token-123456"

            # Save token
            result = save_token_to_file(test_token, token_file)
            assert result is True
            assert token_file.exists()

            # Load token
            loaded_token = load_token_from_file(token_file)
            assert loaded_token == test_token

    def test_save_token_creates_parent_dirs(self):
        """Test saving a token creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "nested" / "dirs" / "test_token"
            test_token = "test-secret-token-123456"

            # Save token (should create directories)
            result = save_token_to_file(test_token, token_file)
            assert result is True
            assert token_file.exists()

            # Parent directories should exist
            assert token_file.parent.exists()

    def test_load_token_nonexistent_file(self):
        """Test loading a token from a nonexistent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "nonexistent_token"

            # Try to load token from nonexistent file
            loaded_token = load_token_from_file(token_file)
            assert loaded_token == ""

    def test_load_token_empty_file(self):
        """Test loading a token from an empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "empty_token"

            # Create empty file
            token_file.touch()

            # Try to load token from empty file
            loaded_token = load_token_from_file(token_file)
            assert loaded_token == ""

    def test_file_permissions(self):
        """Test file permissions are set correctly when on Unix."""
        if os.name != "posix":
            pytest.skip("Test only applicable on Unix-like systems")

        with tempfile.TemporaryDirectory() as temp_dir:
            token_file = Path(temp_dir) / "test_token"
            test_token = "test-secret-token-123456"

            # Save token
            save_token_to_file(test_token, token_file)

            # Check permissions (should be 0o600 = owner read/write only)
            owner_read_write_only = 0o600
            mode = token_file.stat().st_mode & 0o777  # Get permission bits
            assert mode == owner_read_write_only, f"Expected {owner_read_write_only:o}, got {mode:o}"


class TestTokenMasking:
    """Tests for token masking functionality."""

    def test_mask_token_normal(self):
        """Test masking a normal-length token."""
        token = "abcdefghijklmnopqrstuvwxyz"
        masked = mask_token(token)

        # Should show first 4 and last 4 characters
        assert masked.startswith("abcd")
        assert masked.endswith("wxyz")

        # Should have asterisks in the middle
        assert "*" in masked
        assert masked.count("*") == len(token) - 8  # Middle chars replaced

        # Total length should be preserved
        assert len(masked) == len(token)

    def test_mask_token_short(self):
        """Test masking a short token."""
        token = "abcde"
        masked = mask_token(token)

        # Short tokens should be fully masked
        assert masked == "*****"
        assert len(masked) == len(token)

    def test_mask_empty_token(self):
        """Test masking an empty token."""
        masked = mask_token("")
        assert masked == ""
