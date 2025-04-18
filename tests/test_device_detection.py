"""Tests for the device detection module."""

import platform
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kindle2readwise.utils.device_detection import (
    _detect_kindle_macos,
    detect_kindle_devices,
    find_kindle_clippings,
)


@pytest.fixture
def mock_volume_structure(tmp_path):
    """Create a mock volume structure for testing."""
    # Create a Kindle-like volume with clippings file
    kindle_dir = tmp_path / "Kindle"
    kindle_dir.mkdir()

    documents_dir = kindle_dir / "documents"
    documents_dir.mkdir()

    clippings_file = documents_dir / "My Clippings.txt"
    clippings_file.write_text("Test clippings content")

    # Create a non-Kindle volume
    other_dir = tmp_path / "OtherDrive"
    other_dir.mkdir()

    return {"root": tmp_path, "kindle_dir": kindle_dir, "clippings_file": clippings_file, "other_dir": other_dir}


@patch("kindle2readwise.utils.device_detection.platform.system")
def test_detect_kindle_devices_calls_correct_platform_function(mock_system):
    """Test that detect_kindle_devices calls the correct platform-specific function."""
    # Test macOS detection
    mock_system.return_value = "Darwin"
    with patch("kindle2readwise.utils.device_detection._detect_kindle_macos") as mock_macos:
        mock_macos.return_value = [("Kindle", Path("/Volumes/Kindle/documents/My Clippings.txt"))]
        result = detect_kindle_devices()
        assert mock_macos.called
        assert len(result) == 1
        assert result[0][0] == "Kindle"

    # Test Windows detection
    mock_system.return_value = "Windows"
    with patch("kindle2readwise.utils.device_detection._detect_kindle_windows") as mock_windows:
        mock_windows.return_value = [("Kindle", Path("E:/documents/My Clippings.txt"))]
        result = detect_kindle_devices()
        assert mock_windows.called
        assert len(result) == 1
        assert result[0][0] == "Kindle"

    # Test Linux detection
    mock_system.return_value = "Linux"
    with patch("kindle2readwise.utils.device_detection._detect_kindle_linux") as mock_linux:
        mock_linux.return_value = [("Kindle", Path("/media/user/Kindle/documents/My Clippings.txt"))]
        result = detect_kindle_devices()
        assert mock_linux.called
        assert len(result) == 1
        assert result[0][0] == "Kindle"

    # Test unsupported platform
    mock_system.return_value = "Unsupported"
    result = detect_kindle_devices()
    assert len(result) == 0


@patch("kindle2readwise.utils.device_detection.platform.system", return_value="Darwin")
def test_find_kindle_clippings_returns_first_device(mock_system, mock_volume_structure):  # noqa: ARG001
    """Test that find_kindle_clippings returns the first detected device's clippings path."""
    mock_devices = [
        ("Kindle", Path("/Volumes/Kindle/documents/My Clippings.txt")),
        ("Kindle Paperwhite", Path("/Volumes/Kindle Paperwhite/documents/My Clippings.txt")),
    ]

    with patch("kindle2readwise.utils.device_detection.detect_kindle_devices", return_value=mock_devices):
        result = find_kindle_clippings()
        assert result == Path("/Volumes/Kindle/documents/My Clippings.txt")

    # Test no devices found
    with patch("kindle2readwise.utils.device_detection.detect_kindle_devices", return_value=[]):
        result = find_kindle_clippings()
        assert result is None


@patch("pathlib.Path")
def test_detect_kindle_macos(mock_path):
    """Test macOS Kindle detection."""
    # Mock volumes directory
    mock_volumes = MagicMock()
    mock_volumes.exists.return_value = True
    mock_volumes.iterdir.return_value = [
        MagicMock(name="Kindle", spec=Path),
        MagicMock(name="OtherDrive", spec=Path),
    ]

    # Setup kindle volume mock
    kindle_volume = mock_volumes.iterdir.return_value[0]
    kindle_volume.is_dir.return_value = True
    kindle_volume.name = "Kindle"

    # Setup other volume mock
    other_volume = mock_volumes.iterdir.return_value[1]
    other_volume.is_dir.return_value = True
    other_volume.name = "OtherDrive"

    # Setup clippings path for Kindle
    kindle_clippings_path = MagicMock(spec=Path)
    kindle_clippings_path.exists.return_value = True

    # Setup clippings path for OtherDrive - should not exist
    other_clippings_path = MagicMock(spec=Path)
    other_clippings_path.exists.return_value = False

    # Mock the __truediv__ (/) operator for Path
    kindle_volume.__truediv__.return_value = kindle_clippings_path
    other_volume.__truediv__.return_value = other_clippings_path

    # Make Path return the correct mock
    mock_path.return_value = mock_volumes

    # Test detection
    with patch("kindle2readwise.utils.device_detection.Path", mock_path):
        devices = _detect_kindle_macos()
        assert len(devices) == 1
        assert devices[0][0] == "Kindle"


def test_find_kindle_clippings_integration(monkeypatch, tmp_path):
    """Integration test for find_kindle_clippings using monkeypatch."""
    # Setup mock file system
    kindle_dir = tmp_path / "Kindle"
    kindle_dir.mkdir()
    documents_dir = kindle_dir / "documents"
    documents_dir.mkdir()
    clippings_file = documents_dir / "My Clippings.txt"
    clippings_file.write_text("Test clippings content")

    # Mock platform-specific detection based on current platform
    current_platform = platform.system()

    if current_platform == "Darwin":
        # Mock volumes directory for macOS
        monkeypatch.setattr(
            "kindle2readwise.utils.device_detection._detect_kindle_macos", lambda: [("Kindle", clippings_file)]
        )
    elif current_platform == "Windows":
        # Mock drive detection for Windows
        monkeypatch.setattr(
            "kindle2readwise.utils.device_detection._detect_kindle_windows", lambda: [("Kindle", clippings_file)]
        )
    elif current_platform == "Linux":
        # Mock mount points for Linux
        monkeypatch.setattr(
            "kindle2readwise.utils.device_detection._detect_kindle_linux", lambda: [("Kindle", clippings_file)]
        )
    else:
        pytest.skip(f"Unsupported platform for this test: {current_platform}")

    # Test the function
    result = find_kindle_clippings()
    assert result == clippings_file
