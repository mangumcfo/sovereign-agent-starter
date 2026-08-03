"""Bill-of-materials explosion + build feasibility — the manufacturing views over governed inventory.

Co-extrusion for s5_10 (Manufacturing & Quality, KM GO WAVE 2026-08-03). Pure arithmetic over Decimal, no crypto
substrate (pure-clone-clean, F-1 posture). A bill of materials maps a finished item to the component quantities it
consumes; explode_bom scales that to a build quantity, and can_build checks the requirement against the governed
on-hand at a location (via the existing supply.inventory) so a work order cannot be released against material that
is not there. The governance, immutability and provenance of a work order or a material movement come from the
existing ObligationLedger + object model; this module adds only the material arithmetic those governed records must
satisfy. Production scheduling/optimization and real-time shop-floor telemetry stay designed-toward."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

from .inventory import on_hand_for

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def explode_bom(bom: Mapping[str, Number], build_qty: Number) -> Dict[str, Decimal]:
    """Required component quantities to build `build_qty` units, given a BOM {component: qty_per_unit}.

    Refuses a non-positive build quantity or a non-positive per-unit quantity — a BOM line that consumes zero or
    a negative amount is a data error, not a valid build."""
    q = _dec(build_qty)
    if q <= 0:
        raise ValueError("build_qty must be positive")
    if not bom:
        raise ValueError("empty bill of materials")
    req: Dict[str, Decimal] = {}
    for component, per in bom.items():
        p = _dec(per)
        if p <= 0:
            raise ValueError(f"BOM line {component!r} has a non-positive per-unit quantity")
        req[component] = p * q
    return req


def can_build(bom: Mapping[str, Number], build_qty: Number, movements: Iterable[Mapping],
              location: str) -> Dict[str, object]:
    """Can `build_qty` be built at `location` from governed on-hand? Reports the shortfalls honestly.

    Checks each exploded requirement against the replayed on-hand for that component at the location. Returns
    whether the build is feasible and, if not, the exact per-component shortfall — so a work order is released
    against material that is actually there, not against a phantom availability."""
    movements = list(movements)
    required = explode_bom(bom, build_qty)
    shortfalls: Dict[str, Decimal] = {}
    for component, need in required.items():
        have = on_hand_for(movements, component, location)
        if have < need:
            shortfalls[component] = need - have
    return {"feasible": not shortfalls, "required": required, "shortfalls": shortfalls}
