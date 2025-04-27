# Examples

This page provides practical examples of common usage scenarios for `kindle2readwise`.

## Basic Export Workflow

The simplest way to export your Kindle highlights to Readwise:

```bash
# 1. First, configure your API token (only needed once)
kindle2readwise configure --token YOUR_READWISE_TOKEN

# 2. Connect your Kindle via USB

# 3. Find and export your highlights
kindle2readwise export --clippings-file /path/to/your/Kindle/documents/My\ Clippings.txt
```

## Interactive Review Before Export

If you want to review your highlights before exporting them:

```bash
kindle2readwise export --interactive
```

You'll see output similar to:

```
=== Interactive Export Mode ===
Found 5 new highlights to export.

📚 "Book Title 1" - Author Name
--------------------------------------------------------------------------------
  [1] This is the text of highlight 1...
      Location: 1234, Date: 2023-01-01

  [2] This is the text of highlight 2...
      Location: 1245, Date: 2023-01-01

Select highlights to export:
  - Enter highlight IDs separated by commas (e.g., '1,2')
  - Enter 'a' to select all highlights
  - Enter 'q' to quit without exporting

Your selection: 1,2
```

## Exporting to a File Instead of Readwise

To parse your highlights without sending them to Readwise:

```bash
# Export to JSON file
kindle2readwise export --dry-run --output highlights.json

# Export to CSV file
kindle2readwise export --dry-run --output highlights.csv --format csv
```

## Checking Export History

To see a summary of your past exports:

```bash
# View basic history
kindle2readwise history

# View history with details
kindle2readwise history --details

# View the last 5 history entries
kindle2readwise history --limit 5

# Output history as JSON
kindle2readwise history --format json
```

For detailed information about a specific export session:

```bash
kindle2readwise history --session 5
```

## Automatic Kindle Detection

When your Kindle is connected via USB, the tool can automatically find it:

```bash
# Auto-detect Kindle and export highlights
kindle2readwise export --auto-detect
```

## Working with Different Configurations

For users with multiple Readwise accounts or configurations:

```bash
# Show where configuration and database files are stored
kindle2readwise config paths

# Set a default clippings path in the config
kindle2readwise config set default_clippings_path "/Volumes/Kindle/documents/My Clippings.txt"

# Set the API token (interactively)
kindle2readwise config token

# Create different configuration profiles (Manual Example)
# Note: The tool doesn't have built-in profile support like shown below,
# but you could manage multiple config/db files manually or via scripts.

# # Create directories for profiles (Example - manual setup)
# mkdir -p ~/.config/kindle2readwise/profiles/work
# mkdir -p ~/.config/kindle2readwise/profiles/personal

# # Use a specific DB/Config path (Example - manual)
# kindle2readwise --db-path ~/.local/share/kindle2readwise/profiles/work/data.db export

# Configure each profile
# # Example - manually setting token for a specific config file path (if supported)
# kindle2readwise --config-path ~/.config/kindle2readwise/profiles/work/config.json config token YOUR_WORK_TOKEN
# kindle2readwise --config-path ~/.config/kindle2readwise/profiles/personal/config.json config token YOUR_PERSONAL_TOKEN
```

## Managing Stored Highlights

Interact with the highlights stored in the local database.

**List Books and Highlight Counts:**

```bash
kindle2readwise highlights books
```

**List Recent Highlights:**

```bash
# List the last 10 highlights added
kindle2readwise highlights list --limit 10 --sort date_exported --order desc
```

**Search Highlights:**

```bash
# Find highlights from the book "Project Hail Mary"
kindle2readwise highlights list --title "Project Hail Mary"

# Find highlights by author "Andy Weir"
kindle2readwise highlights list --author "Weir"

# Find highlights containing the text "Amaze"
kindle2readwise highlights list --text "Amaze"

# Combine filters
kindle2readwise highlights list --title "Sapiens" --text "history"
```

**Delete Highlights:**

```bash
# First, find the ID of the highlight to delete
kindle2readwise highlights list --text "Specific phrase to find highlight"
# (Assume the ID is 99)

# Delete the highlight by ID (will ask for confirmation)
kindle2readwise highlights delete --id 99

# Delete all highlights from the book "Dune" (will ask for confirmation)
kindle2readwise highlights delete --book "Dune"

# Delete highlights from "Dune" without confirmation
kindle2readwise highlights delete --book "Dune" --force
```

## Debugging and Logging

Increase log verbosity or log to a file for troubleshooting.

```bash
# Run export with DEBUG level logging
kindle2readwise --log-level DEBUG export

# Log export process to a file
kindle2readwise --log-file export.log export
```
