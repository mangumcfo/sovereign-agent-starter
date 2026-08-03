"""FX primitives — currency conversion as an explicit, receipted act at a supplied rate. Bounded on purpose.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM CLOSE-do-not-defer 2026-08-03). Pure arithmetic
over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). Sealed treasury
(`treasury.cash_position`) keeps positions strictly per-currency and pointed FX conversion here; this module lands
exactly that bounded floor and no more: a conversion is an explicit act at a rate the caller supplies (the rate is
an accountable input, never sourced or guessed), it is refused at a non-positive rate, a same-currency conversion
must use rate 1, and converted amounts are summed only within a single target currency — currencies are never
blended into one figure.

Framing A (exists != wired): the conversion *act* + no-blend are PRESENT and tested. The FX *rate engine* — rate
sourcing, curves, period-end revaluation — is designed-toward THIS volume's own growth path, not re-homed."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class FXError(ValueError):
    """Raised on an invalid conversion — a non-positive rate, or a same-currency conversion at a rate other than 1."""


def convert(amount: Number, from_ccy: str, to_ccy: str, rate: Number) -> Dict[str, object]:
    """Convert an amount from one currency to another as an explicit, receipted act at a *supplied* rate.

    The rate is an input the caller is accountable for — this module neither sources nor guesses it. Returns the
    converted amount tagged to the target currency plus a conversion record (from/to/rate), so the act is auditable
    rather than an invisible arithmetic on a blended total. Refuses a non-positive rate; a same-currency conversion
    must use rate 1 (there is no honest rate that turns USD into more USD)."""
    amt, r = _dec(amount), _dec(rate)
    if r <= 0:
        raise FXError(f"rate must be > 0 (got {r})")
    if from_ccy == to_ccy and r != 1:
        raise FXError(f"same-currency conversion {from_ccy}->{to_ccy} must use rate 1 (got {r})")
    converted = (amt * r).quantize(Decimal("0.01"))
    return {
        "from": {"amount": amt, "currency": from_ccy},
        "to": {"amount": converted, "currency": to_ccy},
        "rate": r,
    }


def combine_converted(records: Iterable[Mapping]) -> Dict[str, Decimal]:
    """Sum converted amounts per target currency across many conversion records — never blending currencies.

    Even after conversion, distinct target currencies stay distinct totals; only amounts already in the same
    currency are added. Blending them would re-introduce the cross-currency sum the whole discipline forbids."""
    totals: Dict[str, Decimal] = {}
    for rec in records:
        ccy = rec["to"]["currency"]
        totals[ccy] = totals.get(ccy, Decimal("0")) + _dec(rec["to"]["amount"])
    return totals
