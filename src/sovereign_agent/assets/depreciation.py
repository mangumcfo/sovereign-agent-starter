"""Depreciation — a value-conserving depreciation schedule by a named method.

Co-extrusion for s5_12 (Asset & Maintenance Management). Pure arithmetic over Decimal, no crypto substrate (F-1
pure-clone-clean). Depreciation spreads an asset's depreciable base -- cost minus salvage -- across its useful life by
a NAMED method (straight-line, or units-of-production), and the schedule is value-conserving by construction: the
period charges sum EXACTLY to the depreciable base, and the net book value ends at exactly the salvage value. The last
period absorbs any rounding residual, so the schedule never leaks or invents a cent. The schedule is a derived
projection -- carrying its method and inputs, re-runnable -- not a stored table an operator maintains."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Sequence, Union

Number = Union[int, float, str, Decimal]

STRAIGHT_LINE = "straight_line"
UNITS_OF_PRODUCTION = "units_of_production"
_CENTS = Decimal("0.01")


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class DepreciationError(ValueError):
    """Raised for a salvage outside [0, cost], a non-positive life/units, or a units list that does not match."""


def _finalize(base: Decimal, charges: List[Decimal]) -> List[Decimal]:
    """Make the charges conserve value exactly: the final period absorbs the rounding residual so the charges sum to
    the depreciable base to the cent."""
    charges = [c.quantize(_CENTS) for c in charges]
    charges[-1] = (base - sum(charges[:-1], Decimal("0"))).quantize(_CENTS)
    return charges


def straight_line(cost: Number, salvage: Number, life: int) -> List[Decimal]:
    """Equal charges across `life` periods; the last period absorbs the rounding residual so the total is exact."""
    cost, salvage = _dec(cost), _dec(salvage)
    if not (Decimal("0") <= salvage <= cost):
        raise DepreciationError(f"salvage {salvage} must be in [0, cost {cost}]")
    if life < 1:
        raise DepreciationError("useful life must be >= 1 period")
    base = cost - salvage
    per = (base / Decimal(life)).quantize(_CENTS)
    return _finalize(base, [per] * life)


def units_of_production(cost: Number, salvage: Number, period_units: Sequence[Number]) -> List[Decimal]:
    """Charge each period in proportion to the units it produced. The charges sum to the depreciable base; the last
    period absorbs the residual. Refuses empty or non-positive total units."""
    cost, salvage = _dec(cost), _dec(salvage)
    if not (Decimal("0") <= salvage <= cost):
        raise DepreciationError(f"salvage {salvage} must be in [0, cost {cost}]")
    units = [_dec(u) for u in period_units]
    total = sum(units, Decimal("0"))
    if not units or total <= 0:
        raise DepreciationError("units_of_production needs at least one period and positive total units")
    base = cost - salvage
    charges = [(base * u / total) for u in units]
    return _finalize(base, charges)


def schedule(cost: Number, salvage: Number, life: int = None, method: str = STRAIGHT_LINE,
             period_units: Sequence[Number] = None) -> Dict[str, object]:
    """A value-conserving depreciation schedule by a named method. Returns the method, per-period charges, the running
    accumulated depreciation, and the net book value each period. Value-conserving invariants (checked by the tests):
    `sum(charges) == cost - salvage` and the final net book value == salvage. Re-runnable, carrying its inputs."""
    cost, salvage = _dec(cost), _dec(salvage)
    if method == STRAIGHT_LINE:
        if life is None:
            raise DepreciationError("straight_line needs a useful life")
        charges = straight_line(cost, salvage, life)
    elif method == UNITS_OF_PRODUCTION:
        if not period_units:
            raise DepreciationError("units_of_production needs period_units")
        charges = units_of_production(cost, salvage, period_units)
    else:
        raise DepreciationError(f"unknown method {method!r} (known: {STRAIGHT_LINE}, {UNITS_OF_PRODUCTION})")
    accumulated: List[Decimal] = []
    nbv: List[Decimal] = []
    run = Decimal("0")
    for c in charges:
        run += c
        accumulated.append(run)
        nbv.append(cost - run)
    return {"method": method, "cost": cost, "salvage": salvage, "charges": charges,
            "accumulated": accumulated, "net_book_value": nbv, "periods": len(charges)}
