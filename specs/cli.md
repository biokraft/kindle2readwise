# Command-Line Interface Specification

## Overview

This document outlines the design and functionality of the command-line interface (CLI) for the kindle2readwise application. The CLI serves as the primary user interface, allowing users to parse Kindle clippings and export them to Readwise.

## Design Goals

The CLI design focuses on:
1. **Simplicity**: Intuitive commands and options
2. **Discoverability**: Self-documenting with helpful error messages
3. **Consistency**: Uniform command structure and option naming
4. **Flexibility**: Support for various workflows and customization
5. **Feedback**: Clear progress indication and results summary

## Command Structure

The application will use a hierarchical command structure with subcommands:

```
kindle2readwise [global options] command [command options] [arguments...]
```

### Main Commands

1. **export**: Parse Kindle clippings and export to Readwise
2. **configure**: Set up and manage application configuration
3. **history**: View past export sessions and statistics
4. **version**: Display version information

## Command: `export`

The primary command for exporting Kindle clippings to Readwise.

### Usage

```
kindle2readwise export [options] [clippings_file]
```

### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--clippings-file`, `-f` | Path | Path to the My Clippings.txt file | My Clippings.txt in current directory |
| `--api-token`, `-t` | String | Readwise API token | From configuration file |
| `--batch-size`, `-b` | Integer | Number of highlights to send in each API request | 100 |
| `--skip-duplicates`, `-s` | Flag | Skip highlights that have been previously exported | True |
| `--force`, `-F` | Flag | Force export of all highlights, ignoring duplicates | False |
| `--dry-run`, `-d` | Flag | Parse clippings but don't export to Readwise | False |
| `--output`, `-o` | Path | Save parsed highlights to file | None |
| `--format` | String | Output format for saved highlights (json, csv) | json |
| `--verbose`, `-v` | Flag | Enable verbose output | False |
| `--quiet`, `-q` | Flag | Suppress all output except errors | False |

### Example Usage

```bash
# Basic usage with default clippings file
kindle2readwise export

# Specify clippings file and API token
kindle2readwise export -f ~/Downloads/My\ Clippings.txt -t YOUR_API_TOKEN

# Dry run with verbose output
kindle2readwise export --dry-run --verbose

# Export all highlights, including duplicates
kindle2readwise export --force

# Export and save to file
kindle2readwise export --output highlights.json
```

## Command: `configure`

Manages application configuration settings.

### Usage

```
kindle2readwise configure [options]
```

### Options

| Option | Type | Description |
|--------|------|-------------|
| `--show` | Flag | Display current configuration |
| `--set` | Key=Value | Set a configuration value |
| `--reset` | Flag | Reset configuration to defaults |
| `--token` | String | Set Readwise API token |
| `--default-file` | Path | Set default clippings file path |

### Example Usage

```bash
# Interactive configuration
kindle2readwise configure

# Set API token
kindle2readwise configure --token YOUR_API_TOKEN

# Set default clippings file
kindle2readwise configure --default-file ~/Kindle/documents/My\ Clippings.txt

# Show current configuration
kindle2readwise configure --show
```

## Command: `history`

View past export sessions and statistics.

### Usage

```
kindle2readwise history [options]
```

### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--limit`, `-l` | Integer | Number of sessions to display | 10 |
| `--details`, `-d` | Flag | Show detailed information | False |
| `--session`, `-s` | Integer | Show details for specific session ID | None |
| `--format` | String | Output format (text, json, csv) | text |

### Example Usage

```bash
# Show recent export sessions
kindle2readwise history

# Show detailed information for recent sessions
kindle2readwise history --details

# Show specific session
kindle2readwise history --session 123

# Export history to JSON
kindle2readwise history --format json > history.json
```

## Command: `version`

Display version information.

### Usage

```
kindle2readwise version
```

### Example Output

```
kindle2readwise v1.0.0
Python: 3.9.6
Platform: macOS-13.0
```

## Global Options

These options apply to all commands:

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--help`, `-h` | Flag | Show help message and exit | False |
| `--config`, `-c` | Path | Use custom configuration file | ~/.kindle2readwise.conf |
| `--log-level` | String | Set logging level (debug, info, warning, error) | info |
| `--log-file` | Path | Log output to file | None |

## User Experience Details

### Progress Feedback

For long-running operations, the CLI will provide:
- Progress bars for parsing and exporting
- Periodic status updates
- Clear completion summaries

### Error Handling

The CLI will provide:
- Descriptive error messages
- Suggestions for resolving common errors
- Appropriate exit codes

### Help System

The help system will include:
- Command and option descriptions
- Examples for common use cases
- Related commands suggestions

## Implementation

The CLI will be implemented using the `argparse` module from the Python standard library. Key design aspects include:

1. **Modular Command Implementation**: Each command will be implemented in a separate function
2. **Consistent Return Codes**: Standard exit codes to indicate success or specific failures
3. **Progressive Disclosure**: Basic commands are simple, advanced features available when needed
4. **Terminal Compatibility**: Support for various terminal environments and capabilities

## Global Installation

The application is designed to support installation as a global command-line tool using UV's tool installation capabilities. This allows users to access the `kindle2readwise` command from any directory.

### Installation Methods

```bash
# Standard global installation
uv tool install .

# Development/editable installation
uv tool install --editable .
```

### Design Considerations for Global Usage

1. **Configuration Path Awareness**: The CLI must handle configuration files in platform-appropriate locations:
   - Linux: `~/.config/kindle2readwise/`
   - macOS: `~/Library/Application Support/kindle2readwise/`
   - Windows: `%APPDATA%\kindle2readwise\`

2. **Path Resolution**: For file arguments (like clippings files), support both:
   - Absolute paths
   - Relative paths that resolve correctly regardless of current working directory

3. **Environment Independence**: Operation should be consistent regardless of the directory from which the command is invoked

4. **Access Control**: Respect system permissions when accessing configuration and database files

5. **Update Mechanism**: Provide commands to check for and apply updates to the globally installed tool
