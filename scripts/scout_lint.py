#!/usr/bin/env python3
"""scout_lint.py — the /goal Scout anti-slop gate (ratified spec GB_goal_Scout_Synthesis_2026-06-15.md §3/§4).

MECHANICAL earned-Green RYG + packet-level auto-REJECT. Runs BEFORE anything reaches Atrium — only clean
packets become candidates. This is the volume control: Green = the checklist (and the evidence RESOLVES),
never the vibe. Deterministic + importable; CLI: `scout_lint.py <packet.yaml>` → exit 0 clean / 1 reject.

A packet is the brutally-small RYG yaml (per title, ≤5 tasks, ≤~700 tokens):
  title_id · status · green_items[] · yellow_items[] · red_items[] · top_next_tasks[] · blocked_by[]
  · evidence_refs[] · confidence
Each item / task carries: source (path), location, reason, action, confidence, evidence_ref.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOKEN_CAP = 700                      # spec §2 hard cap (≈ chars/4)
MAX_TASKS = 5                        # spec §2/§4: top 3–5 only
# Fit-gate violations (spec §1/§4): any whiff of authorship/design/architecture → out of fit, RED.
_OUT_OF_FIT = re.compile(r"\b(draft|rewrite|prose|chapter text|architecture|redesign|re-architect|"
                         r"design (a|the|new)|propose (a|an) (new )?(design|architecture)|author)\b", re.I)
_BARE_CONFIDENCE = re.compile(r"^\s*(high|medium|low|certain|sure)\s*\.?\s*$", re.I)


def _resolves(ref: str) -> bool:
    """The earned-Green RESOLVE check (catches confident-but-wrong): a `path` or `path#anchor` evidence_ref
    must resolve — the file exists, and any `#anchor` text is actually present in it. A bare symbolic ref
    (no path separator) is NOT a resolvable file claim and cannot carry Green."""
    if not ref or not isinstance(ref, str):
        return False
    path_part, _, anchor = ref.partition("#")
    path_part = path_part.strip().split(":")[0].strip()        # allow "path:line" — validate the file
    if "/" not in path_part or "." not in path_part.rsplit("/", 1)[-1]:
        return False                                            # symbolic, not a file claim → not Green-eligible
    p = (REPO / path_part)
    if not p.is_file():
        return False
    if anchor:
        try:
            return anchor.strip() in p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False
    return True


def _justified(confidence) -> bool:
    """Confidence must have a BASIS, not be bare (spec §3 'confidence justified, not bare')."""
    s = str(confidence or "").strip()
    return bool(s) and not _BARE_CONFIDENCE.match(s) and len(s) >= 12


def lint_item(item: dict) -> tuple[str, list[str]]:
    """Classify ONE finding/item RED / YELLOW / GREEN. GREEN only if EVERY earned-Green condition holds."""
    reasons = []
    text = " ".join(str(item.get(k, "")) for k in ("item", "reason", "action", "task"))
    if _OUT_OF_FIT.search(text):
        return "RED", ["out of fit-gate (prose/design/architecture/authorship)"]
    ref = item.get("evidence_ref") or item.get("source") or ""
    have_source = bool(ref)
    have_loc = bool(item.get("location") or "#" in str(ref) or ":" in str(ref))
    have_reason = bool(item.get("reason"))
    have_action = bool(item.get("action") or item.get("task"))
    conf_ok = _justified(item.get("confidence"))
    resolves = _resolves(ref)
    if not have_source: reasons.append("no source pointer")
    if not have_loc: reasons.append("no location")
    if not have_reason: reasons.append("no reason")
    if not have_action: reasons.append("no recommended action")
    if not conf_ok: reasons.append("confidence not justified")
    if not resolves: reasons.append(f"evidence_ref does not resolve: {ref!r}")
    if not reasons:
        return "GREEN", []
    # Cited+located but unresolved/uncertain → plausible, needs human review = YELLOW; uncited/subjective = RED.
    if have_source and have_reason and (have_loc or resolves):
        return "YELLOW", reasons
    return "RED", reasons


def _packet_token_estimate(packet: dict) -> int:
    import json
    return len(json.dumps(packet, ensure_ascii=False)) // 4


def lint_packet(packet: dict, existing_obligations: set | None = None) -> tuple[bool, list[str]]:
    """Packet-level auto-REJECT (spec §4). Returns (ok, rejects[]). Only ok=True packets reach Atrium."""
    rejects = []
    tasks = packet.get("top_next_tasks") or []
    refs = packet.get("evidence_refs") or []
    if not refs:
        rejects.append("no evidence_refs (mandatory)")
    if len(tasks) > MAX_TASKS:
        rejects.append(f">{MAX_TASKS} tasks ({len(tasks)})")
    if not packet.get("title_id"):
        rejects.append("no title_id")
    if not _justified(packet.get("confidence")):
        rejects.append("packet confidence not justified (no basis)")
    if _packet_token_estimate(packet) > TOKEN_CAP:
        rejects.append(f"exceeds token cap (~{_packet_token_estimate(packet)} > {TOKEN_CAP})")
    blob = " ".join(str(packet.get(k, "")) for k in ("note", "summary"))
    if _OUT_OF_FIT.search(blob):
        rejects.append("contains prose/architecture (out of fit-gate)")
    # Every top_next_task must state why (evidence_ref) — "cannot state why it matters" → reject.
    for i, t in enumerate(tasks):
        if not (isinstance(t, dict) and (t.get("evidence_ref") or t.get("source"))):
            rejects.append(f"task[{i}] has no evidence_ref (cannot state why)")
    # Duplicate-of-existing-obligation guard.
    if existing_obligations:
        for i, t in enumerate(tasks):
            key = (t.get("task") or "").strip().lower()
            if key and key in existing_obligations:
                rejects.append(f"task[{i}] duplicates an existing obligation")
    return (len(rejects) == 0), rejects


def main(argv: list[str]) -> int:
    import yaml
    if len(argv) < 2:
        print("usage: scout_lint.py <packet.yaml>")
        return 2
    packet = yaml.safe_load(Path(argv[1]).read_text(encoding="utf-8"))
    ok, rejects = lint_packet(packet)
    if ok:
        print(f"CLEAN  {packet.get('title_id')}")
        return 0
    print(f"REJECT {packet.get('title_id')}:")
    for r in rejects:
        print(f"  - {r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
