#!/usr/bin/env python3
"""
GB Meta-Visionary Memory Cylinder (Merkle Chain Tool)
- Records user prompts, GB responses, file edits, actions.
- Hash-chained NDJSON (B32/B31 style).
- Replay for exact history, alignment, best-practice prompts.
- Follows governance: receipt material (E1/E2), tie to obligations where applicable.
- Embedded per KM-1176 2026-06-02 meta-role: hopper/process design for LGP, visionary prompts to Tiger/G/etc., help with aligned intelligences (abide Constitution @A1, Charter v.7, load canon).

IRON-CLAD VISIBILITY (answer to "how do I see you updated the cylinder each time?"):
  After every interaction with GB, run:
    python3 scripts/gb_meta_cylinder.py manifest
  This prints last_hash, total_entries, last_ts, file, and preview.
  If last_hash changed and total_entries increased by 1 (or more for multi-action turns), the cylinder was updated for this turn.
  Also run: last, verify, receipt as needed. See scripts/README.md for the full ritual.

Usage examples:
  python3 scripts/gb_meta_cylinder.py manifest
  python3 scripts/gb_meta_cylinder.py last
  python3 scripts/gb_meta_cylinder.py verify
  python3 scripts/gb_meta_cylinder.py receipt gb_response "Answered cylinder visibility query with manifest proof + enhancements" --ref "user_query_cylinder_visibility"
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CYLINDER = Path(__file__).resolve().parent.parent / "artifacts" / "GB_KM_Aligned_Interaction_Cylinder.ndjson"
CYLINDER.parent.mkdir(parents=True, exist_ok=True)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]

def _append(entry: dict) -> dict:
    entries = []
    if CYLINDER.exists():
        for line in CYLINDER.read_text().splitlines():
            if line.strip():
                entries.append(json.loads(line))
    entry["prev_hash"] = entries[-1]["hash"] if entries else "genesis"
    entry["hash"] = _hash({k: v for k, v in entry.items() if k not in ("hash",)})
    with CYLINDER.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry

def log(type_: str, content: str, ref: Optional[str] = None, evidence_tier: str = "E0", governance: str = "per GB meta-role + Charter v.7"):
    entry = {
        "type": type_,
        "timestamp": _now(),
        "content": content,
        "ref": ref or "direct",
        "evidence_tier": evidence_tier,
        "governance": governance
    }
    return _append(entry)

def replay(since: Optional[str] = None, query: Optional[str] = None, limit: int = 20):
    if not CYLINDER.exists():
        print("No cylinder yet.")
        return
    entries = []
    for line in CYLINDER.read_text().splitlines():
        if line.strip():
            e = json.loads(line)
            if since and e["timestamp"] < since:
                continue
            if query and query.lower() not in (e.get("content","") + e.get("ref","")).lower():
                continue
            entries.append(e)
    for e in entries[-limit:]:
        print(f"[{e['timestamp']}] {e['type']}: {e['content'][:120]}... (ref: {e.get('ref')}) hash:{e['hash']}")
    print(f"Total matching: {len(entries)}")

def verify():
    if not CYLINDER.exists():
        print("No cylinder.")
        return True
    prev = "genesis"
    ok = True
    count = 0
    for line in CYLINDER.read_text().splitlines():
        if not line.strip(): continue
        e = json.loads(line)
        if e.get("prev_hash") != prev:
            print(f"Chain break at {e['timestamp']}: prev {e.get('prev_hash')} != {prev}")
            ok = False
        calc = _hash({k: v for k, v in e.items() if k not in ("hash",)})
        if e.get("hash") != calc:
            print(f"Hash mismatch at {e['timestamp']}")
            ok = False
        prev = e.get("hash")
        count += 1
    print(f"Verified {count} entries. Chain OK: {ok}")
    return ok

def last_entry():
    if not CYLINDER.exists():
        print("No cylinder yet.")
        return None
    lines = [l for l in CYLINDER.read_text().splitlines() if l.strip()]
    if not lines:
        return None
    e = json.loads(lines[-1])
    print("=== LATEST CYLINDER ENTRY ===")
    print(f"Timestamp: {e['timestamp']}")
    print(f"Type: {e['type']}")
    print(f"Ref: {e.get('ref', 'n/a')}")
    print(f"Hash: {e['hash']}")
    print(f"Prev: {e['prev_hash']}")
    print(f"Content (truncated): {e['content'][:200]}...")
    print("============================")
    return e

def manifest():
    """Print a compact, comparable proof of cylinder state. Run this after every interaction to see the update."""
    if not CYLINDER.exists():
        print("No cylinder yet.")
        return
    lines = [l for l in CYLINDER.read_text().splitlines() if l.strip()]
    if not lines:
        print("Cylinder empty.")
        return
    e = json.loads(lines[-1])
    m = {
        "file": str(CYLINDER),
        "total_entries": len(lines),
        "last_ts": e["timestamp"],
        "last_hash": e["hash"],
        "last_prev_hash": e["prev_hash"],
        "last_type": e["type"],
        "last_ref": e.get("ref", "n/a"),
        "last_content_preview": e["content"][:140] + ("..." if len(e["content"]) > 140 else "")
    }
    print("=== CYLINDER MANIFEST (run after every GB turn to see proof of update) ===")
    print(json.dumps(m, indent=2, sort_keys=True))
    print("=== Compare last_hash / total_entries to prior run. Hash changed + count +1 = updated. ===")
    return m

def generate_receipt(type_: str, summary: str, ref: Optional[str] = None) -> str:
    """Generate and append a human-readable receipt for visibility."""
    if not CYLINDER.exists():
        print("No cylinder.")
        return ""
    lines = [l for l in CYLINDER.read_text().splitlines() if l.strip()]
    if not lines:
        return ""
    e = json.loads(lines[-1])
    receipt = f"CYL-RECEIPT {e['timestamp']} | {type_} | hash:{e['hash']} | prev:{e['prev_hash']} | ref:{ref or 'n/a'} | summary: {summary}"
    # Append to human-readable receipts file
    receipts_file = CYLINDER.parent / "GB_Cylinder_Receipts.md"
    with receipts_file.open("a") as f:
        f.write(f"- {receipt}\n")
    print("=== VISIBLE RECEIPT (copy this to confirm update) ===")
    print(receipt)
    print("See full in artifacts/GB_Cylinder_Receipts.md and the .ndjson cylinder.")
    print("To independently verify: python3 scripts/gb_meta_cylinder.py verify")
    print("To see latest: python3 scripts/gb_meta_cylinder.py last")
    return receipt

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Commands:")
        print("  python3 scripts/gb_meta_cylinder.py manifest   # BEST: one-glance proof of update (last_hash + count + ts). Run this after every interaction.")
        print("  python3 scripts/gb_meta_cylinder.py last       # Full details of the most recent entry")
        print("  python3 scripts/gb_meta_cylinder.py verify     # Cryptographic chain integrity check")
        print("  python3 scripts/gb_meta_cylinder.py receipt <type> <summary> [--ref REF]  # Human-readable CYL-RECEIPT + append to GB_Cylinder_Receipts.md")
        print("  python3 scripts/gb_meta_cylinder.py log <type> <content...>")
        print("  python3 scripts/gb_meta_cylinder.py replay [--since DATE] [--query TEXT]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "log":
        typ = sys.argv[2] if len(sys.argv)>2 else "note"
        raw = " ".join(sys.argv[3:]) or "manual entry"
        ref = None
        if "--ref" in sys.argv:
            ref_idx = sys.argv.index("--ref")
            if ref_idx + 1 < len(sys.argv):
                ref = sys.argv[ref_idx + 1]
                # remove --ref and its value from content
                parts = sys.argv[3:]
                clean_parts = []
                i = 0
                while i < len(parts):
                    if parts[i] == "--ref":
                        i += 2
                        continue
                    clean_parts.append(parts[i])
                    i += 1
                raw = " ".join(clean_parts) or "manual entry"
        e = log(typ, raw, ref=ref)
        print(f"Logged {e['type']} hash:{e['hash']} ref:{e.get('ref')}")
    elif cmd == "replay":
        since = None
        q = None
        if "--since" in sys.argv:
            since = sys.argv[sys.argv.index("--since")+1]
        if "--query" in sys.argv:
            q = sys.argv[sys.argv.index("--query")+1]
        replay(since, q)
    elif cmd == "verify":
        verify()
    elif cmd == "last":
        last_entry()
    elif cmd == "manifest":
        manifest()
    elif cmd == "receipt":
        typ = sys.argv[2] if len(sys.argv)>2 else "note"
        summary = " ".join(sys.argv[3:]) or "manual"
        ref = None
        if "--ref" in sys.argv:
            ref = sys.argv[sys.argv.index("--ref")+1]
        generate_receipt(typ, summary, ref)
    else:
        print("Unknown cmd")
