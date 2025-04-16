# Logging System Specification

## Overview

This document outlines the logging approach for the kindle2readwise application. A robust logging system is essential for debugging, monitoring application behavior, and providing transparency to users about what's happening during the export process.

## Logging Requirements

The logging system will:

1. Provide comprehensive visibility into application behavior
2. Enable easy debugging for developers
3. Allow users to understand the status of their export operations
4. Help identify and diagnose issues in production
5. Record information about application performance and resource usage

## Logging Levels

The application will use the standard Python logging levels:

- **DEBUG**: Detailed information, typically of interest only when diagnosing problems
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened, or may happen in the future
- **ERROR**: Due to a more serious problem, the software has not been able to perform a function
- **CRITICAL**: A serious error indicating that the program itself may be unable to continue running

## Log Content

Each log entry will include:

- Timestamp with millisecond precision
- Log level
- Module/component name
- Process/thread ID (when relevant)
- Descriptive message with relevant context
- Exception traceback (for errors)

## Components to Log

The application will log events from these key components:

1. **Kindle Clippings Parser**:
   - File read operations
   - Parsing statistics (items processed, successful, failed)
   - Parsing errors with specific entries
   - Format discrepancies

2. **Readwise API Integration**:
   - API requests (with sensitive data redacted)
   - API responses
   - Authentication status
   - Rate limiting information
   - Request retry attempts

3. **Deduplication System**:
   - Database operations
   - Duplicate detection events
   - Statistics on new vs. existing items

4. **General Application**:
   - Startup and shutdown
   - Configuration loading
   - User commands
   - Performance metrics

## Log Formats

The application will support multiple log formats:

1. **Console output**: Formatted for human readability with color-coding by level
2. **File logs**: More detailed, structured format for persistent storage
3. **JSON format** (optional): For advanced log processing and analysis

## Log File Management

For file-based logging:

1. Log files will be stored in a designated logs directory
2. Log rotation will be implemented to prevent excessive disk usage
3. Retention policies will be configurable
4. Maximum log file size will be limited

## Implementation Approach

The logging system will:

1. Use Python's built-in `logging` module
2. Be configured via a central logging configuration
3. Allow log level adjustment without code changes
4. Support customizable log formatting
5. Provide convenience methods for common logging patterns

## Code Example

```python
import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("application.log"),
        logging.StreamHandler()
    ]
)

# Create module-specific loggers
logger = logging.getLogger("kindle_clippings_parser")

# Example usage
logger.info("Starting to parse clippings file: %s", filename)
try:
    # Operation that might fail
    parse_clippings(filename)
except Exception as e:
    logger.error("Failed to parse clippings file", exc_info=True)
```

## Security Considerations

The logging system will:

1. Never log sensitive information such as API tokens
2. Implement data redaction for potentially sensitive fields
3. Restrict log file permissions appropriately
4. Avoid logging personal user data unnecessarily
