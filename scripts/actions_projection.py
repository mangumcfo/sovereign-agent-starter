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
    from sovereign_agent.evidence.actions_projection import query_actions, verify_proof
    from sovereign_agent.obligations.ledger import get_ledger_root
    return query_actions, verify_proof, get_ledger_root


query_actions, verify_proof, _get_ledger_root = _import_core()
DEFAULT_ROOT = _get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


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
