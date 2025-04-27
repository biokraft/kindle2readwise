# Usage

This guide explains how to use the main commands of `kindle2readwise`.

## Basic Workflow

1.  **(Optional) Configure your API token:** Run `kindle2readwise config token` or the interactive `kindle2readwise config` to set your Readwise API token.
2.  **Export Highlights:** Run `kindle2readwise export` to parse your `My Clippings.txt` file and send new highlights to Readwise.
3.  **(Optional) Manage Stored Highlights:** Use `kindle2readwise highlights` to view, search, or delete highlights stored locally.
4.  **(Optional) View History:** Use `kindle2readwise history` to see past exports.

## Global Options

These options can be used with any command:

- `--log-level {DEBUG|INFO|WARNING|ERROR|CRITICAL}`: Set the verbosity of logging messages (default: `INFO`).
- `--log-file FILE`: Write logs to the specified `FILE` in addition to the console.

## Command: `export`

This is the primary command to parse your Kindle clippings and send them to Readwise.

**Basic Usage:**

```bash
# Use default 'My Clippings.txt' in current dir and configured token
kindle2readwise export

# Specify the clippings file path explicitly
kindle2readwise export /path/to/your/My\ Clippings.txt
```

**Specifying Files and Tokens:**

```bash
# Specify the clippings file path using the positional argument
kindle2readwise export /path/to/your/My\ Clippings.txt

# Specify the API token directly (overrides config/env var)
kindle2readwise export --api-token YOUR_READWISE_TOKEN
# or
kindle2readwise export -t YOUR_READWISE_TOKEN

# Specify a custom database path
kindle2readwise export --db-path /path/to/data.db
```

**Interactive Review:**

Review highlights before they are sent:

```bash
kindle2readwise export --interactive
# or
kindle2readwise export -i
```

**Dry Run:**

See which highlights *would* be exported without actually sending them:

```bash
kindle2readwise export --dry-run
# or
kindle2readwise export -d
```

**Forcing Export (Ignoring Duplicates):**

To re-export highlights that have already been sent (or previously failed):

```bash
kindle2readwise export --force
# or
kindle2readwise export -f
```

**List Kindle Devices:**

List detected Kindle devices based on the clippings file and exit:

```bash
kindle2readwise export --devices
```

**Other Options:**

- `--output FILE`: Save parsed highlights to `FILE` instead of exporting to Readwise.
- `--format {json|csv}`: Specify output file format (used with `--output`). Deprecated? Check export logic.

## Command: `config`

Manage application settings like your Readwise API token and database paths.

**Interactive Configuration:**

Run without subcommands for a guided setup (if implemented):

```bash
kindle2readwise config
```
*(Note: Check if the base command is interactive or requires a subcommand)*

**Show Configuration:**

```bash
kindle2readwise config show
```

**Set API Token:**

```bash
# Set the token directly
kindle2readwise config token YOUR_READWISE_TOKEN

# Run interactively to be prompted for the token
kindle2readwise config token
```

**Set Arbitrary Configuration Value:**

```bash
kindle2readwise config set <key> <value>
```
*Example:*
```bash
kindle2readwise config set default_clippings_path "/Users/me/Documents/My Clippings.txt"
```

**Show Configuration/Data Paths:**

Display the locations of configuration and database files:

```bash
kindle2readwise config paths
```

## Command: `history`

View information about past export sessions stored in the local database.

**Basic Usage:**

Show a summary of the most recent export sessions:

```bash
kindle2readwise history
```

**Controlling Output:**

```bash
# Limit the number of sessions shown
kindle2readwise history --limit 20

# Show detailed information for each session
kindle2readwise history --details

# Output history in JSON or CSV format
kindle2readwise history --format json
kindle2readwise history --format csv
```

**Specific Session:**

Get details for a single session using its ID (shown in the basic history view):

```bash
kindle2readwise history --session SESSION_ID
```

## Command: `highlights`

Manage the highlights stored in the local database after successful exports.

**List/Search Highlights:**

```bash
kindle2readwise highlights list
```

*Filtering:*
```bash
# Filter by book title (partial match)
kindle2readwise highlights list --title "Sapiens"

# Filter by author (partial match)
kindle2readwise highlights list --author "Harari"

# Search within highlight text
kindle2readwise highlights list --text "cognitive revolution"
```

*Pagination and Sorting:*
```bash
# Show 50 results
kindle2readwise highlights list --limit 50

# Show results starting from the 21st item
kindle2readwise highlights list --offset 20

# Sort by highlighting date (oldest first)
kindle2readwise highlights list --sort date_highlighted --order asc
```

*Output Format:*
```bash
# Output as JSON
kindle2readwise highlights list --format json

# Output as CSV
kindle2readwise highlights list --format csv
```
*(Default format is text)*

**List Books:**

Show all unique books found in the highlights database along with highlight counts.

```bash
kindle2readwise highlights books

# Output as JSON or CSV
kindle2readwise highlights books --format json
```

**Delete Highlights:**

Remove highlights from the local database. **This does not affect Readwise.**

```bash
# Delete a single highlight by its ID (get ID from 'highlights list')
kindle2readwise highlights delete --id 123

# Delete all highlights for a specific book (requires confirmation)
kindle2readwise highlights delete --book "The Three-Body Problem"

# Specify author if book title is ambiguous
kindle2readwise highlights delete --book "Foundation" --author "Asimov"

# Skip confirmation prompt when deleting
kindle2readwise highlights delete --book "Dune" --force
kindle2readwise highlights delete --id 456 -f
```

## Command: `version`

Display the application version:

```bash
kindle2readwise version
```

## Command: `reset-db`

**Warning:** This command deletes the local SQLite database file, erasing all stored configuration, export history, and highlight records. This action is irreversible and does not affect your Readwise account.

```bash
# Reset with confirmation prompt
kindle2readwise reset-db

# Force reset without confirmation
kindle2readwise reset-db --force
# or
kindle2readwise reset-db -f
```
