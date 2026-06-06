#!/usr/bin/env python3
"""
Coherence backfill — safe, non-faking extruder for book↔code anchors + honest narrative classification.

The coherence monitor is only trustworthy if every anchor is REAL: a verbatim book passage pinned to a code
file that actually exists. This tool enforces that — it refuses to add an anchor whose passage isn't found
in the manuscript or whose code file is missing. It also lets us classify pure-narrative books (no code spec)
honestly, so the Series Roadmap shows three truthful states: ✅ pinned · 📖 narrative · ◌ awaiting anchor.

Subcommands:
  add        Add one anchor (validated): book passage (by unique --anchor snippet) → real code file.
  classify   Mark a book_id as narrative (no code spec) with a reason — honest coverage, not a faked green.
  status     Per-book coverage report (pinned / narrative / awaiting).

Design: idempotent (skips a passage_hash already present); writes memory/coherence_registry.json (anchors)
and memory/coherence_coverage.json (narrative classification). Two-writers fence: Tiger authors these.

  python3 scripts/coherence_backfill.py add --book-id vol_02_the_primacy_cockpit \
      --book "The Primacy Cockpit (S2 Vol 2)" --book-file <abs> \
      --code-file src/sovereign_agent/obligations/ledger.py --tests-file tests/test_ledger.py \
      --capability "Breath-Gate disposition" --chapter "Ch 2 — Breath-Gate Inbox" \
      --anchor "propose, you dispose" --seal 574
  python3 scripts/coherence_backfill.py classify --book-id 04_xrp --narrative "Trade finance/crypto narrative — no harness code."
  python3 scripts/coherence_backfill.py status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "memory" / "coherence_registry.json"
COVERAGE = REPO / "memory" / "coherence_coverage.json"


def _load(p: Path, default):
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return default


def _paragraph_containing(text: str, anchor: str) -> str | None:
    """Return the verbatim Markdown paragraph (block between blank lines) containing `anchor`, trimmed."""
    if anchor not in text:
        return None
    # split on blank lines; find first block containing the anchor
    for block in re.split(r"\n\s*\n", text):
        if anchor in block:
            return block.strip()
    return None


def cmd_add(a) -> int:
    reg = _load(REGISTRY, {"extrusions": [], "reconciliation": {}})
    book_file = Path(a.book_file)
    if not book_file.is_file():
        print(f"✗ book_file not found: {book_file}", file=sys.stderr)
        return 2
    code_abs = (REPO / a.code_file)
    if not code_abs.is_file():
        print(f"✗ code_file not found (relative to repo): {a.code_file}", file=sys.stderr)
        return 2
    text = book_file.read_text(encoding="utf-8")
    passage = a.passage or _paragraph_containing(text, a.anchor or "")
    if not passage:
        print(f"✗ anchor not found verbatim in manuscript: {a.anchor!r}", file=sys.stderr)
        return 2
    if passage not in text:  # belt + suspenders
        print("✗ resolved passage is not verbatim in the manuscript — refusing.", file=sys.stderr)
        return 2
    phash = hashlib.sha256(passage.encode()).hexdigest()[:12]
    for e in reg["extrusions"]:
        if e.get("passage_hash") == phash:
            print(f"• already present (passage_hash {phash}) — skip.")
            return 0
    entry = {
        "capability": a.capability,
        "code_file": a.code_file,
        "tests_file": a.tests_file or "",
        "book": a.book,
        "book_id": a.book_id,
        "book_file": str(book_file),
        "chapter": a.chapter,
        "passage": passage,
        "passage_hash": phash,
        "landed_seal": a.seal,
    }
    reg["extrusions"].append(entry)
    REGISTRY.write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    tests_note = "" if (REPO / a.tests_file).is_file() else "  (⚠ tests_file absent — anchor still valid; tests_present=false)" if a.tests_file else ""
    print(f"✓ added anchor [{phash}] {a.book_id} · {a.capability} → {a.code_file}{tests_note}")
    return 0


def cmd_classify(a) -> int:
    cov = _load(COVERAGE, {"narrative": {}})
    cov.setdefault("narrative", {})[a.book_id] = a.narrative
    COVERAGE.write_text(json.dumps(cov, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"✓ classified {a.book_id} as narrative (no code spec): {a.narrative}")
    return 0


def cmd_status(a) -> int:
    reg = _load(REGISTRY, {"extrusions": []})
    cov = _load(COVERAGE, {"narrative": {}})
    by = {}
    for e in reg.get("extrusions", []):
        by.setdefault(e.get("book_id", "?"), {"book": e.get("book", ""), "n": 0})["n"] += 1
    print("── Pinned (book↔code anchors) ──")
    for bid, info in sorted(by.items()):
        print(f"  ✅ {bid:36} {info['n']:>2} anchor(s)  {info['book']}")
    print("── Narrative (no code spec, honest) ──")
    for bid, why in sorted(cov.get("narrative", {}).items()):
        print(f"  📖 {bid:36} {why}")
    print(f"\nTotals: {len(by)} pinned book(s) · {len(cov.get('narrative', {}))} narrative · "
          f"{sum(i['n'] for i in by.values())} anchors")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Coherence backfill — safe anchor extruder + narrative classifier.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add")
    for f in ("book-id", "book", "book-file", "code-file", "capability", "chapter"):
        pa.add_argument(f"--{f}", required=True)
    pa.add_argument("--tests-file", default="")
    pa.add_argument("--anchor", default="", help="unique snippet; the verbatim paragraph containing it is pinned")
    pa.add_argument("--passage", default="", help="exact passage (overrides --anchor)")
    pa.add_argument("--seal", type=int, default=0)
    pa.set_defaults(fn=cmd_add)
    pc = sub.add_parser("classify")
    pc.add_argument("--book-id", required=True)
    pc.add_argument("--narrative", required=True)
    pc.set_defaults(fn=cmd_classify)
    ps = sub.add_parser("status")
    ps.set_defaults(fn=cmd_status)
    a = p.parse_args()
    # argparse maps --book-id → a.book_id automatically
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
