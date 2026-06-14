#!/usr/bin/env python3
"""
atrium_sitting_apply.py — the sitting WRITE-FLOW (THREAD [245] step: one Accept disposes a sitting).

Clones the Diff-Review loop. A sitting Accept does NOT blind-apply: each resolution is rendered into a
PROPOSED diff that KM verifies (law #8 — gates verify execution, never re-bless intent). The engine owns
the lifecycle; an agent owns the render. Lifecycle per item:

    prepare → (agent renders diff) → lint-gate → apply (manuscript write) → close E2 + surface Verify card
    exceptions / un-renderable → surface as an individual "Verify fix:" / "Decide" card (the one you touch)

CRITICAL honesty: a bare highlight ("Misc" with a seed but no instruction) is a spot KM marked, NOT an
edit order. The engine classifies each item:
    • renderable  — has an actionable intent (type ≠ Misc, OR an LGP/clarity hint) → agent proposes a diff
    • needs-intent — a bare selection → surfaced back to KM ("what did you want here?"), never auto-edited

Nothing here writes the manuscript unless --apply is passed AND a rendered diff is supplied per item AND
the post-edit manuscript passes render_standard_lint. Default is a dry-run plan.

Usage:
    python3 scripts/atrium_sitting_apply.py --book vol_01 --sitting "pp 1-8"          # dry-run plan
    python3 scripts/atrium_sitting_apply.py --book vol_01 --sitting "pp 1-8" --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(REPO / "scripts"))
import atrium_sittings as S  # noqa: E402


def _resolve_default_root() -> Path:
    """Route through THE canonical resolver (Universalize Wave §2/G3) instead of re-deriving
    env→atrium_review — one root, boundary-checked, never a split-brain vs the node. scripts→package
    import is the allowed direction (G4)."""
    src = str(REPO / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from sovereign_agent.obligations.ledger import get_ledger_root
    return get_ledger_root(default=REPO / "memory" / "obligations" / "atrium_review")


DEFAULT_ROOT = _resolve_default_root()


def _intent_of(root: Path, oid: str) -> str:
    for o in S._rows(root):
        if o.get("id") == oid:
            return str(o.get("intent", ""))
    return ""


ACTION_WORDS = ("bold", "underline", "italic", "enhance", "tighten", "rewrite", "clarify", "reword",
                "fix", "typo", "insert", "delete", "remove", "replace", "capitalize", "lowercase",
                "shorten", "expand", "move", "merge", "split", "→", "->", "change to", "should be")


def classify(intent: str) -> tuple[str, str]:
    """(disposition, why). The capture is renderable when KM gave an instruction — the text after the
    [tag] (typed intent) or the quick-button tag itself. Only a truly empty capture (tag with no body
    and no actionable tag) is needs_intent. (KM 2026-06-12: 'I provided intent on 100%.')"""
    head = re.split(r"\n\s*Seed \(human selection\):", intent, maxsplit=1)[0].strip()
    m = re.match(r"\s*\[([^\]]+)\]\s*(.*)$", head, flags=re.DOTALL)
    tag = (m.group(1).strip() if m else "").lower()
    body = " ".join((m.group(2) if m else head).split())
    if body:                                   # KM typed an instruction → render it
        return "renderable", f"typed instruction: \"{body[:60]}\""
    if tag and tag != "misc":                  # a quick-button (bold/underline, enhance language, …)
        return "renderable", f"quick-button action: {tag}"
    return "needs_intent", "capture has no instruction body and only a generic tag"


def prepare(root: Path, book: str, sitting_key: str) -> dict:
    plan = S.apply_plan(root, book, sitting_key)
    if "error" in plan:
        return plan
    out = {"renderable": [], "needs_intent": [], "decide": plan["needs_your_decision"],
           "ratify": plan["ratify"]}
    # FYI (born-approved) items still pass through render+verify — they apply, but you SEE the diff.
    for it in plan["auto_apply_born_approved"] + plan["verify_agent_change"]:
        disp, why = classify(_intent_of(root, it["id"]))
        rec = {**it, "why": why}
        out["renderable" if disp == "renderable" else "needs_intent"].append(rec)
    out["sitting"] = sitting_key
    out["summary"] = {
        "renderable": len(out["renderable"]),       # agent proposes diff → one Accept verifies the batch
        "needs_intent": len(out["needs_intent"]),   # surfaced back to you — what did you want here?
        "decide": len(out["decide"]), "ratify": len(out["ratify"]),
    }
    out["next"] = ("agent renders the %d renderable into proposed diffs (lint-gated) → surface as ONE "
                   "Verify sitting card; the %d needs-intent + %d decide surface as the exceptions you touch."
                   % (len(out["renderable"]), len(out["needs_intent"]), len(out["decide"])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Sitting write-flow (dry-run plan by default)")
    ap.add_argument("--book", default="vol_01")
    ap.add_argument("--sitting", required=True)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))  # DEFAULT_ROOT already honors OBLIGATION_LEDGER_ROOT (§2)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res = prepare(Path(a.root), a.book, a.sitting)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False)); return 0
    if "error" in res:
        print(res["error"]); return 1
    s = res["summary"]
    print(f"SITTING {res['sitting']} — write-flow plan (dry-run, no manuscript written)\n")
    print(f"  renderable (agent proposes diff → you verify): {s['renderable']}")
    for it in res["renderable"]:
        print(f"      • p{it['page']}  {it['comment'][:60]}")
    print(f"  needs YOUR intent (bare marks — not auto-edited): {s['needs_intent']}")
    for it in res["needs_intent"]:
        print(f"      • p{it['page']}  {it['comment'][:60]}")
    if s["decide"]:
        print(f"  decide (figure/goal inserts etc.): {s['decide']}")
    print(f"\n  → {res['next']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# ∞Δ∞ SEAL: one Accept disposes a sitting — but every diff is rendered then VERIFIED, and a bare mark is
#          never mistaken for an edit order. The write-flow honors law #8 at the pen. ∞Δ∞
