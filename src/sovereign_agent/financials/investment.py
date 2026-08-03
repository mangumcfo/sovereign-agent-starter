"""Investment primitives — a capital position as the treasury view over governed acts, and net holdings.

Co-extrusion for s5_41 (Sovereign Treasury Investment & Financing, KM Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). An investment move is an ordinary
governed act: the sealed human_approval_gate, mandate_guard, witness, and ledger supply the approval, scope, witness,
and immutable receipt. This module adds the treasury *position view* over those governed acts -- what is held, per
issuer and instrument and currency, netting opens against closes. Valuation at a live market price is external (a price
feed, homed in S6-V07); a position here carries the governed amount it was transacted at, not a marked price."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Tuple, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class InvestmentError(ValueError):
    """Raised for a malformed position — a missing issuer/instrument/currency, or a non-numeric amount."""


def _key(p: Mapping) -> Tuple[str, str, str]:
    try:
        return (p["issuer"], p["instrument"], p["currency"])
    except KeyError as e:
        raise InvestmentError(f"position missing {e.args[0]!r}")


def holdings(positions: Iterable[Mapping]) -> Dict[Tuple[str, str, str], Decimal]:
    """Net holdings per (issuer, instrument, currency) from a set of governed position moves.

    Each move is a mapping with `issuer`, `instrument`, `currency`, and a signed `amount` (positive = acquire,
    negative = dispose). Currencies are kept strictly separate -- a holding is never a cross-currency sum, for the same
    reason treasury never nets across currencies. The result is what the ledger says is held, transacted-amount by
    transacted-amount, not a marked-to-market value."""
    pos: Dict[Tuple[str, str, str], Decimal] = {}
    for m in positions:
        k = _key(m)
        pos[k] = pos.get(k, Decimal("0")) + _dec(m["amount"])
    return pos


def total_by_issuer(positions: Iterable[Mapping]) -> Dict[Tuple[str, str], Decimal]:
    """Net held per (issuer, currency) across instruments -- the issuer-level position, currencies never blended."""
    out: Dict[Tuple[str, str], Decimal] = {}
    for m in positions:
        issuer, _instr, currency = _key(m)
        out[(issuer, currency)] = out.get((issuer, currency), Decimal("0")) + _dec(m["amount"])
    return out
