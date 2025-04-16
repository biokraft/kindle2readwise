# kindle2readwise

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

### Using UV (Recommended)

```bash
# Install UV if you don't have it
pip install uv

# Clone the repository
git clone https://github.com/yourusername/kindle2readwise.git
cd kindle2readwise

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
uv sync
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

For development work, install with development dependencies:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest
```

Format code:

```bash
uv run ruff format .
uv run ruff check --fix .
```

## Project Documentation

This project is under active development. See [SPECS.md](SPECS.md) for detailed specifications and development plans.

## License

[MIT License](LICENSE)

## Acknowledgements

- [Readwise](https://readwise.io) for their API and service
- All contributors to the project
