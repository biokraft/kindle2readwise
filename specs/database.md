# Database Specification

## Overview

This document outlines the design and functionality of the database system used by the kindle2readwise application. The primary purpose of the database is to track exported highlights to prevent duplicate exports to Readwise.

## Database Requirements

The database system will:
1. Store a record of all highlights that have been exported to Readwise
2. Provide efficient lookup capability to check if a highlight has been previously exported
3. Maintain metadata about each export operation
4. Be lightweight, requiring minimal setup and maintenance
5. Support concurrent operations (if needed in future iterations)

## Database Technology

SQLite will be used as the database engine due to its:
- Serverless architecture (no separate installation required)
- File-based structure for easy portability
- Native Python support via the `sqlite3` module
- Performance adequate for the expected data volume
- Zero-configuration setup

## Schema Design

### Main Tables

#### `highlights`

Stores information about the highlights that have been exported to Readwise.

| Column          | Type          | Description                                              |
|-----------------|---------------|----------------------------------------------------------|
| id              | INTEGER       | Primary key, auto-incrementing                           |
| highlight_hash  | TEXT          | Unique hash of the highlight (title + author + text)     |
| title           | TEXT          | Book title                                               |
| author          | TEXT          | Book author                                              |
| text            | TEXT          | The highlighted text content                             |
| location        | TEXT          | Position in the book (location or page)                  |
| date_highlighted| TEXT          | When the highlight was created on Kindle                 |
| date_exported   | TEXT          | When the highlight was exported to Readwise              |
| readwise_id     | TEXT          | ID returned by Readwise API (if available)               |
| status          | TEXT          | Export status (success, error)                           |

#### `export_sessions`

Tracks each export operation performed by the user.

| Column          | Type          | Description                                              |
|-----------------|---------------|----------------------------------------------------------|
| id              | INTEGER       | Primary key, auto-incrementing                           |
| start_time      | TEXT          | When the export operation started                        |
| end_time        | TEXT          | When the export operation completed                      |
| highlights_total| INTEGER       | Total number of highlights processed                     |
| highlights_new  | INTEGER       | Number of new highlights exported                        |
| highlights_dupe | INTEGER       | Number of duplicate highlights skipped                   |
| source_file     | TEXT          | Path to the source clippings file                        |
| status          | TEXT          | Overall status (success, partial, error)                 |

### Indexes

The following indexes will be created to optimize performance:

1. `highlights_hash_index` on `highlights(highlight_hash)` - Primary lookup for deduplication
2. `highlights_export_date_index` on `highlights(date_exported)` - For querying recently exported items
3. `highlights_title_author_index` on `highlights(title, author)` - For querying by book

## Database Operations

### Core Functions

1. **Initialize Database**:
   - Create tables if they don't exist
   - Verify schema integrity
   - Perform migrations if needed

2. **Check for Duplicate**:
   - Generate hash for a highlight
   - Query the `highlights` table for the hash
   - Return boolean indicating if the highlight exists

3. **Record Exported Highlight**:
   - Insert new highlight record with export details
   - Update existing record if reprocessed

4. **Start/End Export Session**:
   - Create record of export session
   - Update with results when complete

5. **Query Export History**:
   - Get statistics about past exports
   - List previously exported highlights

## Data Access Layer

The database operations will be encapsulated in a Data Access Object (DAO) pattern:

```python
class HighlightsDAO:
    def __init__(self, db_path="highlights.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        # Create tables and indexes

    def highlight_exists(self, title, author, text):
        # Check if highlight already exported

    def save_highlight(self, highlight_data, export_status):
        # Record an exported highlight

    def start_export_session(self, source_file):
        # Record start of export session

    def complete_export_session(self, session_id, stats):
        # Update export session with results

    def get_export_history(self, limit=10):
        # Get recent export sessions
```

## Database File Management

1. **Location**: The database file will be stored in a user-specific data directory
2. **Backup**: Automatic backups will be created before structural changes
3. **Migrations**: Version tracking will allow for schema updates in future releases

## Security Considerations

1. The database file will have appropriate permissions to prevent unauthorized access
2. No sensitive data (like API tokens) will be stored in the database
3. Input validation will be used to prevent SQL injection
