"""Driver-model library — named allocation drivers that compute weights from a governed base measure, then feed the
value-conserving allocation across centers.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM ratify Option B 2026-08-03). Pure arithmetic over
Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). In mature controlling, allocation
weights are not typed by hand; they are computed from business drivers -- headcount, machine hours, square footage.
This module is that library: a driver is a rule that turns a governed base measure per center into weights, and
`allocate_by_driver` composes it with the sealed value-conserving allocation so the spread still sums to the pool
exactly. The library is deliberately a fixed set of transparent rules (proportional / equal / fixed) -- a *predictive*
driver that learns weights from data is forecasting, homed in S5-V17, not here."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping, Union

from .controlling import allocate_cost_pool

Number = Union[int, float, str, Decimal]

PROPORTIONAL = "proportional"   # weight of a center is proportional to its base measure
EQUAL = "equal"                 # every center weighted equally, regardless of measure
FIXED = "fixed"                 # the supplied measures ARE the weights, used verbatim
DRIVERS = (PROPORTIONAL, EQUAL, FIXED)


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class DriverError(ValueError):
    """Raised for an unknown driver type or an invalid base measure (negative, or all-zero for a proportional
    driver)."""


def weights_from_driver(driver: str, base_measures: Mapping[str, Number]) -> Dict[str, Decimal]:
    """Turn a governed base measure per center into allocation weights, by a named, transparent driver rule.

    - proportional: weight == the center's measure (allocation is proportional to it).
    - equal: every center gets weight 1 (the measure is ignored -- an explicit, auditable choice).
    - fixed: the measures are used verbatim as weights.
    The weights returned feed the value-conserving allocation unchanged; this function only chooses them."""
    if driver not in DRIVERS:
        raise DriverError(f"unknown driver {driver!r} (known: {', '.join(DRIVERS)})")
    if not base_measures:
        raise DriverError("no centers")
    m = {k: _dec(v) for k, v in base_measures.items()}
    if any(v < 0 for v in m.values()):
        raise DriverError("negative base measure")
    if driver == EQUAL:
        return {k: Decimal("1") for k in m}
    if driver in (PROPORTIONAL, FIXED):
        if sum(m.values(), Decimal("0")) <= 0:
            raise DriverError(f"{driver} driver needs a positive total base measure")
        return dict(m)
    raise DriverError(driver)  # defensive


def allocate_by_driver(pool: Number, driver: str, base_measures: Mapping[str, Number]) -> Dict[str, Decimal]:
    """Allocate a cost pool across centers by a named driver: compute the weights from the governed base measure,
    then spread the pool with the sealed value-conserving allocation so the pieces sum to the pool exactly. The
    driver chooses the weights; the conservation guarantee is unchanged."""
    weights = weights_from_driver(driver, base_measures)
    return allocate_cost_pool(pool, weights)
