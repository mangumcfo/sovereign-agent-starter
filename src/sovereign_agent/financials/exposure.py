"""Exposure — risk-from-ledger: exposure by issuer and concentration, computed from governed positions. No valuation,
no prediction.

Co-extrusion for s5_41 (Sovereign Treasury Investment & Financing, KM Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). Exposure here is *observed ledger
state*, not a model: total held per issuer (per currency, never blended), each issuer's concentration as a share of the
total, and the issuers that breach a supplied limit. This is deliberately not a risk *engine*: it does not value
positions at a live market price (external feed, homed in S6-V07) and it does not predict or forecast risk (VaR,
scenario analysis, homed in S5-V17). It reports what is provably held and how concentrated it is -- the honest floor a
predictive layer would later sit on."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, List, Mapping, Tuple, Union

from .investment import total_by_issuer

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def exposure_by_issuer(positions: Iterable[Mapping]) -> Dict[Tuple[str, str], Decimal]:
    """Total exposure per (issuer, currency) from governed positions -- currencies never blended. Exposure is the net
    held amount the ledger records, not a marked value."""
    return total_by_issuer(positions)


def concentration(positions: Iterable[Mapping], currency: str) -> Dict[str, object]:
    """Each issuer's share of the total exposure in one currency, and the single largest concentration.

    Concentration is observed, not predicted: it is each issuer's exposure divided by the total exposure in that
    currency. Negative net positions are clamped to zero for the share base (a short is not a source of long
    concentration); the caller sees the raw exposures in `by_issuer`."""
    by = {i: v for (i, c), v in exposure_by_issuer(positions).items() if c == currency}
    base = sum((v for v in by.values() if v > 0), Decimal("0"))
    shares: Dict[str, Decimal] = {}
    if base > 0:
        for issuer, v in by.items():
            shares[issuer] = (v / base) if v > 0 else Decimal("0")
    largest = max(shares.values(), default=Decimal("0"))
    largest_issuer = max(shares, key=lambda k: shares[k], default=None) if shares else None
    return {
        "currency": currency,
        "by_issuer": by,
        "total": base,
        "shares": shares,
        "largest": largest,
        "largest_issuer": largest_issuer,
    }


def breaches(positions: Iterable[Mapping], limits: Mapping[str, Number], currency: str) -> List[Dict[str, object]]:
    """Issuers whose exposure in `currency` exceeds a supplied per-issuer limit -- observed breaches, not a forecast.

    `limits` is {issuer: max_exposure}. Returns one entry per breaching issuer with its exposure, the limit, and the
    overage. An issuer with no limit is not checked (absence of a limit is not a breach)."""
    by = {i: v for (i, c), v in exposure_by_issuer(positions).items() if c == currency}
    out: List[Dict[str, object]] = []
    for issuer, limit in limits.items():
        lim = _dec(limit)
        exp = by.get(issuer, Decimal("0"))
        if exp > lim:
            out.append({"issuer": issuer, "exposure": exp, "limit": lim, "over": exp - lim})
    return out
