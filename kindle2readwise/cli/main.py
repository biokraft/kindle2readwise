"""Main CLI entry point for kindle2readwise."""

import logging
import sys

from ..logging_config import setup_logging
from .parsers import create_parser

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the CLI application."""
    parser = create_parser()

    # Parse arguments and set up logging
    args = parser.parse_args()

    # Configure logging based on arguments
    level_name = args.log_level  # This already has the name as a string
    setup_logging(level=level_name, log_file=args.log_file)

    # Call the appropriate function
    try:
        args.func(args)
    except Exception as e:
        logger.error("Unhandled exception: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
