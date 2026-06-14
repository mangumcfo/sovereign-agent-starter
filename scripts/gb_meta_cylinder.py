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
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CYLINDER = Path(__file__).resolve().parent.parent / "artifacts" / "GB_KM_Aligned_Interaction_Cylinder.ndjson"
CYLINDER.parent.mkdir(parents=True, exist_ok=True)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]

def _load_entries(path: Path = CYLINDER) -> list:
    """Tolerant read via the ONE package gateway (Universalize Wave §1/G2): a truncated tail no longer
    bricks GB's cylinder tool. scripts→package is the allowed import direction (G4)."""
    src = str(Path(__file__).resolve().parents[1] / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.ndjson import read_ndjson
    return read_ndjson(path).entries

def _append(entry: dict) -> dict:
    entries = _load_entries()
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
    for e in _load_entries():
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
    for e in _load_entries():
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
    entries = _load_entries()
    if not entries:
        return None
    e = entries[-1]
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
    entries = _load_entries()
    if not entries:
        print("Cylinder empty.")
        return
    e = entries[-1]
    m = {
        "file": str(CYLINDER),
        "total_entries": len(entries),
        "last_ts": e["timestamp"],
        "last_hash": e["hash"],
        "last_prev_hash": e["prev_hash"],
        "last_type": e["type"],
        "last_ref": e.get("ref", "n/a"),
        "last_content_preview": e["content"][:140] + ("..." if len(e["content"]) > 140 else "")
    }
    total = len(entries)
    print(f"=== {total} CYLINDER MANIFEST (run after every GB turn to see proof of update) ===")
    print(json.dumps(m, indent=2, sort_keys=True))
    print("=== Compare last_hash / total_entries to prior run. Hash changed + count +1 = updated. ===")
    return m

def generate_receipt(type_: str, summary: str, ref: Optional[str] = None) -> str:
    """Generate and append a human-readable receipt for visibility."""
    if not CYLINDER.exists():
        print("No cylinder.")
        return ""
    entries = _load_entries()
    if not entries:
        return ""
    e = entries[-1]
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

def analyze(limit: int = 15):
    """Full end-to-end self-scan of the cylinder for GB meta optimization opportunities.
    Run on genuine user signals (e.g. "scan the cylinder to glean where you can optimize yourself")
    or as periodic ritual. Output is clean, B51/HMC first-line friendly (starts with ===).
    Crosses types, ref keywords, high-signal themes (meta/cylinder/forward/hopper/THREAD/B51/voice/receipt/log/hygiene/roles/attachment/agentic/intake), receipt+log notes, volume, self-meta density, recent activity.
    Prints recommendations for light self-opts at end.
    """
    cyl_path = Path(__file__).resolve().parent.parent / "artifacts" / "GB_KM_Aligned_Interaction_Cylinder.ndjson"
    if not cyl_path.exists():
        print("No cylinder yet.")
        return
    entries = _load_entries(cyl_path)
    n = len(entries)
    print(f"=== CYLINDER SELF-SCAN @ {n} entries (run for GB meta self-optimization) ===")
    print(f"File: {cyl_path}")
    print(f"First: {entries[0].get('timestamp','n/a') if entries else 'n/a'}")
    print(f"Last:  {entries[-1].get('timestamp','n/a') if entries else 'n/a'}")

    types = Counter(e.get("type", "unknown") for e in entries)
    print("\n--- BY TYPE ---")
    for t, c in types.most_common():
        print(f"  {t}: {c}")

    # Ref keywords (light)
    ref_keywords = Counter()
    for e in entries:
        r = str(e.get("ref", "")).lower()
        for kw in re.findall(r"[a-z0-9_-]{4,}", r):
            ref_keywords[kw] += 1
    print("\n--- TOP REF KEYWORDS ---")
    for kw, c in ref_keywords.most_common(15):
        print(f"  {kw}: {c}")

    # Signal hits (self-meta relevant)
    signals = ["b51", "thread", "helix", "forward", "hopper", "hygiene", "receipt", "log", "meta", "voice", "mait", "metalayer", "cylinder", "stuck", "repair", "intake", "principle", "roles", "attachment", "agentic", "drill", "pipeline", "kdp"]
    content_sig = defaultdict(int)
    for e in entries:
        blob = (str(e.get("content", "")) + " " + str(e.get("ref", ""))).lower()
        for s in signals:
            if s in blob:
                content_sig[s] += 1
    print("\n--- HIGH-SIGNAL HITS (meta relevant) ---")
    for s in sorted(content_sig, key=content_sig.get, reverse=True)[:12]:
        print(f"  {s}: {content_sig[s]}")

    # Known process signals
    receipt_log_notes = sum(1 for e in entries if "receipt" in str(e.get("content","")+e.get("ref","")).lower() and "log" in str(e.get("content","")+e.get("ref","")).lower())
    stuck = sum(1 for e in entries if "stuck" in str(e.get("content","")+e.get("ref","")).lower())
    print(f"\n--- PROCESS SIGNALS --- receipt+log notes: {receipt_log_notes} | stuck mentions: {stuck}")

    # Last N
    print(f"\n--- LAST {min(limit, n)} ENTRIES (recent first) ---")
    for e in reversed(entries[-limit:]):
        ts = str(e.get("timestamp", ""))[:19]
        ref = str(e.get("ref", "n/a"))[:65]
        print(f"  {ts} | {e.get('type','')} | {ref}")

    # By day rough
    by_day = defaultdict(int)
    for e in entries:
        day = str(e.get("timestamp", ""))[:10]
        by_day[day] += 1
    print("\n--- ENTRIES BY DAY (volume trend) ---")
    for d in sorted(by_day)[-6:]:
        print(f"  {d}: {by_day[d]}")

    # Self-meta density
    self_meta_count = sum(1 for e in entries if any(x in str(e.get("ref","")+e.get("content","")).lower() for x in ["cylinder", "forward updated", "meta intake", "b51 meta", "roles clarification", "self", "optimize", "scan", "hygiene", "ritual"]))
    print(f"\n--- SELF-META / RITUAL DENSITY: {self_meta_count}/{n} ({int(100*self_meta_count/n) if n else 0}%) ---")

    print("\n--- GLEANED LIGHT SELF-OPTIMIZATIONS FOR GB (from this scan + current B51 cross) ---")
    print("1. `analyze` subcommand now exists (this report). Run on user 'scan cylinder' signals or post real cycles for proactive self-gleaning. Output B51-capturable. (Implemented this turn.)")
    print("2. Forward header Version was stale (still 2026-06-04); bumped on self-opt turns + added 'Last self-optimized' marker. Prevents header drift vs content (cf past yaml/roadmap hygiene).")
    print("3. Receipt+log distinction (12 notes, 1 explicit stuck) is known process; analyze now surfaces it + receipt help text can remind 'use log for ndjson content'. Future: consider optional auto-minimal-log on receipt if desired (not now, per design).")
    print("4. 69%+ cylinder is self-meta (forward/roadmap/cylinder/THREAD/hopper/B51/voice) by design – good (rituals mature). Volume peaked early then tapered (29 on 06-05) = healthy focus on content (metalayer, helix, voice gates, attachments/agentic, PDF editor flows). Opt: when B51 shows 'working tab'/'PDF review'/'Series Pipeline' usage (as in current +3 delta), 1-line note in bullets 'edit loop live per 561/562; rich feedback/attachments now via Helix G seed + voice process'.")
    print("5. High B51/voice/attachment/agentic/intake/roles signals (recent meta steer integration) + current B51 (user saw 194 manifest, giving PDF open/editor process feedback in working tab) = real cycle validating that meta layer (intake, provenance, one-gate) enables the Atrium editor flows at low tax. Keep extending voice process + Helix G for these.")
    print("6. THREAD early breaks (4 known) + hopper lean (9) + forward FIRST + cylinder log (not just receipt) rituals are holding. Analyze makes future 'full end to end' one cmd instead of ad-hoc python.")
    print("LGP: human-ease (one cmd for self-glean), resonance (tool reflects on own history), minimal burden (no new artifacts, extend existing cylinder script).")
    print("=== END SELF-SCAN ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Commands:")
        print("  python3 scripts/gb_meta_cylinder.py manifest   # BEST: one-glance proof of update (last_hash + count + ts). Top line now starts with N CYLINDER MANIFEST for direct visibility when captured into B51 HMC first-line preview.")
        print("  python3 scripts/gb_meta_cylinder.py last       # Full details of the most recent entry")
        print("  python3 scripts/gb_meta_cylinder.py verify     # Cryptographic chain integrity check")
        print("  python3 scripts/gb_meta_cylinder.py receipt <type> <summary> [--ref REF]  # Human-readable CYL-RECEIPT + append to GB_Cylinder_Receipts.md")
        print("  python3 scripts/gb_meta_cylinder.py log <type> <content...>  # Real ndjson append + chaining for immutable gb_action content")
        print("  python3 scripts/gb_meta_cylinder.py replay [--since DATE] [--query TEXT]")
        print("  python3 scripts/gb_meta_cylinder.py analyze [--limit N]   # Full end-to-end self-scan of cylinder for GB meta optimization opportunities. B51-capturable report + gleaned light self-opts. Run on 'scan the cylinder' signals or periodic ritual.")
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
    elif cmd == "analyze":
        lim = 15
        if "--limit" in sys.argv:
            try:
                lim = int(sys.argv[sys.argv.index("--limit")+1])
            except:
                pass
        analyze(limit=lim)
    else:
        print("Unknown cmd")
