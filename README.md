# kindle2readwise

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/)
[![Latest release](https://img.shields.io/github/v/release/biokraft/kindle2readwise)](https://github.com/biokraft/kindle2readwise/releases/latest)

A Python application for exporting Kindle highlights to Readwise. This tool parses your Kindle's "My Clippings.txt" file and sends the highlights to your Readwise account, helping you manage and review your reading highlights efficiently.

## Documentation

**Looking to use kindle2readwise?** Visit our [official documentation](docs/index.md) for installation instructions, usage guides, examples, and troubleshooting help.

## Features

- Parse Kindle highlights from the "My Clippings.txt" file
- Export your highlights to Readwise using their API
- Prevent duplicate exports with a local database
- Extensive logging for easy debugging and traceability
- Simple command-line interface

## Quick Start

### Requirements

- Python 3.12 or newer
- [UV package manager](https://github.com/astral-sh/uv)
- Kindle device or access to a "My Clippings.txt" file
- Readwise account and API token (get yours at https://readwise.io/access_token)

### Installation

```bash
# Install the latest version
uv tool install git+https://github.com/biokraft/kindle2readwise.git

# Or install a specific version (e.g., v0.1.0)
# uv tool install git+https://github.com/biokraft/kindle2readwise.git@v0.1.0
```

### Basic Usage

```bash
# Configure your Readwise API token (one-time setup)
kindle2readwise configure --token YOUR_API_TOKEN

# Export highlights from your Kindle
kindle2readwise export --clippings-file /path/to/My\ Clippings.txt

# Get help on any command
kindle2readwise --help
```

For detailed usage examples and more advanced features, please refer to the [official documentation](docs/index.md).

## Development

This section is for contributors who want to develop or modify kindle2readwise.

### Setting Up the Development Environment

```bash
# Clone the repository
git clone https://github.com/biokraft/kindle2readwise.git
cd kindle2readwise

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows

# Install dependencies for development (includes all extras)
uv sync --all-extras
```

### Local Development Installation

To install kindle2readwise as a global command-line tool while developing:

```bash
# From the project directory
uv tool install --editable .
```

This allows your code changes to be immediately reflected in the globally installed command.

### Dependency Management with UV

- Add main dependencies: `uv add <package>`
- Add development dependencies: `uv add --optional dev <package>`
- List all dependencies: `uv tree`
- Update lockfile: `uv lock`

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality and consistency. To set up:

```bash
# Install pre-commit (already included in dev dependencies)
uv run pre-commit install

# Run hooks manually on all files
uv run pre-commit run --all-files
```

### Code Quality Tools

Run tests:

```bash
uv run pytest
```

## Project Documentation

This project is under active development. See [SPECS.md](SPECS.md) for detailed specifications and development plans.

## License

[Apache License](LICENSE)

## Acknowledgements

- [Readwise](https://readwise.io) for their API and service
- All contributors to the project
