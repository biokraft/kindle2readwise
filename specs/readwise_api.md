# Readwise API Integration Specification

## Overview

This document outlines the approach for integrating with the Readwise API to export Kindle highlights. The Readwise API allows us to programmatically send highlights to a user's Readwise account.

## API Endpoints

The primary endpoint we'll use is:

- **POST** `https://readwise.io/api/v2/highlights/`
  - Purpose: Create new highlights in Readwise
  - Authentication: Token-based authentication using `Authorization: Token XXX` header
  - Rate Limiting: 240 requests per minute per access token

## Authentication

- Each user will need to provide their Readwise API token
- Tokens can be obtained from: https://readwise.io/access_token
- Tokens should be securely stored (e.g., in a local configuration file)
- The application will validate the token on startup by making a request to `https://readwise.io/api/v2/auth/`

## Highlight Creation

### Request Format

The application will send parsed Kindle highlights to Readwise in the following JSON format:

```json
{
  "highlights": [
    {
      "text": "The highlighted text content",
      "title": "Book Title",
      "author": "Author Name",
      "source_type": "kindle",
      "category": "books",
      "location": 1234,
      "location_type": "location",
      "highlighted_at": "2023-01-01T12:34:56+00:00"
    },
    // Additional highlights...
  ]
}
```

### Required and Optional Fields

For each highlight:

- **Required**:
  - `text`: The content of the highlight

- **Optional but recommended**:
  - `title`: Book title
  - `author`: Book author
  - `location`: Position in the book
  - `highlighted_at`: When the highlight was created
  - `source_type`: Set to "kindle" for our application
  - `category`: Set to "books" for Kindle highlights
  - `location_type`: Set to "location" or "page" depending on the source

## Deduplication Logic

To avoid sending duplicate highlights to Readwise:

1. The application will maintain a local SQLite database to track previously exported highlights
2. Each highlight will be stored with:
   - A unique identifier (hash of title, author, and text)
   - Export timestamp
   - Response status from Readwise

3. Additionally, the application will leverage Readwise's built-in deduplication mechanism, which prevents duplicates based on title/author/text/source_url.

## Error Handling

The application will handle various API-related errors:

- Authentication failures (invalid token)
- Rate limiting (429 responses)
- Network issues
- Malformed data
- Server errors

In each case, appropriate logging and user feedback will be provided.

## Pagination and Batching

For users with many highlights:

1. The application will send highlights in batches (maximum 100 highlights per request)
2. Progress tracking will be implemented to show export status
3. Appropriate delays will be added between requests to respect rate limits

## Implementation Details

The Readwise API integration will be implemented in a separate module with:

- Robust error handling
- Comprehensive logging
- Configuration management for API tokens
- Retry mechanisms for failed requests
- Unit tests for API interactions
