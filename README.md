# kindle2readwise

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-black)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen)](https://pre-commit.com/)

A Python application for exporting Kindle highlights to Readwise. This tool parses your Kindle's "My Clippings.txt" file and sends the highlights to your Readwise account, helping you manage and review your reading highlights efficiently.

## Features

- Parse Kindle highlights from the "My Clippings.txt" file
- Export your highlights to Readwise using their API
- Prevent duplicate exports with a local database
- Extensive logging for easy debugging and traceability
- Simple command-line interface

## Requirements

- Python 3.12 or newer
- [UV package manager](https://github.com/astral-sh/uv)
- Kindle device or access to a "My Clippings.txt" file
- Readwise account and API token (get yours at https://readwise.io/access_token)

## Installation

### Installing UV

This project uses the UV package manager. Follow the [official UV installation instructions](https://github.com/astral-sh/uv#installation) to install UV on your system.

### Setting Up the Project

```bash
# Clone the repository
git clone https://github.com/biokraft/kindle2readwise.git
cd kindle2readwise

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows

# Install dependencies for regular usage
uv sync

# Install dependencies for development (includes all extras)
# uv sync --all-extras
```

### Global Installation

To install kindle2readwise as a global command-line tool that can be used from any directory:

```bash
# From the project directory
uv tool install .

# For development/editable installation (changes to code are reflected immediately)
uv tool install --editable .
```

This creates an isolated environment for the tool while making the `kindle2readwise` command globally available in your PATH.

### Uninstallation

To uninstall the globally installed tool:

```bash
# Uninstall the tool
uv tool uninstall kindle2readwise
```

If you need to clean up UV-related data:

```bash
# Clean UV cache (optional)
uv cache clean
```

## Usage

Basic usage:

```bash
kindle2readwise export -f path/to/My\ Clippings.txt -t YOUR_READWISE_API_TOKEN
```

For more options and commands:

```bash
kindle2readwise --help
```

## Development

For development work, install with all dependencies including development extras:

```bash
# Install all dependencies including development extras
uv sync --all-extras

# Alternatively, you can install just the development extras
uv sync --extra dev
```

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

[MIT License](LICENSE)

## Acknowledgements

- [Readwise](https://readwise.io) for their API and service
- All contributors to the project
