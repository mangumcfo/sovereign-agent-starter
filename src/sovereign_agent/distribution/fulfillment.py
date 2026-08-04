"""Fulfillment — a governed sales order composing the sealed inventory, billing, credit, and posting surfaces.

Co-extrusion for s5_20 (Distribution & Wholesale, KM 2026-08-04). Pure / structural, no crypto substrate (F-1
pure-clone-clean). A distributor does not re-implement inventory or invoicing: this vertical composes the sealed
primitives into one governed distribution act -- a sales order that is fail-closed against real stock and value-conserving
into the ledger. A sales order opens against a warehouse location; its allocation is fail-closed against governed on-hand
(a line that would drive stock negative is refused -- no phantom fulfillment, composing supply.inventory); its lifecycle
is fail-closed (open -> allocated -> shipped -> invoiced); its shipment becomes a value-conserving invoice whose lines
conserve to the shipped quantities (composing revenue.billing); the order is gated by the sealed fail-closed credit
check (composing revenue.credit); and the sale posts accounts-receivable against sales revenue as a balanced
{debits, credits} entry that composes the sealed general ledger via financials.posting.from_entry. Human primacy holds:
the order is committed and shipped by governed acts; this module holds the lifecycle and refuses what would break it --
shipping stock that is not there, billing more than shipped, or a sale over the customer's credit."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple, Union

from ..supply.inventory import would_overdraw
from ..revenue.billing import invoice as _invoice
from ..revenue.credit import check_order as _check_order

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")

# Sales-order lifecycle -- fail-closed transitions (added to docs/DOMAIN_VOCAB_CARD.md per spine item 8).
_SO_ALLOWED: Dict[str, set] = {
    "open": {"allocated", "cancelled"},
    "allocated": {"shipped", "cancelled"},
    "shipped": {"invoiced"},
    "invoiced": set(),
    "cancelled": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class FulfillmentError(ValueError):
    """Raised for an illegal lifecycle transition, an allocation that would overdraw governed on-hand (phantom
    fulfillment), a ship before full allocation, or an invoice that would exceed what was shipped -- fail-closed."""


def open_sales_order(order_id: str, customer: str, lines: Sequence[Mapping], location: str) -> Dict[str, object]:
    """Open a sales order at a warehouse `location`. Each line carries an `item`, a `quantity`, and a `unit_price`
    (optional `description`). The order starts `open` with nothing allocated. Refuses a non-positive quantity or price
    -- a line that orders nothing, or at a negative price, is not a governed order line."""
    if not lines:
        raise FulfillmentError("sales order needs at least one line")
    norm: List[Dict] = []
    for ln in lines:
        q, p = _dec(ln["quantity"]), _dec(ln["unit_price"])
        if q <= 0 or p < 0:
            raise FulfillmentError(f"line {ln.get('item')!r}: quantity must be > 0 and price >= 0 (q={q}, p={p})")
        norm.append({"item": ln["item"], "quantity": q, "unit_price": p, "description": ln.get("description", ln["item"])})
    return {"id": order_id, "customer": customer, "location": location, "lines": norm,
            "allocated": {}, "status": "open"}


def transition(order: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move a sales order to `to_status`, fail-closed: the lifecycle must permit the move (you cannot ship an
    unallocated order, or invoice one that never shipped). Returns (new_order, event); the input is not mutated."""
    frm = order.get("status", "open")
    if to_status not in _SO_ALLOWED.get(frm, set()):
        raise FulfillmentError(f"order {order.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                               f"(allowed from {frm!r}: {sorted(_SO_ALLOWED.get(frm, set())) or 'none'})")
    no = dict(order)
    no["status"] = to_status
    return no, {"order": order.get("id"), "from": frm, "to": to_status}


def allocate(order: Mapping, movements: Iterable[Mapping]) -> Dict[str, object]:
    """Allocate the order's lines against governed on-hand at its location, fail-closed: a line whose quantity would
    drive on-hand negative is refused (no phantom fulfillment -- the order cannot allocate stock that is not there;
    composes supply.inventory.would_overdraw). Allocation is all-or-nothing per the whole order: if every line can be
    covered, the order is fully allocated (allocated conserves to what was ordered, and never exceeds on-hand) and moves
    to `allocated`; otherwise it is refused and the caller may backorder. Returns the allocated order; input not
    mutated."""
    if order.get("status") != "open":
        raise FulfillmentError(f"order {order.get('id')!r}: only an open order can be allocated (is {order.get('status')!r})")
    movements = list(movements)
    loc = order["location"]
    allocated: Dict[str, Decimal] = {}
    for ln in order["lines"]:
        item, q = ln["item"], ln["quantity"]
        if would_overdraw(movements, item, loc, q):
            raise FulfillmentError(f"order {order.get('id')!r}: allocating {q} of {item!r} at {loc!r} would overdraw "
                                   "governed on-hand -- refused (no phantom fulfillment; backorder instead)")
        allocated[item] = allocated.get(item, Decimal("0")) + q
    no = dict(order)
    no["allocated"] = allocated
    no["status"] = "allocated"
    return no


def credit_check(order: Mapping, credit_limit: Number, outstanding: Number) -> Dict[str, object]:
    """Gate the order against the customer's governed credit limit, fail-closed, composing the sealed credit surface
    (revenue.credit.check_order). The order amount is its subtotal (allocated quantities at their prices, or the ordered
    lines before allocation). An over-limit order is refused (raises), never passed with a flag."""
    amount = order_subtotal(order)
    return _check_order(credit_limit, outstanding, amount)


def _billable_lines(order: Mapping) -> List[Dict]:
    alloc = order.get("allocated") or {}
    out: List[Dict] = []
    for ln in order["lines"]:
        qty = alloc.get(ln["item"], ln["quantity"]) if alloc else ln["quantity"]
        out.append({"description": ln["description"], "quantity": qty, "unit_price": ln["unit_price"]})
    return out


def order_subtotal(order: Mapping) -> Decimal:
    """The order's subtotal: the sum of allocated (or, before allocation, ordered) quantity times unit price."""
    return sum((_dec(l["quantity"]) * _dec(l["unit_price"]) for l in _billable_lines(order)), Decimal("0")).quantize(_CENTS)


def invoice_shipment(order: Mapping, tax: Number = 0, currency: str = "USD") -> Dict[str, object]:
    """Invoice a shipped order, value-conserving: the invoice lines are built from the SHIPPED (allocated) quantities,
    so the invoice can never bill more than was shipped, and it composes the sealed value-conserving invoice
    (revenue.billing.invoice -- lines sum to subtotal, total = subtotal + named tax). Only a shipped order may be
    invoiced."""
    if order.get("status") != "shipped":
        raise FulfillmentError(f"order {order.get('id')!r}: only a shipped order can be invoiced (is {order.get('status')!r})")
    return _invoice(_billable_lines(order), tax=tax, currency=currency)


def sale_posting(order: Mapping, tax: Number = 0, ar_account: str = "accounts receivable",
                 revenue_account: str = "sales revenue", tax_account: str = "sales tax payable") -> Dict[str, object]:
    """The sale as a value-conserving, balanced posting in the {debits, credits} shape: accounts receivable is debited
    the invoice total, sales revenue is credited the subtotal, and sales tax payable is credited the named tax -- so
    debits equal credits by construction (total == subtotal + tax). Posts to the sealed general ledger via
    financials.posting.from_entry."""
    inv = _invoice(_billable_lines(order), tax=tax)
    subtotal, t, total = inv["subtotal"], inv["tax"], inv["total"]
    credits = [{"account": revenue_account, "amount": subtotal}]
    if t > 0:
        credits.append({"account": tax_account, "amount": t})
    return {"order_id": order.get("id"), "debits": [{"account": ar_account, "amount": total}],
            "credits": credits, "balanced": total == subtotal + t, "amount": total}
