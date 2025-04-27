# Troubleshooting

This page covers common issues and how to resolve them.

## Common Issues

### 1. "My Clippings.txt" not found

**Error Message:** `FileNotFoundError: [Errno 2] No such file or directory: 'My Clippings.txt'`

**Solution:**

- Ensure your Kindle is connected via USB and mounted.
- Provide the full path to the file using the `export` command argument or the `--clippings-file` option (if still supported, check `usage.md`).
  ```bash
  kindle2readwise export /Volumes/Kindle/documents/My\ Clippings.txt
  ```
- Alternatively, copy `My Clippings.txt` from your Kindle (`/documents/` folder) to the directory where you are running the command.
- You can set a default path using `kindle2readwise config set default_clippings_path /path/to/file`.

### 2. Invalid Readwise API Token

**Error Message:** Might vary, often includes `401 Unauthorized` or similar HTTP errors during export.

**Solution:**

- Verify your API token is correct. Get it from [https://readwise.io/access_token](https://readwise.io/access_token).
- Reconfigure the token:
  ```bash
  kindle2readwise config token YOUR_CORRECT_TOKEN
  ```
- Ensure there are no typos or extra spaces in the token.
- Check if the `READWISE_API_TOKEN` environment variable is set and potentially overriding the configuration.

### 3. Parsing Errors

**Error Message:** May mention issues parsing specific lines in `My Clippings.txt`.

**Solution:**

- The `My Clippings.txt` file can sometimes become corrupted or contain entries in unexpected formats (especially non-English highlights or clippings from PDFs/web articles).
- Try opening `My Clippings.txt` in a text editor and look for unusual entries around the location mentioned in the error (if any).
- You might need to manually edit or remove problematic entries from the file.
- Consider backing up `My Clippings.txt` before editing.
- Run with increased logging to potentially pinpoint the problematic line:
  ```bash
  kindle2readwise --log-level DEBUG export /path/to/My\ Clippings.txt
  ```

### 4. Duplicate Highlights Not Exported

**Behavior:** Running `export` multiple times doesn't re-send highlights that were already successfully exported.

**Solution:**

- This is the intended behavior to prevent duplicates in Readwise.
- If you need to force a re-export (e.g., if highlights were deleted in Readwise or an export failed partially), use the `--force` flag:
  ```bash
  kindle2readwise export --force
  ```
- You can check which highlights are stored locally using `kindle2readwise highlights list`.

### 5. Database Errors

**Error Message:** Errors related to SQLite, database locking, or schema issues.

**Solution:**

- Ensure no other instances of the tool are running simultaneously, which might lock the database.
- Check file permissions for the database file. Use `kindle2readwise config paths` to find its location.
- **Last Resort:** If the database seems corrupted, you can reset it. **Warning:** This deletes all history and stored highlight records (but not your Readwise data).
  ```bash
  kindle2readwise reset-db --force
  ```

## Getting More Help

If you encounter an issue not covered here:

1.  **Enable Debug Logging:** Run the command with `--log-level DEBUG` and `--log-file debug.log` to capture detailed logs.
    ```bash
    kindle2readwise --log-level DEBUG --log-file debug.log export [other options]
    ```
2.  **Check Existing Issues:** Look for similar problems on the [GitHub Issues page](https://github.com/biokraft/kindle2readwise/issues).
3.  **Create a New Issue:** If your problem is unique, please [open a new issue](https://github.com/biokraft/kindle2readwise/issues/new), providing:
    - The command you ran.
    - The full output, including any error messages.
    - The relevant logs (from the debug file, removing any personal info like API tokens).
    - Your operating system and `kindle2readwise` version (`kindle2readwise version`).
