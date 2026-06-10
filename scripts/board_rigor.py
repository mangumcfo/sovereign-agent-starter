#!/usr/bin/env python3
"""
board_rigor.py — enforce the Board Rigor Standard v1.0 (KM-1176, 2026-06-10): NO RUBBER STAMPS.

Validates a board's structured findings file against the five structural requirements so boards prove they
did real work before their book can reach KM. Wired into review_ready_contract.py (R1): a board that fails
rigor does NOT count as executed.

  python3 scripts/board_rigor.py <findings.json>     # exit 0 pass / 1 fail; prints failing rules
  (importable: rigor_check(findings_dict) -> dict)

Rules (Board Rigor Standard §five):
  R-LGP    every finding.lgp_alignment ≥25 chars AND references an LGP/primacy/sovereign/generational concept
  R-OBL    every material finding has obligation_id; deferred findings have defer_reason
  R-DEPTH  every section has finding_count≥1 OR all_clear_justification ≥40 chars
  R-HUMAN  every finding.detail ≥80 chars and not bare boilerplate ("looks good"/"all good"/"fine"/"n/a")

∞Δ∞ The board proves its depth, or the book never reaches the human. ∞Δ∞
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_LGP_TERMS = re.compile(r"lgp|generational|prosperit|human primacy|sovereign|continuit|families|heirs|stewardship", re.I)
_BOILERPLATE = re.compile(r"^\s*(looks good|all good|fine|n/?a|ok|good|clean|no issues?)\.?\s*$", re.I)


def _check_lgp(findings: list) -> list:
    gaps = []
    for f in findings:
        v = (f.get("lgp_alignment") or "").strip()
        if len(v) < 25 or not _LGP_TERMS.search(v):
            gaps.append(f"{f.get('id', '?')}: LGP alignment missing/weak (≥25 chars + LGP/primacy/sovereign concept)")
    return gaps


def _check_obligations(findings: list) -> list:
    gaps = []
    for f in findings:
        sev = (f.get("severity") or "").lower()
        if sev == "material" and not (f.get("obligation_id") or "").strip():
            gaps.append(f"{f.get('id', '?')}: material finding has no obligation_id")
        if (f.get("disposition") or "").lower() == "deferred" and not (f.get("defer_reason") or "").strip():
            gaps.append(f"{f.get('id', '?')}: deferred without defer_reason")
    return gaps


def _check_depth(coverage: list) -> list:
    gaps = []
    for c in coverage:
        n = c.get("finding_count", 0) or 0
        just = (c.get("all_clear_justification") or "").strip()
        if n < 1 and len(just) < 40:
            gaps.append(f"{c.get('section', '?')}: no findings + no ≥40-char all-clear justification (Depth Gate)")
    return gaps


def _check_human(findings: list) -> list:
    gaps = []
    for f in findings:
        d = (f.get("detail") or "").strip()
        if len(d) < 80 or _BOILERPLATE.match(d):
            gaps.append(f"{f.get('id', '?')}: detail too thin/boilerplate for a discerning human (≥80 chars, specific)")
    return gaps


def rigor_check(data: dict) -> dict:
    findings = data.get("findings") or []
    coverage = data.get("section_coverage") or []
    rules = {
        "R-LGP": _check_lgp(findings),
        "R-OBL": _check_obligations(findings),
        "R-DEPTH": _check_depth(coverage),
        "R-HUMAN": _check_human(findings),
    }
    # structural minimums: a board with zero findings AND zero coverage is not a board
    if not findings and not coverage:
        rules["R-STRUCT"] = ["empty board — no findings and no section_coverage"]
    gaps = [g for gg in rules.values() for g in gg]
    return {"board": data.get("board"), "book_id": data.get("book_id"),
            "pass": not gaps, "rules": rules, "gaps": gaps,
            "n_findings": len(findings), "n_sections": len(coverage)}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: board_rigor.py <findings.json>"); return 2
    p = Path(sys.argv[1])
    if not p.is_file():
        print(f"✗ not found: {p}"); return 1
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"✗ invalid JSON: {e}"); return 1
    r = rigor_check(data)
    flag = "✅ RIGOR PASS" if r["pass"] else "⛔ RIGOR FAIL"
    print(f"{flag} — {r['board']} board / {r['book_id']} ({r['n_findings']} findings, {r['n_sections']} sections)")
    for rule, gg in r["rules"].items():
        print(f"  {'✓' if not gg else '✗'} {rule} ({len(gg)})")
        for g in gg[:8]:
            print(f"      • {g}")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
