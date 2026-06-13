"""Open Card Parity harness — the invariant that kills the whole "view out-truthing the ledger" class.

Audit 2026-06-13 (GB [279]/[280]): the single-resolver + by_owner-from-replay fixes are INSTANCES of a
class. This harness is the INVARIANT: every read view of the obligation chain must agree with the
order-aware `replay()` ground truth. No view may report a card CLOSED that replay says is OPEN (or
vice-versa). That is the exact disease behind KM's 42 dropped comments — a projection out-truthing the
hash chain, silently hiding live work.

Ground truth = `ObligationLedger.replay()` (reopen-aware: the last credit/reopen per id governs).
Checked views:
  1. by_status()        — open/closed/total counts match replay.
  2. by_owner()         — per-owner sums match replay; no negative counts.
  3. open_obligations() — id set equals replay's open set.
  4. _is_closed(id)     — per-id verdict matches replay membership (the reopen-aware core).
  5. sittings project   — no replay-OPEN feedback/finding card is HIDDEN from the sittings projection
                          (the 42-card disease was live work hidden by a view). NB: sittings
                          deliberately OVER-surfaces closed-without-disposition cards as its anti-hiding
                          design, so over-surfacing is not a breach — only HIDING an open card is.

Usage:
  PYTHONPATH=src python3 scripts/open_card_parity.py [ledger_root]   # default: canonical node root
Exit 0 = parity holds; exit 1 = one or more breaches (printed). Designed to run on the LIVE chain.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sovereign_agent.obligations.ledger import ObligationLedger, get_ledger_root  # noqa: E402

# The Atrium sittings predicate (kept in lockstep with scripts/atrium_sittings.py:project()).
_SITTINGS_KEYWORDS = ("pdf edit", "feedback", "renderability", "board finding", "review brief")


def _sittings_would_surface(rows: list[dict]) -> set:
    """The id set the sittings projection WOULD surface as awaiting work. Mirrors project()'s predicate:
    a debit whose title matches a feedback/finding keyword AND whose raw `approved` flag is False.
    Sittings deliberately keys off `approved` (not the closed flag) so closed-without-disposition cards
    resurface — its anti-hiding design. The parity invariant we assert is one-directional: this set must
    never MISS a replay-open card (live work must never hide)."""
    return {o.get("id") for o in rows
            if o.get("type") == "debit"
            and any(k in str(o.get("title", "")).lower() for k in _SITTINGS_KEYWORDS)
            and not o.get("approved")}


def check_parity(root, led=None) -> dict:
    """Return {ok, violations[], summary, root}. ok=False iff any view disagrees with replay.
    `led` may be injected (tests) to exercise the detector against a deliberately-broken view."""
    led = led if led is not None else ObligationLedger(root=str(root))
    st = led.replay()
    truth_open = {o["id"] for o in st["open"]}
    truth_closed = {o["id"] for o in st["closed"]}
    all_ids = {o["id"] for o in st["all"]}
    violations: list[str] = []

    # 1. by_status
    bs = led.by_status()
    if bs.get("open") != len(truth_open):
        violations.append(f"by_status.open={bs.get('open')} != replay.open={len(truth_open)}")
    if bs.get("closed") != len(truth_closed):
        violations.append(f"by_status.closed={bs.get('closed')} != replay.closed={len(truth_closed)}")
    if bs.get("total") != len(all_ids):
        violations.append(f"by_status.total={bs.get('total')} != replay.total={len(all_ids)}")

    # 2. by_owner
    bo = led.by_owner()
    open_sum = sum(v["open"] for v in bo.values())
    closed_sum = sum(v["closed"] for v in bo.values())
    if open_sum != len(truth_open):
        violations.append(f"by_owner open-sum={open_sum} != replay.open={len(truth_open)}")
    if closed_sum != len(truth_closed):
        violations.append(f"by_owner closed-sum={closed_sum} != replay.closed={len(truth_closed)}")
    for owner, v in bo.items():
        if v["open"] < 0 or v["closed"] < 0:
            violations.append(f"by_owner[{owner}] has a NEGATIVE count: {v} (the reopen double-count bug)")

    # 3. open_obligations()
    oo = {o["id"] for o in led.open_obligations()}
    if oo != truth_open:
        only_view = sorted(oo - truth_open)[:5]
        only_truth = sorted(truth_open - oo)[:5]
        violations.append(f"open_obligations() != replay.open (view-only={only_view}, truth-only={only_truth})")

    # 4. _is_closed(id) per-id (the reopen-aware core: a card closed-in-view but open-in-truth is THE disease)
    for oid in all_ids:
        closed_view = led._is_closed(oid)
        if closed_view and oid in truth_open:
            violations.append(f"PARITY BREACH: {oid} is CLOSED per _is_closed but OPEN in replay")
        if (not closed_view) and oid in truth_closed:
            violations.append(f"PARITY BREACH: {oid} is OPEN per _is_closed but CLOSED in replay")

    # 5. sittings anti-hiding: no replay-OPEN feedback/finding card may be MISSING from what sittings
    #    surfaces (the 42-card disease was live work HIDDEN). Over-surfacing closed cards is by design.
    surfaced = _sittings_would_surface(led._entries())
    # open AND not-yet-disposed (replay-corrected approved) + keyword = what sittings MUST show.
    # An open-but-approved card is awaiting execution, not KM — correctly not surfaced.
    open_feedback = {o["id"] for o in st["open"]
                     if not o.get("approved")
                     and any(k in str(o.get("title", "")).lower() for k in _SITTINGS_KEYWORDS)}
    hidden = open_feedback - surfaced
    if hidden:
        violations.append(f"SITTINGS BREACH: {len(hidden)} OPEN feedback card(s) HIDDEN from sittings "
                          f"(e.g. {sorted(hidden)[:5]}) — live work a view would silently drop")

    return {"ok": not violations, "violations": violations,
            "summary": {"open": len(truth_open), "closed": len(truth_closed), "total": len(all_ids)},
            "root": str(led.root)}


def main() -> int:
    cli = sys.argv[1] if len(sys.argv) > 1 else None
    root = get_ledger_root(explicit=cli)
    result = check_parity(root)
    print(json.dumps(result, indent=2))
    if result["ok"]:
        print(f"∞Δ∞ PARITY HOLDS — {result['summary']} @ {result['root']}")
        return 0
    print(f"✗ PARITY BREACHED — {len(result['violations'])} violation(s) @ {result['root']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
