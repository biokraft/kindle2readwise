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

### Phase 3: Advanced Features
- Add configuration management
- Implement filtering options
- Create export history features
