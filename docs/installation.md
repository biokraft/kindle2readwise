# Installation

`kindle2readwise` is designed to be installed as a global command-line tool using [UV](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

## Prerequisites

- Python 3.12 or newer
- UV installed (see [UV installation guide](https://github.com/astral-sh/uv#installation))

## Installation Steps

You can install `kindle2readwise` directly from the GitHub repository using `uv`. This ensures you get the version you need.

1.  **Install the latest version:**
    To install the most recent release:
    ```bash
    uv tool install git+https://github.com/biokraft/kindle2readwise.git
    ```

2.  **Install a specific version:**
    If you need a particular version (e.g., `v0.1.0`), you can specify the tag:
    ```bash
    uv tool install git+https://github.com/biokraft/kindle2readwise.git@v0.1.0
    ```
    Replace `v0.1.0` with the desired version tag from the [GitHub Releases page](https://github.com/biokraft/kindle2readwise/releases).

3.  **(Optional) Install for development:**
    If you plan to contribute to the project, clone the repository and install in editable mode:
    ```bash
    # Clone the repository first (if you haven't already)
    # git clone https://github.com/biokraft/kindle2readwise.git
    # cd kindle2readwise

    # Install in editable mode
    uv tool install --editable .
    ```
    This links the command to your local source code.

## Uninstallation

To remove the tool, use the following command:

```bash
uv tool uninstall kindle2readwise
```

## Verifying Installation

After installation, you should be able to run the tool from any directory:

```bash
kindle2readwise --version
```
