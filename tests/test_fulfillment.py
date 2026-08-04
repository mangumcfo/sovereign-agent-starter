"""Sales-order fulfillment invariants — co-extrusion for s5_20 (Distribution & Wholesale, second vertical).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the governed sales
order is fail-closed against real stock (an allocation that would overdraw governed on-hand is refused -- no phantom
fulfillment), value-conserving (invoice lines conserve to the shipped quantities; the sale posting balances), and
fail-closed on the lifecycle and the credit gate; and that the sale posts to the sealed general ledger in the canonical
posting shape via financials.posting.from_entry (spine step S3 order->invoice -> S5 one ledger)."""
from decimal import Decimal
import pytest
from sovereign_agent.distribution import (
    open_sales_order, transition, allocate, credit_check, invoice_shipment, sale_posting, FulfillmentError,
)
from sovereign_agent.financials import from_entry, trial_balance

# governed on-hand: 100 widget + 40 gadget at warehouse W1
MOVES = [{"item": "widget", "location": "W1", "qty": "100"}, {"item": "gadget", "location": "W1", "qty": "40"}]
LINES = [{"item": "widget", "quantity": "20", "unit_price": "9.99"},
         {"item": "gadget", "quantity": "5", "unit_price": "50"}]


def _open():
    return open_sales_order("SO-1", "Ridgeline", LINES, location="W1")


def test_allocate_ship_invoice_conserves_value():
    o = _open()
    o = allocate(o, MOVES)                                  # within on-hand
    assert o["status"] == "allocated" and o["allocated"] == {"widget": Decimal("20"), "gadget": Decimal("5")}
    o, _ = transition(o, "shipped")
    inv = invoice_shipment(o, tax="14.99")
    # invoice lines conserve to the shipped (allocated) quantities
    assert sum((l["amount"] for l in inv["lines"]), Decimal("0")) == inv["subtotal"]   # 20*9.99 + 5*50 = 449.80
    assert inv["subtotal"] == Decimal("449.80")
    assert inv["total"] == inv["subtotal"] + inv["tax"]


def test_allocation_fail_closed_no_phantom_stock():
    over = open_sales_order("SO-2", "Ridgeline", [{"item": "gadget", "quantity": "41", "unit_price": "50"}], location="W1")
    with pytest.raises(FulfillmentError):
        allocate(over, MOVES)                              # 41 > 40 on-hand -> would overdraw -> refused


def test_ship_before_allocation_refused():
    o = _open()
    with pytest.raises(FulfillmentError):
        transition(o, "shipped")                           # open -> shipped is not an allowed edge (must allocate first)


def test_credit_gate_fail_closed():
    o = allocate(_open(), MOVES)                           # subtotal 449.80
    with pytest.raises(Exception):                          # composes revenue.credit.check_order (raises CreditError)
        credit_check(o, credit_limit="1000", outstanding="700")   # 700 + 449.80 = 1149.80 > 1000 -> refused
    ok = credit_check(o, credit_limit="1000", outstanding="500")  # 949.80 <= 1000 -> approved
    assert ok["approved"] is True


def test_invoice_only_a_shipped_order():
    o = allocate(_open(), MOVES)                           # allocated, not shipped
    with pytest.raises(FulfillmentError):
        invoice_shipment(o)


def test_sale_posts_balanced_to_sealed_ledger():
    o, _ = transition(allocate(_open(), MOVES), "shipped")
    entry = sale_posting(o, tax="14.99")
    assert entry["balanced"] is True                        # AR debit == revenue + tax credits
    assert entry["amount"] == Decimal("464.79")             # 449.80 + 14.99
    posting = from_entry(entry)                             # posting-shape composes the sealed ledger (spine S5)
    assert posting["balanced"] is True
    assert sum(trial_balance([posting]).values(), Decimal("0")) == Decimal("0")   # nets to zero
