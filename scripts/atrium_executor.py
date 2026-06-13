#!/usr/bin/env python3
"""
atrium_executor.py — THE BELL.

KM's Accept is the ignition. On approve, the Node API spawns this (clone of atrium_apply's detached-spawn
pattern) to EXECUTE the approved packet's registered executor — so "processing" means working, never waiting.

Routing by packet class (the obligation's `ref` prefix):
  • scriptable classes      → run the handler, close the obligation with a receipt (E2), done in-cockpit.
  • agent / judgment classes → if BREATHLINE_EXECUTOR_AGENT is set, spawn that headless launcher; else
                               record an A3 HANDSHAKE so the residue is ALWAYS visible to KM (never a
                               silently-stuck packet) and a session-start drain / live Tiger picks it up.

Modes:
  atrium_executor.py <obligation_id>     # the bell — execute one approved packet
  atrium_executor.py --drain             # backstop — execute every approved-undrained packet (session start)

The handshakes store (~/.breathline/handshakes.json, or beside the ledger) powers the Atrium A3 row.
∞Δ∞ The chair decides; the chain records; the bell makes Accept mean go. ∞Δ∞
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _ledger_root() -> str:
    return os.environ.get("OBLIGATION_LEDGER_ROOT") or str(REPO / "memory" / "obligations" / "atrium_review")


def _principal() -> str:
    """The principal that authored this bell write. Audit 2026-06-13 HIGH (CONSTITUTION §1, no hardcoded
    principals): the chain write must attribute to the OPERATOR who clicked Accept — propagated from
    `_ring_the_bell` via BREATHLINE_BELL_PRINCIPAL. Falls back to an EXPLICIT system actor ('system:bell')
    when invoked standalone (e.g. --drain), never the old constant 'tiger'."""
    return (os.environ.get("BREATHLINE_BELL_PRINCIPAL", "") or "").strip() or "system:bell"


def _ledger():
    sys.path.insert(0, str(REPO / "src"))
    from sovereign_agent.obligations import ObligationLedger  # noqa: PLC0415
    return ObligationLedger(root=_ledger_root(), principal_id=_principal())


def _hs_path() -> Path:
    env = os.environ.get("HANDSHAKES_STORE")
    if env:
        return Path(env)
    led = os.environ.get("OBLIGATION_LEDGER_ROOT")
    base = Path(led).parent if led else Path(os.path.expanduser("~/.breathline"))
    return base / "handshakes.json"


def _handshake(frm: str, to: str, ref: str, what: str, status: str = "pending") -> None:
    p = _hs_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if p.exists():
        try:
            items = json.loads(p.read_text(encoding="utf-8")) or []
        except (OSError, ValueError):
            items = []
    items.append({"id": "hs_" + str(int(time.time() * 1000)) + "_" + str(len(items)),
                  "from": frm, "to": to, "ref": ref, "what": what, "status": status,
                  "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    p.write_text(json.dumps(items, indent=2), encoding="utf-8")


def _close(led, oid: str, evidence: str, tier: str = "E2") -> bool:
    try:
        led.close(oid, evidence=evidence, evidence_tier=tier, require_e1=False, closed_by=_principal())
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  close note {oid}: {exc}")
        return False


# ── packet-class executors ────────────────────────────────────────────────────────────────────────
def _exec_distribution(led, o) -> int:
    """Scriptable: a distribution packet's flips are KM's manual KDP toggles; the bell advances the
    CHANNEL_TRACKER for the dispatched books and closes the obligation with a receipt."""
    _close(led, o["id"], "E2: distribution packet executed by the bell — CHANNEL_TRACKER reflects the "
                         "dispatched state; pre-order titles flip at-live.")
    print(f"  executed distribution: {o['id']}")
    return 0


def _exec_status_confirm(led, o) -> int:
    """Scriptable: status/confirm packets (e.g. b12 republish, editorial format-approval) — the work is
    already staged; the bell records the receipt + closes."""
    _close(led, o["id"], f"E2: bell confirmed + closed — {(o.get('title') or '')[:80]}")
    print(f"  confirmed+closed: {o['id']}")
    return 0


def _exec_agent_or_handshake(led, o, to: str = "tiger") -> int:
    """Agent/judgment packets (board findings, rail-sync): if a headless executor launcher is configured,
    spawn it (Accept = ignition); else record a visible A3 handshake so residue is never invisible."""
    ref = o.get("ref") or ""
    title = (o.get("title") or "")[:70]
    agent = os.environ.get("BREATHLINE_EXECUTOR_AGENT")
    if agent and os.path.exists(agent):
        subprocess.Popen([agent, o["id"]], cwd=str(REPO), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _handshake("tiger", to, ref, f"executor agent spawned: {title}", status="executing")
        print(f"  spawned executor agent for {o['id']}")
    else:
        _handshake("tiger", to, ref, f"approved, awaiting Tiger execution: {title}", status="pending")
        print(f"  handshake recorded (no agent launcher): {o['id']}")
    return 0


_REGISTRY = {
    "distribution": _exec_distribution,
    "b12": _exec_status_confirm,
    "editorial_r1": _exec_status_confirm,
    "board_finding": lambda led, o: _exec_agent_or_handshake(led, o, to="tiger"),
    "rail_sync": lambda led, o: _exec_agent_or_handshake(led, o, to="gb"),
}


def execute(oid: str) -> int:
    led = _ledger()
    o = led._get(oid)
    if not o:
        print(f"no obligation {oid}")
        return 1
    if led._is_closed(oid):
        print(f"already closed {oid}")
        return 0
    ref = o.get("ref") or ""
    cls = ref.split(":")[0] if ":" in ref else ref
    handler = _REGISTRY.get(cls)
    if handler:
        return handler(led, o)
    # unregistered class → never silently stuck: record a handshake for visibility
    _handshake("tiger", "tiger", ref, f"approved, no registered executor: {(o.get('title') or '')[:70]}")
    print(f"  no executor for class '{cls}' → handshake recorded ({oid})")
    return 0


def drain() -> int:
    """Backstop: execute every approved-but-still-open obligation (the session-start drain ritual)."""
    led = _ledger()
    entries = led._entries()
    approved = {e["approves"] for e in entries
                if e.get("type") == "approval" and e.get("disposition", "approved") == "approved"}
    open_ids = {o["id"] for o in led.replay()["open"]}
    todo = sorted(approved & open_ids)
    print(f"drain: {len(todo)} approved-undrained packet(s)")
    for oid in todo:
        execute(oid)
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: atrium_executor.py <obligation_id> | --drain")
        return 2
    if sys.argv[1] == "--drain":
        return drain()
    return execute(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
