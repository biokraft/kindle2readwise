# kindle2readwise Specifications

## Overview

kindle2readwise is a Python application designed to extract highlights from a Kindle's "My Clippings.txt" file and export them to the Readwise service. The application parses the clippings file into a structured format, then uses the Readwise API to upload the highlights while preventing duplicates.

## Key Features

- Parse Kindle clippings files into structured data
- Export highlights to Readwise via API
- Prevent duplicate exports using local SQLite database
- Provide detailed logging for troubleshooting
- Command-line interface for user interaction

## Specification Documents

The following table lists the detailed specification documents for each domain:

| Domain | Description | Specification Link |
|--------|-------------|-------------------|
| Application Structure | Overall application architecture and organization | [Application Structure](specs/application_structure.md) |
| Kindle Clippings Parser | Format and parsing approach for Kindle clippings | [Kindle Clippings](specs/kindle_clippings.md) |
| Readwise API Integration | Integration with the Readwise API for exporting highlights | [Readwise API](specs/readwise_api.md) |
| Database | SQLite database for deduplication and tracking | [Database](specs/database.md) |
| Logging | Comprehensive logging system | [Logging](specs/logging.md) |
| Command-Line Interface | User interface and commands | [CLI](specs/cli.md) |
| Dependencies | Dependency management using UV | [Dependencies](specs/dependencies.md) |

## Implementation Approach

The application follows these design principles:

1. **Modularity**: Independent components with clear interfaces
2. **Robustness**: Comprehensive error handling and logging
3. **Maintainability**: Clean code structure with documentation
4. **User-Focused**: Simple interface with clear feedback

## Technical Requirements

- Python 3.12 or newer
- UV package manager for dependency management
- SQLite database support
- Internet connection for API access
- Kindle clippings file ("My Clippings.txt")
- Readwise API token

## Development Roadmap

### Phase 1: Core Functionality (Completed)
- Implement Kindle clippings parser (Done)
- Create Readwise API client (Done)
- Establish basic deduplication (Done)

### Phase 2: Reliability and User Experience (Completed)
- Add comprehensive logging (Done)
- Implement database storage (Done)
- Create command-line interface (Done)

### Phase 3: Configuration Management (Completed)
- Implement secure storage for Readwise API token (Done)
- Create config file structure for user preferences (Done)
- Add command-line options for configuration settings (Done)
- Support platform-specific configuration directories (Done)

### Phase 4: Export History (Completed)
- Implement tracking of export sessions (Done)
- Add ability to view past export statistics (Done)
- Create summary reports of exported highlights (Done)
- Allow review of previously exported content (Done)

### Phase 5: Enhanced Database Management (Completed)
- Add command to list highlights stored in the local database with filtering (Done)
- Implement functionality to delete highlights/books from the local database (Done)
- Provide more detailed summary reports extending Phase 4 (Done)

### Phase 6: Kindle Device Detection (Completed)
- Implement automatic Kindle device detection when connected (Done)
- Support cross-platform device detection (Windows, macOS, Linux) (Done)

### Phase 7: Interactive Export Review (Completed)
- Implement interactive mode for reviewing new highlights before export (Done)
- Allow users to selectively skip items during review (Done)

### Phase 8: User Documentation (Completed)
- Set up Documentation for the repository (Done)
- Write documentation covering installation (pipx/uv tool install) (Done)
- Write documentation covering basic usage and commands (export, history, config) (Done)
- Include examples and troubleshooting tips (Done)

### Phase 9: Highlight Note Detection
- Implement detection and handling of notes related to highlights (they seem to appear as a clipping right after the highlight and read - Your Note on page X at the beginning)
- These notes should be added to the highlight above and sent to Readwise as a parameter of the processed highlight (See Readwise API)
- Once done, update documentation to indicate notes can use the inline tagging feature of Readwise, as highlight related notes are processed correctly

### Phase 10: Auto search for cover images
- The readwise API supports image_url as a parameter for highlights to send a fitting cover image for the currently processed book or article
- Implement auto search for cover images using the book's title and author
- Implement a fallback image (e.g. a generic book icon) if no cover image is found

### Phase 11: Advanced Highlight Processing
- Implement smarter duplicate detection (e.g., fuzzy matching)
- Detect and handle cases where a highlight might have been updated on the Kindle

### Phase 12: Reliability & Error Handling
- Implement more robust error handling and recovery
- Add retries for failed Readwise API calls

### Phase 13: Database Maintainability
- Add database migration support for future schema changes

### Phase 14: Notification System (Postponed)
- Add OS-dependent notification system for export events
- Implement OS notification system for error reporting
- Create user-configurable notification preferences
- *Postponed due to 2024 Kindle device not being programmatically accessible*

### Phase 15: Automated Export Controls (Postponed)
- Create configurable user confirmation options before export
- Allow users to enable/disable automated export via CLI options
- *Postponed due to 2024 Kindle device not being programmatically accessible*

## Global Installation

kindle2readwise can be installed as a global command-line tool using UV's tool installation capabilities. This allows users to run the application from any directory without having to navigate to the project folder.

### Installation Options

- **Standard Global Installation**: Installs the tool globally while isolating its dependencies
  ```bash
  uv tool install .
  ```

- **Development Installation**: Installs in editable mode, allowing code changes to be immediately reflected
  ```bash
  uv tool install --editable .
  ```

### Uninstallation

The tool can be uninstalled using:
```bash
uv tool uninstall kindle2readwise
```

### Configuration with Global Installation

When installed globally, the application should:
- Use appropriate platform-specific directories for configuration and data storage
- Consider the user's home directory for default config locations
- Support both global and local (project-specific) configuration options
