"""Kindle device detection utilities.

This module provides functions to detect connected Kindle devices
across different operating systems (Windows, macOS, Linux).

Note:
    For newer Kindle models (Scribe and 2024 models), Amazon requires:
    1. Using the Send to Kindle app for Mac OS
    2. Accessing files through its USB File Manager feature

    These newer models may not be directly detectable using the standard methods.
"""

import logging
import os
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Common Kindle device identifiers
KINDLE_IDENTIFIERS = [
    "Kindle",
    "kindle",
    "KINDLE",
    "Amazon Kindle",
]

# Common locations of My Clippings.txt on Kindle devices
CLIPPINGS_RELATIVE_PATH = "documents/My Clippings.txt"


def detect_kindle_devices() -> list[tuple[str, Path]]:
    """Detect connected Kindle devices across platforms.

    Returns:
        List of tuples containing (device_name, clippings_path)
    """
    system = platform.system()

    logger.debug("Detecting Kindle devices on %s platform", system)

    if system == "Darwin":  # macOS
        return _detect_kindle_macos()
    if system == "Windows":
        return _detect_kindle_windows()
    if system == "Linux":
        return _detect_kindle_linux()
    logger.warning("Unsupported operating system for Kindle detection: %s", system)
    return []


def _detect_kindle_macos() -> list[tuple[str, Path]]:
    """Detect Kindle devices on macOS.

    Returns:
        List of tuples containing (device_name, clippings_path)
    """
    devices = []

    # Check /Volumes directory for mounted Kindles
    volumes_dir = Path("/Volumes")
    if not volumes_dir.exists():
        logger.debug("/Volumes directory not found on macOS")
        return devices

    # Check each volume to see if it might be a Kindle
    for volume in volumes_dir.iterdir():
        if not volume.is_dir():
            continue

        volume_name = volume.name

        # Check if volume name contains Kindle identifier
        if any(kindle_id in volume_name for kindle_id in KINDLE_IDENTIFIERS):
            clippings_path = volume / CLIPPINGS_RELATIVE_PATH
            if clippings_path.exists():
                logger.info("Found Kindle device: %s with clippings at %s", volume_name, clippings_path)
                devices.append((volume_name, clippings_path))
                continue

        # If name doesn't match, check for documents/My Clippings.txt
        clippings_path = volume / CLIPPINGS_RELATIVE_PATH
        if clippings_path.exists():
            logger.info("Found probable Kindle device: %s with clippings at %s", volume_name, clippings_path)
            devices.append((volume_name, clippings_path))

    return devices


def _detect_kindle_windows() -> list[tuple[str, Path]]:
    """Detect Kindle devices on Windows.

    Returns:
        List of tuples containing (device_name, clippings_path)
    """
    devices = []

    # Check all drive letters
    import ctypes
    import string

    # Get bitmask of available drives
    bitmask = ctypes.windll.kernel32.GetLogicalDrives() if hasattr(ctypes, "windll") else 0

    for letter in string.ascii_uppercase:
        # Check if drive exists using bitmask
        if not (bitmask & (1 << (ord(letter) - ord("A")))):
            continue

        drive_path = Path(f"{letter}:")

        # Skip if drive doesn't exist
        if not drive_path.exists():
            continue

        # Check for Kindle clippings file
        clippings_path = drive_path / CLIPPINGS_RELATIVE_PATH
        if clippings_path.exists():
            try:
                # Try to get volume label
                volume_info = subprocess.check_output(
                    ["cmd", "/c", f"vol {letter}:"], stderr=subprocess.STDOUT, text=True
                )
                volume_name = volume_info.strip().split("\n")[0].split(" ")[-1]
                if any(kindle_id in volume_name for kindle_id in KINDLE_IDENTIFIERS):
                    logger.info("Found Kindle device on %s: with clippings at %s", volume_name, clippings_path)
                    devices.append((volume_name, clippings_path))
                else:
                    logger.info("Found probable Kindle device on %s: with clippings at %s", volume_name, clippings_path)
                    devices.append((f"Drive {letter}", clippings_path))
            except (subprocess.SubprocessError, IndexError) as e:
                logger.debug("Error getting volume info for drive %s: %s", letter, e)
                # Still add the device if clippings file exists
                devices.append((f"Drive {letter}", clippings_path))

    return devices


