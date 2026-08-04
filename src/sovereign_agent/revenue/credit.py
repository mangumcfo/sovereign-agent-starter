"""Credit — a governed, fail-closed credit-limit check on an order.

Co-extrusion for s5_15 (Revenue & Order-to-Cash). Pure / structural, no crypto substrate (F-1 pure-clone-clean). An
order is checked against a customer's governed credit limit before it is accepted: if the customer's current
outstanding balance plus the new order would exceed the limit, the order is refused fail-closed -- not accepted with a
warning someone may ignore. The check is a plain, reproducible computation over governed balances; who may override a
refused order is a governed act on the sealed access surface (S5-V2), not a silent bypass."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class CreditError(ValueError):
    """Raised when an order would breach the governed credit limit, or an input is negative."""


def available_credit(credit_limit: Number, outstanding: Number) -> Decimal:
    """The credit still available to a customer: limit minus current outstanding (never below zero for reporting)."""
    return max(Decimal("0"), _dec(credit_limit) - _dec(outstanding))


def check_order(credit_limit: Number, outstanding: Number, order_amount: Number) -> Dict[str, object]:
    """Check an order against a customer's governed credit limit, fail-closed. Refuses a negative input, and refuses
    the order if `outstanding + order_amount` would exceed `credit_limit`. Returns the decision and the available
    credit; a refused order raises rather than passing with a flag, so an over-limit order cannot slip through
    unnoticed. An override is a governed act on the sealed access surface, not a value this function quietly returns."""
    limit, out, amt = _dec(credit_limit), _dec(outstanding), _dec(order_amount)
    if limit < 0 or out < 0 or amt <= 0:
        raise CreditError(f"credit inputs invalid (limit={limit}, outstanding={out}, order={amt})")
    if out + amt > limit:
        raise CreditError(f"order {amt} would put the customer at {out + amt}, over the credit limit {limit} "
                          f"(available {available_credit(limit, out)}) -- refused; an override is a governed act")
    return {"approved": True, "new_exposure": out + amt, "available_after": (limit - (out + amt))}
