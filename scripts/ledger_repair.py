#!/usr/bin/env python3
"""ledger_repair.py — chain-repair command for an already-forked obligation ledger (audit 2026-06-10).

A forked chain (verify_chain()==False, from pre-fence concurrent appends) cannot self-heal: prev_hash
links are broken. This re-links every entry in file order, backs up the raw forked record to
obligations.ndjson.forked.<n>, and rewrites a valid chain. Held under the same flock as _append.

  python3 scripts/ledger_repair.py [<ledger_root>]      # default = OBLIGATION_LEDGER_ROOT / repo default
  python3 scripts/ledger_repair.py --verify [<root>]    # just report verify_chain(), no changes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sovereign_agent.obligations import ObligationLedger  # noqa: E402


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--verify"]
    verify_only = "--verify" in sys.argv
    root = args[0] if args else None
    lg = ObligationLedger(root)
    print(f"ledger: {lg.path}")
    ok = lg.verify_chain()
    print(f"verify_chain (before): {ok}")
    if verify_only:
        return 0 if ok else 1
    res = lg.repair_chain()
    if res["repaired"]:
        print(f"REPAIRED {res['entries']} entries · raw fork backed up to {res['backup']}")
    else:
        print("no repair needed — chain already valid")
    print(f"verify_chain (after):  {lg.verify_chain()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
