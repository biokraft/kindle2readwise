# Installation

`kindle2readwise` is designed to be installed as a global command-line tool using [UV](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

## Prerequisites

- Python 3.12 or newer
- UV installed (see [UV installation guide](https://github.com/astral-sh/uv#installation))

## Installation Steps

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/biokraft/kindle2readwise.git
    cd kindle2readwise
    ```

2.  **Install using UV:**

    *   **Standard Global Installation:** Installs the tool globally, isolating its dependencies.
        ```bash
        uv tool install .
        ```

    *   **Development Installation:** Installs in editable mode, ideal for development. Changes to the source code are reflected immediately without needing to reinstall.
        ```bash
        uv tool install --editable .
        ```

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
