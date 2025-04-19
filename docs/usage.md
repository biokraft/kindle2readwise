# Usage

This guide explains how to use the main commands of `kindle2readwise`.

## Basic Workflow

1.  **(Optional) Configure your API token:** Run `kindle2readwise configure` to set your Readwise API token if you haven't already.
2.  **Export Highlights:** Run `kindle2readwise export` to parse your `My Clippings.txt` file and send new highlights to Readwise.
3.  **(Optional) View History:** Use `kindle2readwise history` to see past exports.

## Command: `export`

This is the primary command to parse your Kindle clippings and send them to Readwise.

**Basic Usage:**

```bash
kindle2readwise export
```

By default, it looks for `My Clippings.txt` in the current directory and uses the API token from your configuration.

**Specifying Files and Tokens:**

```bash
# Specify the clippings file path
kindle2readwise export --clippings-file /path/to/your/My\ Clippings.txt

# Specify the API token directly (overrides config)
kindle2readwise export --api-token YOUR_READWISE_TOKEN
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

To re-export highlights that have already been sent:

```bash
kindle2readwise export --force
# or
kindle2readwise export -F
```

**Other Options:**

- `--batch-size`: Control how many highlights are sent per API request.
- `--output FILE`: Save parsed highlights to a file instead of exporting.
- `--format {json|csv}`: Specify output file format (used with `--output`).
- `--verbose` / `-v`: Show more detailed output.
- `--quiet` / `-q`: Show only errors.

## Command: `configure`

Manage application settings like your Readwise API token and default clippings file location.

**Interactive Configuration:**

Run without options for a guided setup:

```bash
kindle2readwise configure
```

**Setting Specific Values:**

```bash
# Set API token
kindle2readwise configure --token YOUR_READWISE_TOKEN

# Set default clippings file path
kindle2readwise configure --default-file "/path/to/your/My Clippings.txt"
```

**Viewing Configuration:**

```bash
kindle2readwise configure --show
```

**Resetting Configuration:**

```bash
kindle2readwise configure --reset
```

## Command: `history`

View information about past export sessions.

**Basic Usage:**

Show the last 10 export sessions:

```bash
kindle2readwise history
```

**Viewing More Sessions:**

```bash
kindle2readwise history --limit 20
```

**Detailed View:**

Show details for each session (like number of highlights processed):

```bash
kindle2readwise history --details
```

**Specific Session:**

Get details for a single session using its ID (shown in the basic history view):

```bash
kindle2readwise history --session SESSION_ID
```

## Command: `version`

Display the application version and environment details:

```bash
kindle2readwise version
```

## Command: `reset-db`

**Warning:** This command deletes all stored export history and configuration.

```bash
# Interactive reset (prompts for confirmation)
kindle2readwise reset-db

# Force reset (no confirmation)
kindle2readwise reset-db --force
```
