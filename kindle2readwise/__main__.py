"""Allows running the application as a module (python -m kindle2readwise)."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
