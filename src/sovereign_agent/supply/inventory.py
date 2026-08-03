"""Inventory on-hand + no-phantom-stock — the supply-chain views a governed inventory ledger must satisfy.

Pure arithmetic over Decimal; no crypto substrate. On-hand quantity is a replay of governed inventory movements
(receipts positive, issues negative), computed per item and location — never blended across locations, because a
unit in one warehouse is not a unit in another. A no-phantom-stock check reports whether an issue would drive a
location negative, so the ledger cannot quietly ship stock it does not have. Immutability and provenance of a
movement come from the existing ObligationLedger + object model."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Mapping, Tuple, Union

Number = Union[int, float, str, Decimal]


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class NegativeStockError(ValueError):
    """Raised when a movement set drives a location's on-hand below zero — phantom stock."""


def on_hand(movements: Iterable[Mapping]) -> Dict[Tuple[str, str], Decimal]:
    """Net on-hand quantity per (item, location) from governed movements (receipt +, issue -).

    Locations are never blended: a unit in one warehouse is a distinct on-hand from a unit in another, because
    fulfilling from a location you cannot ship from is exactly the phantom-availability error this prevents."""
    qty: Dict[Tuple[str, str], Decimal] = {}
    for m in movements:
        key = (m["item"], m["location"])
        qty[key] = qty.get(key, Decimal("0")) + _dec(m["qty"])
    return qty


def on_hand_for(movements: Iterable[Mapping], item: str, location: str) -> Decimal:
    """On-hand for a single item at a single location."""
    return on_hand(movements).get((item, location), Decimal("0"))


def would_overdraw(movements: Iterable[Mapping], item: str, location: str, issue_qty: Number) -> bool:
    """Would issuing `issue_qty` of `item` at `location` drive on-hand negative? True = phantom stock.

    A no-phantom-stock guard: the sovereign inventory ledger can refuse an issue that ships what is not there,
    rather than recording a negative on-hand that a reconciliation later discovers."""
    q = _dec(issue_qty)
    if q < 0:
        raise ValueError("issue_qty must be non-negative")
    return on_hand_for(movements, item, location) - q < 0
