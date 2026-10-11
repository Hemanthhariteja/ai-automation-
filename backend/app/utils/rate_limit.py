import time
from collections import defaultdict, deque

# In-memory sliding-window limiter — deliberately simple (no Redis) for a
# single-process app; resets on restart, which is an acceptable tradeoff for
# a public-facing form that just needs basic spam protection, not billing-grade limits.
_hits: dict[str, deque] = defaultdict(deque)


def is_rate_limited(key: str, max_hits: int, window_seconds: int) -> bool:
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > window_seconds:
        hits.popleft()
    if len(hits) >= max_hits:
        return True
    hits.append(now)
    return False
