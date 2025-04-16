# Application Structure Specification

## Overview

This document outlines the overall structure and architecture of the kindle2readwise application. The application is designed to parse Kindle clippings and export them to Readwise with a focus on reliability, maintainability, and extensibility.

## Design Principles

1. **Modularity**: The application is structured into independent, loosely coupled modules
2. **Single Responsibility**: Each component has a clear, focused purpose
3. **Testability**: Components are designed to be easily testable in isolation
4. **Error Handling**: Robust error handling at all levels of the application
5. **User Experience**: Clear feedback and logging throughout the process

## Core Components

The application consists of the following core components:

### 1. Kindle Clippings Parser

Responsible for:
- Reading Kindle clippings files
- Parsing the text into structured data
- Handling various formats and edge cases
- Providing a clean, consistent data model

### 2. Readwise API Client

Responsible for:
- Authenticating with the Readwise API
- Preparing and sending highlight data
- Handling API responses and errors
- Managing rate limits and retries

### 3. Deduplication System

Responsible for:
- Maintaining a database of exported highlights
- Identifying potential duplicates
- Preventing redundant exports
- Tracking export history

### 4. Logging System

Responsible for:
- Providing comprehensive application logging
- Supporting different log levels and outputs
- Assisting with debugging and troubleshooting
- Tracking application performance

### 5. Application Core

Responsible for:
- Coordinating the overall workflow
- Handling user input and configuration
- Managing the execution pipeline
- Providing user feedback

## Directory Structure

Following the standard Python project structure:

```
kindle2readwise/
├── kindle2readwise/     # Main package
│   ├── __init__.py                # Package initialization
│   ├── __main__.py                # Entry point for direct execution
│   ├── cli.py                     # Command-line interface
│   ├── config.py                  # Configuration management
│   ├── parser/                    # Kindle clippings parser module
│   │   ├── __init__.py
│   │   ├── parser.py              # Core parsing logic
│   │   └── models.py              # Data models for clippings
│   ├── readwise/                  # Readwise API module
│   │   ├── __init__.py
│   │   ├── client.py              # API client implementation
│   │   └── models.py              # Data models for API
│   ├── database/                  # Database module
│   │   ├── __init__.py
│   │   ├── dao.py                 # Data access objects
│   │   └── models.py              # Database models
│   └── utils/                     # Utility functions
│       ├── __init__.py
│       └── logging.py             # Logging configuration
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_readwise.py
│   ├── test_database.py
│   ├── test_utils.py
│   └── fixtures/                  # Test data
│       └── clippings_sample.txt
├── specs/                         # Specification documents
├── .venv/                         # Virtual environment (not in version control)
├── README.md                      # Project overview
├── SPECS.md                       # Top-level spec summary/entry point
├── pyproject.toml                 # Project metadata and dependencies
├── uv.lock                        # UV lockfile for dependency versions
├── .gitignore                     # Git ignore file
├── .pre-commit-config.yaml        # Pre-commit hook configuration
└── LICENSE                        # Project license
```

## Module Organization Guidelines

- **Keep modules focused**: Each module should have a single responsibility
- **Use `__init__.py` appropriately**: Export public interfaces while hiding implementation details
- **Implement lazy imports**: For heavy dependencies to optimize startup time
- **Use relative imports within packages**: For better maintainability and refactoring

## Configuration Management

The application will handle configuration through:

1. **Default configuration**: Sensible defaults defined in code
2. **Configuration file**: User-specific settings stored in a config file
3. **Command-line arguments**: Override settings for a single execution
4. **Environment variables**: Support for environment-based configuration

Configuration will be stored in appropriate locations based on the platform:
- Linux: `~/.config/kindle2readwise/`
- macOS: `~/Library/Application Support/kindle2readwise/`
- Windows: `%APPDATA%\kindle2readwise\`

## Dependency Management

The application will use UV for dependency management:

- Dependencies will be defined in `pyproject.toml`
- A lockfile (`uv.lock`) will ensure reproducible builds
- Virtual environment will be created with `uv venv`

For details, see the [Dependencies](dependencies.md) specification.

## Execution Flow

The typical execution flow of the application is:

1. User provides:
   - Path to Kindle clippings file
   - Readwise API token (first-time setup)
   - Optional configuration parameters

2. Application:
   - Validates inputs and configuration
   - Reads and parses the clippings file
   - Checks for duplicates against local database
   - Exports new highlights to Readwise
   - Records successful exports in the database
   - Provides summary of the operation

## Error Handling Strategy

The application implements a layered error handling approach:

1. **Function-level**: Each function handles and logs its specific errors
2. **Module-level**: Modules handle broader errors related to their domain
3. **Application-level**: Global error handling for unexpected issues
4. **User-level**: Clear error messages with suggested remediation steps

## Extensibility Points

The application is designed to be extended in the following ways:

1. **Additional parsers**: Support for other clipping formats
2. **Alternative export targets**: Beyond Readwise to other platforms
3. **Enhanced filtering**: More sophisticated highlight filtering options
4. **User interfaces**: CLI first, with potential for GUI in the future

## Development Tools and Practices

The application development will follow these practices:

1. **Version Control**: Git for source code management
2. **Testing**: Pytest for unit and integration tests
3. **Type Hints**: Python type annotations throughout the codebase
4. **Linting and Formatting**: Ruff and Black for code quality
5. **Documentation**: Docstrings and dedicated documentation
6. **CI/CD**: Automated testing and deployment
