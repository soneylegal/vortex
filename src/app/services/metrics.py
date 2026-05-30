"""
Cache Metrics — In-memory counters for semantic cache observability.

Tracks hit/miss counts and cumulative lookup latency so operators can
monitor cache effectiveness without external tooling.
"""

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _CacheMetrics:
    """Thread-safe in-memory cache metrics counters."""

    hits: int = 0
    misses: int = 0
    total_lookup_time_ms: float = 0.0
    total_lookups: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_hit(self, duration_ms: float) -> None:
        with self._lock:
            self.hits += 1
            self.total_lookups += 1
            self.total_lookup_time_ms += duration_ms

    def record_miss(self, duration_ms: float) -> None:
        with self._lock:
            self.misses += 1
            self.total_lookups += 1
            self.total_lookup_time_ms += duration_ms

    def snapshot(self) -> dict:
        """Return a point-in-time snapshot of all metrics."""
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            avg_latency = (
                (self.total_lookup_time_ms / self.total_lookups)
                if self.total_lookups > 0
                else 0.0
            )
            return {
                "cache_hits": self.hits,
                "cache_misses": self.misses,
                "cache_total": total,
                "cache_hit_rate_pct": round(hit_rate, 2),
                "cache_avg_lookup_ms": round(avg_latency, 2),
            }

    def reset(self) -> None:
        """Reset all counters (useful for testing)."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.total_lookup_time_ms = 0.0
            self.total_lookups = 0


# ── Singleton ───────────────────────────────────────────────────────────
cache_metrics = _CacheMetrics()


class CacheTimer:
    """Context manager to measure cache lookup duration in milliseconds."""

    def __init__(self) -> None:
        self.duration_ms: float = 0.0

    def __enter__(self) -> "CacheTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.duration_ms = (time.perf_counter() - self._start) * 1000
