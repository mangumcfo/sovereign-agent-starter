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
    # Route through the ONE resolver (audit 2026-06-13) so the executor and the API can never disagree.
    sys.path.insert(0, str(REPO / "src"))
    from sovereign_agent.obligations.ledger import get_ledger_root  # noqa: PLC0415
    return str(get_ledger_root())


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
    # one resolver shared with the node + apply subprocess (audit 2026-06-13c #9)
    sys.path.insert(0, str(REPO / "src"))
    from sovereign_agent.node_api._jsonstore import sidecar_store  # noqa: PLC0415
    return sidecar_store("handshakes.json", "HANDSHAKES_STORE")


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


def _close_or_residue(led, o, evidence: str, to: str = "tiger") -> bool:
    """Close with an E2 receipt; on FAILURE record an apply_close_failed handshake (mirror atrium_apply) so
    the still-OPEN obligation is visible residue, and report False so the caller returns non-zero.

    Engine 95+ HIGH #4 (card cd010960): the scriptable handlers used to DISCARD _close()'s bool and return 0
    (success) while the obligation stayed OPEN — a false success on a silent close failure. They now honor it:
    a close failure is hard, never a green exit (the same discipline as atrium_apply's apply_close_failed)."""
    if _close(led, o["id"], evidence):
        return True
    _handshake("tiger", to, o.get("ref") or "",
               f"close FAILED — obligation OPEN, not closed: {(o.get('title') or '')[:70]}",
               status="apply_close_failed")
    print(f"  CLOSE FAILED {o['id']} — obligation OPEN, no false success")
    return False


# ── packet-class executors ────────────────────────────────────────────────────────────────────────
def _exec_distribution(led, o) -> int:
    """Scriptable: a distribution packet's flips are KM's manual KDP toggles; the bell advances the
    CHANNEL_TRACKER for the dispatched books and closes the obligation with a receipt."""
    if not _close_or_residue(led, o, "E2: distribution packet executed by the bell — CHANNEL_TRACKER reflects "
                                     "the dispatched state; pre-order titles flip at-live."):
        return 1
    print(f"  executed distribution: {o['id']}")
    return 0


def _exec_distribution_launch(led, o) -> int:
    """THE LAUNCH BELL (B1, KM 2026-06-23): KM's Accept on a `distribution_launch:<book>` card is the ignition
    that moves the book from gated → live. We fire the scheduler's LIVE dispatch for the book. The constitutional
    launch gate (CONSTITUTION §2 Propose→Approve→Execute) re-checks inside dispatch(): launch_approval() requires
    THIS obligation approved=True (Accept set it), so the post proceeds; absent approval it still fails CLOSED and
    posts nothing. On a clean dispatch we close with an E2 receipt naming the dispatched channels."""
    ref = o.get("ref") or ""
    book_id = ref.split(":", 1)[1] if ":" in ref else ""
    if not book_id:
        return _close_or_residue(led, o, "E2: distribution_launch packet had no book_id in ref — no-op") and 0 or 1
    try:
        sys.path.insert(0, str(REPO / "scripts" / "dist_scheduler"))
        from scheduler import dispatch  # noqa: PLC0415
        res = dispatch(book_id, dry_run=False)  # gate re-checked inside; returns {refused:True} if not approved
    except Exception as e:  # noqa: BLE001 — dispatch failure must be loud, never close green
        _handshake("tiger", "tiger", ref, f"launch dispatch error for {book_id}: {e}", status="apply_close_failed")
        print(f"  launch dispatch error for {book_id}: {e}")
        return 1
    # CONSTITUTIONAL GATE refusal is SIGNALLED in the return dict ({refused:True}), not raised — check it FIRST,
    # before mode (a refusal carries mode="live" too). Audit HIGH [491] 2026-06-24: the old PermissionError branch
    # was dead (dispatch never raises it) and the chans line below called .keys() on `results`, which is a LIST.
    if res.get("refused"):  # gate not cleared (launch obligation absent/unapproved) — never a silent green
        reason = res.get("reason", "gate refused")
        _handshake("tiger", "tiger", ref, f"launch REFUSED by gate for {book_id}: {reason}",
                   status="blocked_unapproved")
        print(f"  launch refused (gate) for {book_id}: {reason}")
        return 1
    mode = res.get("mode", "?")
    if mode != "live":  # gate held it to dry_run — do NOT close as launched
        _handshake("tiger", "tiger", ref, f"launch held to {mode} for {book_id} (gate not cleared)",
                   status="blocked_unapproved")
        print(f"  launch held to {mode} for {book_id} — not closing as live")
        return 1
    # dispatch() returns results as a LIST of {channel, ok, live, ...} dicts — name the dispatched channels.
    chans = ",".join(sorted(r.get("channel", "?") for r in (res.get("results") or []))) or "none"
    if not _close_or_residue(led, o, f"E2: LIVE dispatch fired for {book_id} via the launch bell — channels: "
                                     f"{chans}; CHANNEL_TRACKER advanced gated→dispatched→live (approved_by="
                                     f"{res.get('approved_by')})"):
        return 1
    print(f"  LAUNCHED {book_id} live → channels: {chans}")
    return 0


def _exec_status_confirm(led, o) -> int:
    """Scriptable: status/confirm packets (e.g. b12 republish, editorial format-approval) — the work is
    already staged; the bell records the receipt + closes."""
    if not _close_or_residue(led, o, f"E2: bell confirmed + closed — {(o.get('title') or '')[:80]}"):
        return 1
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
    "distribution_launch": _exec_distribution_launch,
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
    # Fail-fast defense-in-depth (audit 2026-06-16 #4b-ii): the material breath-gate is enforced downstream
    # at ledger.close() (PermissionError), but refuse a material+unapproved packet HERE too so it never even
    # enters a packet-class handler. Non-material packets (the scriptable classes) are unaffected.
    if o.get("material") and not led._is_approved(oid):
        _handshake("tiger", "tiger", o.get("ref") or "",
                   f"execute refused — material + unapproved (breath-gate not cleared): {(o.get('title') or '')[:60]}",
                   status="blocked_unapproved")
        print(f"  REFUSED {oid} — material obligation has not cleared the breath-gate")
        return 1
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
    entries = list(led.iter_entries())   # public read-gateway (audit 2026-06-13c #15)
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
