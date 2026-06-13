"""Fenced node-local JSON store (audit 2026-06-13 W5 #2/#3/#11; closes LOW #25).

The ObligationLedger's write-fence (flock + tmp+os.replace) stopped at the ledger boundary. The colocated
JSON stores — proposals.json, relays.json — did read→mutate→write as separate statements with NO lock,
while the node runs threaded=True (and a cross-process apply subprocess writes too). Concurrent
create/decide/dismiss interleaved → last-writer-wins, silently losing a proposal or a decision (and the
Propose→Decide→Execute disposition state the owner-gated /apply depends on). This is the SAME fence the
ledger already proved, factored out so every store shares one locked writer.

- read_json(path)         — unlocked best-effort read (GET projections that don't mutate).
- update_json(path, fn)   — LOCKED read→mutate→write; `fn(items) -> (new_items, result)`; returns result.
- write_json(path, data)  — atomic tmp+os.replace (call inside `locked`).
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover — non-POSIX
    _fcntl = None
    _HAS_FCNTL = False


def read_json(path, default=None):
    """Best-effort read; a missing/truncated file yields `default` (or [])."""
    fallback = [] if default is None else default
    p = Path(path)
    if not p.exists():
        return fallback
    try:
        return json.loads(p.read_text(encoding="utf-8")) or fallback
    except (OSError, ValueError):
        return fallback


def write_json(path, data, *, ensure_ascii: bool = True) -> None:
    """Atomic write via tmp + os.replace. Call INSIDE `locked()` for a fenced RMW."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=ensure_ascii), encoding="utf-8")
    tmp.replace(p)


@contextmanager
def locked(path):
    """Exclusive advisory lock on `<path>.lock` across a read-modify-write critical section. Degrades to
    a no-op on a platform without fcntl (single-process safe), mirroring the ledger's guard."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.with_suffix(p.suffix + ".lock")
    lf = open(lock_path, "w")
    try:
        if _HAS_FCNTL:
            _fcntl.flock(lf.fileno(), _fcntl.LOCK_EX)
        yield
    finally:
        if _HAS_FCNTL:
            _fcntl.flock(lf.fileno(), _fcntl.LOCK_UN)
        lf.close()


def update_json(path, mutate, *, default=None, ensure_ascii: bool = True):
    """LOCKED read→mutate→write. `mutate(items)` returns `(new_items, result)`; the new items are written
    atomically under the lock and `result` is returned. The whole critical section holds the lock, so
    concurrent updaters serialize instead of interleaving (the lost-write race)."""
    with locked(path):
        items = read_json(path, default)
        new_items, result = mutate(items)
        write_json(path, new_items, ensure_ascii=ensure_ascii)
        return result
