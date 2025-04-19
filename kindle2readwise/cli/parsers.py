"""Command-line argument parsers for kindle2readwise."""

import argparse

from .. import __version__

DEFAULT_CLIPPINGS_PATH = "My Clippings.txt"


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Export Kindle clippings ('My Clippings.txt') to Readwise.", prog="kindle2readwise"
    )

    # Global options
    _setup_global_options(parser)

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Add all command subparsers
    _setup_export_command(subparsers)
    _setup_config_command(subparsers)
    _setup_history_command(subparsers)
    _setup_highlights_command(subparsers)
    _setup_version_command(subparsers)

    return parser


def _setup_global_options(parser):
    """Set up global options for the CLI."""
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}", help="Show program's version number and exit."
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO).",
    )
    parser.add_argument(
        "--log-file", type=str, default=None, help="Log output to a specified file in addition to the console."
    )


def _setup_export_command(subparsers):
    """Set up the export command and its options."""
    from .commands.export import handle_export

    parser_export = subparsers.add_parser("export", help="Export Kindle highlights to Readwise")
    parser_export.add_argument(
        "file",
        type=str,
        nargs="?",
        default=DEFAULT_CLIPPINGS_PATH,
        help=f"Path to the 'My Clippings.txt' file (default: {DEFAULT_CLIPPINGS_PATH})",
    )
    parser_export.add_argument(
        "--api-token", "-t", type=str, help="Readwise API token (or use the READWISE_API_TOKEN environment variable)."
    )
    parser_export.add_argument(
        "--db-path",
        type=str,
        help="Path to the SQLite database (default: from config or database directory).",
    )
    parser_export.add_argument("--force", "-f", action="store_true", help="Force export of all highlights.")
    parser_export.add_argument(
        "--dry-run", "-d", action="store_true", help="Simulate export without sending to Readwise."
    )
    parser_export.add_argument("--output", "-o", type=str, help="Output highlights to a file instead of Readwise.")
    parser_export.add_argument("--devices", action="store_true", help="List detected Kindle devices and exit.")
    parser_export.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Review and select highlights interactively before export",
    )
    parser_export.set_defaults(func=handle_export)


def _setup_config_command(subparsers):
    """Set up the config command and its subcommands."""
    from .commands.config import handle_configure

    parser_config = subparsers.add_parser("config", help="Configure the application")
    config_subparsers = parser_config.add_subparsers(dest="config_command", help="Configuration commands")

    # Config show subcommand
    parser_config_show = config_subparsers.add_parser("show", help="Show current configuration")
    parser_config_show.set_defaults(func=handle_configure)

    # Config token subcommand
    parser_config_token = config_subparsers.add_parser("token", help="Set the Readwise API token")
    parser_config_token.add_argument(
        "token", nargs="?", type=str, help="The Readwise API token (omit for interactive prompt)"
    )
    parser_config_token.set_defaults(func=handle_configure)

    # Config set subcommand
    parser_config_set = config_subparsers.add_parser("set", help="Set a configuration value")
    parser_config_set.add_argument("key", type=str, help="Configuration key to set")
    parser_config_set.add_argument("value", type=str, help="Value to set")
    parser_config_set.set_defaults(func=handle_configure)

    # Config paths subcommand
    parser_config_paths = config_subparsers.add_parser("paths", help="Show configuration and data paths")
    parser_config_paths.set_defaults(func=handle_configure)

    parser_config.set_defaults(func=handle_configure)


def _setup_history_command(subparsers):
    """Set up the history command and its options."""
    from .commands.history import handle_history

    parser_history = subparsers.add_parser("history", help="View export history")
    parser_history.add_argument("--session", type=str, help="Show details for a specific session")
    parser_history.add_argument("--format", type=str, choices=["json", "csv"], help="Output format for history")
    parser_history.add_argument("--details", action="store_true", help="Show detailed session details")
    parser_history.add_argument("--limit", type=int, help="Limit the number of history entries to display")
    parser_history.set_defaults(func=handle_history)


def _setup_highlights_command(subparsers):
    """Set up the highlights command and its subcommands."""
    from .commands.highlights import handle_highlights

    parser_highlights = subparsers.add_parser("highlights", help="Manage stored highlights")
    highlights_subparsers = parser_highlights.add_subparsers(
        dest="highlights_command", help="Highlight management commands"
    )

    # Highlights list subcommand
    parser_highlights_list = highlights_subparsers.add_parser("list", help="List and search highlights in the database")
    parser_highlights_list.add_argument("--title", type=str, help="Filter by book title (partial match)")
    parser_highlights_list.add_argument("--author", type=str, help="Filter by author (partial match)")
    parser_highlights_list.add_argument("--text", type=str, help="Search in highlight text (partial match)")
    parser_highlights_list.add_argument("--limit", type=int, default=20, help="Maximum number of results (default: 20)")
    parser_highlights_list.add_argument(
        "--offset", type=int, default=0, help="Results offset for pagination (default: 0)"
    )
    parser_highlights_list.add_argument(
        "--sort",
        type=str,
        default="date_exported",
        choices=["date_exported", "date_highlighted", "title", "author"],
        help="Field to sort by (default: date_exported)",
    )
    parser_highlights_list.add_argument(
        "--order", type=str, default="desc", choices=["asc", "desc"], help="Sort direction (default: desc)"
    )
    parser_highlights_list.add_argument(
        "--format", type=str, choices=["text", "json", "csv"], help="Output format (default: text)"
    )

    # Highlights books subcommand
    parser_highlights_books = highlights_subparsers.add_parser("books", help="List all books with highlight counts")
    parser_highlights_books.add_argument(
        "--format", type=str, choices=["text", "json", "csv"], help="Output format (default: text)"
    )

    # Highlights delete subcommand
    parser_highlights_delete = highlights_subparsers.add_parser("delete", help="Delete highlights or books")
    delete_group = parser_highlights_delete.add_mutually_exclusive_group(required=True)
    delete_group.add_argument("--id", type=int, help="Delete a single highlight by ID")
    delete_group.add_argument("--book", type=str, help="Delete all highlights for a specific book")
    parser_highlights_delete.add_argument("--author", type=str, help="Author name (when deleting by book)")
    parser_highlights_delete.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")

    # Set default handler for the main highlights command
    parser_highlights.set_defaults(func=handle_highlights)


def _setup_version_command(subparsers):
    """Set up the version command."""
    from .commands.version import handle_version

    parser_version = subparsers.add_parser("version", help="Show version information")
    parser_version.set_defaults(func=handle_version)
