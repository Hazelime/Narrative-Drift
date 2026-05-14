from __future__ import annotations

import itertools
import sys
import threading
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def run_with_spinner(message: str, work: Callable[[], T]) -> T:
    if not sys.stderr.isatty():
        print(f"{message}...", file=sys.stderr)
        return work()

    done = threading.Event()
    frames = itertools.cycle("|/-\\")

    def animate() -> None:
        while not done.is_set():
            sys.stderr.write(f"\r{next(frames)} {message}...")
            sys.stderr.flush()
            time.sleep(0.12)
        sys.stderr.write("\r" + " " * (len(message) + 6) + "\r")
        sys.stderr.flush()

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()
    try:
        return work()
    finally:
        done.set()
        thread.join()
