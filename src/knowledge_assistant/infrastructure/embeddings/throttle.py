"""Sliding-window throttle for per-minute request and token limits (ADR-0005)."""

import math
import time
from collections import deque
from collections.abc import Callable

from knowledge_assistant.core.exceptions import EmbeddingError

CHARS_PER_TOKEN = 4  # ADR-0003 D3 rule of thumb; calibrated against the V-1 probe in ADR-0005


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


class SlidingWindowThrottle:
    """Blocks until one more request of `tokens` fits in the last `window_s` seconds."""

    def __init__(
        self,
        requests_per_window: int,
        tokens_per_window: int,
        window_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_requests = requests_per_window
        self._max_tokens = tokens_per_window
        self._window_s = window_s
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[tuple[float, int]] = deque()  # (time, estimated tokens)
        self.total_wait_s = 0.0

    def acquire(self, tokens: int) -> float:
        """Record one request; return the seconds waited for it."""
        if tokens > self._max_tokens:
            raise EmbeddingError(
                f"one request needs ~{tokens} tokens, above the per-minute limit {self._max_tokens}; "
                "use a smaller batch"
            )
        waited = 0.0
        while True:
            now = self._clock()
            while self._sent and self._sent[0][0] <= now - self._window_s:
                self._sent.popleft()
            used_tokens = sum(t for _, t in self._sent)
            if len(self._sent) < self._max_requests and used_tokens + tokens <= self._max_tokens:
                self._sent.append((now, tokens))
                self.total_wait_s += waited
                return waited
            wait = self._sent[0][0] + self._window_s - now
            self._sleep(wait)
            waited += wait
