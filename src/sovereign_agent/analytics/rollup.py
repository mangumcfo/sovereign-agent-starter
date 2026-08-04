"""Rollup — a thin analytic dimensional rollup over the sealed dimension engine. Projection only; read-only.

Co-extrusion for s5_17 (Analytics & Decision Intelligence, KM Option B+ 2026-08-03). Pure / structural, no crypto
substrate (runs in a pure public clone, no skip — F-1 posture). Analytics wants to roll a metric up a governed
dimension -- spend by geography rolled to region rolled to global. This helper does exactly that and no more: it
aggregates tagged amounts to each dimension member and rolls them up the sealed dimension hierarchy
(`financials.dimensions`), value-conserving. It is a projection -- it reads governed amounts and returns a rolled view;
it never mutates the ledger or the dimension. Multi-dimensional modeling itself is sealed in the controlling volume
(S5-V12); this is the analytic rollup over it."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

from ..financials.dimensions import validate_dimension, roll_up_members, DimensionError

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def rollup_metric(tagged: Iterable[Mapping], dimension_name: str, dimension: Mapping[str, Mapping],
                  value_key: str = "amount") -> Dict[str, Decimal]:
    """Roll an analytic metric up a governed dimension: sum the tagged amounts to each member, then roll the hierarchy
    up value-conserving (reusing the sealed dimension engine). Projection only -- read-only over governed amounts.

    Each tagged item carries `value_key` and a `coord` mapping naming its member on `dimension_name`. An item whose
    member the dimension does not define is refused, not silently dropped; an untagged item is skipped. The rolled
    result gives every member (leaf and rollup) its total, and the sum over roots equals the sum of the tagged leaves."""
    validate_dimension(dimension)
    leaf: Dict[str, Decimal] = {}
    for item in tagged:
        member = item.get("coord", {}).get(dimension_name)
        if member is None:
            continue
        if member not in dimension:
            raise DimensionError(f"tagged amount names member {member!r} not in dimension {dimension_name!r}")
        leaf[member] = leaf.get(member, Decimal("0")) + _dec(item[value_key])
    return roll_up_members(leaf, dimension)
