"""Performance tracking utilities."""
import time
import functools
from typing import Callable, Optional, Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimingEntry:
    """Single timing measurement."""
    name: str
    duration: float
    start_time: float
    end_time: float
    order_index: int
    metadata: Dict[str, Any] = None
    children: List['TimingEntry'] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.children is None:
            self.children = []


class PerformanceTracker:
    """Performance metrics tracker."""
    
    def __init__(self, name: str = "Performance"):
        self.name = name
        self._entries: List[TimingEntry] = []
        self._order_counter = 0
        self._stack: List[TimingEntry] = []
    
    def clear(self) -> None:
        self._entries.clear()
        self._order_counter = 0
        self._stack.clear()
    
    def record(self, name: str, duration: float, metadata: Optional[Dict] = None) -> None:
        end_time = time.perf_counter()
        entry = TimingEntry(
            name=name,
            duration=duration,
            start_time=end_time - duration,
            end_time=end_time,
            order_index=self._order_counter,
            metadata=metadata or {}
        )
        self._entries.append(entry)
        self._order_counter += 1
    
    def start(self, name: str) -> 'TimingContext':
        return TimingContext(self, name)
    
    def get_all_entries(self) -> List[TimingEntry]:
        return sorted(self._entries, key=lambda x: x.order_index)
    
    def summary_lines(self, title: Optional[str] = None) -> List[str]:
        """Render timing summary as lines for logging or printing."""
        title = title or f"{self.name} Summary"
        entries = self.get_all_entries()

        if not entries:
            return [f"{title}: No timing data"]

        lines: List[str] = []
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)
        lines.append(f"{'Operation':<40} {'Duration':>10}")
        lines.append("-" * 60)

        grouped: Dict[str, List[TimingEntry]] = defaultdict(list)
        for entry in entries:
            base = entry.name.lstrip(" ├─")
            grouped[base].append(entry)

        total = 0.0
        for name in sorted(grouped.keys()):
            dur = sum(e.duration for e in grouped[name])
            total += dur
            lines.append(f"{name:<40} {dur:>9.4f}s")

        lines.append("-" * 60)
        lines.append(f"{'TOTAL':<40} {total:>9.4f}s")
        lines.append("=" * 60)
        return lines

    def log_summary(self, title: Optional[str] = None, logger_obj: Optional[logging.Logger] = None) -> None:
        """Log summary using provided logger (defaults to module logger)."""
        log_target = logger_obj or logger
        for line in self.summary_lines(title):
            log_target.info(line)

    def print_summary(self, title: Optional[str] = None) -> None:
        """Print human-friendly summary to stdout."""
        for line in self.summary_lines(title):
            print(line)


class TimingContext:
    """Timing context manager."""
    
    def __init__(self, tracker: PerformanceTracker, name: str):
        self.tracker = tracker
        self.name = name
        self._start: float = 0
    
    def __enter__(self) -> 'TimingContext':
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        dur = time.perf_counter() - self._start
        self.tracker.record(self.name, dur)


# Global tracker
_default_tracker: Optional[PerformanceTracker] = None


def get_tracker() -> PerformanceTracker:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = PerformanceTracker("Default")
    return _default_tracker


# Backward compatibility
def clear_timings(): get_tracker().clear()
def _record_timing(name: str, dur: float): get_tracker().record(name, dur)
def print_timings(title: str = "Summary"): get_tracker().print_summary(title)


def timing(name: str = None):
    def decorator(func: Callable) -> Callable:
        op_name = name or func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            r = func(*args, **kwargs)
            _record_timing(op_name, time.perf_counter() - start)
            return r
        return wrapper
    return decorator


class timing_context:
    def __init__(self, name: str):
        self.name = name
        self.ctx = None
    
    def __enter__(self):
        self.ctx = get_tracker().start(self.name)
        return self.ctx.__enter__()
    
    def __exit__(self, *args):
        if self.ctx:
            self.ctx.__exit__(*args)
