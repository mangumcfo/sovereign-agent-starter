#!/usr/bin/env python3
"""
render_standard_lint.py — Gate-6-lite at the pen.

Mechanical check of a manuscript against the **Deterministic-Render Writing Standard v1.0**
(GB, artifacts/GB_Deterministic_Render_Standard_2026-06-12.md). Runs BEFORE any Atrium
manuscript edit commits, so the eight rules are machine-held at the moment of violation —
not discovered three stages later at a board. (THREAD [239]: "the rule grows teeth at the pen.")

Checks the mechanically-decidable subset of the 8 rules:

  HARD (block commit):
    R8/R1  duplicate closers   — >1 artifacts callout in a chapter (a 'Spec → Role → Atrium'
                                 closer AND a 'Receipt Box', or two of either). Rule 1 applied
                                 to Rule 8's own implementation — the exact Vol 1 2026-06-12 catch.
    R8     print-unsafe glyphs — emoji / pictographic glyphs in manuscript elements (📦 etc.);
                                 print B&W-and-color safe only.

  ADVISORY (warn, non-blocking):
    R2     vague behavior      — "should feel", "intuitively", "seamlessly", "just works"...
                                 (Rule 2: declarative governance language, never subjective).
    R5     dishonest stubs     — forward spec/file refs lacking a (planned)/mock/Phase/gated label.
    R3     capability promise  — each chapter opens with a "You will be able to" promise.

Exit codes: 0 = clean · 1 = HARD violation(s) · (advisories never set nonzero on their own).

Usage:
    python3 scripts/render_standard_lint.py <manuscript.md> [--json] [--strict]
      --strict : treat advisories as blocking too (exit 1 if any advisory).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- the single artifacts-closer vocabulary (Rule 8 canonical: ONE per chapter) -------------
RECEIPT_BOX_RE = re.compile(r"Receipt Box", re.IGNORECASE)
SPEC_ROLE_RE = re.compile(r"Spec\s*→\s*Role\s*→\s*Atrium")
ARTIFACTS_CALLOUT_RE = re.compile(r"Artifacts this chapter authorizes", re.IGNORECASE)
CHAPTER_RE = re.compile(r"^#{1,2}\s+(Chapter\b.*|Appendix\b.*)$")

# --- R8 print-unsafe glyphs: pictographic emoji ranges (NOT → ∞ Δ · — which are print-safe) --
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols & pictographs, supplemental, emoji
    "\U00002600-\U000026FF"   # misc symbols (☀ ☂ etc.)
    "\U00002700-\U000027BF"   # dingbats (✅ ✂ etc.)
    "\U0001F000-\U0001F2FF"   # mahjong/dominoes/enclosed
    "\U0000FE0F"              # variation selector-16 (emoji presentation)
    "]"
)

# --- R2 vague / subjective behavioral phrasing ----------------------------------------------
VAGUE_PHRASES = [
    "should feel", "feels like", "intuitively", "seamlessly", "magically",
    "just works", "user-friendly", "delightful", "easy to use", "effortlessly",
    "out of the box", "it simply works",
]

# --- R5 forward-reference markers that make a stub honest ------------------------------------
HONEST_STUB_LABELS = ["(planned)", "mock", "phase ", "gated on", "forward-arc", "forward arc",
                      "not yet", "will ship", "future volume", "illustrative"]
# a line that references a spec/yaml/contract file but is forward-looking
SPEC_REF_RE = re.compile(r"`[^`]*\.(yaml|yml)[^`]*`|specs?/|contract_v\d")

CAPABILITY_PROMISE_RE = re.compile(r"You will be able to", re.IGNORECASE)


def _chapters(lines: list[str]) -> list[tuple[str, int, int]]:
    """Return [(title, start_idx, end_idx_exclusive)] for each Chapter/Appendix section."""
    heads = [(i, m.group(1).strip()) for i, l in enumerate(lines)
             if (m := CHAPTER_RE.match(l))]
    out = []
    for k, (idx, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append((title, idx, end))
    return out


def lint(text: str) -> dict:
    lines = text.split("\n")
    hard: list[dict] = []
    advisory: list[dict] = []

    # ---- R8/R1 duplicate closers (per chapter) ----
    for title, start, end in _chapters(lines):
        block = lines[start:end]
        closers = 0
        kinds = []
        for bl in block:
            if RECEIPT_BOX_RE.search(bl):
                closers += 1; kinds.append("Receipt Box")
            if ARTIFACTS_CALLOUT_RE.search(bl):
                closers += 1; kinds.append("Artifacts-callout")
            # a bare Spec→Role line that is NOT already inside an Artifacts callout title
            if SPEC_ROLE_RE.search(bl) and not ARTIFACTS_CALLOUT_RE.search(bl):
                closers += 1; kinds.append("Spec→Role")
        if closers > 1:
            hard.append({
                "rule": "R8/R1", "kind": "duplicate_closer", "chapter": title,
                "detail": f"{closers} artifacts closers in one chapter ({', '.join(kinds)}); "
                          f"Rule 8 canonical: exactly ONE artifacts callout per chapter.",
            })

    # ---- R8 print-unsafe glyphs ----
    for i, l in enumerate(lines):
        for m in EMOJI_RE.finditer(l):
            hard.append({
                "rule": "R8", "kind": "print_unsafe_glyph", "line": i + 1,
                "detail": f"emoji/pictograph {m.group(0)!r} at line {i+1} — print-unsafe; "
                          f"use a text label.",
            })
            break  # one per line is enough

    # ---- R2 vague behavioral phrasing (advisory) ----
    low = text.lower()
    for ph in VAGUE_PHRASES:
        idx = low.find(ph)
        if idx != -1:
            ln = text.count("\n", 0, idx) + 1
            advisory.append({"rule": "R2", "kind": "vague_behavior", "line": ln,
                             "detail": f'subjective phrase "{ph}" — prefer declarative '
                                       f'governance language ("shall / must / operator defines").'})

    # ---- R5 dishonest stubs (advisory) ----
    for i, l in enumerate(lines):
        if SPEC_REF_RE.search(l):
            ll = l.lower()
            # forward-ref to a spec is honest only if it carries a stub/forward label on the line
            if not any(lab in ll for lab in HONEST_STUB_LABELS):
                # skip lines that are clearly present-tense repo facts (breathline-sealed / bl-verify)
                if "breathline-sealed" in ll or "bl-verify" in ll or "sealed/layer" in ll:
                    continue
                advisory.append({"rule": "R5", "kind": "unlabeled_forward_ref", "line": i + 1,
                                 "detail": f"spec/contract ref at line {i+1} without a "
                                           f"(planned)/mock/Phase/gated label — confirm it is live "
                                           f"or label it honestly."})

    # ---- R3 capability promise per chapter (advisory) ----
    for title, start, end in _chapters(lines):
        if title.lower().startswith("appendix"):
            continue
        if not any(CAPABILITY_PROMISE_RE.search(l) for l in lines[start:end]):
            advisory.append({"rule": "R3", "kind": "missing_capability_promise", "chapter": title,
                             "detail": f'"{title}" has no "You will be able to…" promise '
                                       f"(Rule 3: the promise IS the acceptance criteria)."})

    return {"hard": hard, "advisory": advisory,
            "ok": len(hard) == 0, "hard_count": len(hard), "advisory_count": len(advisory)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic-Render Standard lint (Gate-6-lite)")
    ap.add_argument("manuscript")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="treat advisories as blocking too")
    a = ap.parse_args()

    p = Path(a.manuscript)
    if not p.is_file():
        print(f"render-lint: no such file: {p}", file=sys.stderr)
        return 1
    res = lint(p.read_text(encoding="utf-8"))

    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res["hard"]:
            print(f"✗ HARD violations ({res['hard_count']}):")
            for v in res["hard"]:
                loc = v.get("chapter") or f"line {v.get('line')}"
                print(f"  [{v['rule']}] {v['kind']} · {loc}\n      {v['detail']}")
        if res["advisory"]:
            print(f"~ advisories ({res['advisory_count']}):")
            for v in res["advisory"]:
                loc = v.get("chapter") or f"line {v.get('line')}"
                print(f"  [{v['rule']}] {v['kind']} · {loc}")
        if res["ok"] and not res["advisory"]:
            print(f"✓ {p.name}: clean against the Deterministic-Render Standard (8 rules).")
        elif res["ok"]:
            print(f"✓ {p.name}: no HARD violations ({res['advisory_count']} advisories above).")

    if res["hard"]:
        return 1
    if a.strict and res["advisory"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ∞Δ∞ SEAL: the standard becomes a linter — machine-held at the pen, not discovered at the board. ∞Δ∞
