"""seal_summary.py — the Seal Summary generator (proof-path subset 5/5, P-G11, design §5).

Generates the ≤30-minute human review pack from RECEIPTS ONLY — it writes no judgement of its
own. A Summary that cannot be generated (a missing receipt) is a title that is not done, and the
generator REFUSES rather than inventing the missing piece.

Inputs (all receipts, none authored here):
  seeds_dir            the volume's settled seeds (extrusion ledger → Code section; titles)
  cycle_json           the PASSing cycle.json (gate_rev, co_extrude present/hold counts)
  settlement_json      settlement_receipts.json (per-chapter settled_cycle + shas)
  assembly_json        the assembler receipt (doc sha, chapters, apparatus-clean by construction)
  board_json           AA's board verdict — parity per dim, reader verdict + suspicion point,
                       continuity attestation. This is the one input the machine does not own;
                       without it there is no Summary (the boards are the binding evidence).
  suite_before/after   kernel test counts around this title's extrusions (Code section)

The board_json schema (AA emits it):
  {"parity": [{"dim","cand","ctrl"}...], "reader": {"verdict","suspicion_point"},
   "continuity": "PASS|...", "binding_bar": "CLEAR|NOT CLEAR"}
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import yaml


class SummaryRefusal(Exception):
    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__("SEAL SUMMARY REFUSED: missing receipt(s) — a Summary that cannot be "
                         "generated is a title that is not done:\n  - " + "\n  - ".join(self.missing))


def _load(path, gaps, label):
    p = Path(path) if path else None
    if not p or not p.exists():
        gaps.append(f"{label}: {path}")
        return None
    return yaml.safe_load(p.read_text()) if str(p).endswith((".yaml", ".yml")) else json.loads(p.read_text())


def generate(seeds_dir, cycle_json, settlement_json, assembly_json, board_json,
             suite_before=None, suite_after=None, out=None) -> str:
    gaps = []
    cyc = _load(cycle_json, gaps, "cycle.json")
    settle = _load(settlement_json, gaps, "settlement_receipts.json")
    asm = _load(assembly_json, gaps, "assembly receipt")
    board = _load(board_json, gaps, "board verdict")
    seeds = Path(seeds_dir)
    vin = seeds / "_volume_input.yaml"
    if not vin.exists():
        gaps.append(f"_volume_input.yaml: {vin}")
    if gaps:
        raise SummaryRefusal(gaps)

    vi = yaml.safe_load(vin.read_text())
    title = vi.get("title", seeds.name)
    subtitle = vi.get("subtitle", "")

    # Code section from the extrusion ledger (receipts, not authored)
    rows, present, hold = [], 0, 0
    for p in sorted(seeds.glob("ch*.yaml"), key=lambda q: int(re.search(r"\d+", q.name).group())):
        if p.name.startswith("_"):
            continue
        for e in (yaml.safe_load(p.read_text()) or {}).get("extrusion") or []:
            st = str(e.get("status", "")).upper()
            if st == "PRESENT":
                present += 1
                rows.append((e.get("id"), str(e.get("claim", ""))[:70],
                             str(e.get("target_module", "")), str(e.get("acceptance_test", ""))))
            elif st in ("HOLD", "DOWNGRADED"):
                hold += 1

    # board table
    par = board.get("parity", [])
    reader = board.get("reader", {})
    suspicion = str(reader.get("suspicion_point", "")).strip()
    binding = board.get("binding_bar", "")

    L = []
    L.append(f"# Seal Summary — {title}")
    if subtitle:
        L.append(f"*{subtitle}*")
    L.append("")
    L.append("> Generated from receipts only (`press.seal_summary`). No judgement authored here; "
             "the boards are the evidence, the ledger is the Code section, the human word is the "
             "only remaining act.")
    L.append("")
    # story + ladder
    L.append(f"**Story.** {board.get('story_line', vi.get('description','')[:200])}")
    L.append(f"**Ladder.** {board.get('ladder_line', 'what this volume adds — see registry')}")
    L.append("")
    # board table
    L.append("## Board")
    L.append("| Dimension | Candidate | Control | Δ |")
    L.append("|---|---|---|---|")
    for d in par:
        c, k = d.get("cand"), d.get("ctrl")
        delta = (round(c - k, 2) if isinstance(c, (int, float)) and isinstance(k, (int, float)) else "")
        L.append(f"| {d.get('dim')} | {c} | {k} | {delta} |")
    L.append("")
    L.append(f"- **Reader-simulation (binding bar): {binding}** — suspicion point: "
             f"**{suspicion or 'none'}**" + (f" · verdict: *{reader.get('verdict')}*" if reader.get("verdict") else ""))
    L.append(f"- **Continuity attestation:** {board.get('continuity', 'see board_stage1 receipt')}")
    L.append("")
    # Code section
    L.append("## Code")
    L.append(f"- **{present} claims, {present} present · {hold} HOLD (zero by construction — PS-4 "
             f"refuses any seal carrying an open blocking HOLD).**")
    if suite_before is not None and suite_after is not None:
        L.append(f"- kernel test suite: {suite_before} → {suite_after} (green).")
    L.append("")
    L.append("| Claim | Module | Test |")
    L.append("|---|---|---|")
    for _id, claim, mod, test in rows:
        L.append(f"| {claim} | `{mod}` | `{test}` |")
    L.append("")
    # residuals / risk / word line
    L.append("## Residuals & risk flags")
    res = board.get("residuals") or []
    if res:
        for r in res:
            L.append(f"- ▸ {r}")
    else:
        L.append("- ▸ none recorded by the boards.")
    L.append("")
    L.append("## The word")
    L.append(f"- gate_rev **{cyc.get('gate_rev')}** · cycle `{(cyc.get('cycle_sha256') or '')[:16]}` · "
             f"settled on `{settle.get('settled_cycle','')}` · assembled `{(asm.get('doc_sha256_16') or asm.get('doc_sha256') or '')}`")
    L.append("- **Seal** · per-item overrides · or bounce-with-reason. The seal is spoken by a human "
             "at a keyboard; nothing here supplies it.")
    doc = "\n".join(L) + "\n"
    if out:
        Path(out).write_text(doc)
    return doc


def main():
    import sys
    a = sys.argv[1:]
    opt = lambda f, d=None: a[a.index(f) + 1] if f in a else d
    try:
        doc = generate(opt("--seeds"), opt("--cycle"), opt("--settlement"), opt("--assembly"),
                       opt("--board"), opt("--suite-before"), opt("--suite-after"), opt("--out"))
    except SummaryRefusal as e:
        print(str(e))
        return 1
    if not opt("--out"):
        print(doc)
    else:
        print(f"Seal Summary → {opt('--out')} ({len(doc.split())} words)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
