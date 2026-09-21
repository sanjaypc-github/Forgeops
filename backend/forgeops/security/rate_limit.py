import time
from collections import defaultdict, deque
from collections.abc import Callable


class LoginLimiter:
    """In-process failed-login limiter keyed by e.g. "email|ip"."""

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 300,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._clock = clock
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        entries = self._failures[key]
        cutoff = self._clock() - self._window
        while entries and entries[0] <= cutoff:
            entries.popleft()
        return entries

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self._max

    def record_failure(self, key: str) -> None:
        self._prune(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
