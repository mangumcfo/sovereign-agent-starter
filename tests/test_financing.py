"""Financing-structure invariants — co-extrusion for s5_41 (Option B).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves a financing structure
as a governed object -- a positive commitment, drawdown refused past the commitment, outstanding = drawn - repaid,
available = commitment - outstanding. Bank/lender execution is external (S6-V07), not tested here."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import new_facility, outstanding, draw, available, FinancingError


def test_new_facility_requires_positive_commitment():
    f = new_facility("RC-1", "5000000", "USD", kind="revolver")
    assert f["commitment"] == Decimal("5000000") and f["currency"] == "USD"
    with pytest.raises(FinancingError):
        new_facility("BAD", "0", "USD")


def test_outstanding_is_drawn_minus_repaid():
    f = new_facility("RC-1", "5000000", "USD")
    mv = [
        {"facility": "RC-1", "type": "draw", "amount": "2000000"},
        {"facility": "RC-1", "type": "repay", "amount": "500000"},
        {"facility": "OTHER", "type": "draw", "amount": "999"},  # ignored
    ]
    assert outstanding(f, mv) == Decimal("1500000")
    assert available(f, mv) == Decimal("3500000")


def test_draw_within_commitment_is_allowed():
    f = new_facility("RC-1", "5000000", "USD")
    mv = [{"facility": "RC-1", "type": "draw", "amount": "2000000"}]
    d = draw(f, "1000000", mv)
    assert d == {"facility": "RC-1", "type": "draw", "amount": Decimal("1000000"), "currency": "USD"}


def test_draw_past_commitment_is_refused():
    f = new_facility("RC-1", "5000000", "USD")
    mv = [{"facility": "RC-1", "type": "draw", "amount": "4500000"}]
    with pytest.raises(FinancingError):
        draw(f, "1000000", mv)  # 4.5M + 1M > 5M commitment


def test_unknown_movement_type_is_refused():
    f = new_facility("RC-1", "5000000", "USD")
    with pytest.raises(FinancingError):
        outstanding(f, [{"facility": "RC-1", "type": "gift", "amount": "1"}])
