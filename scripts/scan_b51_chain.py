#!/usr/bin/env python3
"""
B51 Human Memory Cylinder Scanner
GB meta tool for direct read-only access to the user's B51 chain.
Scans for new/pre-seal entries in the live B51 capture directories.
Provides latest context for full awareness of human's conversational history and current work.

Usage examples:
  python3 scripts/scan_b51_chain.py --limit 5
  python3 scripts/scan_b51_chain.py --history --limit 10   # mimics the UI Capture History list
  python3 scripts/scan_b51_chain.py --limit 1 --content    # full text of latest
  python3 scripts/scan_b51_chain.py --recent --limit 5     # latest entries (tail) from the *current open unsealed cyl* the user sees in HMC UI right now (direct, no share needed)
  python3 scripts/scan_b51_chain.py --delta --limit 5      # ONLY new entries since last scan (incremental; prior already captured by GB). Live json only.

This is now standard GB practice: run before status queries, "what am I working on?", or when human context from B51 is relevant.
"""

import os
import sys
import json
import argparse
from pathlib import Path

B51_BASE = Path("/home/kmangum/molt_workspace/exports/b51")
QUICK_SHARE = B51_BASE / "quick-share"
# Primary source for unsealed/current HMC (live app storage, not exports/snapshots)
LIVE_SESSIONS = Path("/home/kmangum/.local/share/human-memory-cylinder/sessions")

def find_sessions(base_dir):
    """Find all capture-session directories, return sorted by mtime desc."""
    sessions = []
    for root, dirs, files in os.walk(base_dir):
        for d in dirs:
            if "capture-session" in d:
                full = Path(root) / d
                try:
                    mtime = full.stat().st_mtime
                    sessions.append((full, mtime))
                except:
                    pass
    sessions.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in sessions]

def find_live_sessions():
    """Find live unsealed cyl_*.json from the B51 app's active sessions dir (primary for current HMC)."""
    sessions = []
    if not LIVE_SESSIONS.exists():
        return sessions
    for p in LIVE_SESSIONS.glob("cyl_*.json"):
        try:
            mtime = p.stat().st_mtime
            sessions.append((p, mtime))
        except:
            pass
    sessions.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in sessions]

def parse_live_json(json_path):
    """Parse a live cyl_*.json for metadata + first-line preview from entries (direct unsealed content)."""
    info = {"path": str(json_path), "source": "live-unsealed"}
    try:
        data = json.loads(json_path.read_text())
    except Exception as e:
        info["error"] = str(e)
        return info
    info["session_id"] = data.get("id")
    info["timestamp"] = data.get("started_at")
    info["entry_count"] = len(data.get("entries", []))
    info["sealed"] = data.get("sealed", False)
    info["ended_at"] = data.get("ended_at")
    info["status"] = "unsealed" if not data.get("sealed") and not data.get("ended_at") else "sealed"
    entries = data.get("entries", [])
    if entries:
        first = entries[0]
        content = first.get("content") or first.get("preview") or ""
        first_line = content.splitlines()[0].strip() if content else "(empty)"
        info["md_preview"] = first_line[:300]
        info["first_entry_ts"] = first.get("timestamp")
        # full first content for --content
        info["md_full"] = "\n".join(e.get("content", "") for e in entries[:5])
        # NEW: recent/tail for the active unsealed "current view" the user sees in HMC now
        info["recent_entries"] = []
        for e in entries[-5:]:
            c = (e.get("content") or e.get("preview") or "").strip()
            line = c.splitlines()[0].strip()[:200] if c else "(empty)"
            info["recent_entries"].append({"ts": e.get("timestamp"), "line": line})
    else:
        info["md_preview"] = "(no entries)"
        info["md_full"] = ""
        info["recent_entries"] = []
    info["has_proof"] = bool(data.get("root_hash"))
    info["merkle_root"] = data.get("root_hash")
    return info

def parse_session(session_dir):
    """Parse a single session dir for metadata and content."""
    info = {"path": str(session_dir)}
    digest_file = session_dir / "session.digest.yaml"
    if digest_file.exists():
        with open(digest_file) as f:
            content = f.read()
            info["digest_raw"] = content
            for line in content.splitlines():
                if "session_id:" in line:
                    info["session_id"] = line.split(":", 1)[1].strip().strip("'\"")
                if "timestamp:" in line:
                    info["timestamp"] = line.split(":", 1)[1].strip().strip("'\"")
                if "entry_count:" in line:
                    info["entry_count"] = line.split(":", 1)[1].strip()
                if "merkle_root:" in line:
                    info["merkle_root"] = line.split(":", 1)[1].strip().strip("'\"")
    else:
        info["digest_raw"] = "no digest.yaml"

    md_file = session_dir / "session.md"
    if md_file.exists():
        with open(md_file) as f:
            md = f.read()
            info["md_full"] = md
            info["md_preview"] = md[:400] + "..." if len(md) > 400 else md
            if "sealed" in md.lower() or "proof" in md.lower() or "Seal" in md:
                info["status"] = "likely sealed"
            else:
                info["status"] = "possible pre-seal"
    else:
        info["md_full"] = "no session.md"
        info["md_preview"] = "no session.md"
        info["status"] = "unknown"

    proof_file = session_dir / "proof.json"
    if proof_file.exists():
        try:
            with open(proof_file) as f:
                proof = json.load(f)
            info["has_proof"] = True
            info["proof_summary"] = str(proof)[:150]
        except:
            info["has_proof"] = False
    else:
        info["has_proof"] = False

    return info

