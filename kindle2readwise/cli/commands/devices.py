"""Device detection command handler for the kindle2readwise CLI."""

import logging

from ...utils.device_detection import detect_kindle_devices, format_device_list

logger = logging.getLogger(__name__)


def handle_devices(_):
    """List detected Kindle devices."""
    logger.info("Detecting Kindle devices...")
    devices = detect_kindle_devices()

    formatted_output = format_device_list(devices)
    print(formatted_output)
