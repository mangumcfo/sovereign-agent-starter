#!/usr/bin/env python3
"""
extract_r1_candidates.py — mechanical R1 (explicit-anchor) edge extractor for the Book↔Code Tree.

Spec §3 calls R1 edges "machine-extractable." This tool does ONLY that mechanical extraction and emits
CANDIDATES — it never writes book_code_map.yaml (GB sole-write). GB reviews these candidates and folds the
real ones into his map. Fence stays crisp: Tiger provides the deterministic extractor; GB owns the map.

R1 signals scanned in src/*.py:
  - a docstring / `∞Δ∞` Seal block / comment citing a book id (NN_slug) or 'Chapter N' / 'Book NN' / 'B10'..'B12'
  - a `generated_from:` / `book:` / `chapter:` annotation
Each candidate carries the resolving anchor (the actual line) so GB can verify — no vibes-edges.

  python3 scripts/extract_r1_candidates.py     # → artifacts/book_code_r1_candidates.yaml (for GB)

∞Δ∞ Candidates, not canon — the map is GB's to seal. ∞Δ∞
"""
from __future__ import annotations

import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
OUT = REPO / "artifacts" / "book_code_r1_candidates.yaml"

# book-id tokens like  10_scaling_enterprise , 01_strategic_finance ; and explicit book/chapter cites
_BOOKID = re.compile(r"\b(\d{2}_[a-z][a-z0-9_]+)\b")
_BOOK = re.compile(r"\bB(\d{1,2})\b|\bBook\s+(\d{1,2})\b", re.I)
_CHAP = re.compile(r"\bchapter\s+(\d{1,3})\b", re.I)
_CITE = re.compile(r"^\s*(?:#|\*|generated_from|book|chapter)\b", re.I)


def _signal_lines(text: str) -> list[tuple[int, str]]:
    """Lines plausibly citing a book/chapter: docstring/comment/annotation carrying a book token."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if _BOOKID.search(line) or _BOOK.search(line) or (_CHAP.search(line) and _CITE.search(line)):
            out.append((i, line.strip()[:200]))
    return out


def _candidates_for(path: Path) -> list[dict]:
    rel = str(path.relative_to(REPO))
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:6000]
    except OSError:
        return []
    cands = []
    for ln, line in _signal_lines(text):
        bid = _BOOKID.search(line)
        bk = _BOOK.search(line)
        book_ref = bid.group(1) if bid else (f"B{bk.group(1) or bk.group(2)}" if bk else "")
        cands.append({"code": rel, "rule": "R1", "class": "pending",
                      "book": book_ref, "anchor": f"{rel}:{ln}: {line}", "note": "auto-extracted candidate — GB verify"})
    return cands


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("PyYAML required"); return 1
    cands = []
    for p in sorted(SRC.rglob("*.py")):
        if p.name == "__init__.py":
            continue
        cands.extend(_candidates_for(p))
    doc = {
        "_meta": {
            "kind": "R1 explicit-anchor CANDIDATES (mechanical) — NOT the map",
            "for": "GB to review + fold real edges into artifacts/book_code_map.yaml (GB sole-write)",
            "spec": "artifacts/GB_BookCode_Tree_Derivation_Spec_2026-06-10.md §3 R1",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "n_candidates": len(cands),
            "discipline": "every candidate's anchor is a real source line; GB promotes to class:derived on verify",
        },
        "candidates": cands,
    }
    OUT.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    print(f"wrote {OUT.name} — {len(cands)} R1 candidates across {len({c['code'] for c in cands})} modules (for GB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
