"""Supplier registry + composed scoring invariants — co-extrusion for s5_16 (Procurement-to-Pay).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the supplier lifecycle
is fail-closed (no illegal transition), scoring is transparent (carries the per-criterion breakdown from the composed
decision-support surface), and award is fail-closed on qualification (an unqualified supplier is refused at award even
when its raw scorecard is highest)."""
from decimal import Decimal
import pytest
from sovereign_agent.procurement import register, transition, score_suppliers, award, SupplierError

WEIGHTS = {"quality": "0.5", "on_time": "0.3", "price": "0.2"}


def _qualified(sid, name, sc):
    s = register(sid, name, scorecard=sc)
    s, _ = transition(s, "qualified")
    return s


def test_lifecycle_is_fail_closed():
    s = register("SUP-1", "Ridgeline Steel", scorecard={"quality": "9"})
    assert s["status"] == "prospective"
    with pytest.raises(SupplierError):
        transition(s, "active")                     # cannot activate a supplier that was never qualified
    s2, ev = transition(s, "qualified")
    assert s2["status"] == "qualified" and s["status"] == "prospective"   # input not mutated
    assert ev["from"] == "prospective" and ev["to"] == "qualified"


def test_scoring_is_transparent():
    sups = [_qualified("A", "A", {"quality": "9", "on_time": "8", "price": "7"}),
            _qualified("B", "B", {"quality": "7", "on_time": "9", "price": "9"})]
    ranked = score_suppliers(sups, WEIGHTS)
    assert ranked[0]["id"] == "A"                   # A 9*.5+8*.3+7*.2 = 8.3 > B 7*.5+9*.3+9*.2 = 8.0
    top = ranked[0]
    assert "breakdown" in top and "weights" in top  # score is never silent
    assert sum(top["breakdown"].values()) == top["score"]


def test_award_is_fail_closed_on_qualification():
    # The highest raw scorecard belongs to an UNqualified (prospective) supplier; it must not be awarded.
    hot = register("HOT", "Unvetted Superbid", scorecard={"quality": "10", "on_time": "10", "price": "10"})
    ok = _qualified("OK", "Vetted Vendor", {"quality": "8", "on_time": "8", "price": "8"})
    rec = award([hot, ok], WEIGHTS)
    assert rec["recommended"] == "OK"               # unqualified top-scorer excluded, qualified vendor wins
    assert rec["eligible_ids"] == ["OK"]


def test_award_refused_when_none_eligible():
    only_prospective = [register("P1", "P1", scorecard={"quality": "9", "on_time": "9", "price": "9"})]
    with pytest.raises(SupplierError):
        award(only_prospective, WEIGHTS)            # no qualified/active supplier -> refused
