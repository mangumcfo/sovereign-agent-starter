#!/usr/bin/env python3
"""
atrium_sittings.py — "The Queue Is a Query" (THREAD [245], migration step 1+2, read-only).

A PURE PROJECTION over the obligation ledger. Mints nothing; stores nothing. Re-running always
reflects ledger truth. Implements:

  • Queue-as-Query   — the awaiting view is a predicate over the packet store, not minted cards.
  • Born-approved-as-predicate — mechanical edits are 'approved' because they MATCH a predicate at
                       read time, never because a fragile promotion flag flipped (the failure that
                       silently ate KM's 42 Vol 1 comments — they resurface here by predicate).
  • Human granularity → sittings — atomic resolutions aggregate into per-page-band SITTING cards
                       (one Accept + exceptions, not N approvals).
  • Lanes by act     — every resolution is Decide · Verify · Ratify · FYI.

Predicate for "awaiting me" = a KM comment / finding / brief for the target book that is NOT yet
truly disposed (approved == False) — REGARDLESS of the draft/closed bookkeeping. That is the whole
point: it asks "what has the chair not actually decided?", not "what obligation is open?", so
closed-without-disposition packets cannot hide.

Usage:
    python3 scripts/atrium_sittings.py --book vol_01 [--json]
    OBLIGATION_LEDGER_ROOT defaults to memory/obligations/atrium_review.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _resolve_default_root() -> Path:
    """Route through THE canonical resolver (audit 2026-06-13d #31) — one root, boundary-checked, never a
    split-brain vs the node. Same default (atrium_review), now honoring OBLIGATION_LEDGER_ROOT via the
    shared resolver (the --root CLI flag still wins, as before)."""
    import sys
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


DEFAULT_ROOT = _resolve_default_root()


def _rows(root: Path) -> list[dict]:
    f = root / "obligations.ndjson"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _txt(o: dict) -> str:
    return " ".join(str(o.get(k, "")) for k in ("title", "intent", "ref", "detail", "note")).lower()


def _page(o: dict) -> int | None:
    m = re.search(r"\bp(\d{1,3})\b", str(o.get("ref", "")) or str(o.get("title", "")))
    return int(m.group(1)) if m else None


def instruction_of(o: dict) -> str:
    """KM's actual instruction — the text he typed/the quick-button action, NOT the highlighted seed.
    Format: '[<tag>] <instruction…>\\nSeed (human selection): "<seed>"\\nPage:…\\nLGP hint:…'.
    The instruction = the tag's body + any free text after ']' up to the Seed line. (Bug 2026-06-12:
    we were surfacing the seed as the comment and dropping the instruction — KM provided 100%.)"""
    intent = str(o.get("intent", ""))
    if not intent:
        return re.sub(r"\[judgment\] Feedback:\s*", "", str(o.get("title", "")))[:120]
    # cut everything from the Seed line onward
    head = re.split(r"\n\s*Seed \(human selection\):", intent, maxsplit=1)[0].strip()
    m = re.match(r"\s*\[([^\]]+)\]\s*(.*)$", head, flags=re.DOTALL)
    if m:
        tag, body = m.group(1).strip(), " ".join(m.group(2).split())
        return f"{body}" if body else tag           # body is KM's typed intent; tag is the quick-button
    return " ".join(head.split())[:200]


def seed_of(o: dict) -> str:
    """The highlighted text the instruction applies TO (the anchor)."""
    m = re.search(r'Seed \(human selection\):\s*"([^"]+)"', str(o.get("intent", "")))
    return m.group(1).replace("\n", " ").strip() if m else ""


def _seed(o: dict) -> str:
    """Display string = KM's instruction, with the anchor in parens."""
    instr, anchor = instruction_of(o), seed_of(o)
    return f'{instr} — on: "{anchor[:40]}"' if anchor and instr else (instr or anchor)


def _lane(o: dict) -> str:
    """Decide · Verify · Ratify · FYI — the act, derived from the packet (not stored)."""
    t = _txt(o)
    if any(k in t for k in ("board finding", "review brief", "renderability", "charter", "ratify")):
        return "Ratify"
    # an applied change (disposed + has evidence) is something to VERIFY, not re-decide
    if o.get("approved"):
        return "Verify"
    # mechanical edits (typo/wording/structure) are born-approved-by-predicate → FYI digest
    title = str(o.get("title", "")).lower()
    mechanical = any(k in title for k in ("misc", "enhance language", "typo", "wording", "structure",
                                          "highlight/callout"))
    if mechanical and o.get("material") is False:
        return "FYI"
    return "Decide"


def project(root: Path, book: str) -> dict:
    rows = _rows(root)
    # PREDICATE: a comment/finding for this book that the chair has not actually disposed.
    pred = [o for o in rows
            if book in _txt(o)
            and any(k in str(o.get("title", "")).lower()
                    for k in ("pdf edit", "feedback", "renderability", "board finding", "review brief"))
            and not o.get("approved")]

    # SITTING aggregation: group by page-band of 8 (a read-through sitting). Page-less → "general".
    sittings: dict[str, list[dict]] = defaultdict(list)
    for o in pred:
        pg = _page(o)
        key = f"pp {((pg - 1)//8)*8 + 1:>3}-{((pg - 1)//8)*8 + 8:<3}" if pg else "general"
        sittings[key].append({"id": o.get("id"), "page": pg, "lane": _lane(o),
                              "comment": _seed(o), "title": o.get("title")})

    cards = []
    for key in sorted(sittings, key=lambda k: (k == "general", k)):
        items = sorted(sittings[key], key=lambda r: (r["page"] or 999))
        lanes = defaultdict(int)
        for it in items:
            lanes[it["lane"]] += 1
        # ONE Accept + exceptions: the sitting's default act = its dominant non-FYI lane.
        default_act = ("Decide" if lanes["Decide"] else
                       "Verify" if lanes["Verify"] else
                       "Ratify" if lanes["Ratify"] else "FYI")
        cards.append({
            "sitting": key, "resolutions": len(items), "lanes": dict(lanes),
            "default_act": default_act, "items": items,
        })
    return {"book": book, "predicate": "comment/finding for book AND approved==False",
            "sitting_count": len(cards), "resolution_count": len(pred), "cards": cards}


