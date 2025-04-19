---
layout: default
title: Troubleshooting
---

# Troubleshooting

This page covers common issues and how to resolve them.

## Common Issues

### "My Clippings.txt not found"

- **Cause:** The application cannot find the `My Clippings.txt` file.
- **Solution:**
    - Ensure the file is named exactly `My Clippings.txt`.
    - Run the command from the directory containing the file, OR
    - Specify the full path using the `--clippings-file` option:
      ```bash
      kindle2readwise export --clippings-file /path/to/your/My\ Clippings.txt
      ```
    - You can also set the default path using `kindle2readwise configure --default-file "/path/to/your/My Clippings.txt"`.

### "Invalid API Token"

- **Cause:** The Readwise API token provided is incorrect or expired.
- **Solution:**
    - Verify your token at [https://readwise.io/access_token](https://readwise.io/access_token).
    - Re-configure the token using:
      ```bash
      kindle2readwise configure --token YOUR_NEW_TOKEN
      ```

### Duplicate Highlights Exported

- **Cause:** Duplicate detection might be disabled or reset.
- **Solution:**
    - Ensure you are not using the `--force` flag with the `export` command, as this bypasses duplicate checks.
    - If you suspect the database is corrupted, you might need to reset it using `kindle2readwise reset-db` (use with caution, this deletes history!).

### Clippings Not Parsing Correctly

- **Cause:** The format of your `My Clippings.txt` might differ slightly (e.g., due to Kindle language settings or firmware version).
- **Solution:**
    - Please open an issue on the project's GitHub repository, providing:
        - A small, anonymized sample from your `My Clippings.txt` that shows the problematic format.
        - The version of `kindle2readwise` you are using (`kindle2readwise version`).
        - Your Kindle model and language settings, if known.

## Getting Help

If your issue isn't listed here, please:
1.  Run the command with the `--verbose` flag (`-v`) to get more detailed output.
2.  Check the application logs (location depends on configuration, often in a platform-specific directory).
3.  Open an issue on the [GitHub repository](https://github.com/biokraft/kindle2readwise) with the details and any relevant logs.
