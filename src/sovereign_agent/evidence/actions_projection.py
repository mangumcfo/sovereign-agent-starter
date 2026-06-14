"""
Queryable actions projection core (R22-2) — the importable package home (Universalize Wave §5, G4 law).

Answers "what actions occurred, by class / principal / obligation / time?" as a VERIFIABLE QUERY over the
ledger's Merkle leaves. Every returned row cites its leaf (the entry's chain hash) and a Merkle inclusion
proof to the root, so any consumer can independently confirm the row is in the sealed set.

Lives in the installed package so the Node API (`GET /actions`) imports it directly — no `scripts/` on the
runtime sys.path. The `scripts/actions_projection.py` CLI is a thin wrapper over this module. G4 law:
scripts may import package code; package code must NEVER import scripts.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..ndjson import read_ndjson  # the ONE tolerant ndjson reader (Universalize Wave §1)

_CACHE: dict = {}   # (path, mtime, size) -> (rows, leaves, layers)
_ACTION = {"debit": "open", "approval": "approve", "credit": "close", "reopen": "reopen"}


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def _layers(leaves: list) -> list:
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


def _proof(layers: list, index: int) -> list:
    proof, idx = [], index
    for lvl in layers[:-1]:
        sib = idx ^ 1
        if sib < len(lvl):
            proof.append({"hash": lvl[sib].hex(), "right": sib > idx})
        idx //= 2
    return proof


def verify_proof(leaf_hex: str, proof: list, root_hex: str) -> bool:
    h = bytes.fromhex(leaf_hex)
    for step in proof:
        s = bytes.fromhex(step["hash"])
        h = _h(h + s) if step["right"] else _h(s + h)
    return h.hex() == root_hex


def _ledger(root: Path):
    # Memoized on the chain's (mtime,size); tolerant read via the ONE gateway (Universalize Wave §1/§3).
    f = Path(root) / "obligations.ndjson"
    try:
        st = f.stat()
        key = (str(f), st.st_mtime_ns, st.st_size)
    except OSError:
        key = (str(f), 0, 0)
    if key not in _CACHE:
        rows = read_ndjson(f).entries
        leaves = [e["hash"] for e in rows if e.get("hash")]
        _CACHE.clear()
        _CACHE[key] = (rows, leaves, _layers(leaves))
    return _CACHE[key]


def _entity(e: dict):
    return e.get("id") or e.get("closes") or e.get("approves") or e.get("reopens")


def query_actions(root: Path, *, type=None, principal=None, obligation=None,
                  since=None, until=None) -> dict:
    rows, leaves, layers = _ledger(root)
    root_hex = layers[-1][0].hex() if leaves else _h(b"").hex()
    out = []
    li = 0
    for e in rows:
        if not e.get("hash"):
            continue
        idx = li
        li += 1
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
