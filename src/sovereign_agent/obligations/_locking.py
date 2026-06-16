"""POSIX advisory-lock write-fence helpers — extracted verbatim from ledger.py (audit 2026-06-16 #6).

Guarded so the module imports on non-POSIX platforms (audit 2026-06-13: a top-level `import fcntl`
hard-failed on Windows at package load). On a platform without fcntl the fence degrades to a no-op with
a ONE-TIME loud warning — never a silent weakening of the hash-chain fence."""
from __future__ import annotations

try:
    import fcntl as _fcntl
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover — non-POSIX
    _fcntl = None
    _HAS_FCNTL = False

_FLOCK_WARNED = False


def _flock_ex(fileobj) -> None:
    if _HAS_FCNTL:
        _fcntl.flock(fileobj.fileno(), _fcntl.LOCK_EX)
        return
    global _FLOCK_WARNED
    if not _FLOCK_WARNED:
        import warnings
        warnings.warn(
            "fcntl unavailable on this platform — the obligation-ledger cross-process write fence is "
            "NOT enforced; concurrent multi-process appends could fork the chain. Single-process use "
            "is safe.", RuntimeWarning, stacklevel=2)
        _FLOCK_WARNED = True


def _flock_un(fileobj) -> None:
    if _HAS_FCNTL:
        _fcntl.flock(fileobj.fileno(), _fcntl.LOCK_UN)
