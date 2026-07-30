"""co_extrude.py — condition-5 (co-extrusion) enforcement, in the single press authority.

Promoted into the kernel package (2026-07-28, KM proof-path subset P-G3) from the legacy
workbench co-extrude script, so the orchestrator calls ONE gate chain. Wired as the 4th
cmd_cycle stage: a cycle that passes L0→prescreen→L1 then proves every runtime claim.

Each `extrusion:` entry in a seed is either VALIDATED in-cycle or an explicit blocking HOLD —
silent deferral is forbidden:
  PRESENT → the target_module(s) exist AND the acceptance_test passes right now (pytest against
            the code repo). A 'present' that fails is a DEFECT: the seed lied about the substrate.
  HOLD    → must carry blocks_seal: true. Recorded, never validated, never silently dropped;
            a HOLD whose acceptance_test path does not exist yet is a recorded warning (test_pending),
            not a defect (the code legitimately may not exist yet).

Posture stays tight (AA's reading): runs_today stays [] even for validated claims — validation
proves the machinery and receipts it; prose still states nothing as live.

  repo resolves from PRESS_CODE_REPO env → the kernel-src's own repo root (single authority).
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml


def _repo_root(repo=None):
    if repo:
        return Path(repo)
    env = os.environ.get("PRESS_CODE_REPO")
    if env:
        return Path(env)
    # the single authority: this module lives at <repo>/src/sovereign_agent/press/co_extrude.py
    return Path(__file__).resolve().parents[3]


def _vol_key(s):
    """Normalized (series, volume) from a volume-shaped token — for the disposition rule
    'a closes_in naming THIS volume is unbuilt scope, not a deferral'. Handles both the entry-id
    shape (S5-06-E2-3) and the closes_in shape (S5-V6 / S6-V5). Returns None for non-volume tokens
    (OPEN-DECISION:..., spec paths, 'live-runtime cutover')."""
    m = re.search(r"S(\d+)[-\s]?V?(\d+)", str(s), re.I)
    return (m.group(1), str(int(m.group(2)))) if m else None


def run(seeds_dir, repo=None, receipt_out=None) -> dict:
    """Validate a volume's extrusion ledger against the code repo. Returns the receipt dict;
    `receipt["defects"]` empty == pass. Never raises on a defect — the caller decides."""
    seeds = Path(seeds_dir)
    root = _repo_root(repo)
    results, defects = [], []
    for p in sorted(seeds.glob("ch*.yaml")):
        if p.name.startswith("_"):
            continue
        card = yaml.safe_load(p.read_text()) or {}
        for e in card.get("extrusion") or []:
            st = str(e.get("status", "")).upper()
            rec = {"id": e.get("id"), "chapter": card.get("chapter"), "status": st,
                   "claim": str(e.get("claim"))[:120]}
            if st == "PRESENT":
                raw = str(e.get("target_module", ""))
                # fs-1 annotates modules "path.py (symbol)" and compounds "A + B" — strip to paths
                paths = [re.sub(r"\s*\([^)]*\)", "", part).strip()
                         for part in raw.split(" + ") if part.strip()]
                missing = [q for q in paths if q and not (root / q).exists()]
                test = str(e.get("acceptance_test", ""))
                if missing:
                    rec["validated"] = False
                    rec["why"] = f"module(s) missing: {missing}"
                    defects.append(rec)
                else:
                    r = subprocess.run([sys.executable, "-m", "pytest", test, "-q", "--no-header"],
                                       cwd=root, capture_output=True, text=True, timeout=300)
                    rec["validated"] = (r.returncode == 0)
                    if r.returncode != 0:
                        rec["why"] = (r.stdout + r.stderr)[-300:]
                        defects.append(rec)
            elif st == "HOLD":
                ci = str(e.get("closes_in", "")).strip()          # P-1/HG-1: required book home
                this_vol = _vol_key(rec["id"])
                if e.get("blocks_seal") is not True:
                    rec["why"] = "HOLD without blocks_seal:true — silent deferral forbidden"
                    defects.append(rec)
                elif not ci:
                    rec["why"] = "HOLD without closes_in — unhosted designed-toward forbidden"
                    defects.append(rec)
                elif this_vol and _vol_key(ci) == this_vol:
                    rec["why"] = (f"closes_in names this volume ({ci}) — unbuilt scope, not a "
                                  "deferral; build it in-volume or REMOVE the claim")
                    defects.append(rec)
                else:
                    rec["closes_in"] = ci
                    tp = str(e.get("acceptance_test", "")).split("::")[0]
                    if tp and not (root / tp).exists():
                        rec["test_pending"] = tp
            elif st:
                rec["why"] = f"unknown status {st!r}"
                defects.append(rec)
            results.append(rec)
    receipt = {"tool": "press.co_extrude", "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
               "repo": str(root),
               "posture": "tight (validated claims still not stated live; runs_today stays [])",
               "present_validated": sum(1 for r in results if r.get("validated")),
               "present_failed": sum(1 for r in results if r.get("validated") is False),
               "holds": sum(1 for r in results if r["status"] == "HOLD" and "why" not in r),
               "defects": defects, "entries": results}
    if receipt_out:
        Path(receipt_out).write_text(json.dumps(receipt, indent=1))
    return receipt


def main():
    a = sys.argv[1:]
    opt = lambda f, d=None: a[a.index(f) + 1] if f in a else d
    rec = run(opt("--seeds"), opt("--repo"), opt("--receipt"))
    print(json.dumps({k: rec[k] for k in ("present_validated", "present_failed", "holds")}, indent=1))
    for d in rec["defects"]:
        print(f"  DEFECT [{d.get('id')}]: {d.get('why', '')[:140]}")
    sys.exit(1 if rec["defects"] else 0)


if __name__ == "__main__":
    main()
