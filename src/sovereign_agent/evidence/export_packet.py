"""
Evidence-Packet Export core (R22-1) — the importable package home (Universalize Wave §5, G4 law).

The request path (`GET /export/packet`) and the `scripts/export_packet.py` CLI both call THIS — the core
lives in the installed package so the Node API never injects `scripts/` onto `sys.path` at runtime (which
breaks in a container / non-editable install). The script is now a thin CLI wrapper over this module.
G4 law: scripts may import package code; package code must NEVER import scripts.

Assembles a set of obligations + their receipts into ONE signed, self-verifying export bundle a
buyer/auditor can validate on a clean machine: { manifest, entries[], receipts[], merkle_proof,
chain_range, sha }. Deterministic + re-runnable (canonical sorted JSON → byte-identical bundle).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from ..ndjson import read_ndjson  # the ONE tolerant ndjson reader (Universalize Wave §1)

VERSION = "r22-1/v1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _merkle_root(leaves: list) -> str:
    """sha256 Merkle root over the ordered leaf hashes. Odd node duplicates the last (standard)."""
    if not leaves:
        return _sha(b"")
    level = [bytes.fromhex(h) for h in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def _rows(root: Path) -> list:
    # Tolerant read via the ONE gateway (Universalize Wave §1): a truncated ledger tail no longer raises.
    return read_ndjson(Path(root) / "obligations.ndjson").entries


def build_packet(obl_ids: list, root: Path) -> dict:
    rows = _rows(root)
    want = set(obl_ids)
    # every ledger entry touching a requested obligation, in chain order
    entries = [e for e in rows
               if (e.get("type") == "debit" and e.get("id") in want)
               or (e.get("type") == "credit" and e.get("closes") in want)
               or (e.get("type") == "reopen" and e.get("reopens") in want)
               or (e.get("type") == "approval" and e.get("approves") in want)]
    if not entries:
        raise ValueError(f"no ledger entries for obligations {sorted(want)}")
    leaves = [e["hash"] for e in entries if e.get("hash")]
    receipts = [e["receipt"] for e in entries if e.get("type") == "credit" and e.get("receipt")]
    merkle = {"root": _merkle_root(leaves), "leaves": leaves}
    chain_range = {"first_hash": entries[0].get("hash"), "last_hash": entries[-1].get("hash")}
    manifest = {
        "version": VERSION,
        "generated_for": sorted(want),
        "entry_count": len(entries),
        "receipt_count": len(receipts),
        "generated_note": "deterministic evidence packet; verify with: "
                          "python3 export_packet.py verify <bundle.json>",
    }
    core = {"manifest": manifest, "entries": entries, "receipts": receipts,
            "merkle_proof": merkle, "chain_range": chain_range}
    return {**core, "sha": _sha(_canon(core))}


def verify_packet(bundle: dict, check_anchor: Optional[str] = None) -> tuple:
    """Self-verify on a clean machine: recompute Merkle root + bundle sha; optionally check anchor."""
    core = {k: bundle[k] for k in ("manifest", "entries", "receipts", "merkle_proof", "chain_range")
            if k in bundle}
    if _sha(_canon(core)) != bundle.get("sha"):
        return False, "bundle sha mismatch — tampered or non-canonical"
    leaves = [e["hash"] for e in bundle.get("entries", []) if e.get("hash")]
    root = _merkle_root(leaves)
    if root != bundle.get("merkle_proof", {}).get("root"):
        return False, "Merkle root mismatch — receipts/entries altered"
    # chain_range must match the first/last included entry
    cr = bundle.get("chain_range", {})
    if bundle["entries"] and (cr.get("first_hash") != bundle["entries"][0].get("hash")
                              or cr.get("last_hash") != bundle["entries"][-1].get("hash")):
        return False, "chain_range does not bound the included entries"
    if check_anchor and root != check_anchor:
        return False, f"anchor mismatch — Merkle root {root[:12]}… != anchor {check_anchor[:12]}…"
    return True, f"OK — {len(leaves)} entries, root {root[:12]}…, {bundle['manifest']['receipt_count']} receipts"
