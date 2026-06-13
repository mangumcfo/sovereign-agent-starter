"""mtime/size-keyed memoization for file-derived lens projections (audit 2026-06-13 W5 #4/#5/#15).

The polled cockpit lens routes (`/series` parses a 112KB roadmap + 5 index files; `/coherence` scans
~948KB of manuscripts) re-read and re-parse on every request with no cache, while the ledger right beside
them memoizes on `(mtime_ns, size)`. This is that same discipline, factored out: re-derive ONLY when a
watched file actually changes (re-parse on change, hit otherwise). Sole-write files that change rarely →
~100% hit rate.
"""
from __future__ import annotations

from functools import wraps
from pathlib import Path


def stat_key(paths) -> tuple:
    """A change-detecting key over the given files: (path, mtime_ns, size) each; (0,0) when absent."""
    out = []
    for p in paths:
        try:
            st = Path(p).stat()
            out.append((str(p), st.st_mtime_ns, st.st_size))
        except OSError:
            out.append((str(p), 0, 0))
    return tuple(out)


def memoize_on(paths_fn):
    """Decorator: cache `fn(*a, **k)` keyed on `stat_key(paths_fn(*a, **k))`. Re-runs only when one of the
    watched files changes. `paths_fn` receives the same args as `fn` and returns an iterable of paths."""
    def deco(fn):
        box: dict = {}

        @wraps(fn)
        def wrapper(*a, **k):
            key = stat_key(paths_fn(*a, **k))
            cached = box.get("v")
            if cached is not None and cached[0] == key:
                return cached[1]
            val = fn(*a, **k)
            box["v"] = (key, val)
            return val

        wrapper._cache_box = box  # exposed for tests
        return wrapper
    return deco
