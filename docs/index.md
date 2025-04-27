# kindle2readwise

A tool to export your Kindle highlights to Readwise.

## 🚀 Quick Start

1.  **Install:**
    ```bash
    uv tool install git+https://github.com/biokraft/kindle2readwise.git@v0.1.1
    ```
    *(Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv))*

2.  **Configure:**
    Get your API token from [Readwise](https://readwise.io/access_token) and store it (only needed once):
    ```bash
    kindle2readwise config token YOUR_READWISE_API_TOKEN
    ```
    *(Alternatively, run `kindle2readwise config token` without the token for an interactive prompt)*

3.  **Export:**
    Connect your Kindle via USB and specify your clippings file:
    ```bash
    kindle2readwise export --clippings-file /path/to/My\\ Clippings.txt
    ```

## Table of Contents

- [Installation](installation.md)
- [Usage](usage.md)
- [Highlights Management](usage.md#command-highlights)
- [Examples](examples.md)
- [Troubleshooting](troubleshooting.md)
