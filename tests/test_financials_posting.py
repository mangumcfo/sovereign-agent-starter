"""Double-entry posting + cost allocation invariants — co-extrusion for s5_07 Sovereign Financials.

Pure arithmetic: NO sealed crypto substrate, so this runs green in a pure public clone (no skip). It proves the
financial-accounting truths a governed ledger posting must satisfy — debits==credits fail-closed, a trial balance
that nets to zero, and value-conserving cost allocation — independently of the immutability/attestation the
ObligationLedger supplies."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    Line, UnbalancedPostingError, AllocationError, post, trial_balance, allocate,
)


def test_balanced_posting_accepted():
    p = post([Line.dr("1000-Cash", "100.00"), Line.cr("4000-Revenue", "100.00")], memo="sale")
    assert p["balanced"] is True
    assert p["amount"] == "100.00"


def test_unbalanced_posting_refused_fail_closed():
    with pytest.raises(UnbalancedPostingError):
        post([Line.dr("1000-Cash", "100.00"), Line.cr("4000-Revenue", "90.00")])


def test_line_cannot_carry_both_sides():
    with pytest.raises(UnbalancedPostingError):
        post([Line("1000-Cash", debit=Decimal("50"), credit=Decimal("50")),
              Line.cr("4000-Revenue", "0")])


def test_empty_posting_refused():
    with pytest.raises(UnbalancedPostingError):
        post([])


def test_trial_balance_nets_to_zero():
    ps = [
        post([Line.dr("1000-Cash", "100"), Line.cr("4000-Revenue", "100")]),
        post([Line.dr("5000-COGS", "60"), Line.cr("1300-Inventory", "60")]),
    ]
    tb = trial_balance(ps)
    assert tb["1000-Cash"] == Decimal("100")
    assert tb["4000-Revenue"] == Decimal("-100")
    assert sum(tb.values(), Decimal("0")) == Decimal("0")   # the trial balance balances, by construction


def test_allocation_conserves_the_pool_with_rounding():
    # 100.00 across 3:3:1 does not divide evenly to cents — the residual must be placed, not lost.
    alloc = allocate("100.00", {"CC-A": 3, "CC-B": 3, "CC-C": 1})
    assert sum(alloc.values(), Decimal("0")) == Decimal("100.00")
    assert all(v >= 0 for v in alloc.values())


def test_allocation_rejects_bad_weights():
    with pytest.raises(AllocationError):
        allocate("100", {})
    with pytest.raises(AllocationError):
        allocate("100", {"CC-A": 0, "CC-B": 0})
    with pytest.raises(AllocationError):
        allocate("100", {"CC-A": -1, "CC-B": 2})
