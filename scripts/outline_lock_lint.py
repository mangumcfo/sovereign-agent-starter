#!/usr/bin/env python3
"""outline_lock_lint — the all-series outline-readiness map, as a re-runnable structural check.

KM directive 2026-06-18 (after the S3 dig): "I thought we have all outlines for all series."
The honest answer is half-true — outlines are *extracted* broadly, but *locked* almost nowhere.
GB + Tiger endorsed making that a mechanical lint, not a verbal claim — the same structural-not-
verbal bar set for /seeit (seeit_lint), applied to outline-readiness.

THE DISTINCTION THIS ENFORCES (the crux of the whole S3 exchange): **exists != locked**, and a
lock label must RESOLVE to real outline content (chapters), or it is a phantom lock — a TRUTH
violation. We found exactly this: S3 V3 Helix and S4 vols are tagged `outline_locked`; the lock
is real only because the roadmap entry carries full inline `chapters[]`. A title that claims
`outline_locked` but carries NO resolving chapters anywhere is flagged PHANTOM and fails the gate.

SOURCE OF TRUTH (canonical, GB-written): artifacts/series_roadmap.yaml `series[].titles[].stage`.
CONTENT RESOLVERS (does the outline actually exist, in priority order):
  1. roadmap-inline  — the title entry's own non-empty `chapters[]` (how a lock is materialized)
  2. extracted       — artifacts/extracted_chapter_outlines_*.json `books[<key>].chapters` (enrichment stage)
  3. vault           — breathline-books-vault/kdp/**/outline*.md for the title (drafting-stage outline)

PER TITLE → one of:
  OK_LOCKED     locked stage AND outline content resolves           (drafting-ready, verified)
  PHANTOM_LOCK  locked stage BUT no resolving chapters anywhere      (TRUTH violation — gate FAIL)
  UNDERCOUNTED  pre-lock stage BUT full outline content resolves     (promotable — lock it)
  IN_PROGRESS   pre-lock stage, partial/no content                   (outline not done)

Exit 0 only if zero PHANTOM_LOCK (every lock claim resolves). 1 otherwise.

Usage: python3 scripts/outline_lock_lint.py [--json] [--series PREFIX] [--show-undercounted]

SOURCE: per book_id (sovereign id). TRUTH: a lock must resolve to chapters, not just a label.
INTEGRITY: read-only; exit-coded; re-runnable — the map is linted, not asserted.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
ROADMAP = REPO / "artifacts" / "series_roadmap.yaml"
EXTRACTED_GLOB = str(REPO / "artifacts" / "extracted_chapter_outlines_*.json")
VAULT = Path(os.path.expanduser(
    "~/work-repos/mangumcfo/breathline-books-vault/kdp"))

# Stages at or beyond the outline-lock point — a locked outline is required to reach any of these.
# (concept/phase_1/phase_1_outline/outline_partial/handoff are PRE-lock: outline still in progress.)
LOCKED_STAGES = {
    "outline_locked", "drafting", "draft", "phase_2", "phase_2_iteration",
    "review_ready", "awaiting_human_review", "sealed", "published",
}
# Pre-lock stages we recognize explicitly; anything else unknown is treated as pre-lock (conservative).
PRELOCK_STAGES = {
    "concept", "phase_1", "phase_1_outline", "outline_partial", "handoff",
}


def _norm_stage(raw: str) -> str:
    """Collapse a free-form stage string to its leading token (e.g. 'concept/outline begun ...' -> 'concept')."""
    s = (raw or "").strip().lower()
    return re.split(r"[\s/]", s, 1)[0] if s else ""


def _titles(roadmap: dict):
    for s in roadmap.get("series", []) or []:
        if not isinstance(s, dict):
            continue
        sname = s.get("name", "?")
        for t in (s.get("titles") or s.get("books") or []):
            if isinstance(t, dict):
                yield sname, t


def _key_tail(k: str) -> str:
    """Strip series/vol prefixes so roadmap book_id and extracted key can fuzzy-match on the meaningful tail."""
    k = k.lower()
    k = re.sub(r"^(s\d+_|vol_)?\d*_?", "", k)   # drop s5_ / s4_ / vol_NN_ / NN_ prefixes
    return re.sub(r"[^a-z0-9]", "", k)


def _complete(chapters) -> tuple[int, int]:
    """(total, complete) — a chapter is COMPLETE only if it carries promise OR beats, not just a title.
    This is GB's V4 flag as code: 8 chapter slots with 3 title-only stubs is 5/8, not 8/8."""
    if not isinstance(chapters, list):
        return 0, 0
    done = sum(1 for c in chapters
               if isinstance(c, dict) and (str(c.get("promise", "")).strip() or c.get("beats")))
    return len(chapters), done


