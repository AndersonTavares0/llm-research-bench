"""Client-side latency statistics for probe evaluators.

Timing is measured around the HTTP call on the client, so it includes queueing
on the server: it is end-to-end latency, not model compute time.
"""

from __future__ import annotations

import statistics


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolation percentile (q in [0, 100]); None for empty input."""
    if not values:
        return None
    if not 0 <= q <= 100:
        raise ValueError("q must be within [0, 100]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    pos = (len(ordered) - 1) * q / 100
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    value = ordered[low] + (ordered[high] - ordered[low]) * (pos - low)
    return round(value, 3)


def summarize_ms(samples_ms: list[float]) -> dict[str, float | int | None]:
    """p50/p95/mean for a latency sample; null when nothing was measured."""
    if not samples_ms:
        return {"n": 0, "p50_ms": None, "p95_ms": None, "mean_ms": None}
    return {
        "n": len(samples_ms),
        "p50_ms": percentile(samples_ms, 50),
        "p95_ms": percentile(samples_ms, 95),
        "mean_ms": round(statistics.fmean(samples_ms), 3),
    }
