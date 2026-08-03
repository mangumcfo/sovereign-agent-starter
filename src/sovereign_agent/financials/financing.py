"""Financing structures — a facility/debt/equity instrument as a governed object with a commitment and a receipted
drawdown/repayment record.

Co-extrusion for s5_41 (Sovereign Treasury Investment & Financing, KM Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). A financing structure is a
first-class governed object: it carries a commitment (the maximum that may be drawn), and every drawdown and repayment
is a governed movement on it. A draw that would exceed the commitment is refused; outstanding is drawn minus repaid,
computed from the governed movements. The *execution* of a draw through a bank or lender is external connectivity,
homed in S6-V07; the structure and its governed record are here."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class FinancingError(ValueError):
    """Raised on an invalid facility (non-positive commitment) or a draw that would exceed the commitment."""


def new_facility(facility_id: str, commitment: Number, currency: str, kind: str = "facility") -> Dict[str, object]:
    """Open a financing structure as a governed object: an id, a positive commitment, a currency, and a kind
    (facility / term-debt / equity). The commitment is the ceiling; drawing beyond it is refused later."""
    c = _dec(commitment)
    if c <= 0:
        raise FinancingError(f"commitment must be > 0 (got {c})")
    return {"id": facility_id, "commitment": c, "currency": currency, "kind": kind}


def outstanding(facility: Mapping, movements: Iterable[Mapping]) -> Decimal:
    """Outstanding on a facility: total draws minus total repayments, from its governed movements.

    Each movement is a mapping with `facility` (id), `type` ('draw' or 'repay'), and `amount` (>= 0). Movements for
    other facilities are ignored; currencies are not mixed (a facility has a single currency)."""
    fid = facility["id"]
    drawn = Decimal("0")
    repaid = Decimal("0")
    for m in movements:
        if m.get("facility") != fid:
            continue
        amt = _dec(m["amount"])
        if amt < 0:
            raise FinancingError("movement amount must be non-negative")
        if m["type"] == "draw":
            drawn += amt
        elif m["type"] == "repay":
            repaid += amt
        else:
            raise FinancingError(f"unknown movement type {m.get('type')!r}")
    return drawn - repaid


def draw(facility: Mapping, amount: Number, movements: Iterable[Mapping]) -> Dict[str, object]:
    """Draw against a facility -- refused fail-closed if it would push outstanding past the commitment.

    Returns the drawdown movement (to be recorded on the immutable ledger by the caller, which supplies the approval
    gate and receipt). A draw that fits within the remaining commitment is allowed; one that exceeds it is refused, so
    a facility cannot be silently over-drawn."""
    a = _dec(amount)
    if a <= 0:
        raise FinancingError(f"draw amount must be > 0 (got {a})")
    current = outstanding(facility, movements)
    if current + a > facility["commitment"]:
        raise FinancingError(
            f"draw {a} would exceed commitment {facility['commitment']} (outstanding {current})")
    return {"facility": facility["id"], "type": "draw", "amount": a, "currency": facility["currency"]}


def available(facility: Mapping, movements: Iterable[Mapping]) -> Decimal:
    """Undrawn commitment remaining: commitment minus current outstanding."""
    return facility["commitment"] - outstanding(facility, movements)
