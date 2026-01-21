"""Compatibility layer that delegates to the PerformanceTracker."""
import functools
import time
from typing import Callable, Dict, Any

from .performance import get_tracker, timing as perf_timing, timing_context as PerfTimingContext


def clear_timings() -> None:
    """Clear all timing data on the shared tracker."""
    get_tracker().clear()


def get_timings() -> Dict[str, float]:
    """Get current timing data as a dict (aggregated by name)."""
    tracker = get_tracker()
    timings: Dict[str, float] = {}
    for entry in tracker.get_all_entries():
        timings[entry.name] = timings.get(entry.name, 0.0) + entry.duration
    return timings


def _record_timing(name: str, duration: float) -> None:
    """Record a timing on the shared tracker."""
    get_tracker().record(name, duration)


def print_timings(title: str = "Performance Summary") -> None:
    """Print timing summary in execution order using the shared tracker."""
    get_tracker().print_summary(title)


def timing(name: str = None):
    """Decorator that uses the shared PerformanceTracker."""
    return perf_timing(name)


timing_context = PerfTimingContext
