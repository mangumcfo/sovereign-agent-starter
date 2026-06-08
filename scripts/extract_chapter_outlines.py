#!/usr/bin/env python3
"""
Extract REAL chapter TOCs from the actual book manuscripts → staging for GB to fold into series_roadmap.yaml.

Honest by design: Tiger extracts STRUCTURE (real chapter n + title from `# Chapter N: …` headers in the
manuscript) — accurate, mechanical, not fabricated. The enrichment (promise / beats / keywords) is GB/G's lane
(G prices KW on x.com; GB folds). So each extracted chapter carries stage:"extracted" with empty enrichment
fields, clearly distinguished from G's stage:"outline_locked" (fully-outlined) chapters already in the roadmap.

Fence: Tiger extracts → writes a STAGING artifact (never the roadmap directly) → GB folds the extracted TOCs
into series_roadmap.yaml (its lane), skipping any title already at outline_locked → KM accepts.

  python3 scripts/extract_chapter_outlines.py
  → artifacts/extracted_chapter_outlines_2026-06-08.json  + a printed summary
"""
from __future__ import annotations

import json
import re
from pathlib import Path

VAULT = Path("/home/kmangum/work-repos/mangumcfo/breathline-books-vault/kdp")
OUT = Path(__file__).resolve().parents[1] / "artifacts" / "extracted_chapter_outlines_2026-06-08.json"
CH_RE = re.compile(r"^#\s+Chapter\s+(\d+)\s*[:\.\)\-—]?\s*(.+?)\s*$", re.IGNORECASE)


def _latest_manuscript(book_dir: Path) -> Path | None:
    """The highest-version manuscript_*.md under <book_dir>/v*/."""
    cands = sorted(book_dir.glob("v*/manuscript_v*.md"))
    if not cands:
        cands = sorted(book_dir.glob("v*/manuscript*.md"))
    return cands[-1] if cands else None


def _extract(ms: Path) -> list[dict]:
    chapters = []
    for line in ms.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = CH_RE.match(line)
        if m:
            chapters.append({"n": int(m.group(1)), "title": m.group(2).strip(),
                             "promise": "", "beats": [], "keywords": [],
                             "stage": "extracted", "coherence_pin": None})
    # dedupe by n (keep first), sort
    seen, out = set(), []
    for c in sorted(chapters, key=lambda x: x["n"]):
        if c["n"] in seen:
            continue
        seen.add(c["n"]); out.append(c)
    return out


def main() -> int:
    # every book dir = a dir that contains a v*/manuscript file
    books = {}
    for ms in VAULT.rglob("manuscript*.md"):
        book_dir = ms.parent.parent           # <book_id>/v1.0/manuscript.md → <book_id>
        books.setdefault(book_dir, ms)        # any; we re-pick latest below
    result = {}
    for book_dir in sorted(books):
        ms = _latest_manuscript(book_dir)
        if not ms:
            continue
        chs = _extract(ms)
        if not chs:
            continue
        book_id = book_dir.name
        result[book_id] = {"book_id": book_id, "manuscript": str(ms),
                           "n_chapters": len(chs), "chapters": chs}
    OUT.write_text(json.dumps({"source": "Tiger extraction of real manuscript TOCs (# Chapter N headers)",
                               "honest_note": "stage='extracted' = real structure (n+title); promise/beats/"
                               "keywords are GB/G enrichment. Do NOT overwrite stage='outline_locked' titles.",
                               "books": result}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"✓ extracted real TOCs → {OUT.name}")
    print(f"  {len(result)} titles · {sum(b['n_chapters'] for b in result.values())} chapters total")
    for bid, b in sorted(result.items()):
        print(f"   {b['n_chapters']:>2} ch · {bid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