def _load_extracted() -> dict:
    """book-key-tail -> (total, complete) chapters, unioned across every extracted_chapter_outlines_*.json."""
    out = {}
    for f in glob.glob(EXTRACTED_GLOB):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for k, v in (d.get("books", {}) or {}).items():
            tot, done = _complete(v.get("chapters", []) or [])
            prev = out.get(_key_tail(k), (0, 0))
            if tot >= prev[0]:
                out[_key_tail(k)] = (tot, done)
    return out


def _vault_outline_exists(book_id: str) -> bool:
    """A vault outline*.md whose path contains the book_id's tail (drafting-stage outline artifact)."""
    if not VAULT.exists():
        return False
    tail = _key_tail(book_id)
    if len(tail) < 4:
        return False
    for p in VAULT.glob("**/outline*.md"):
        if tail[:12] in _key_tail(p.parent.parent.name + p.parent.name):
            return True
    return False


def resolve_content(title: dict, extracted: dict) -> tuple[bool, str, int, int]:
    """(resolves, source, total, complete) — where the outline exists + how complete, priority order."""
    inline = title.get("chapters") or []
    if isinstance(inline, list) and inline:
        tot, done = _complete(inline)
        return True, "roadmap-inline", tot, done
    bid = title.get("book_id") or title.get("id") or ""
    tot, done = extracted.get(_key_tail(bid), (0, 0))
    if tot:
        return True, "extracted", tot, done
    if _vault_outline_exists(bid):
        return True, "vault", -1, -1   # -1 = present, completeness unknown (markdown outline)
    return False, "none", 0, 0


def classify(title: dict, extracted: dict) -> dict:
    bid = title.get("book_id") or title.get("id") or "?"
    stage = _norm_stage(title.get("stage", ""))
    locked = stage in LOCKED_STAGES
    resolves, source, tot, done = resolve_content(title, extracted)
    full = (tot == -1) or (tot > 0 and done == tot)   # vault-unknown counts as full; else every chapter complete
    if locked and not resolves:
        status = "PHANTOM_LOCK"                       # lock label, no content — TRUTH violation
    elif stage == "outline_locked" and resolves and not full:
        status = "THIN_LOCK"                          # locked but the outline still has stub chapters
    elif locked and resolves:
        status = "OK_LOCKED"
    elif not locked and resolves and (tot == -1 or done >= 5):
        status = "UNDERCOUNTED"                       # substantial outline exists, just not locked
    else:
        status = "IN_PROGRESS"
    return {"book_id": bid, "title": title.get("title", ""), "stage": stage, "locked": locked,
            "content": source, "total": tot, "done": done, "status": status}


