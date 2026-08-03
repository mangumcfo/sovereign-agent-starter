"""Planning invariants — co-extrusion for s5_17 (discharges planning/scheduling/optimization->S5-V17 debts).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the transparent
planning trio -- net requirements (demand - on-hand, floored), a deterministic capacity schedule ordered by due then
priority, and a fill-first priority allocation of a scarce supply, value-conserving."""
from decimal import Decimal

import pytest

from sovereign_agent.analytics import net_requirements, schedule, allocate_by_priority, PlanningError


def test_net_requirements_floors_at_zero():
    net = net_requirements({"A": "100", "B": "40"}, {"A": "30", "B": "60"})
    assert net["A"] == Decimal("70")   # 100 - 30
    assert net["B"] == Decimal("0")    # 40 - 60 -> floored, no negative requirement


def test_net_requirements_refuses_negative_inputs():
    with pytest.raises(PlanningError):
        net_requirements({"A": "-5"}, {"A": "0"})


def test_schedule_packs_by_capacity_ordered_by_due():
    jobs = [
        {"id": "late", "units": "4", "due": 3},
        {"id": "early", "units": "4", "due": 1},
        {"id": "mid", "units": "4", "due": 2},
    ]
    s = schedule(jobs, capacity_per_period="6")
    # ordered early(1), mid(2), late(3); cap 6 -> period0=[early(4)], mid(4) doesn't fit -> period1, late -> period1? 4+4>6 -> period2
    assert s["job_order"] == ["early", "mid", "late"]
    assert s["periods"][0] == ["early"]
    # each period respects capacity
    assert all(u <= Decimal("6") for u in s["used_per_period"])


def test_schedule_refuses_oversized_job():
    with pytest.raises(PlanningError):
        schedule([{"id": "huge", "units": "10", "due": 1}], capacity_per_period="6")


def test_allocate_by_priority_fills_in_order_and_conserves():
    r = allocate_by_priority("100", [
        {"id": "hi", "qty": "60"},
        {"id": "mid", "qty": "50"},
        {"id": "lo", "qty": "30"},
    ])
    assert r["allocated"]["hi"] == Decimal("60")
    assert r["allocated"]["mid"] == Decimal("40")   # only 40 left after hi
    assert r["allocated"]["lo"] == Decimal("0")
    assert r["unmet"]["mid"] == Decimal("10") and r["unmet"]["lo"] == Decimal("30")
    # value-conserving: allocated + leftover == supply
    assert sum(r["allocated"].values(), Decimal("0")) + r["leftover"] == Decimal("100")
