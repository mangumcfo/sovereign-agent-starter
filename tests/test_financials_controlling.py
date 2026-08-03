"""Controlling-floor invariants — co-extrusion for s5_40 Sovereign Controlling & Financial Close.

Pure arithmetic: NO sealed crypto substrate, so this runs green in a pure public clone (no skip). It proves the
controlling floor over governed postings — a validated Chart of Accounts hierarchy, value-conserving roll-up, and
cost-pool allocation across centers conserving value exactly — independently of the immutability/governance the
ObligationLedger supplies. The dimension-modeling and driver-model engines are designed-toward (not tested here)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    validate_coa, roll_up_accounts, allocate_cost_pool, roll_up_center_costs, CoAError,
)

# A small chart: two roots (Assets, Expenses); Expenses has two leaf children.
COA = {
    "1000-Assets": {"type": "asset", "parent": None},
    "5000-Expenses": {"type": "expense", "parent": None},
    "5100-COGS": {"type": "expense", "parent": "5000-Expenses"},
    "5200-Opex": {"type": "expense", "parent": "5000-Expenses"},
}


def test_validate_coa_accepts_a_well_formed_hierarchy():
    validate_coa(COA)  # no raise


def test_validate_coa_rejects_missing_parent():
    bad = {"5100-COGS": {"type": "expense", "parent": "9999-Ghost"}}
    with pytest.raises(CoAError):
        validate_coa(bad)


def test_validate_coa_rejects_a_cycle():
    cyclic = {
        "A": {"parent": "B"},
        "B": {"parent": "A"},
    }
    with pytest.raises(CoAError):
        validate_coa(cyclic)


def test_validate_coa_rejects_empty():
    with pytest.raises(CoAError):
        validate_coa({})


def test_roll_up_accounts_conserves_value_to_the_roots():
    balances = {"5100-COGS": "300.00", "5200-Opex": "150.00", "1000-Assets": "900.00"}
    rolled = roll_up_accounts(balances, COA)
    # parent = sum of children
    assert rolled["5000-Expenses"] == Decimal("450.00")
    assert rolled["5100-COGS"] == Decimal("300.00")
    assert rolled["1000-Assets"] == Decimal("900.00")
    # value conservation: sum over ROOT accounts == sum of supplied leaf balances
    roots = [a for a, m in COA.items() if m.get("parent") is None]
    assert sum((rolled[r] for r in roots), Decimal("0")) == Decimal("1350.00")


def test_roll_up_rejects_balance_for_unknown_account():
    with pytest.raises(CoAError):
        roll_up_accounts({"7777-Nope": "10"}, COA)


def test_allocate_cost_pool_conserves_the_pool_exactly():
    alloc = allocate_cost_pool("1000.00", {"CC-Weld": 1, "CC-Paint": 1, "CC-Assembly": 1})
    # value-conserving: the three allocations sum to the pool to the cent (largest-remainder places the residual)
    assert sum(alloc.values(), Decimal("0")) == Decimal("1000.00")
    # a 3-way split of 1000.00 cannot be equal thirds; residual is placed, nothing invented
    assert set(alloc) == {"CC-Weld", "CC-Paint", "CC-Assembly"}


def test_allocate_cost_pool_respects_weights():
    alloc = allocate_cost_pool("900.00", {"CC-A": 2, "CC-B": 1})
    assert alloc["CC-A"] == Decimal("600.00")
    assert alloc["CC-B"] == Decimal("300.00")


def test_roll_up_center_costs_totals_per_center_and_never_blends_currency():
    totals = roll_up_center_costs([
        {"center": "CC-Weld", "amount": "600.00", "currency": "USD"},
        {"center": "CC-Weld", "amount": "50.00", "currency": "USD"},
        {"center": "CC-Weld", "amount": "40.00", "currency": "EUR"},
        {"center": "CC-Paint", "amount": "300.00", "currency": "USD"},
    ])
    assert totals[("CC-Weld", "USD")] == Decimal("650.00")
    assert totals[("CC-Weld", "EUR")] == Decimal("40.00")  # distinct — never merged into USD
    assert totals[("CC-Paint", "USD")] == Decimal("300.00")
