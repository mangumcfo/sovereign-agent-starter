#!/usr/bin/env python3
"""Ledger manifest ritual (P0-1, per GB's optimization analysis).

Gives the sovereign agent's OWN ObligationLedger the same iron-clad "see that it updated" proof
GB built for its meta-cylinder (scripts/gb_meta_cylinder.py). The ledger uses the identical
sha256-16 hash chain, so this is a thin, honest mirror — no new trust required.

Usage:
  PYTHONPATH=src python3 scripts/ledger_manifest.py manifest [ledger_root]
  PYTHONPATH=src python3 scripts/ledger_manifest.py verify   [ledger_root]
  PYTHONPATH=src python3 scripts/ledger_manifest.py last     [ledger_root]

Default ledger_root = memory/obligations/tiger_coordination.
Run after any open/approve/close: last_hash changes + obligation counts move = state updated.
Independent + cryptographic + countable + replayable — exactly like the FEC chain proof.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root  # noqa: E402

# This tool manifests the Tiger↔GB COORDINATION ledger by default (a deliberately different root from
# the node's review queue). Audit 2026-06-13: route through the ONE resolver so a CLI arg or
# OBLIGATION_LEDGER_ROOT env is honored, with tiger_coordination as this tool's documented fallback
# (no longer a silent 4th default that ignored the env).
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "memory" / "obligations" / "tiger_coordination"


def _ledger(argv) -> ObligationLedger:
    cli = argv[2] if len(argv) > 2 else None
    return ObligationLedger(root=str(get_ledger_root(explicit=cli, default=DEFAULT_ROOT)))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "manifest"
    led = _ledger(sys.argv)
    if cmd == "manifest":
        print("=== LEDGER MANIFEST (run after any open/approve/close to see the update) ===")
        print(json.dumps(led.manifest(), indent=2, sort_keys=True))
        print("=== Compare last_hash + obligations{open,closed,total} to the prior run. ===")
    elif cmd == "verify":
        print("Chain OK:", led.verify_chain(), "·", led.by_status())
    elif cmd == "last":
        entries = led._entries()
        print(json.dumps(entries[-1], indent=2, sort_keys=True) if entries else "empty")
    else:
        print("commands: manifest | verify | last  [ledger_root]")
        sys.exit(1)


if __name__ == "__main__":
    main()
