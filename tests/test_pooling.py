"""Situational Supply (s5_38 / reading Vol 40) — pooled demand as formation capital, gated by a human."""
import pytest

from sovereign_agent.pooling import pool_demand, gate_formation, SituationalError

# a pool of member demand commitments (total 105)
C = [{"member": "north-guild", "amount": 40},
     {"member": "river-coop", "amount": 35},
     {"member": "ridge-works", "amount": 30}]


def test_pool_demand_aggregates_and_clears():
    pool = pool_demand(C, minimum=100)
    assert pool["total"] == 105 and pool["clears"] is True and pool["count"] == 3


def test_a_pool_that_does_not_clear_is_honest():
    pool = pool_demand(C, minimum=200)
    assert pool["clears"] is False and pool["total"] == 105


def test_pool_demand_refuses_empty_commitments():
    with pytest.raises(SituationalError, match="at least one"):
        pool_demand([], minimum=100)


def test_gate_formation_forms_on_a_cleared_pool_and_a_named_human():
    pool = pool_demand(C, minimum=100)
    r = gate_formation(pool, approver="pool-steward", approval_ref="pool-vote:2026-08-05")
    assert r["formed"] is True and r["cleared"] is True and r["approver"] == "pool-steward"


def test_gate_formation_refuses_an_uncleared_pool_fail_closed():
    pool = pool_demand(C, minimum=200)  # does not clear
    with pytest.raises(SituationalError, match="does not clear"):
        gate_formation(pool, approver="pool-steward", approval_ref="pool-vote:2026-08-05")


def test_gate_formation_refuses_with_no_named_approver():
    pool = pool_demand(C, minimum=100)
    with pytest.raises(SituationalError, match="named human approver"):
        gate_formation(pool, approver="   ", approval_ref="pool-vote:2026-08-05")


def test_gate_formation_refuses_with_no_approval_reference():
    pool = pool_demand(C, minimum=100)
    with pytest.raises(SituationalError, match="approval reference"):
        gate_formation(pool, approver="pool-steward", approval_ref="")
