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
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _import_core():
    """Thin CLI wrapper (Universalize Wave §5): the core now lives in the installed package. scripts→package
    is the allowed import direction (G4); package code never depends on this script."""
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.evidence.export_packet import build_packet, verify_packet, _canon
    from sovereign_agent.obligations.ledger import get_ledger_root
    return build_packet, verify_packet, _canon, get_ledger_root


build_packet, verify_packet, _canon, _get_ledger_root = _import_core()
DEFAULT_ROOT = _get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


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
