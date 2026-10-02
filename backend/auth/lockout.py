"""In-memory attempt limiter for sign-in and account links."""

import math
import threading
import time
from collections.abc import Callable

MAX_FAILS = 5
LOCK_MINUTES = 15
WINDOW_SECONDS = LOCK_MINUTES * 60


class Lockout:
    """Count attempts per key over a sliding window and lock the key at the limit."""

    def __init__(self, clock: Callable[[], float] = time.time, max_fails: int = MAX_FAILS):
        self._clock = clock
        self._max = max_fails
        self._fails: dict[str, dict] = {}
        self._lock = threading.Lock()

    def minutes_left(self, key: str) -> int:
        """Return whole minutes until the key may try again, or 0."""
        with self._lock:
            entry = self._fails.get(key)
            now = self._clock()
            if entry and entry["until"] > now:
                return math.ceil((entry["until"] - now) / 60)
            return 0

    def fail(self, key: str) -> None:
        """Count one attempt and lock the key when the window holds the limit."""
        with self._lock:
            now = self._clock()
            entry = self._fails.get(key, {"times": [], "until": 0})
            times = [t for t in entry["times"] if now - t < WINDOW_SECONDS] + [now]
            locked = len(times) >= self._max
            self._fails[key] = {"times": [] if locked else times, "until": now + WINDOW_SECONDS if locked else entry["until"]}

    def clear(self, key: str) -> None:
        """Forget a key after a successful attempt."""
        with self._lock:
            self._fails.pop(key, None)

    def reset(self) -> None:
        """Forget every key."""
        with self._lock:
            self._fails.clear()


def wait_message(minutes: int, what: str = "attempts") -> str:
    """Return the message shown while a key is locked."""
    return f"Too many {what}. Try again in {minutes} minute{'s' if minutes != 1 else ''}."


logins = Lockout()
links = Lockout()
