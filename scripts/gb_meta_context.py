#!/usr/bin/env python3
"""
GB Meta Context Helper - Tiny script to solidify GB's process.

Purpose: Provide a single command for GB to gather a "grounded context pack" for the meta arc:
- LGP north-star
- Book to Code (co-extrusion, WORKFLOW, prompts to G/Tiger)
- Breath to Code (B51/HMC direct scan as human memory source)
- Coordination across AIs (Tiger, G on x.com/grok.com, Lumen, self as local GB)
- Watch the repo (this workspace) and keep all grounded.

Usage:
  python3 scripts/gb_meta_context.py [--for-ai TIGER|G_X|G_GROK|LUMEN] [--package]

- Without --for-ai: Prints internal context pack for GB's thinking (latest HMC from live unsealed first, cylinder, forward path P0, recent canon changes).
- With --for-ai: Generates a ready-to-handoff message + attachment notes for that AI, focused on next steps that advance the Objective.
- --package: Also suggests files to attach (e.g. the helper itself, updated forward path, recent B51 export).

This is now part of the iron-clad GB meta process. Run this (or equivalent) before any status, proposal, or coordination turn to stay grounded on historical threads + latest.

It improves on the previous B51 scanner by:
- Reading LIVE unsealed sessions (~/.local/share/human-memory-cylinder/sessions/cyl_*.json with full entries) as primary source (direct write, never exports/quick-shares which are snapshots).
- Delta mode (#2 approved): on each run only reports "new since last scan" for the active unsealed cyl (entry_count cursor persisted in artifacts/.b51_last_scan.json). Prior entries already captured by GB are skipped.
- Prioritizing unsealed + recency (and now incremental tail for current work) so GB always has fresh human context for Breath to Code without duplication.
- Combining with GB cylinder replay for meta history + producing handoff-ready packages.

Run after every major user steer on process/format/arc.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

B51_BASE = Path("/home/kmangum/molt_workspace/exports/b51")
QUICK_SHARE = B51_BASE / "quick-share"
# Primary for unsealed/current: the app's live HMC storage (json cylinders with full entries)
LIVE_SESSIONS = Path("/home/kmangum/.local/share/human-memory-cylinder/sessions")
CYLINDER = Path("artifacts/GB_KM_Aligned_Interaction_Cylinder.ndjson")
FORWARD_PATH = Path("artifacts/GB_Prioritized_Forward_Path.md")
ROLE_DOC = Path("artifacts/GB_Meta_Visionary_Role_and_Constitutional_Memory_Cylinder.md")
WORKFLOW = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/WORKFLOW.md")  # canon reference
# Delta state for "only what's new" (per user: prior captured, just report increments on active unsealed)
B51_SCAN_STATE = Path("artifacts/.b51_last_scan.json")

def get_latest_hmc(limit=3):
    """Latest HMC from live unsealed app storage first (cyl_*.json with inline entries), then exports.
    This captures the user's current open B51 HMC (unsealed, pre-seal, latest voice) not just shares/exports.
    """
    sessions = []
    # Live unsealed primary (current HMC the user sees in app UI)
    if LIVE_SESSIONS.exists():
        for p in sorted(LIVE_SESSIONS.glob("cyl_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(p.read_text())
                started = data.get("started_at", "")
                sealed = data.get("sealed", False)
                ended = data.get("ended_at")
                entries = data.get("entries", [])
                # Prefer a "current view" preview from the *tail* (latest entries the user is working on now) for the unsealed active cyl
                preview = ""
                recent_line = ""
                if entries:
                    # For active unsealed, use last entry as the "what I see now" preview
                    if not sealed and not ended:
                        c = entries[-1].get("content") or entries[-1].get("preview") or ""
                        recent_line = c.splitlines()[0][:300] if c else ""
                        preview = f"[LATEST in active unsealed] {recent_line}"
                    else:
                        c = entries[0].get("content") or entries[0].get("preview") or ""
                        preview = c.splitlines()[0][:500] if c else ""
                mtime = p.stat().st_mtime
                meta = {"sealed": sealed, "ended": bool(ended), "count": len(entries)}
                if recent_line:
                    meta["latest_line"] = recent_line
                sessions.append((p, started or "", mtime, preview, meta))
            except:
                continue
    # Fallback to exports for older sealed
    for base in [QUICK_SHARE, B51_BASE]:
        if not base.exists():
            continue
        for p in base.iterdir():
            if "capture-session" not in p.name:
                continue
            md = p / "session.md"
            if not md.exists():
                continue
            try:
                content = md.read_text()
                exported = None
                for line in content.splitlines()[:10]:
                    if "exported_at:" in line:
                        exported = line.split(":", 1)[1].strip().strip("'\"")
                        break
                mtime = p.stat().st_mtime
                sessions.append((p, exported or "", mtime, content[:500], {"sealed": True, "ended": True, "count": None}))
            except:
                continue
    # Sort preferring unsealed + recency (live mtime or started)
    def key(s):
        meta = s[4] if len(s) > 4 else {}
        if not meta.get("sealed", True):
            return (0, s[2])  # unsealed first
        exp = s[1]
        try:
            return (1, datetime.fromisoformat(exp.replace('Z', '+00:00')).timestamp())
        except:
            return (1, s[2])
    sessions.sort(key=key, reverse=False)  # unsealed (0) bubble up; within group newest
    # de-dupe by stem name (cyl hash or capture id)
    seen = set()
    uniq = []
    for s in sessions:
        keyname = s[0].stem if hasattr(s[0], "stem") else s[0].name
        if keyname not in seen:
            seen.add(keyname)
            uniq.append(s)
    return uniq[:limit]

def get_recent_cylinder(limit=5):
    """Pull recent cylinder entries for historical meta threads (LGP, Book/Breath to Code, coordination)."""
    # Tolerant read via the ONE package gateway (Universalize Wave §1/G2). scripts→package allowed (G4).
    src = str(Path(__file__).resolve().parents[1] / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.ndjson import read_ndjson
    return read_ndjson(CYLINDER).entries[-limit:]

def get_forward_path_p0():
    """Summarize current P0 from forward path for grounding."""
    if not FORWARD_PATH.exists():
        return "Forward path not found."
    text = FORWARD_PATH.read_text()
    # Crude extract P0 section
    if "## P0" in text:
        start = text.find("## P0")
        end = text.find("## P1", start)
        return text[start:end].strip()[:800]
    return "P0 section not located."

def get_canon_status():
    """Quick note on recent canon changes (WORKFLOW co-extrusion, etc.)."""
    status = []
    if WORKFLOW.exists():
        wf = WORKFLOW.read_text()
        if "Co-extrusion is the rule" in wf:
            status.append("WORKFLOW.md: Co-extrusion + Tech/Arch Review Board active (17.6).")
    if ROLE_DOC.exists():
        role = ROLE_DOC.read_text()
        if "Standard Response Format" in role:
            status.append("Role doc: Standard response format + B51 scanner embedded as iron-clad.")
    return "; ".join(status) if status else "Canon status: check files directly."


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def load_b51_scan_state():
    if B51_SCAN_STATE.exists():
        try:
            return json.loads(B51_SCAN_STATE.read_text())
        except:
            return {}
    return {}


def save_b51_scan_state(state):
    B51_SCAN_STATE.parent.mkdir(parents=True, exist_ok=True)
    B51_SCAN_STATE.write_text(json.dumps(state, indent=2, sort_keys=True))


def get_b51_delta(max_new=5):
    """Incremental 'only what's new' for the active unsealed cyl.
    Per user approval on #2: only check/report what is new (prior posts already captured previously by GB).
    Always from live unsealed json write (not exports or shares). Uses entry_count cursor per cyl.
    """
    # Find the currently active unsealed cyl (sealed=False + ended_at=None), most recent mtime first
    active = None
    for p in sorted(LIVE_SESSIONS.glob("cyl_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text())
            if not d.get("sealed") and not d.get("ended_at"):
                active = (p, d)
                break
        except:
            continue
    if not active:
        return {"active_cyl": None, "message": "No active unsealed cyl found in live storage (pulling from json, not exports)."}

    p, data = active
    cyl_id = data.get("id")
    entries = data.get("entries", [])
    current_count = len(entries)

    state = load_b51_scan_state()
    last_cyl = state.get("cyl_id")
    last_count = state.get("last_entry_count", 0) if last_cyl == cyl_id else 0

    new_count = max(0, current_count - last_count)
    new_entries = entries[-new_count:] if new_count > 0 else []

    # Persist state so next run only sees increments (user: "only need to check what is new")
    new_state = {
        "cyl_id": cyl_id,
        "path": str(p),
        "last_entry_count": current_count,
        "last_mtime": p.stat().st_mtime,
        "last_scan_ts": _now_iso()
    }
    save_b51_scan_state(new_state)

    # Limit the new ones returned (most recent of the new)
    limited = new_entries[-max_new:] if max_new and new_count > 0 else new_entries
    previews = []
    for e in limited:
        c = (e.get("content") or e.get("preview") or "").strip()
        line = c.splitlines()[0][:160] if c else "(empty)"
        previews.append({"ts": e.get("timestamp", "?")[:19], "line": line})

    return {
        "active_cyl": cyl_id,
        "path": str(p),
        "previous_count": last_count,
        "current_count": current_count,
        "new_since_last_scan": new_count,
        "new_entries": previews,
        "source": "live-unsealed-json (direct write, not exports/shares)"
    }


def build_context_pack():
    hmc = get_latest_hmc(3)
    cyl = get_recent_cylinder(5)
    p0 = get_forward_path_p0()
    canon = get_canon_status()
    delta = get_b51_delta(5)  # incremental only-new for the active unsealed (user-approved #2)
    pack = {
        "latest_hmc": [{"path": str(s[0]), "ts": s[1], "preview": s[3][:300], "meta": s[4] if len(s)>4 else {}} for s in hmc],
        "b51_delta": delta,
        "recent_cylinder_themes": [e.get("ref", e.get("type")) for e in cyl],
        "forward_path_p0_summary": p0[:600],
        "canon_status": canon,
        "meta_arc_reminder": "LGP | Book to Code (co-extrusion + board) | Breath to Code (HMC direct as input, delta only new entries) | GB watches repo, coordinates AIs, grounds on Objective."
    }
    return pack

def generate_handoff(for_ai, pack):
    """Generate ready message + suggested attachments for the target AI."""
    if for_ai == "TIGER":
        msg = f"""Tiger,

