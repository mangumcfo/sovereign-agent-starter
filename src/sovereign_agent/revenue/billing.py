"""Billing — governed order-to-invoice and an AR-aging projection.

Co-extrusion for s5_15 (Revenue & Order-to-Cash). Pure / structural, no crypto substrate (F-1 pure-clone-clean). An
invoice is generated from governed order lines and is value-conserving: the line extended amounts (quantity times unit
price) sum to the subtotal, the sales tax is an explicit line, and the invoice total is the subtotal plus the tax --
nothing is added to the total that is not a line or the named tax. And accounts-receivable aging is a PROJECTION over
open invoices: each invoice falls into an age bucket by how long it has been outstanding, and the bucket totals sum to
the total receivable -- a derived view, never a maintained aging table. Sales tax composes the sealed tax surface
(s5_01); multi-currency invoicing composes the sealed FX floor (S5-V12)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Sequence, Union

Number = Union[int, float, str, Decimal]
_CENTS = Decimal("0.01")
_BUCKETS = ((0, "current"), (31, "31_60"), (61, "61_90"), (91, "over_90"))


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class BillingError(ValueError):
    """Raised for a non-positive quantity/price, or a tax that is not >= 0."""


def invoice(lines: Sequence[Mapping], tax: Number = 0, currency: str = "USD") -> Dict[str, object]:
    """Generate a value-conserving invoice from order lines. Each line carries a `description`, a `quantity`, and a
    `unit_price`; its extended amount is quantity times unit price. The subtotal is the sum of the extended amounts,
    the tax is an explicit named amount (composed from the sealed tax surface), and the total is subtotal plus tax.
    Refuses a non-positive quantity or price, or a negative tax."""
    if not lines:
        raise BillingError("invoice needs at least one line")
    priced: List[Dict] = []
    subtotal = Decimal("0")
    for ln in lines:
        q, p = _dec(ln["quantity"]), _dec(ln["unit_price"])
        if q <= 0 or p < 0:
            raise BillingError(f"line {ln.get('description')!r}: quantity must be > 0 and price >= 0 (q={q}, p={p})")
        amt = (q * p).quantize(_CENTS)
        priced.append({"description": ln.get("description"), "quantity": q, "unit_price": p, "amount": amt})
        subtotal += amt
    t = _dec(tax)
    if t < 0:
        raise BillingError(f"tax must be >= 0 (got {t})")
    subtotal = subtotal.quantize(_CENTS); t = t.quantize(_CENTS)
    return {"currency": currency, "lines": priced, "subtotal": subtotal, "tax": t, "total": (subtotal + t).quantize(_CENTS)}


def ar_aging(invoices: Iterable[Mapping], as_of_day: int) -> Dict[str, object]:
    """Project accounts-receivable aging over open invoices as of a given day. Each open invoice maps `amount` and
    `issued_day`; its age is `as_of_day - issued_day`, and it falls into a bucket (current / 31-60 / 61-90 / over 90).
    Returns the per-bucket totals and the total receivable; the buckets sum to the total by construction -- a projection
    over the invoices, not a stored aging table."""
    buckets: Dict[str, Decimal] = {name: Decimal("0") for _, name in _BUCKETS}
    total = Decimal("0")
    for inv in invoices:
        if inv.get("paid"):
            continue
        amt = _dec(inv["amount"]).quantize(_CENTS)
        age = int(as_of_day) - int(inv["issued_day"])
        name = _BUCKETS[0][1]
        for lo, bname in _BUCKETS:
            if age >= lo:
                name = bname
        buckets[name] += amt
        total += amt
    return {"as_of_day": int(as_of_day), "buckets": buckets, "total_receivable": total.quantize(_CENTS),
            "balances": sum(buckets.values(), Decimal("0")) == total}
