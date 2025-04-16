# Kindle Clippings Format Specification

## Overview

This document outlines the format of Kindle clippings files and the approach for parsing them in the kindle2readwise application.

## Clippings File Format

Amazon Kindle devices store user highlights, notes, and bookmarks in a file called `My Clippings.txt` found in the `documents` folder of the device. The file follows a specific format with the following structure:

Each clipping entry consists of 5 lines:
1. **Title line**: Contains the book title and sometimes the author in parentheses.
2. **Metadata line**: Contains type of clipping, location, and timestamp.
3. **Empty line**: A blank line separating metadata from content.
4. **Content**: The actual highlight text or note.
5. **Separator**: A line with 10 equal signs (`==========`).

### Example Clipping Format

```
Book Title (Author Name)
- Your Highlight on Location 1234-1235 | Added on Monday, January 1, 2023 12:34:56 PM

This is the highlighted text from the book.
==========
```

Some variations in format may include:
- Bookmark entries
- Notes without highlighting
- Page numbers instead of locations
- Different date formats depending on device settings

## Parsing Approach

The parser will:
1. Read the entire clippings file
2. Split the content based on the separator (`==========`)
3. Process each entry to extract the following information:
   - Book title
   - Author (if available)
   - Type (highlight, note, bookmark)
   - Location/position in the book
   - Date added
   - Content (the highlighted text or note)

## Data Structure

After parsing, each clipping will be represented as:

```python
{
    "title": str,               # Book title
    "author": str,              # Author name (if available)
    "type": str,                # "highlight", "note", or "bookmark"
    "location": str,            # Location/position in the book
    "date": datetime.datetime,  # When the clipping was created
    "content": str              # The highlighted text or note content
}
```

## Edge Cases

The parser will handle various edge cases, including:
- Missing author information
- Different date formats
- Clippings from PDFs with page numbers instead of locations
- Non-English languages
- Special characters and encoding issues
- Multi-line highlights
- Missing content (for bookmarks)

## Implementation Details

The clippings parser will be implemented in a separate module with appropriate error handling and logging to ensure robustness. It will leverage regular expressions to efficiently parse the structured format of the clippings file.