GB meta here. Per the current meta arc (LGP, Book to Code via co-extrusion in WORKFLOW.md with the new Tech/Arch Review Board, Breath to Code via direct HMC/B51 as human memory source), GB maintains the live unsealed B51 scans (delta only-new from the active cyl json in ~/.local/share/human-memory-cylinder/sessions/, never exports) so the meta layer always has fresh human context. User relies on GB to keep you (Tiger) grounded on the current HMC ("Tiger should check the HMC as well").

See the attached/created tiny helper: scripts/gb_meta_context.py (GB runs it to get a grounded pack combining latest HMC + B51 delta (only new entries from live unsealed) + cylinder + forward path P0). GB will include the latest delta + explicit instruction in every handoff that you must ground on the current unsealed HMC before changes to agent/Atrium/hopper surfaces.

Next steps for you:
- Enhance the sovereign agent (or Atrium) to treat HMC/B51 sessions as first-class input (e.g., import latest cyl_* from ~/.local/share/human-memory-cylinder/sessions as breath/packets or obligations; prefer unsealed live over exports; support delta/incremental reads).
- Make the scan_b51_chain.py or gb_meta_context.py callable from the node or as a background process (GB can invoke for context).
- Ensure pre-seal entries + hopper-shaped B51 tail are visible in the Atrium coherence lens or LGP Watch / new Hopper intake (Breath to Code). See GB's hopper-in-Atrium flow proposal (to be aligned with G first).

