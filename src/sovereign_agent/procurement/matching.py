"""Matching — the governed three-way match (PO <-> goods receipt <-> invoice), fail-closed and value-conserving.

Co-extrusion for s5_16 (Procurement-to-Pay, KM Option B 2026-08-04). Pure / structural, no crypto substrate (F-1
pure-clone-clean). On a legacy system an invoice can be paid before anyone confirms the goods arrived, or at a price
that never matched the purchase order, and the mismatch is discovered -- if ever -- in a later audit. Here an invoice
is authorized for payment only when three governed records reconcile: the purchase order (what was agreed), the goods
receipt (what actually arrived -- composing the sealed supply-chain receipt surface, Supply Chain Execution), and the
invoice (what is billed). Quantity and price must agree within a governed tolerance, per line; any breach is refused
fail-closed, never silently auto-approved. The authorized payable is value-conserving: it decomposes exactly into
per-line amounts, each the billed-and-received quantity at the agreed price, so nothing is paid for goods not received
or above the agreed price. The matched payable posts value-conserving to accounts payable (debits equal credits),
composing the sealed posting surface (Sovereign Financials)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class MatchError(ValueError):
    """Raised when PO / goods-receipt / invoice fail to reconcile within tolerance -- a mismatch is refused fail-closed,
    never silently auto-approved (no payment for un-ordered goods, goods not received, or a price above the PO)."""


def _index_po(po: Mapping) -> Dict[str, Dict[str, Decimal]]:
    lines = po.get("lines", ())
    if not lines:
        raise MatchError(f"purchase order {po.get('po_id')!r} has no lines")
    idx: Dict[str, Dict[str, Decimal]] = {}
    for ln in lines:
        item = ln["item"]
        q, p = _dec(ln["quantity"]), _dec(ln["unit_price"])
        if q <= 0 or p < 0:
            raise MatchError(f"PO line {item!r}: quantity must be > 0 and price >= 0 (q={q}, p={p})")
        idx[item] = {"quantity": q, "unit_price": p}
    return idx


def _index_receipt(receipt: Mapping) -> Dict[str, Decimal]:
    got: Dict[str, Decimal] = {}
    for ln in receipt.get("lines", ()):
        q = _dec(ln["quantity"])
        if q < 0:
            raise MatchError(f"goods-receipt line {ln.get('item')!r}: received quantity must be >= 0 (got {q})")
        got[ln["item"]] = got.get(ln["item"], Decimal("0")) + q
    return got


def three_way_match(po: Mapping, receipt: Mapping, invoice: Mapping,
                    qty_tolerance: Number = 0, price_tolerance: Number = 0) -> Dict[str, object]:
    """Reconcile an invoice against its purchase order and goods receipt, fail-closed, and return the value-conserving
    payable. `po` carries `po_id` and `lines` (each `item`, `quantity`, `unit_price` -- the agreed price governs);
    `receipt` carries `lines` (each `item`, `quantity` received); `invoice` carries `invoice_id` and `lines` (each
    `item`, `quantity`, `unit_price` billed). For every invoiced line: the item must be on the PO (no payment for
    un-ordered goods); it must have a goods receipt (no payment for goods not received); the billed quantity must not
    exceed the received quantity beyond `qty_tolerance`, and the received quantity must not exceed the ordered quantity
    beyond `qty_tolerance` (over-receipt); the billed price must be within `price_tolerance` of the PO price. Any breach
    raises MatchError -- the mismatch is refused, not auto-approved. The line payable is the billed quantity at the
    agreed PO price; the payable is the sum, decomposing exactly into the per-line amounts."""
    po_idx = _index_po(po)
    got = _index_receipt(receipt)
    qtol, ptol = _dec(qty_tolerance), _dec(price_tolerance)
    if qtol < 0 or ptol < 0:
        raise MatchError(f"tolerances must be >= 0 (qty={qtol}, price={ptol})")
    inv_lines = invoice.get("lines", ())
    if not inv_lines:
        raise MatchError(f"invoice {invoice.get('invoice_id')!r} has no lines")
    matched: List[Dict[str, object]] = []
    payable = Decimal("0")
    for ln in inv_lines:
        item = ln["item"]
        if item not in po_idx:
            raise MatchError(f"invoice {invoice.get('invoice_id')!r} line {item!r}: not on purchase order "
                             f"{po.get('po_id')!r} -- no payment for un-ordered goods")
        if item not in got:
            raise MatchError(f"invoice {invoice.get('invoice_id')!r} line {item!r}: no goods receipt -- "
                             f"no payment for goods not received")
        po_q, po_p = po_idx[item]["quantity"], po_idx[item]["unit_price"]
        recv_q = got[item]
        inv_q, inv_p = _dec(ln["quantity"]), _dec(ln["unit_price"])
        if inv_q <= 0 or inv_p < 0:
            raise MatchError(f"invoice line {item!r}: quantity must be > 0 and price >= 0 (q={inv_q}, p={inv_p})")
        if inv_q - recv_q > qtol:
            raise MatchError(f"invoice line {item!r}: billed quantity {inv_q} exceeds received {recv_q} "
                             f"beyond tolerance {qtol} -- refused (no payment for goods not received)")
        if recv_q - po_q > qtol:
            raise MatchError(f"invoice line {item!r}: received quantity {recv_q} exceeds ordered {po_q} "
                             f"beyond tolerance {qtol} -- over-receipt refused")
        if abs(inv_p - po_p) > ptol:
            raise MatchError(f"invoice line {item!r}: billed price {inv_p} differs from PO price {po_p} "
                             f"beyond tolerance {ptol} -- refused (no payment above the agreed price)")
        amt = (inv_q * po_p).quantize(_CENTS)
        matched.append({"item": item, "quantity": inv_q, "unit_price": po_p, "amount": amt})
        payable += amt
    payable = payable.quantize(_CENTS)
    return {"invoice_id": invoice.get("invoice_id"), "po_id": po.get("po_id"), "matched": True,
            "lines": matched, "payable": payable,
            "conserves": sum((l["amount"] for l in matched), Decimal("0")) == payable}


def ap_entry(match: Mapping, gr_ir_account: str = "GR/IR clearing",
             ap_account: str = "accounts payable") -> Dict[str, object]:
    """Post a matched invoice to accounts payable, value-conserving: the payable is debited to the goods-received /
    invoice-received clearing account and credited to accounts payable, so debits equal credits by construction. A
    balanced entry -- the matched three-way payable becomes a governed AP obligation with nothing added or lost."""
    amt = _dec(match["payable"]).quantize(_CENTS)
    debits = [{"account": gr_ir_account, "amount": amt}]
    credits = [{"account": ap_account, "amount": amt}]
    d = sum((e["amount"] for e in debits), Decimal("0"))
    c = sum((e["amount"] for e in credits), Decimal("0"))
    return {"invoice_id": match.get("invoice_id"), "debits": debits, "credits": credits,
            "balanced": d == c, "amount": amt}
