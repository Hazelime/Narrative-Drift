"""Terminal spinner overlay for interactive command-line feedback.

Displays a rotating character animation in stderr while running synchronous
long-running tasks (e.g., API requests or inference models) in CLI mode.
"""

from __future__ import annotations

import itertools
import sys
import threading
import time
from collections.abc import Callable
from typing import TypeVar

# Generic type variable for return value of the wrapped callable
T = TypeVar("T")


def run_with_spinner(message: str, work: Callable[[], T]) -> T:
    """Execute a callable synchronously while rendering a console animation in a background thread.

    If the output stream is not an interactive terminal (TTY), skips the spinner
    animation and simply logs a static message to prevent console pollution.

    Args:
        message: The status description text to display next to the spinner.
        work: A zero-argument callable representing the task to execute.

    Returns:
        The return value of the executed task.
    """
    if not sys.stderr.isatty():
        # Fall back to static print if run in non-interactive environment (CI, redirect)
        print(f"{message}...", file=sys.stderr)
        return work()

    done = threading.Event()
    frames = itertools.cycle("|/-\\")

    def animate() -> None:
        while not done.is_set():
            # \r moves the cursor back to the start of the line
            sys.stderr.write(f"\r{next(frames)} {message}...")
            sys.stderr.flush()
            time.sleep(0.12)
        # Clear the spinner text from the console line before terminating
        sys.stderr.write("\r" + " " * (len(message) + 6) + "\r")
        sys.stderr.flush()

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()
    try:
        return work()
    finally:
        # Signal the spinner to stop and wait for cleanup
        done.set()
        thread.join()