def _detect_kindle_linux() -> list[tuple[str, Path]]:
    """Detect Kindle devices on Linux.

    Returns:
        List of tuples containing (device_name, clippings_path)
    """
    devices = []

    # Common Linux mount points
    mount_points = [
        Path("/media"),
        Path("/mnt"),
        Path(os.path.expanduser("~/.local/media")),
        Path(f"/media/{os.getenv('USER')}"),
    ]

    # Check each mount point
    for mount_point in mount_points:
        if not mount_point.exists() or not mount_point.is_dir():
            continue

        # Check first level subdirectories
        for device_dir in mount_point.iterdir():
            if not device_dir.is_dir():
                continue

            # Check if name matches Kindle identifiers
            device_name = device_dir.name
            is_likely_kindle = any(kindle_id in device_name for kindle_id in KINDLE_IDENTIFIERS)

            # Also check second level for systems like Ubuntu that create user subdirs
            subdirs_to_check = [device_dir]
            if not is_likely_kindle:
                for subdir in device_dir.iterdir():
                    if subdir.is_dir() and any(kindle_id in subdir.name for kindle_id in KINDLE_IDENTIFIERS):
                        subdirs_to_check.append(subdir)

            # Check each candidate path for clippings file
            for check_dir in subdirs_to_check:
                clippings_path = check_dir / CLIPPINGS_RELATIVE_PATH
                if clippings_path.exists():
                    logger.info("Found Kindle device: %s with clippings at %s", check_dir.name, clippings_path)
                    devices.append((check_dir.name, clippings_path))

    return devices


def find_kindle_clippings() -> Path | None:
    """Find the My Clippings.txt file from a connected Kindle device.

    Returns:
        Path to the clippings file if found, None otherwise
    """
    kindle_devices = detect_kindle_devices()

    if not kindle_devices:
        logger.debug("No Kindle devices detected")
        return None

    # Return the clippings path from the first device found
    if kindle_devices:
        device_name, clippings_path = kindle_devices[0]
        logger.info("Using Kindle clippings from %s: %s", device_name, clippings_path)
        return clippings_path

    return None


def format_device_list(devices: list[tuple[str, Path]]) -> str:
    """Format the list of detected devices for display.

    Args:
        devices: List of tuples containing (device_name, clippings_path)

    Returns:
        Formatted string for display
    """
    if not devices:
        return "No Kindle devices detected.\n\n" + _get_newer_kindle_notice()

    lines = [f"Detected {len(devices)} Kindle device(s):"]
    lines.append("------------------------------------")

    for i, (device_name, clippings_path) in enumerate(devices, 1):
        lines.append(f"{i}. {device_name}")
        lines.append(f"   Clippings file: {clippings_path}")

        if clippings_path.exists():
            lines.append("   Status: Available")
        else:
            lines.append("   Status: Not available (file not found)")
        lines.append("")

    lines.append("To use a specific device, run:")
    lines.append("  kindle2readwise export CLIPPINGS_PATH")
    lines.append("Where CLIPPINGS_PATH is the path shown above.")

    lines.append("\n" + _get_newer_kindle_notice())

    return "\n".join(lines)


def _get_newer_kindle_notice() -> str:
    """Return a notice about newer Kindle models.

    Returns:
        String containing information about newer Kindle models
    """
    return """Note for newer Kindle models (Scribe and 2024 models):
Amazon requires:
1. Using the Send to Kindle app for Mac OS
2. Accessing files through its USB File Manager feature

To export clippings from your Kindle:
1. Download and install Send to Kindle app from Amazon
2. Use the USB File Manager to copy My Clippings.txt to your computer
3. Then run: kindle2readwise export /path/to/saved/My\\ Clippings.txt"""
