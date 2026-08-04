"""Credit invariants — co-extrusion for s5_15 (Revenue & Order-to-Cash).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the credit-limit check
is fail-closed -- an order that would breach the limit is refused, not passed with a flag."""
from decimal import Decimal
import pytest
from sovereign_agent.revenue import check_order, available_credit, CreditError


def test_order_within_limit_approved():
    r = check_order(credit_limit="10000", outstanding="6000", order_amount="3000")
    assert r["approved"] is True and r["new_exposure"] == Decimal("9000")
    assert available_credit("10000", "6000") == Decimal("4000")


def test_order_over_limit_refused_fail_closed():
    with pytest.raises(CreditError):
        check_order(credit_limit="10000", outstanding="8000", order_amount="3000")   # 11000 > 10000
    with pytest.raises(CreditError):
        check_order(credit_limit="10000", outstanding="0", order_amount="0")         # non-positive order
