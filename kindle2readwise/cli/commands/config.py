"""Configuration command handler for the kindle2readwise CLI."""

import logging
import sys

from ...config import (
    get_config_dir,
    get_config_value,
    get_data_dir,
    get_readwise_token,
    is_configured,
    list_config,
    set_config_value,
    set_readwise_token,
)
from ...utils.credentials import mask_token

logger = logging.getLogger(__name__)


def handle_configure(args):
    """Handle the 'config' command and its subcommands."""
    if not hasattr(args, "config_command") or not args.config_command:
        # Default to 'show' if no subcommand specified
        args.config_command = "show"

    if args.config_command == "show":
        handle_config_show(args)
    elif args.config_command == "token":
        handle_config_token(args)
    elif args.config_command == "set":
        handle_config_set(args)
    elif args.config_command == "paths":
        handle_config_paths(args)
    else:
        logger.error(f"Unknown config subcommand: {args.config_command}")
        sys.exit(1)


def handle_config_show(_):
    """Show current configuration."""
    logger.info("Showing current configuration")
    config = list_config()

    print("\n--- Current Configuration ---")
    for key, value in config.items():
        print(f"{key}: {value}")

    print(f"\nConfiguration directory: {get_config_dir()}")
    print(f"Data directory: {get_data_dir()}")

    if is_configured():
        print("\nApplication is properly configured.")
    else:
        print("\nWARNING: Application is not fully configured.")
        if not get_readwise_token():
            print("Missing Readwise API token. Set it with 'kindle2readwise config token'.")


def handle_config_token(args):
    """Configure the Readwise API token."""
    if args.token:
        # Set the token from the command line argument
        token = args.token
        if set_readwise_token(token):
            logger.info("Readwise API token successfully saved.")
            print(f"Readwise API token {mask_token(token)} successfully saved.")
        else:
            logger.error("Failed to save Readwise API token.")
            print("Failed to save Readwise API token.")
            sys.exit(1)
    else:
        # Interactive mode - prompt for token
        try:
            import getpass

            token = getpass.getpass("Enter your Readwise API token: ")
            if not token:
                print("No token provided. Operation cancelled.")
                return

            if set_readwise_token(token):
                logger.info("Readwise API token successfully saved.")
                print(f"Readwise API token {mask_token(token)} successfully saved.")
            else:
                logger.error("Failed to save Readwise API token.")
                print("Failed to save Readwise API token.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return


def handle_config_set(args):
    """Set a configuration value."""
    if not args.key or not args.value:
        logger.error("Both key and value must be specified.")
        print("Error: Both key and value must be specified.")
        print("Usage: kindle2readwise config set KEY VALUE")
        sys.exit(1)

    # Validate key is a known configuration option
    valid_keys = ["export_format", "auto_confirm", "log_level", "database_path"]
    if args.key not in valid_keys:
        logger.error(f"Unknown configuration key: {args.key}")
        print(f"Error: Unknown configuration key: {args.key}")
        print(f"Valid keys are: {', '.join(valid_keys)}")
        sys.exit(1)

    # Special handling for boolean values
    if args.key == "auto_confirm":
        if args.value.lower() in ("true", "yes", "1", "on"):
            value = True
        elif args.value.lower() in ("false", "no", "0", "off"):
            value = False
        else:
            logger.error(f"Invalid boolean value for {args.key}: {args.value}")
            print("Error: Invalid boolean value. Use 'true' or 'false'.")
            sys.exit(1)
    # Validate log_level values
    elif args.key == "log_level":
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if args.value.upper() not in valid_log_levels:
            logger.error(f"Invalid log level: {args.value}")
            print(f"Error: Invalid log level. Valid values are: {', '.join(valid_log_levels)}")
            sys.exit(1)
        value = args.value.upper()
    else:
        value = args.value

    if set_config_value(args.key, value):
        logger.info(f"Configuration value set: {args.key} = {value}")
        print(f"Configuration updated: {args.key} = {value}")
    else:
        logger.error(f"Failed to set configuration value: {args.key}")
        print("Error: Failed to update configuration.")
        sys.exit(1)


def handle_config_paths(_):
    """Show configuration and data paths."""
    print("\n--- Application Paths ---")
    print(f"Configuration directory: {get_config_dir()}")
    print(f"Data directory: {get_data_dir()}")
    print(f"Database path: {get_config_value('database_path')}")

    # Detect platform
    import sys

    system = sys.platform
    if system.startswith("darwin"):
        platform_name = "macOS"
    elif system.startswith("win"):
        platform_name = "Windows"
    elif system.startswith("linux"):
        platform_name = "Linux"
    else:
        platform_name = system

    print(f"Detected platform: {platform_name}")
