"""Three-way match invariants — co-extrusion for s5_16 (Procurement-to-Pay).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the three-way match is
fail-closed (un-ordered goods, goods not received, over-billed quantity, price above the PO are all refused) and the
authorized payable is value-conserving (decomposes exactly into per-line billed-quantity-at-agreed-price amounts, and
posts to AP with debits equal to credits)."""
from decimal import Decimal
import pytest
from sovereign_agent.procurement import three_way_match, ap_entry, MatchError

PO = {"po_id": "PO-1", "lines": [
    {"item": "steel-rod", "quantity": "100", "unit_price": "4.50"},
    {"item": "flux", "quantity": "10", "unit_price": "12.00"},
]}
GR = {"lines": [{"item": "steel-rod", "quantity": "100"}, {"item": "flux", "quantity": "10"}]}
INV = {"invoice_id": "INV-1", "lines": [
    {"item": "steel-rod", "quantity": "100", "unit_price": "4.50"},
    {"item": "flux", "quantity": "10", "unit_price": "12.00"},
]}


def test_clean_match_conserves_value():
    m = three_way_match(PO, GR, INV)
    assert m["matched"] is True
    assert m["payable"] == Decimal("570.00")                                  # 100*4.50 + 10*12.00
    assert sum((l["amount"] for l in m["lines"]), Decimal("0")) == m["payable"]  # decomposes exactly
    assert m["conserves"] is True


def test_matched_payable_posts_balanced_to_ap():
    entry = ap_entry(three_way_match(PO, GR, INV))
    assert entry["amount"] == Decimal("570.00")
    assert entry["balanced"] is True                                          # debits == credits
    assert sum((e["amount"] for e in entry["debits"]), Decimal("0")) == \
           sum((e["amount"] for e in entry["credits"]), Decimal("0"))


def test_refuses_billing_for_goods_not_received():
    gr_short = {"lines": [{"item": "steel-rod", "quantity": "60"}, {"item": "flux", "quantity": "10"}]}
    with pytest.raises(MatchError):
        three_way_match(PO, gr_short, INV)                                    # billed 100 > received 60


def test_refuses_price_above_po():
    inv_hi = {"invoice_id": "INV-2", "lines": [
        {"item": "steel-rod", "quantity": "100", "unit_price": "5.00"},       # PO price 4.50
        {"item": "flux", "quantity": "10", "unit_price": "12.00"}]}
    with pytest.raises(MatchError):
        three_way_match(PO, GR, inv_hi)


def test_refuses_unordered_goods():
    inv_extra = {"invoice_id": "INV-3", "lines": [{"item": "gold-bar", "quantity": "1", "unit_price": "1000"}]}
    with pytest.raises(MatchError):
        three_way_match(PO, GR, inv_extra)                                    # not on the PO


def test_tolerance_admits_small_variance_at_po_price():
    inv_tol = {"invoice_id": "INV-4", "lines": [
        {"item": "steel-rod", "quantity": "101", "unit_price": "4.50"},       # 1 over, within qty tol
        {"item": "flux", "quantity": "10", "unit_price": "12.05"}]}           # 0.05 over, within price tol
    gr_tol = {"lines": [{"item": "steel-rod", "quantity": "101"}, {"item": "flux", "quantity": "10"}]}
    m = three_way_match(PO, gr_tol, inv_tol, qty_tolerance="1", price_tolerance="0.10")
    assert m["payable"] == Decimal("574.50")                                  # 101*4.50 + 10*12.00 (agreed price governs)
    assert m["conserves"] is True                                            # billed at the AGREED price, not the invoice price
