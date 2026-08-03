"""Dimension engine — multi-dimensional modeling over governed postings: several validated hierarchies, and the
ability to roll up and slice the same amounts by any of them.

Co-extrusion for s5_40 (Sovereign Controlling & Financial Close, KM ratify Option B 2026-08-03). Pure arithmetic /
structural over Decimal, no crypto substrate (runs in a pure public clone, no skip — F-1 posture). A management view
wants more than the account tree: a geography, a product line, a legal entity -- dimensions that cut the same governed
postings different ways. A dimension here is a validated member hierarchy (the same discipline as a Chart of Accounts),
an amount is tagged with a coordinate naming one member per dimension, and the engine rolls up or slices by any
dimension conserving value. The BI/reporting layer that renders cubes and packs over this floor is elsewhere
(reporting -> S5-V14); this module is the governed modeling floor beneath it."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Union

from .controlling import validate_coa, CoAError

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class DimensionError(ValueError):
    """Raised when a dimension hierarchy is invalid, or an amount is tagged with a member the dimension does not
    define."""


def validate_dimension(dimension: Mapping[str, Mapping]) -> None:
    """A management dimension (geography, product line, entity, ...) is a governed hierarchy of members, validated
    the same fail-closed way a Chart of Accounts is: no missing parents, no cycles."""
    try:
        validate_coa(dimension)
    except CoAError as e:
        raise DimensionError(str(e))


def _descendants(member: str, dimension: Mapping[str, Mapping]) -> set:
    """The member itself and everything whose parent-chain passes through it."""
    out = set()
    for m in dimension:
        cur = m
        while cur is not None:
            if cur == member:
                out.add(m)
                break
            cur = dimension[cur].get("parent")
    return out


def roll_up_members(member_balances: Mapping[str, Number], dimension: Mapping[str, Mapping]) -> Dict[str, Decimal]:
    """Roll balances up a dimension's member hierarchy: each member's rolled balance is its own plus all its
    descendants'. Value-conserving -- the sum over root members equals the sum of the supplied balances."""
    validate_dimension(dimension)
    for m in member_balances:
        if m not in dimension:
            raise DimensionError(f"balance for unknown member {m!r}")
    rolled: Dict[str, Decimal] = {m: Decimal("0") for m in dimension}
    for m, bal in member_balances.items():
        b = _dec(bal)
        cur = m
        while cur is not None:
            rolled[cur] += b
            cur = dimension[cur].get("parent")
    return rolled


def slice_amounts(tagged: Iterable[Mapping], dimension_name: str, member: str,
                  dimension: Mapping[str, Mapping]) -> Decimal:
    """Total tagged amounts whose coordinate on `dimension_name` is `member` or one of its descendants -- cutting the
    same governed postings by a chosen dimension. Value-conserving: slicing at a root totals everything under it.

    Each tagged item is a mapping with `amount` and `coord` (a mapping of dimension_name -> member). An item whose
    coordinate names a member the dimension does not define is refused, not silently dropped."""
    validate_dimension(dimension)
    if member not in dimension:
        raise DimensionError(f"slice member {member!r} not in dimension")
    members = _descendants(member, dimension)
    total = Decimal("0")
    for item in tagged:
        coord = item.get("coord", {})
        m = coord.get(dimension_name)
        if m is None:
            continue  # untagged on this dimension -> not in this slice
        if m not in dimension:
            raise DimensionError(f"tagged amount names member {m!r} not in dimension {dimension_name!r}")
        if m in members:
            total += _dec(item["amount"])
    return total
