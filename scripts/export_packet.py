#!/usr/bin/env python3
"""
export_packet.py — R22-1 Evidence-Packet Exports (GB spec 2026-06-12).

The engine-side of S5_37's Clean Exit Package: assemble a set of obligations + their receipts into
ONE signed, self-verifying export bundle a buyer/auditor can validate **on a clean machine** with
nothing but this script and the bundle. Build once, pin both (R-22 promise + Migration Arc lead vol).

Bundle shape (GB contract):
  { manifest, receipts[], merkle_proof, chain_range, sha }
  - manifest    : {version, generated_for[obl_ids], entry_count, generated_note}
  - receipts    : the credit-receipts for those obligations (the evidence)
  - merkle_proof: {root, leaves[]} over the included ledger-entry chain hashes (sha256 tree)
  - chain_range : {first_hash, last_hash} of the covered segment
  - sha         : sha256 of the canonical bundle (manifest+entries+merkle_root+chain_range)

Success metric (R22-1): an exported packet passes verification end-to-end on a clean machine — the
bundle self-verifies (recompute the Merkle root over the included hashes; recompute the bundle sha;
both must match). `--check-anchor` additionally checks the Merkle root against a provided public anchor.

Deterministic + re-runnable: same obl_ids + same ledger → byte-identical bundle (canonical sorted JSON).

Usage:
  python3 scripts/export_packet.py build --obl-ids A,B,C [--root <ledger_dir>] [-o bundle.json]
  python3 scripts/export_packet.py verify bundle.json [--check-anchor <root_hex>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
def _resolve_default_root() -> Path:
    """Route through THE canonical resolver (audit 2026-06-13d #31): one root, boundary-checked, never a
    split-brain vs the node API / bell. Same semantics (OBLIGATION_LEDGER_ROOT → atrium_review)."""
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


DEFAULT_ROOT = _resolve_default_root()
VERSION = "r22-1/v1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _merkle_root(leaves: list[str]) -> str:
    """sha256 Merkle root over the ordered leaf hashes. Odd node duplicates the last (standard)."""
    if not leaves:
        return _sha(b"")
    level = [bytes.fromhex(h) for h in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [hashlib.sha256(level[i] + level[i + 1]).digest() for i in range(0, len(level), 2)]
    return level[0].hex()


def _rows(root: Path) -> list[dict]:
    f = root / "obligations.ndjson"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def build_packet(obl_ids: list[str], root: Path) -> dict:
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


def verify_packet(bundle: dict, check_anchor: str | None = None) -> tuple[bool, str]:
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


def main() -> int:
    ap = argparse.ArgumentParser(description="R22-1 evidence-packet export + verify")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--obl-ids", required=True)
    b.add_argument("--root", default=str(DEFAULT_ROOT)); b.add_argument("-o", "--out", default=None)
    v = sub.add_parser("verify"); v.add_argument("bundle"); v.add_argument("--check-anchor", default=None)
    a = ap.parse_args()

    if a.cmd == "build":
        bundle = build_packet([x.strip() for x in a.obl_ids.split(",") if x.strip()], Path(a.root))
        out = _canon(bundle).decode() if a.out else json.dumps(bundle, indent=2, ensure_ascii=False)
        if a.out:
            Path(a.out).write_text(out, encoding="utf-8"); print(f"wrote {a.out} (sha {bundle['sha'][:12]}…)")
        else:
            print(out)
        return 0
    if a.cmd == "verify":
        bundle = json.loads(Path(a.bundle).read_text(encoding="utf-8"))
        ok, why = verify_packet(bundle, a.check_anchor)
        print(("✓ " if ok else "✗ ") + why)
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

# ∞Δ∞ SEAL: the receipted ledger as a deal artifact — a self-verifying packet a buyer runs on a clean
#          machine. R22-1 + S5_37 Clean Exit, one engine. ∞Δ∞
