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

# Sample output:
# ID  Date                 Books  Highlights  Status
# --  -------------------  -----  ----------  ------
# 5   2023-06-15 15:30:22  3      15          Success
# 4   2023-06-10 09:45:11  2      7           Success
# 3   2023-06-05 18:20:05  1      3           Success
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
# Create different configuration profiles
mkdir -p ~/.config/kindle2readwise/profiles/work
mkdir -p ~/.config/kindle2readwise/profiles/personal

# Use a specific profile
kindle2readwise --config ~/.config/kindle2readwise/profiles/work/config.json export

# Configure each profile
kindle2readwise --config ~/.config/kindle2readwise/profiles/work/config.json configure
kindle2readwise --config ~/.config/kindle2readwise/profiles/personal/config.json configure
```
