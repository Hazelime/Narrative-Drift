"""Package entry point for running Vane as a script.

Allows executing the command-line interface directly via `python -m vane`.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
