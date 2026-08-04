"""Regulated traceability invariants — co-extrusion for s5_24 (Regulated Industries, order-A vertical 5/5).

Pure/structural: composes the sealed merkle accumulator (whose own tests are green in a pure public clone). Proves the
chain of custody is value-conserving (received == held + consumed, and no holder is ever driven negative -- no phantom
custody), that provenance anchors the ORDERED custody events to a merkle root (a reordered or altered chain -> a
different root), and that release is fail-closed on BOTH gates (a broken chain OR a failed quality gate refuses release),
with recall always available as a fork once shipped."""
from decimal import Decimal
import pytest
from sovereign_agent.regulated import (
    open_lot, receipt, transfer, consume, reconcile_custody, assert_custody, trace_root,
    lot_transition, release, TraceabilityError,
)

# A clean batch: 100 received at the warehouse, 40 moved to the line, 30 consumed into product.
CLEAN = [
    receipt("LOT-1", "API-X", 100, "WH"),
    transfer("LOT-1", 40, "WH", "LINE"),
    consume("LOT-1", 30, "LINE", "built into FG-1"),
]


def test_clean_chain_reconciles_and_conserves():
    rep = reconcile_custody(CLEAN)
    assert rep["reconciled"] is True
    assert rep["received_total"] == Decimal("100")
    assert rep["held_total"] == Decimal("70") and rep["consumed_total"] == Decimal("30")  # 100 == 70 + 30
    assert rep["held"] == {"WH": Decimal("60"), "LINE": Decimal("10")}
    assert rep["breaks"] == []


def test_custody_break_refused():
    # A transfer of 50 from a holder that only holds 40 -> phantom custody (LINE driven negative).
    leaky = [
        receipt("LOT-2", "API-X", 100, "WH"),
        transfer("LOT-2", 40, "WH", "LINE"),
        transfer("LOT-2", 50, "LINE", "SHIP"),        # LINE holds 40, moves 50 -> break
    ]
    rep = reconcile_custody(leaky)
    assert rep["reconciled"] is False
    assert any(b["holder"] == "LINE" and b["kind"] == "transfer" for b in rep["breaks"])
    with pytest.raises(TraceabilityError):
        assert_custody(leaky)


def test_trace_root_orders_and_distinguishes_chains():
    r1 = trace_root(CLEAN)
    assert r1                                                    # non-empty root for a non-empty chain
    reordered = [CLEAN[0], CLEAN[2], CLEAN[1]]                   # custody order is history ...
    assert trace_root(reordered) != r1                          # ... so a reordered chain -> a different root
    altered = [receipt("LOT-1", "API-X", 999, "WH"), CLEAN[1], CLEAN[2]]
    assert trace_root(altered) != r1                            # any altered event -> a different root


def test_release_fail_closed_on_quality():
    lot = open_lot("LOT-3", "API-X", 100, "WH")
    lot, _ = lot_transition(lot, "in_custody")
    events = [receipt("LOT-3", "API-X", 100, "WH")]             # chain reconciles ...
    with pytest.raises(TraceabilityError):
        release(lot, events, quality_passed=False)             # ... but quality gate failed -> release refused
    done = release(lot, events, quality_passed=True)
    assert done["status"] == "released" and done["trace_root"] == trace_root(events)


def test_release_fail_closed_on_broken_chain():
    lot = open_lot("LOT-4", "API-X", 100, "WH")
    lot, _ = lot_transition(lot, "in_custody")
    broken = [receipt("LOT-4", "API-X", 100, "WH"), consume("LOT-4", 150, "WH", "over-consumed")]  # -> negative
    with pytest.raises(TraceabilityError):
        release(lot, broken, quality_passed=True)              # quality ok, but chain does not reconcile -> refused


def test_lifecycle_fail_closed_and_recall_is_a_fork():
    lot = open_lot("LOT-5", "API-X", 1, "WH")                   # a serial (qty one)
    with pytest.raises(TraceabilityError):
        lot_transition(lot, "shipped")                         # received -> shipped is not an allowed edge
    lot, _ = lot_transition(lot, "in_custody")
    lot = release(lot, [receipt("LOT-5", "API-X", 1, "WH")], quality_passed=True)
    lot, _ = lot_transition(lot, "shipped")
    recalled, ev = lot_transition(lot, "recalled")             # a shipped lot is always recallable -- the fork
    assert recalled["status"] == "recalled" and ev["from"] == "shipped"
    quarantined, qev = lot_transition({"id": "LOT-6", "status": "in_custody"}, "quarantined")
    assert quarantined["status"] == "quarantined"              # non-conformance containable as a fork
