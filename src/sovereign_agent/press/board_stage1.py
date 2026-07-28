"""board_stage1.py — the deterministic board stage-1 (continuity) + board-package builder.

Proof-path subset 4/5 (KM 2026-07-28, design station 6 + P-G5/6). Two responsibilities, both
mechanical and both in the single press authority so the orchestrator calls one chain:

  continuity_check(seeds)  — the deterministic stage-1 gate the model boards run behind. It
      RE-RUNS the continuity ledger (forbid / must / pinned facts, class-shaped), ASSERTS the
      inventories (population sum, canonical figures present in their required chapters — not
      advisory), and scans reader-facing prose for apparatus leaks + cross-chapter duplicate
      shingles. Returns findings; empty == PASS. No judge tokens are spent until this passes.

  build_board_package(seeds, assembled, out) — the deterministic package handed to the board
      (prose-only chapter exports + the assembled reader doc + settlement receipts + a
      MANIFEST.sha256.json). F4 law: the packet is verified before any judge is spent — this
      builder emits the shas so the board can attest exactly what it judged. The blind-parity
      PACKET (excerpts + calibration controls + shuffle key) is the board's to build and the
      shuffle key never touches this side.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path

import yaml

from .prescreen import apparatus_leaks


def _sha(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _body(prose: str) -> str:
    return re.sub(r"(?m)^>.*$", "", re.sub(r"```.*?```", "", prose, flags=re.S))


def continuity_check(seeds_dir) -> dict:
    """Deterministic stage-1. Returns {result, findings[]} — findings empty == PASS."""
    seeds = Path(seeds_dir)
    cards = {}
    for p in sorted(seeds.glob("ch*.yaml")):
        if p.name.startswith("_"):
            continue
        c = yaml.safe_load(p.read_text()) or {}
        cards[str(c.get("chapter"))] = c
    findings = []

    # (1) continuity ledger — forbid / must / pinned, scoped
    ledger = yaml.safe_load((seeds / "_continuity_facts.yaml").read_text()) if (seeds / "_continuity_facts.yaml").exists() else []
    for f in ledger or []:
        fp, mp = f.get("forbid_pattern"), f.get("must_pattern")
        scope = [str(x) for x in f["scope"]] if f.get("scope") else None
        req = [str(x) for x in f.get("required_in", [])]
        pin = " (PINNED)" if f.get("pin") else ""
        for ch, c in cards.items():
            b = _body(c.get("prose", ""))
            if fp and (scope is None or ch in scope) and re.search(fp, b, re.I):
                findings.append(f"ch{ch}: contradicts{pin} ledger fact {f.get('name')!r} (forbidden pattern present)")
            if mp and ch in req and not re.search(mp, b, re.I):
                findings.append(f"ch{ch}: missing{pin} required fact {f.get('name')!r}")

    # (2) asserted inventories (not advisory): the population classes must SUM to the canonical
    # total, and each canonical figure the ledger requires must be present where required.
    vin = seeds / "_volume_input.yaml"
    if vin.exists():
        canon = (yaml.safe_load(vin.read_text()) or {}).get("continuity_canon", {})
        classes = str(((canon.get("population") or {}).get("classes")) or "")
        classes = re.sub(r"\([^)]*\)", "", classes)  # drop a "(sums to 41,830)" total annotation
        total = str(((canon.get("population") or {}).get("total_objects")) or "").replace(",", "")
        nums = [int(x.replace(",", "")) for x in re.findall(r"\b\d[\d,]*\b", classes)]
        if total and nums and sum(nums) != int(total):
            findings.append(f"inventory: population classes sum to {sum(nums)} != canonical total {total}")

    # (3) apparatus leaks in reader-facing prose (body + receipt/verify fields)
    for ch, c in cards.items():
        rb = c.get("receipt_box") or {}
        faces = [_body(c.get("prose", "")), str(rb.get("claim", "")), str(rb.get("runs_today", "")),
                 str(rb.get("designed", ""))] + [str(x) for x in (c.get("verify_affordance") or [])]
        hard, stale = apparatus_leaks(faces)
        if hard:
            findings.append(f"ch{ch}: apparatus leak in reader-facing text: {hard[:4]}")
        if stale:
            findings.append(f"ch{ch}: stale 'nothing runs today' claim (post-extrusion)")

    # (4) cross-chapter duplicate 10-word shingles (recycled boilerplate)
    seen = {}
    for ch in sorted(cards, key=lambda x: int(x)):
        w = re.findall(r"[a-z'’]+", _body(cards[ch].get("prose", "")).lower())
        mine = set(tuple(w[i:i + 10]) for i in range(len(w) - 9))
        for sh in mine:
            if sh in seen and seen[sh] != ch:
                findings.append(f"ch{ch}: 10-word shingle recycled from ch{seen[sh]}: {' '.join(sh)[:60]!r}")
                break
        for sh in mine:
            seen.setdefault(sh, ch)

    return {"tool": "board_stage1.continuity_check", "volume": seeds.name,
            "result": "PASS" if not findings else "FAIL", "findings": findings}


def build_board_package(seeds_dir, assembled_path, out_dir) -> dict:
    """Deterministic board package (F4-ready). prose-only chapters + assembled reader doc +
    settlement receipts + MANIFEST.sha256.json. Returns the manifest."""
    seeds = Path(seeds_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}

    def put(name, text):
        (out / name).write_text(text)
        manifest[name] = _sha(text)

    settle = []
    for p in sorted(seeds.glob("ch*.yaml"), key=lambda q: int(re.search(r"\d+", q.name).group())):
        if p.name.startswith("_"):
            continue
        c = yaml.safe_load(p.read_text())
        put(f"{p.stem}.md", str(c["prose"]).strip() + "\n")
        settle.append({"chapter": c.get("chapter"), "title": c.get("title"),
                       "words": len(str(c["prose"]).split()),
                       "settled": c.get("settled"), "settled_cycle": c.get("settled_cycle")})
    for extra in ("_continuity_facts.yaml", "_volume_input.yaml"):
        if (seeds / extra).exists():
            put(extra, (seeds / extra).read_text())
    if assembled_path and Path(assembled_path).exists():
        put("assembled_volume.md", Path(assembled_path).read_text())
    put("settlement_receipts.json", json.dumps(settle, indent=1))
    (out / "MANIFEST.sha256.json").write_text(json.dumps(manifest, indent=1))
    return {"out": str(out), "files": len(manifest), "manifest": manifest}


def main():
    import sys
    a = sys.argv[1:]
    opt = lambda f, d=None: a[a.index(f) + 1] if f in a else d
    if a and a[0] == "package":
        r = build_board_package(opt("--seeds"), opt("--assembled"), opt("--out"))
        print(json.dumps({"out": r["out"], "files": r["files"]}, indent=1))
        return 0
    r = continuity_check(opt("--seeds") or (a[0] if a else "."))
    print(json.dumps(r, indent=1))
    return 0 if r["result"] == "PASS" else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
