#!/usr/bin/env python3
"""
actions_projection.py — R22-2 Queryable `.actions[]` Projection over Merkle (GB spec 2026-06-12).

Answers "what actions occurred, by class / principal / obligation / time?" as a VERIFIABLE QUERY over
the ledger's Merkle leaves — not a file scan. Pure projection (the queue-is-a-query discipline applied
to actions): reads nothing it cannot anchor, writes nothing, memoized on the ledger's (mtime, size).

Each ledger entry is one action (debit=open · approval=approve · credit=close · reopen=reopen). Every
returned row cites its **leaf** (the entry's chain hash) and a **Merkle inclusion proof** to the root,
so any consumer can independently confirm the row is in the sealed set — no row without a verifiable anchor.

Success metric (R22-2): every `/actions` row resolves to its Merkle leaf + proof; read-only + re-runnable.

Usage:
  python3 scripts/actions_projection.py [--type credit] [--principal KM-1176] [--obligation ID]
                                        [--since 2026-06-12] [--until 2026-06-13] [--root <dir>] [--json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _resolve_default_root() -> Path:
    """Route through THE canonical resolver (audit 2026-06-13d #31) so this script can NEVER resolve a
    different root than the node API / bell executor — the split-brain get_ledger_root() exists to prevent.
    Same semantics as before (OBLIGATION_LEDGER_ROOT → atrium_review), now single-sourced + boundary-checked."""
    import sys
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


DEFAULT_ROOT = _resolve_default_root()

_CACHE: dict = {}   # (path, mtime, size) -> (leaves, layers)
_ACTION = {"debit": "open", "approval": "approve", "credit": "close", "reopen": "reopen"}


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _layers(leaves: list[str]) -> list[list[bytes]]:
    """All Merkle levels (leaf → root), odd node duplicates last — matches export_packet._merkle_root."""
    level = [bytes.fromhex(x) for x in leaves]
    out = [level]
    while len(level) > 1:
        if len(level) % 2:
            level = level + [level[-1]]
            out[-1] = level
        level = [_h(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        out.append(level)
    return out


def _proof(layers: list[list[bytes]], index: int) -> list[dict]:
    proof, idx = [], index
    for lvl in layers[:-1]:
        sib = idx ^ 1
        if sib < len(lvl):
            proof.append({"hash": lvl[sib].hex(), "right": sib > idx})
        idx //= 2
    return proof


def verify_proof(leaf_hex: str, proof: list[dict], root_hex: str) -> bool:
    h = bytes.fromhex(leaf_hex)
    for step in proof:
        s = bytes.fromhex(step["hash"])
        h = _h(h + s) if step["right"] else _h(s + h)
    return h.hex() == root_hex


def _ledger(root: Path):
    f = root / "obligations.ndjson"
    st = f.stat()
    key = (str(f), st.st_mtime_ns, st.st_size)
    if key not in _CACHE:
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        leaves = [e["hash"] for e in rows if e.get("hash")]
        _CACHE.clear()
        _CACHE[key] = (rows, leaves, _layers(leaves))
    return _CACHE[key]


def _entity(e: dict) -> str | None:
    return e.get("id") or e.get("closes") or e.get("approves") or e.get("reopens")


def query_actions(root: Path, *, type=None, principal=None, obligation=None,
                  since=None, until=None) -> dict:
    rows, leaves, layers = _ledger(root)
    root_hex = layers[-1][0].hex() if leaves else _h(b"").hex()
    out = []
    leaf_index = {}
    li = 0
    for e in rows:
        if not e.get("hash"):
            continue
        idx = li; li += 1
        et = e.get("type")
        if type and _ACTION.get(et, et) != type and et != type:
            continue
        if principal and e.get("principal_id") != principal and e.get("closed_by") != principal \
                and e.get("approved_by") != principal:
            continue
        if obligation and _entity(e) != obligation:
            continue
        ts = str(e.get("timestamp", ""))[:10]
        if since and ts and ts < since:
            continue
        if until and ts and ts > until:
            continue
        out.append({
            "action": _ACTION.get(et, et),
            "obligation": _entity(e),
            "principal": e.get("principal_id"),
            "timestamp": e.get("timestamp"),
            "leaf": e["hash"],
            "merkle_proof": _proof(layers, idx),
            "root": root_hex,
        })
    return {"root": root_hex, "count": len(out), "read_only": True, "actions": out}


def main() -> int:
    ap = argparse.ArgumentParser(description="R22-2 queryable actions projection over Merkle")
    ap.add_argument("--type"); ap.add_argument("--principal"); ap.add_argument("--obligation")
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--root", default=str(DEFAULT_ROOT)); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res = query_actions(Path(a.root), type=a.type, principal=a.principal, obligation=a.obligation,
                        since=a.since, until=a.until)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
    print(f"actions: {res['count']} (root {res['root'][:12]}…, read-only)")
    for r in res["actions"][:20]:
        ok = verify_proof(r["leaf"], r["merkle_proof"], r["root"])
        print(f"  {'✓' if ok else '✗'} {r['action']:<8} {str(r['obligation'])[-12:]:<13} "
              f"{r['principal'] or '—':<10} leaf {r['leaf'][:10]}…")
    if res["count"] > 20:
        print(f"  … +{res['count']-20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ∞Δ∞ SEAL: actions as a verifiable query — every row anchors to its Merkle leaf + proof; read-only,
#          re-runnable, memoized. The queue-is-a-query discipline, applied to the action record. ∞Δ∞
