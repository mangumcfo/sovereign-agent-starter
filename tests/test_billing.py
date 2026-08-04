"""Billing invariants — co-extrusion for s5_15 (Revenue & Order-to-Cash).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves an invoice is
value-conserving (lines sum to subtotal, total = subtotal + tax) and AR aging is a projection whose buckets sum to the
total receivable."""
from decimal import Decimal
import pytest
from sovereign_agent.revenue import invoice, ar_aging, BillingError


def test_invoice_conserves_value():
    inv = invoice([{"description": "widget", "quantity": "10", "unit_price": "9.99"},
                   {"description": "setup", "quantity": "1", "unit_price": "50"}], tax="14.99")
    assert inv["subtotal"] == Decimal("149.90")                 # 99.90 + 50.00
    assert inv["total"] == inv["subtotal"] + inv["tax"]          # total = subtotal + tax
    assert sum((l["amount"] for l in inv["lines"]), Decimal("0")) == inv["subtotal"]   # lines sum to subtotal


def test_invoice_refuses_bad_lines():
    with pytest.raises(BillingError):
        invoice([{"description": "x", "quantity": "0", "unit_price": "5"}])   # non-positive quantity
    with pytest.raises(BillingError):
        invoice([{"description": "x", "quantity": "1", "unit_price": "5"}], tax="-1")   # negative tax


def test_ar_aging_is_a_projection_that_balances():
    invs = [
        {"amount": "100", "issued_day": 100},   # age 20 -> current
        {"amount": "200", "issued_day": 60},    # age 60 -> 31_60
        {"amount": "300", "issued_day": 10},    # age 110 -> over_90
        {"amount": "999", "issued_day": 5, "paid": True},   # paid -> excluded
    ]
    ag = ar_aging(invs, as_of_day=120)
    assert ag["total_receivable"] == Decimal("600.00")          # paid invoice excluded
    assert ag["buckets"]["current"] == Decimal("100.00")
    assert ag["buckets"]["over_90"] == Decimal("300.00")
    assert ag["balances"] is True                               # buckets sum to total
