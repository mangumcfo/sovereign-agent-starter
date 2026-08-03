"""Forecast — transparent, named projections and scenarios from a governed history. Not a black box.

Co-extrusion for s5_17 (Analytics & Decision Intelligence, KM Option B 2026-08-03). Pure arithmetic over Decimal, no
crypto substrate (runs in a pure public clone, no skip — F-1 posture). This discharges the forecasting debt the sealed
wave homed here (treasury cash forecasting, controlling/investment/compliance forecasting): a projection is computed
by a named method (a moving average or a linear trend) from a governed history, and the result carries its method,
parameters, and the history it used — so a forecast is re-runnable and auditable, never an opaque model output. A
scenario applies named driver adjustments to a base projection. Learned/black-box models are refused by construction;
the transparent method library accretes in-volume (S5-V17)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Union

Number = Union[int, float, str, Decimal]

MOVING_AVERAGE = "moving_average"
LINEAR_TREND = "linear_trend"
_METHODS = (MOVING_AVERAGE, LINEAR_TREND)


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class ForecastError(ValueError):
    """Raised for an unknown method, a non-positive horizon, or a history too short for the method."""


def project(history: List[Number], periods: int, method: str = MOVING_AVERAGE, window: int = 3) -> Dict[str, object]:
    """Project `periods` future values from a governed `history` by a named, transparent method.

    - moving_average: each projected value is the mean of the last `window` known values (rolling, including prior
      projections). Smooths; assumes no trend.
    - linear_trend: fit a slope from the first and last history points and extrapolate linearly.
    The result carries the method, its parameters, and the history — re-runnable and auditable, not a black box."""
    if periods <= 0:
        raise ForecastError(f"periods must be > 0 (got {periods})")
    if method not in _METHODS:
        raise ForecastError(f"unknown method {method!r} (known: {', '.join(_METHODS)})")
    hist = [_dec(x) for x in history]
    if not hist:
        raise ForecastError("empty history")
    projections: List[Decimal] = []
    if method == MOVING_AVERAGE:
        if window <= 0:
            raise ForecastError("window must be > 0")
        series = list(hist)
        for _ in range(periods):
            w = series[-window:] if len(series) >= window else series
            nxt = (sum(w, Decimal("0")) / len(w)).quantize(Decimal("0.01"))
            projections.append(nxt)
            series.append(nxt)
    else:  # LINEAR_TREND
        if len(hist) < 2:
            raise ForecastError("linear_trend needs at least 2 history points")
        slope = (hist[-1] - hist[0]) / Decimal(len(hist) - 1)
        last = hist[-1]
        for k in range(1, periods + 1):
            projections.append((last + slope * k).quantize(Decimal("0.01")))
    return {"method": method, "window": window if method == MOVING_AVERAGE else None,
            "history": hist, "periods": periods, "projections": projections}


def scenario(base: Mapping, adjustments: Mapping) -> Dict[str, object]:
    """Apply named driver adjustments to a base projection, producing a governed scenario.

    `adjustments` may carry a `factor` (multiply every projected value) and/or a `delta` (add to every value). The
    scenario records the base projections and the named adjustments applied, so it is reproducible: the same base and
    adjustments yield the same scenario, and a reviewer sees exactly what was changed."""
    factor = _dec(adjustments.get("factor", 1))
    delta = _dec(adjustments.get("delta", 0))
    if factor < 0:
        raise ForecastError("scenario factor must be >= 0")
    adjusted = [((_dec(p) * factor) + delta).quantize(Decimal("0.01")) for p in base["projections"]]
    return {"base_method": base.get("method"), "adjustments": {"factor": factor, "delta": delta},
            "base_projections": list(base["projections"]), "projections": adjusted}