def main() -> int:
    as_json = "--json" in sys.argv
    show_under = "--show-undercounted" in sys.argv
    sfilter = sys.argv[sys.argv.index("--series") + 1] if "--series" in sys.argv else None

    if not ROADMAP.exists():
        print(f"FAIL — roadmap not found: {ROADMAP}")
        return 1
    roadmap = yaml.safe_load(ROADMAP.read_text(encoding="utf-8")) or {}
    extracted = _load_extracted()

    def _ch(r):
        return "?" if r["total"] == -1 else f"{r['done']}/{r['total']}"

    by_series, rows = {}, []
    for sname, t in _titles(roadmap):
        if sfilter and sfilter.lower() not in sname.lower():
            continue
        r = classify(t, extracted)
        r["series"] = sname
        rows.append(r)
        b = by_series.setdefault(sname, {"total": 0, "locked": 0, "phantom": 0, "thin": 0, "under": 0})
        b["total"] += 1
        b["locked"] += 1 if r["status"] == "OK_LOCKED" else 0
        b["phantom"] += 1 if r["status"] == "PHANTOM_LOCK" else 0
        b["thin"] += 1 if r["status"] == "THIN_LOCK" else 0
        b["under"] += 1 if r["status"] == "UNDERCOUNTED" else 0

    total = len(rows)
    locked = sum(1 for r in rows if r["status"] == "OK_LOCKED")
    phantom = [r for r in rows if r["status"] == "PHANTOM_LOCK"]
    thin = [r for r in rows if r["status"] == "THIN_LOCK"]
    under = [r for r in rows if r["status"] == "UNDERCOUNTED"]
    fail = phantom + thin   # a lock must resolve AND be complete — both break the gate

    if as_json:
        print(json.dumps({
            "total": total, "locked_verified": locked,
            "phantom_locks": len(phantom), "thin_locks": len(thin), "undercounted": len(under),
            "by_series": by_series,
            "phantom": [{"book_id": r["book_id"], "series": r["series"], "stage": r["stage"]} for r in phantom],
            "thin": [{"book_id": r["book_id"], "series": r["series"], "chapters": _ch(r)} for r in thin],
            "undercounted": [{"book_id": r["book_id"], "series": r["series"], "stage": r["stage"], "chapters": _ch(r), "src": r["content"]} for r in under],
        }, indent=2))
        return 0 if not fail else 1

    print("Outline-readiness across the catalog (canonical = series_roadmap.yaml stage; "
          "a lock must resolve to COMPLETE chapters)\n")
    print(f"{'series':52} {'locked':>7} {'phantom':>8} {'thin':>5} {'under':>6} {'total':>6}")
    print("-" * 90)
    for s in by_series:
        b = by_series[s]
        nm = (s[:49] + "…") if len(s) > 50 else s
        ph = f"\033[31m{b['phantom']}\033[0m" if b["phantom"] else "0"
        th = f"\033[33m{b['thin']}\033[0m" if b["thin"] else "0"
        print(f"{nm:52} {b['locked']:>7} {ph:>8} {th:>5} {b['under']:>6} {b['total']:>6}")
    print("-" * 90)
    print(f"CATALOG: {locked}/{total} outlines LOCKED + verified (drafting-ready)  ·  "
          f"{len(phantom)} phantom · {len(thin)} thin · {len(under)} undercounted (promotable)\n")

    if phantom:
        print("\033[31mPHANTOM LOCKS — stage says locked but NO outline content resolves (fix before drafting):\033[0m")
        for r in phantom:
            print(f"  ✗ {r['book_id']}  ({r['series'][:40]} · stage={r['stage']})")
        print()
    if thin:
        print("\033[33mTHIN LOCKS — stage=outline_locked but the outline still has stub chapters (not drafting-ready):\033[0m")
        for r in thin:
            print(f"  ~ {r['book_id']}  ({r['series'][:40]} · {_ch(r)} chapters complete via {r['content']})")
        print()
    if under and show_under:
        print("\033[33mUNDERCOUNTED — substantial outline exists but stage is pre-lock (candidates to lock):\033[0m")
        for r in under:
            print(f"  ~ {r['book_id']}  (stage={r['stage']} · {_ch(r)} via {r['content']})")
        print()
    print("Re-run: python3 scripts/outline_lock_lint.py [--json] [--series S3] [--show-undercounted]")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
