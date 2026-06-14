"""
Section — Dialogue + crypto-assurance (extracted from series.py, audit 2026-06-13d #8).

The Helix Comm Protocol surface — /dialogue (the hash-chained Tiger↔GB THREAD + KM's live B51 Memory
Cylinder captures as one receipted graph) and its helpers (_thread_entries, _b51_entries), plus the
read-only /crypto_assurance status chip. Carved out of series.py so each route module stays under the
500-line breath ceiling (CONSTITUTION §5): series.py keeps the Series-Pipeline projection; this module
keeps the coordination-graph + assurance lenses. Same url_prefix, same auth gate — only the file
boundary moved; URLs unchanged. Read-only throughout (we never write the THREAD or the cylinder).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from flask import Blueprint, jsonify

from ...ndjson import read_ndjson  # the ONE tolerant ndjson reader (Universalize Wave §1)
from .._filecache import memoize_on
from ..auth import require_principal

bp = Blueprint("dialogue", __name__, url_prefix="/api/v1")


def _thread_path() -> Path:
    return Path(__file__).resolve().parents[4] / "memory" / "coordination" / "THREAD_Tiger_GB.ndjson"


@memoize_on(lambda: [_thread_path()])
def _thread_entries():
    """The hash-chained Tiger↔GB THREAD as dialogue cards. Returns (entries, chain_ok). Read-only.
    Memoized on the THREAD's (mtime,size) (audit 2026-06-13d #6) — /dialogue re-parsed 498KB per poll."""
    # Tolerant read via the ONE gateway (Universalize Wave §1/G2): the THREAD is read through the same
    # primitive as every other ndjson chain — a truncated tail no longer drops the whole dialogue lens, and
    # a corrupt middle line flags chain_ok=False (loud) rather than being silently skipped.
    res = read_ndjson(_thread_path())
    entries, ok = [], not res.chain_corrupt
    prev_hash = None
    for e in res.entries:
        if prev_hash is not None and e.get("prev") and e.get("prev") != prev_hash:
            ok = False
        prev_hash = e.get("hash")
        entries.append({
            "n": e.get("n"), "ts": e.get("ts"), "from": e.get("from"), "to": e.get("to"),
            "ref": e.get("ref", ""), "msg": e.get("msg", ""),
            "receipt": (e.get("hash") or "")[:16], "prev": (e.get("prev") or "")[:12],
            "source": "thread",
        })
    entries.reverse()  # newest first
    return entries, ok


# B51 = the human's live Memory Cylinder (KM's own raw capture stream). It is anchored by a single Merkle
# root_hash over the whole cylinder, NOT a per-entry prev/hash chain like the THREAD. So we render each entry
# honestly: receipt = sha256(content)[:16] (deterministic, verifiable per-entry), and the cylinder's
# merkle_root is the chain anchor surfaced in meta. Read-only; we never write the cylinder.
# B51 live capture dir flows from B51_LIVE_DIR (default: XDG data home) so it resolves per-operator
# rather than for one host (runs_anywhere); read-only — we never write the cylinder.
_B51_LIVE_DIR = Path(os.environ.get(
    "B51_LIVE_DIR",
    os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                 "human-memory-cylinder", "sessions"),
))


def _b51_cylinder_path() -> Path | None:
    scan = Path(__file__).resolve().parents[4] / "artifacts" / ".b51_last_scan.json"
    if scan.is_file():
        try:
            p = Path(json.loads(scan.read_text(encoding="utf-8")).get("path", ""))
            if p.is_file():
                return p
        except (ValueError, OSError):
            pass
    if _B51_LIVE_DIR.is_dir():  # fallback: newest live cyl_*.json
        cyls = sorted(_B51_LIVE_DIR.glob("cyl_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if cyls:
            return cyls[0]
    return None


@memoize_on(lambda limit=12: [p for p in [_b51_cylinder_path()] if p])
def _b51_entries(limit: int = 12):
    """The latest `limit` entries of KM's live B51 Memory Cylinder, as dialogue cards. Returns
    (entries_newest_first, merkle_root, cyl_id). Honest: per-entry receipt = content hash; merkle_root anchors.
    Memoized on the cylinder's (mtime,size) (audit 2026-06-13d #6) — re-loaded the whole cylinder per poll.
    NB: the single caller uses the default limit, so a stat-only key is correct here."""
    path = _b51_cylinder_path()
    if not path:
        return [], "", ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return [], "", ""
    raw = data.get("entries", []) or []
    merkle = data.get("root_hash") or ""
    cyl_id = data.get("id") or ""
    total = len(raw)
    out = []
    for i, e in enumerate(raw[-limit:]):
        content = (e.get("content") or e.get("preview") or "").strip()
        idx = total - len(raw[-limit:]) + i  # absolute index in the cylinder
        out.append({
            "n": "b51-%d" % idx, "ts": e.get("timestamp", ""),
            "from": "KM-1176", "to": "field", "ref": "B51 capture · %s" % (cyl_id[:12] or "live"),
            "msg": content,
            "receipt": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            "prev": (merkle or "")[:12], "source": "b51",
        })
    out.reverse()  # newest first
    return out, merkle, cyl_id


@bp.get("/dialogue")
@require_principal
def dialogue():
    """Helix Comm Protocol — the unified, receipted coordination graph as dialogue cards. Two slices today:
    the hash-chained Tiger↔GB THREAD (source=thread) + KM's live B51 Memory Cylinder captures (source=b51).
    Each entry is a per-card-receipted Helix card; one cockpit-native graph. G responses extend the same lens
    next. Read-only; thin wrapper over what already exists (THREAD chain + B51 cylinder)."""
    thread, ok = _thread_entries()
    b51, merkle, cyl_id = _b51_entries()
    # Unified, newest-first by ISO timestamp (both sources emit ISO ts; string sort is correct + stable).
    entries = sorted(thread + b51, key=lambda e: str(e.get("ts") or ""), reverse=True)
    return jsonify({
        "meta": {"source": "THREAD_Tiger_GB + B51", "count": len(entries), "chain_ok": ok,
                 "sources": {"thread": len(thread), "b51": len(b51)},
                 "b51_merkle": (merkle or "")[:16], "b51_cyl": cyl_id[:12],
                 "note": "Helix Comm Protocol — the coordination THREAD + KM's live B51 captures as one "
                         "receipted graph. THREAD is per-entry hash-chained; B51 is content-hashed + "
                         "Merkle-anchored. Hopper / G responses extend the same lens next."},
        "entries": entries,
    })


@bp.get("/crypto_assurance")
@require_principal
def crypto_assurance():
    """The daily crypto-assurance status (GREEN/RED · last run · Merkle root) — the simple card G asked for.
    Read-only projection of the deterministic daily math (vector + reference cross-verify + seal tripwire).
    Green is just a chip; a RED here means a gating CRITICAL card already sits in the Awaiting-Me queue."""
    repo = Path(__file__).resolve().parents[4]
    f = repo / "artifacts" / "crypto" / "assurance_status.json"
    if not f.is_file():
        return jsonify({"status": "not-run", "what": "crypto_assurance has not run yet"})
    try:
        return jsonify(json.loads(f.read_text(encoding="utf-8")))
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "ERROR", "what": str(e)}), 500
