#!/usr/bin/env python3
"""scout_run.py — the /goal Scout deterministic runner (ratified spec GB_goal_Scout_Synthesis_2026-06-15.md).

PROPOSE-ONLY · DETERMINISTIC · READ-ONLY (except its own artifacts/scout/ tree + the propose-only proposals
store). It never edits source, never git/seal, never creates a real obligation. Both pilot packet types are
OBJECTIVE derivers — Book↔Code drift (artifacts/book_code_tree.json findings) + static-scan delta
(scripts/static_scan.sh vs a stored baseline) — so there is NO LLM in the loop: objective input → deterministic
packet → mechanical lint (scout_lint) → candidate. Slop is engineered out, not promised away.

  python3 scripts/scout_run.py --titles a,b,c --dry-run   # derive + lint + write packets; POST nothing
  python3 scripts/scout_run.py                             # default 3 highest-drift titles + post candidates

A real obligation is born only when KM+GB DECIDE a candidate in the cockpit. The scout proposes; it cannot decide.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import scout_lint  # noqa: E402

TREE = REPO / "artifacts" / "book_code_tree.json"
SCOUT = REPO / "artifacts" / "scout"
BASELINE = SCOUT / "static_baseline.json"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Book↔Code drift packets (per title) — deterministic from book_code_tree.json findings ───────────
def _drift_by_title() -> dict[str, list[str]]:
    findings = json.loads(TREE.read_text()).get("findings", {})
    by_title: dict[str, list[str]] = {}
    for ch in findings.get("unrendered_chapters", []):
        book_id = str(ch).split("#", 1)[0]
        by_title.setdefault(book_id, []).append(str(ch))
    return by_title


def _book_code_packet(title_id: str, chapters: list[str]) -> dict:
    """Drift is surfaced as YELLOW (needs-human: narrative vs should-render) — the scout flags, never decides.
    ONE bounded top_next_task: review the unrendered set. Evidence resolves to book_code_tree.json."""
    n = len(chapters)
    return {
        "title_id": title_id,
        "status": "yellow",
        "green_items": [],
        "yellow_items": [{
            "item": f"{n} chapters have no code edge (unrendered)",
            "source": "artifacts/book_code_tree.json",
            "location": "findings.unrendered_chapters",
            "reason": "Book↔Code drift: chapters in this title carry no edge in book_code_map.yaml.",
            "action": "Human: mark each narrative (n/a) or queue for render — the scout does not decide which.",
            "confidence": f"Derived deterministically from book_code_tree.json: {n} unrendered chapter ids.",
            "evidence_ref": "artifacts/book_code_tree.json#unrendered_chapters",
            "sample": chapters[:5],
        }],
        "red_items": [],
        "top_next_tasks": [{
            "task": f"Review {n} unrendered chapters for {title_id} (mark n/a or queue render)",
            "evidence_ref": "artifacts/book_code_tree.json#unrendered_chapters",
            "effort": "S (triage)",
        }],
        "blocked_by": [],
        "evidence_refs": ["artifacts/book_code_tree.json#unrendered_chapters"],
        "confidence": f"Deterministic deriver over book_code_tree.json findings ({n} ids for {title_id}).",
    }


# ── static-scan delta packet — deterministic from scripts/static_scan.sh vs baseline ─────────────────
def _static_findings() -> list[str]:
    """Objective ruff finding lines (file:rule) — the stable signal set for the delta."""
    out = subprocess.run([sys.executable, "-m", "ruff", "check", "src", "scripts",
                          "--select", "F,C90,E722,E741", "--output-format", "concise"],
                         cwd=str(REPO), capture_output=True, text=True).stdout
    found = set()
    for ln in out.splitlines():
        m = re.match(r"^(\S+:\d+:\d+):\s+([A-Z]\d+)\b", ln)   # path:line:col: CODE …
        if m:
            found.add(f"{m.group(1)} :: {m.group(2)}")
    return sorted(found)


def _static_packet(dry_run: bool) -> dict:
    cur = _static_findings()
    prev = json.loads(BASELINE.read_text()).get("findings", []) if BASELINE.is_file() else None
    new = sorted(set(cur) - set(prev)) if prev is not None else cur
    status = "green" if prev is not None and not new else "yellow"
    tasks = []
    for f in new[:5]:
        loc = f.split(" :: ", 1)[0]
        tasks.append({"task": f"Disposition static finding: {f}", "evidence_ref": loc, "effort": "S"})
    if not dry_run and prev is None:                                 # establish baseline on the first real run
        SCOUT.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({"findings": cur, "ts": _today()}, indent=2))
    return {
        "title_id": "static-scan-delta",
        "status": status,
        "green_items": [],
        "yellow_items": [{
            "item": f"{len(new)} static finding(s) since baseline" if prev is not None
                    else f"{len(cur)} static findings (baseline establishing)",
            "source": "scripts/static_scan.sh", "location": "ruff F/C90/E722/E741",
            "reason": "Objective dead-code/complexity findings (vulture+ruff) needing disposition.",
            "action": "Human: remove/justify dead code; track complexity>10 as M-tail or refactor.",
            "confidence": f"Reproducible ruff scan; {len(new)} new vs {('baseline' if prev else 'none')}.",
            "evidence_ref": "scripts/static_scan.sh",
        }],
        "red_items": [],
        "top_next_tasks": tasks or [{
            "task": "No new static findings since baseline (clean)",
            "evidence_ref": "scripts/static_scan.sh", "effort": "—"}],
        "blocked_by": [],
        "evidence_refs": ["scripts/static_scan.sh", "artifacts/scout/static_baseline.json"],
        "confidence": f"Deterministic ruff scan; delta of {len(new)} computed against the stored baseline.",
    }


# ── runner ───────────────────────────────────────────────────────────────────────────────────────
def run(titles: list[str] | None, dry_run: bool) -> int:
    drift = _drift_by_title()
    if not titles:
        titles = [t for t, _ in Counter({t: len(c) for t, c in drift.items()}).most_common(3)]
    packets = [_book_code_packet(t, drift.get(t, [])) for t in titles] + [_static_packet(dry_run)]

    out_dir = SCOUT / "packets" / _today()
    rej_dir = SCOUT / "rejected" / _today()
    out_dir.mkdir(parents=True, exist_ok=True)
    rej_dir.mkdir(parents=True, exist_ok=True)
    import yaml
    clean, rejected = [], []
    for p in packets:
        ok, rejects = scout_lint.lint_packet(p)
        target = (out_dir if ok else rej_dir) / f"{p['title_id'].replace('/', '_')}.yaml"
        body = yaml.safe_dump(p, sort_keys=False, allow_unicode=True)
        if not ok:
            body = f"# REJECTED by scout_lint: {rejects}\n" + body
        target.write_text(body, encoding="utf-8")
        (clean if ok else rejected).append((p["title_id"], rejects))

    print(f"scout_run {_today()} — {len(clean)} clean / {len(rejected)} rejected "
          f"(dry_run={dry_run}; {'NO candidates posted' if dry_run else 'candidates posted to proposals'})")
    for tid, _ in clean:
        print(f"  CLEAN  {tid}")
    for tid, rj in rejected:
        print(f"  REJECT {tid}: {rj}")
    if not dry_run:
        _post_candidates(clean, out_dir)
    print(f"packets → {out_dir}")
    return 0


def _post_candidates(clean, out_dir: Path) -> None:
    """Propose-only: post each clean packet as an INFO candidate to the node's /proposals (status 'proposed').
    Best-effort over the local node; if the node is down, the packets remain on disk for the next run."""
    import urllib.request
    base = "http://127.0.0.1:8421/api/v1"
    for tid, _ in clean:
        payload = {"info": True, "route": "observation", "book": tid,
                   "note": f"/goal Scout candidate: {tid} — see {out_dir}/{tid.replace('/', '_')}.yaml"}
        try:
            req = urllib.request.Request(f"{base}/proposals", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json",
                                                  "X-Principal-Id": "scout"}, method="POST")
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:  # noqa: BLE001 — propose-only; a down node never breaks the scout
            print(f"  (candidate post deferred for {tid}: {exc})")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="/goal Scout — propose-only deterministic runner")
    ap.add_argument("--titles", help="comma-separated book_ids; default = 3 highest-drift")
    ap.add_argument("--dry-run", action="store_true", help="derive + lint + write packets; POST nothing")
    a = ap.parse_args(argv[1:])
    titles = [t.strip() for t in a.titles.split(",")] if a.titles else None
    return run(titles, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
