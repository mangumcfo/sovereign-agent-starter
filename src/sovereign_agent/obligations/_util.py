"""Pure id / hash / time helpers for the obligation ledger — extracted verbatim from ledger.py
(audit 2026-06-16 #6, extraction not abstraction). No deps beyond stdlib; imported by ledger.py
AND projection.py, so it must not import either (no cycle)."""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(obj: dict) -> str:
    """SHA-256 of canonical JSON, first 16 hex (matches the cylinder/molt convention)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def _entry_id() -> str:
    return f"obl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"


def _receipt_id() -> str:
    return f"rcpt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