Full context in the forward path and role doc (attached or in repo). GB will continue running the live scans and preparing the delta for you on every relevant turn.

Grounded on Objective. LGP.

[Attachment package: this message + scripts/gb_meta_context.py + forward path (P0) + role doc + series_roadmap excerpt on atrium_integration]"""
        attachments = ["scripts/gb_meta_context.py", "artifacts/GB_Prioritized_Forward_Path.md (P0 section)", "artifacts/GB_Meta_Visionary_Role_and_Constitutional_Memory_Cylinder.md", "artifacts/series_roadmap.yaml (atrium_integration + hopper notes)"]
    elif for_ai in ("G_X", "G_GROK"):
        msg = f"""G,

GB (local meta in the sovereign-agent-starter repo) checking alignment on the meta arc.

Current drive: LGP as north-star. Book to Code (initial manuscript + code/tests co-extruded per the new rule + Tech/Arch Review Board in WORKFLOW.md). Breath to Code (user's live HMC/B51 human memory cylinder as direct input for context, now with improved scanner/helper so GB always has the absolute latest human captures, not just exports).

We just standardized GB's output format for better handoffs (receipts first, summary + bullets, detail, TLDR + next steps).

Question for alignment/steers: How does this fit the hopper vision and 3-lane you helped shape? Any refinements to how GB should prepare packages for you vs Tiger vs Lumen?

See attached forward path (current P0/P1) and the new gb_meta_context.py helper.

Grounded on Objective. Ready for your input.

[Attachment: GB_Prioritized_Forward_Path.md + gb_meta_context.py + cylinder genesis for role]"""
        attachments = ["artifacts/GB_Prioritized_Forward_Path.md", "scripts/gb_meta_context.py", "artifacts/GB_Meta_Visionary_Role_and_Constitutional_Memory_Cylinder.md (genesis)"]
    else:
        msg = f"Support for {for_ai} not yet templated. Use the context pack below."
        attachments = ["scripts/gb_meta_context.py"]
    return msg, attachments

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--for-ai", choices=["TIGER", "G_X", "G_GROK", "LUMEN"], default=None)
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()

    pack = build_context_pack()
    print("=== GB META CONTEXT PACK (run this for every turn) ===")
    print(json.dumps(pack, indent=2, default=str))
    # Friendly delta summary (only new since last, from live unsealed)
    d = pack.get("b51_delta", {})
    if d.get("active_cyl"):
        print(f"\n--- B51 DELTA (live unsealed only, new since last GB scan) ---")
        print(f"Active: {d['active_cyl']} (total now {d.get('current_count')}, was {d.get('previous_count')})")
        print(f"New entries since last: {d.get('new_since_last_scan')}")
        for ne in d.get("new_entries", []):
            print(f"  + {ne['ts']}: {ne['line']}")
        print(f"Source: {d.get('source')}")

    if args.for_ai:
        msg, atts = generate_handoff(args.for_ai, pack)
        print(f"\n=== READY HANDOFF FOR {args.for_ai} ===")
        print(msg)
        if args.package:
            print("\nSuggested attachments:", atts)
        print("\nCopy the message above and drop the listed files into their window.")

if __name__ == "__main__":
    main()