def _age_days(o: dict, now_iso: str | None) -> int | None:
    ts = str(o.get("timestamp", ""))[:10]
    if not (ts and now_iso):
        return None
    try:
        from datetime import date
        a = date.fromisoformat(ts); b = date.fromisoformat(now_iso[:10])
        return (b - a).days
    except Exception:
        return None


def backpressure(root: Path, book: str, now_iso: str | None = None, age_floor: int = 3) -> dict:
    """Visible metrics + WIP + 'aging pages → machines first' (THREAD [245] fix #3). Read-only.
    age_floor = days after which an undisposed mechanical (FYI) item should be handled by machine,
    not left rotting in the human queue. now_iso passed in (scripts cannot call Date.now)."""
    res = project(root, book)
    lanes: dict[str, int] = defaultdict(int)
    aging_fyi = 0
    rows = {o.get("id"): o for o in _rows(root)}
    for c in res["cards"]:
        for it in c["items"]:
            lanes[it["lane"]] += 1
            if it["lane"] == "FYI":
                age = _age_days(rows.get(it["id"], {}), now_iso)
                if age is not None and age >= age_floor:
                    aging_fyi += 1
    return {
        "book": book,
        "resolutions": res["resolution_count"], "sittings": res["sitting_count"],
        "by_lane": dict(lanes),
        "human_gates": lanes["Decide"] + lanes["Ratify"],          # what actually needs KM
        "machine_eligible": lanes["FYI"],                          # born-approved → machines
        "aging_to_machines": aging_fyi,                            # FYI past the floor → sweep first
        "wip_note": "lane Decide is the only true human-WIP; FYI/Verify are machine/confirm lanes",
    }


def apply_plan(root: Path, book: str, sitting_key: str) -> dict:
    """What ONE Accept on a sitting does (act-lanes). Read-only PLAN — no manuscript write here;
    application is the executor/agent's job, each diff lint-gated, exceptions reopen as 'Verify fix:'."""
    res = project(root, book)
    norm = lambda s: " ".join(str(s).split())
    card = next((c for c in res["cards"] if norm(c["sitting"]) == norm(sitting_key)), None)
    if not card:
        return {"error": f"no sitting '{sitting_key}'"}
    plan = {"FYI": [], "Decide": [], "Verify": [], "Ratify": []}
    for it in card["items"]:
        plan[it["lane"]].append({"id": it["id"], "page": it["page"], "comment": it["comment"]})
    return {
        "sitting": sitting_key, "one_accept_disposes": len(plan["FYI"]) + len(plan["Verify"]),
        "auto_apply_born_approved": plan["FYI"],          # one Accept applies these (lint-gated)
        "needs_your_decision": plan["Decide"],            # exceptions → surface as Decide cards
        "verify_agent_change": plan["Verify"],
        "ratify": plan["Ratify"],
        "rule": "one Accept + exceptions: FYI auto-apply, Decide are the exceptions you actually touch",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Atrium sittings projection (read-only, Queue-as-Query)")
    ap.add_argument("--book", default="vol_01")
    ap.add_argument("--root", default=os.environ.get("OBLIGATION_LEDGER_ROOT") or str(DEFAULT_ROOT))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--metrics", action="store_true", help="backpressure metrics")
    ap.add_argument("--now", default=None, help="today's date ISO (for aging) — scripts can't self-clock")
    ap.add_argument("--plan", default=None, help="apply-plan for a sitting key, e.g. 'pp   1-8'")
    a = ap.parse_args()

    if a.metrics:
        print(json.dumps(backpressure(Path(a.root), a.book, a.now), indent=2, ensure_ascii=False)); return 0
    if a.plan:
        print(json.dumps(apply_plan(Path(a.root), a.book, a.plan), indent=2, ensure_ascii=False)); return 0

    res = project(Path(a.root), a.book)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0
    print(f"AWAITING ME — {res['book']} · {res['resolution_count']} resolutions → "
          f"{res['sitting_count']} sittings (one Accept + exceptions each)\n")
    for c in res["cards"]:
        lanestr = " ".join(f"{k}:{v}" for k, v in c["lanes"].items())
        print(f"▎ Sitting {c['sitting']} · {c['resolutions']} resolutions · [{lanestr}] "
              f"· default act: {c['default_act']}")
        for it in c["items"][:6]:
            pg = f"p{it['page']}" if it["page"] else "—"
            print(f"    {it['lane']:<7} {pg:<5} {it['comment'][:64]}")
        if c["resolutions"] > 6:
            print(f"    … +{c['resolutions']-6} more")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ∞Δ∞ SEAL: nothing minted — the queue is a query; the dropped 42 resurface by predicate, aggregated
#          into sittings, lane-typed by act. Packets keep their receipts; this is presentation. ∞Δ∞
