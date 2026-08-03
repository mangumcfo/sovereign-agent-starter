"""FX primitives — currency conversion as an explicit, receipted act at a supplied rate. Bounded on purpose.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM CLOSE-do-not-defer 2026-08-03). Pure arithmetic
over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). Sealed treasury
(`treasury.cash_position`) keeps positions strictly per-currency and pointed FX conversion here; this module lands
exactly that bounded floor and no more: a conversion is an explicit act at a rate the caller supplies (the rate is
an accountable input, never sourced or guessed), it is refused at a non-positive rate, a same-currency conversion
must use rate 1, and converted amounts are summed only within a single target currency — currencies are never
blended into one figure.

The rate engine over this act is now landed too (KM ratify Option B 2026-08-03): a governed rate table holds supplied
rates by (from, to, as-of date), and period-end revaluation converts open foreign balances at the closing rate and
reports the unrealized gain/loss -- each a recorded conversion act. What stays external is the *sourcing* of live
market rates and forward curves from a data provider (network connectivity), homed in S6-V07; the rates in the table
here are governed inputs, not a live feed. Framing A (exists != wired) holds at that seam."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Tuple, Union

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


def rate_for(table: Mapping[Tuple[str, str, str], Number], from_ccy: str, to_ccy: str, as_of: str) -> Decimal:
    """Look up a governed rate for (from_ccy, to_ccy, as_of) in a rate table, fail-closed if it is absent.

    The table is a mapping of (from, to, date) -> rate: rates that were *entered as governed inputs*, not sourced from
    a live market feed (that sourcing is external connectivity, homed in S6-V07). A missing rate is refused rather than
    guessed -- a revaluation must not run on a rate the ledger does not hold."""
    key = (from_ccy, to_ccy, as_of)
    if key not in table:
        raise FXError(f"no governed rate for {from_ccy}->{to_ccy} as of {as_of}")
    r = _dec(table[key])
    if r <= 0:
        raise FXError(f"rate for {from_ccy}->{to_ccy} as of {as_of} must be > 0 (got {r})")
    return r


def revalue(open_balances: Iterable[Mapping], table: Mapping[Tuple[str, str, str], Number],
            base_ccy: str, as_of: str) -> List[Dict[str, object]]:
    """Revalue open foreign-currency balances at a governed closing rate, reporting the unrealized gain/loss.

    Each open balance is a mapping with `amount`, `currency` (a foreign currency), and the `book_value` at which it
    currently sits in `base_ccy`. For each, the closing value is a receipted conversion at the governed rate for
    (currency, base_ccy, as_of); the unrealized gain/loss is closing_value - book_value. A same-currency balance is
    skipped (nothing to revalue). Currencies are never blended -- each result carries its own currency and its base
    equivalent, and gain/loss is expressed in the base currency only."""
    out: List[Dict[str, object]] = []
    for bal in open_balances:
        ccy = bal["currency"]
        if ccy == base_ccy:
            continue
        rate = rate_for(table, ccy, base_ccy, as_of)
        act = convert(bal["amount"], ccy, base_ccy, rate)
        closing = act["to"]["amount"]
        book = _dec(bal["book_value"])
        out.append({
            "currency": ccy,
            "amount": _dec(bal["amount"]),
            "book_value": book,
            "closing_value": closing,
            "unrealized_gl": closing - book,
            "as_of": as_of,
            "rate": rate,
        })
    return out
