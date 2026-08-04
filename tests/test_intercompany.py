"""Intercompany invariants — co-extrusion for s5_18 (Multi-Entity & Consolidation).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves an intercompany
transaction is a matched pair across two entity ledgers whose intercompany accounts net to zero at the group -- and
that a one-sided/self-dealing entry is refused."""
from decimal import Decimal

import pytest

from sovereign_agent.consolidation import record_intercompany, intercompany_accounts, IntercompanyError
from sovereign_agent.financials import trial_balance


def test_intercompany_pair_is_balanced_and_nets_to_zero_at_group():
    rec = record_intercompany("IC1", "Sub60", "Parent", "100.00",
                              seller_account="revenue", buyer_account="expense")
    # each side is a balanced posting
    assert rec["entries"]["Sub60"]["balanced"] and rec["entries"]["Parent"]["balanced"]
    # the two intercompany accounts, summed across both ledgers, net to zero
    combined = trial_balance([rec["entries"]["Sub60"], rec["entries"]["Parent"]])
    ic = intercompany_accounts([rec])
    assert sum((combined[a] for a in ic), Decimal("0")) == Decimal("0")
    assert combined["IC_receivable:Parent"] == Decimal("100.00")   # seller booked a receivable
    assert combined["IC_payable:Sub60"] == Decimal("-100.00")      # buyer booked a payable


def test_intercompany_refuses_bad_input():
    with pytest.raises(IntercompanyError):
        record_intercompany("IC2", "A", "A", "10", "revenue", "expense")   # self-dealing
    with pytest.raises(IntercompanyError):
        record_intercompany("IC3", "A", "B", "0", "revenue", "expense")    # non-positive
