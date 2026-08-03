"""Treasury primitives — cash position + liquidity coverage over the immutable ledger.

Co-extrusion for s5_08 (Treasury & Cash, KM GO WAVE 2026-08-03). Pure arithmetic over Decimal, no crypto
substrate (runs in a pure public clone, no skip — F-1 posture). The immutability, governance (gate/mandate/
witness/quorum) and receipting of a cash movement come from the existing ObligationLedger + witness/quorum_guard;
this module adds the treasury *views* over those governed movements: the net cash position by account and
currency, and whether available cash covers committed outflows. Forecasting, investment management, and bank
connectivity are NOT here — they are designed-toward their own homes (Framing A: exists != wired)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Tuple, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def cash_position(movements: Iterable[Mapping]) -> Dict[Tuple[str, str], Decimal]:
    """Net cash position per (account, currency) from a set of governed cash movements.

    Each movement is a mapping with `account`, `currency`, and a signed `amount` (positive = inflow, negative =
    outflow). Currencies are kept strictly separate — a position is never a cross-currency sum, because netting
    across currencies would invent an exchange rate the ledger does not hold (FX is designed-toward)."""
    pos: Dict[Tuple[str, str], Decimal] = {}
    for m in movements:
        key = (m["account"], m["currency"])
        pos[key] = pos.get(key, Decimal("0")) + _dec(m["amount"])
    return pos


def total_by_currency(position: Mapping[Tuple[str, str], Number]) -> Dict[str, Decimal]:
    """Aggregate a cash position to a net per currency (still never mixing currencies)."""
    totals: Dict[str, Decimal] = {}
    for (account, currency), amount in position.items():
        totals[currency] = totals.get(currency, Decimal("0")) + _dec(amount)
    return totals


def liquidity_coverage(available: Number, committed_outflows: Number) -> Dict[str, object]:
    """Does available cash cover committed outflows? Reports the shortfall honestly rather than hiding it.

    This is a *governed-position* check over real movements, not a forecast: it compares cash the ledger says is
    available against outflows the ledger says are committed. Predicting future cash is designed-toward the
    analytics/forecasting engine and is deliberately not attempted here."""
    avail, committed = _dec(available), _dec(committed_outflows)
    if committed < 0 or avail < 0:
        raise ValueError("available and committed_outflows must be non-negative")
    shortfall = committed - avail
    return {
        "covered": shortfall <= 0,
        "available": avail,
        "committed": committed,
        "shortfall": shortfall if shortfall > 0 else Decimal("0"),
    }
