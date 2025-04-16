# Dependency Management Specification

## Overview

This document outlines the dependency management approach for the kindle2readwise application using UV, a modern Python package manager that provides faster and more reliable dependency resolution than traditional tools like pip.

## Package Manager

The application will use [UV](https://github.com/astral-sh/uv) as the primary package manager for the following reasons:

- Significantly faster installation and dependency resolution
- Reliable lockfile mechanism for deterministic builds
- Native virtual environment management
- Improved compatibility with modern Python packaging standards
- Support for organizing dependencies in optional groups

## Project Configuration

### pyproject.toml

Dependencies will be managed through a `pyproject.toml` file in the project root, following modern Python packaging standards:

```toml
[project]
name = "kindle2readwise"
version = "0.1.0"
description = "Export Kindle highlights to Readwise"
readme = "README.md"
requires-python = ">=3.12"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
dependencies = [
    "requests>=2.31.0",      # HTTP requests for API communication
    "sqlite-utils>=3.35",    # SQLite database utilities
    "pydantic>=2.0.0",       # Data validation
    "rich>=13.0.0",          # Rich terminal output
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",         # Testing framework
    "pytest-cov>=6.0.0",     # Test coverage
    "pre-commit>=4.2.0",     # Pre-commit hooks
    "jupyter>=1.1.1",        # Jupyter notebooks
    "ruff>=0.11.2",          # Linting and formatting
]
ci = [
    "pytest>=8.0.0",
    "pytest-cov>=6.0.0",
]

[project.scripts]
kindle2readwise = "kindle2readwise.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Dependencies

The application will have the following main dependencies:

| Package | Purpose | Version Constraint |
|---------|---------|-------------------|
| requests | HTTP requests for Readwise API | >=2.31.0 |
| sqlite-utils | SQLite database management | >=3.35 |
| pydantic | Data validation and serialization | >=2.0.0 |
| rich | Enhanced terminal output | >=13.0.0 |

### Development Dependencies

Development dependencies will be organized in an optional "dev" group:

| Package | Purpose | Version Constraint |
|---------|---------|-------------------|
| pytest | Testing framework | >=8.0.0 |
| pytest-cov | Test coverage | >=6.0.0 |
| pre-commit | Git hooks | >=4.2.0 |
| jupyter | Jupyter notebooks | >=1.1.1 |
| ruff | Linting and formatting | >=0.11.2 |

A separate "ci" group is also defined for continuous integration environments with a minimal set of dependencies needed for testing.

## Environment Management

### Virtual Environment

- The application will use a UV-managed virtual environment located in `.venv/`
- This environment will isolate the application's dependencies from the system Python
- The environment can be created with `uv venv`

### Dependency Installation

For developers working on the project:
```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies with development tools
uv sync --extra dev
```

For users installing the package:
```bash
# Install only runtime dependencies
uv sync
```

### Dependency Locking

- Dependencies will be locked using `uv.lock` to ensure reproducible builds
- The lockfile should be committed to version control
- The lockfile can be updated with `uv lock`

## Dependency Updating

To update dependencies:
1. Update version constraints in `pyproject.toml`
2. Run `uv lock` to update the lockfile
3. Run `uv sync` to install the updated packages

## Execution in Development

To run commands during development:
```bash
# Run application
uv run python -m kindle2readwise

# Run tests
uv run pytest

# Run formatter and linter
uv run ruff format .
uv run ruff check --fix .
```

## Dependency Documentation

- All direct dependencies will be documented with their purpose and version constraints
- The README will include clear installation instructions using UV
- Changes to dependencies will be documented in version control commits