def print_history_like_ui(sessions, limit=20):
    """Output a simple list mimicking the B51 UI CAPTURE HISTORY pane."""
    print("CAPTURE HISTORY (mimicking B51 UI)")
    for i, s in enumerate(sessions[:limit], 1):
        info = parse_session(s)
        md = info.get("md_full", "") or ""
        first_line = s.name
        # Look for the first meaningful user-captured line in the Conversation section
        in_conv = False
        for line in md.splitlines():
            line = line.strip()
            if "Conversation" in line:
                in_conv = True
                continue
            if in_conv and line and not line.startswith("*") and not line.startswith("---"):
                if "User copied" in line or line.startswith("Done") or line.startswith("Thanks") or line.startswith("KM-") or "meta" in line.lower() or "prompt" in line.lower() or "extrusion" in line.lower():
                    first_line = line[:75]
                    break
                if len(line) > 15 and not line.startswith("["):
                    first_line = line[:75]
                    break
        print(f"  {i}. {s.name}  {first_line}...")
    print(f"  ... ({len(sessions)} total)")

def scan(limit=5, since=None, include_content=False):
    """Scan live (primary for unsealed/current) + exports (for archived)."""
    candidates = []
    # Live unsealed first (current B51 HMC open captures)
    candidates.extend(find_live_sessions())
    # Then exports/quick-shares (older sealed snapshots)
    if QUICK_SHARE.exists():
        candidates.extend(find_sessions(QUICK_SHARE))
    if B51_BASE.exists():
        candidates.extend(find_sessions(B51_BASE))

    seen = set()
    unique = []
    for s in candidates:
        name = s.name
        if name not in seen:
            seen.add(name)
            unique.append(s)

    unique.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

    results = []
    for s in unique[:limit]:
        if str(s).endswith(".json"):
            info = parse_live_json(s)
        else:
            info = parse_session(s)
        if since:
            ts = info.get("timestamp", "") or ""
            if ts < since:
                continue
        if include_content:
            info["full_content"] = info.get("md_full", "")
        results.append(info)
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan B51 human memory cylinder for latest entries (direct FS access).")
    parser.add_argument("--limit", type=int, default=5, help="Max recent sessions")
    parser.add_argument("--since", type=str, default=None, help="ISO timestamp filter")
    parser.add_argument("--content", action="store_true", help="Include full content (careful, large)")
    parser.add_argument("--history", action="store_true", help="Print Capture History list like the B51 UI")
    parser.add_argument("--recent", action="store_true", help="For the active unsealed cyl (current HMC view), print the latest N entries (tail) instead of session starters. This is the 'what I see right now' in the open capture.")
    parser.add_argument("--delta", action="store_true", help="Only report NEW entries since last scan (incremental, using persisted entry count for the active unsealed cyl). Prior captured entries are skipped. Always from live json write.")
    args = parser.parse_args()

    print("=== B51 Human Memory Cylinder Scan (direct read-only) ===")
    print(f"Live unsealed primary: {LIVE_SESSIONS}")
    print(f"Exports fallback: {B51_BASE}")
    print("Scanning for new/pre-seal entries (live first for current HMC)...")
    print("Use --recent to get the tail (latest entries) of the active unsealed cyl that is open in your HMC UI. Use --delta for ONLY new since last scan (incremental from live json write).")

    if args.history:
        sessions = []
        sessions.extend(find_live_sessions())
        if QUICK_SHARE.exists():
            sessions.extend(find_sessions(QUICK_SHARE))
        sessions.extend(find_sessions(B51_BASE))
        seen = set()
        unique = []
        for s in sessions:
            name = s.name
            if name not in seen:
                seen.add(name)
                unique.append(s)
        unique.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        # For live json, use a simple history printer that works for both
        print("CAPTURE HISTORY (mimicking B51 UI)  [live unsealed + exports]")
        shown = 0
        for p in unique[:args.limit]:
            if str(p).endswith(".json"):
                info = parse_live_json(p)
                first = info.get("md_preview", p.name)[:75]
                print(f"  {shown+1}. {p.name}  {first}...")
            else:
                info = parse_session(p)
                md = info.get("md_full", "") or ""
                first_line = p.name
                in_conv = False
                for line in md.splitlines():
                    line = line.strip()
                    if "Conversation" in line:
                        in_conv = True
                        continue
                    if in_conv and line and not line.startswith("*") and not line.startswith("---"):
                        if len(line) > 15 and not line.startswith("["):
                            first_line = line[:75]
                            break
                print(f"  {shown+1}. {p.name}  {first_line}...")
            shown += 1
        print(f"  ... ({len(unique)} total; live at {LIVE_SESSIONS})")
        print("\nRun this regularly as part of GB meta context gathering.")
        sys.exit(0)

    if args.recent:
        # Find the active unsealed (sealed=False or the live one with most recent mtime among unsealed)
        live_files = find_live_sessions()
        active = None
        for p in live_files:
            try:
                d = json.loads(p.read_text())
                if not d.get("sealed") and not d.get("ended_at"):
                    active = (p, d)
                    break
            except:
                pass
        if not active and live_files:
            # fallback most recent live
            p = live_files[0]
            active = (p, json.loads(p.read_text()))
        if active:
            p, d = active
            print("=== CURRENT UNSEALED HMC VIEW (live json tail) ===")
            print(f"Active cyl: {d.get('id')}  entries:{len(d.get('entries',[]))}  started:{d.get('started_at','?')[:16]}")
            print("Latest entries (most recent first in UI sense; tail of live data):")
            ents = d.get("entries", [])[-args.limit:]
            for e in reversed(ents):  # so most recent on top
                ts = (e.get("timestamp") or "?")[:19]
                c = (e.get("content") or e.get("preview") or "").strip()
                line = c.splitlines()[0][:160] if c else "(empty)"
                print(f"  [{ts}] {line}")
            print(f"\nSource (direct unsealed, no share required): {p}")
            print("This gives line of sight to content *while unsealed*. Share action creates the dated export snapshot you see in quick-share.")
            sys.exit(0)
        else:
            print("No active unsealed cyl found in live sessions.")
            sys.exit(0)

    if args.delta:
        # Incremental only-new (user #2: prior posts already captured, just surface deltas)
        # State lives in artifacts/.b51_last_scan.json (simple, no deps)
        state_path = Path("artifacts/.b51_last_scan.json")
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text())
            except:
                state = {}
        live_files = find_live_sessions()
        active = None
        for p in live_files:
            try:
                d = json.loads(p.read_text())
                if not d.get("sealed") and not d.get("ended_at"):
                    active = (p, d)
                    break
            except:
                pass
        if not active and live_files:
            p = live_files[0]
            active = (p, json.loads(p.read_text()))
        if active:
            p, d = active
            cyl_id = d.get("id")
            ents = d.get("entries", [])
            curr = len(ents)
            last_c = state.get("last_entry_count", 0) if state.get("cyl_id") == cyl_id else 0
            new_n = max(0, curr - last_c)
            new_ents = ents[-new_n:] if new_n > 0 else []
            # persist
            new_state = {"cyl_id": cyl_id, "path": str(p), "last_entry_count": curr, "last_mtime": p.stat().st_mtime}
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(new_state, indent=2))
            print("=== B51 DELTA (live unsealed only -- new since last scan) ===")
            print(f"Active: {cyl_id}  total:{curr} (was {last_c})  +{new_n} new")
            print(f"Source: {p} (direct live write, not exports)")
            shown = 0
            for e in new_ents[-args.limit:]:
                ts = (e.get("timestamp") or "?")[:19]
                c = (e.get("content") or e.get("preview") or "").strip()
                line = c.splitlines()[0][:140] if c and c.splitlines() else "(empty or no text)"
                print(f"  + [{ts}] {line}")
                shown += 1
            if new_n == 0:
                print("  (no new entries since last delta scan)")
            print(f"\nState saved to {state_path} for next incremental run.")
            sys.exit(0)
        else:
            print("No active unsealed for delta.")
            sys.exit(0)

    results = scan(limit=args.limit, since=args.since, include_content=args.content)

    if not results:
        print("No sessions found or matching criteria.")
        sys.exit(0)

    for i, r in enumerate(results, 1):
        print(f"\n--- Entry {i} ---")
        print(f"Path: {r.get('path')}")
        print(f"Session ID: {r.get('session_id', 'N/A')}")
        print(f"Timestamp: {r.get('timestamp', 'N/A')}")
        print(f"Entries: {r.get('entry_count', 'N/A')}")
        print(f"Merkle Root: {r.get('merkle_root', 'N/A')}")
        print(f"Status: {r.get('status', 'N/A')}")
        print(f"Has Proof: {r.get('has_proof', False)}")
        print(f"Preview: {r.get('md_preview', '')[:250]}...")
        if 'full_content' in r:
            print("FULL CONTENT (first 1500 chars):")
            print(r['full_content'][:1500])

    print("\n=== Scan complete. Use --history, --recent, --delta for incremental live view. ===")
    print("Always live unsealed json (direct write) primary for Breath to Code. Exports = snapshots only.")
