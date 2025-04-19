"""Version command handler for the kindle2readwise CLI."""

import sys

from ... import __version__


def handle_version(_):
    """Show version information."""
    print(f"kindle2readwise v{__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
