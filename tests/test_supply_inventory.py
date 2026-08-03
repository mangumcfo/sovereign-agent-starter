"""Inventory on-hand + no-phantom-stock invariants — co-extrusion for s5_09 Supply Chain Execution.

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the supply-chain
views over governed inventory movements — on-hand per item/location (locations never blended) and a no-phantom-stock
check — independently of the immutability/provenance the ObligationLedger + object model supply."""
from decimal import Decimal

import pytest

from sovereign_agent.supply import on_hand, on_hand_for, would_overdraw, NegativeStockError


def test_on_hand_nets_receipts_and_issues_per_item_location():
    mv = [
        {"item": "SKU-1", "location": "WH-A", "qty": "100"},
        {"item": "SKU-1", "location": "WH-A", "qty": "-30"},
        {"item": "SKU-1", "location": "WH-B", "qty": "50"},
    ]
    q = on_hand(mv)
    assert q[("SKU-1", "WH-A")] == Decimal("70")
    assert q[("SKU-1", "WH-B")] == Decimal("50")


def test_locations_are_never_blended():
    mv = [{"item": "SKU-1", "location": "WH-A", "qty": "10"},
          {"item": "SKU-1", "location": "WH-B", "qty": "10"}]
    # same item, two locations -> two distinct on-hands, never one blended "20 available"
    assert on_hand_for(mv, "SKU-1", "WH-A") == Decimal("10")
    assert on_hand_for(mv, "SKU-1", "WH-B") == Decimal("10")


def test_no_phantom_stock_check():
    mv = [{"item": "SKU-1", "location": "WH-A", "qty": "40"}]
    assert would_overdraw(mv, "SKU-1", "WH-A", "50") is True   # ship 50 from 40 -> phantom
    assert would_overdraw(mv, "SKU-1", "WH-A", "40") is False  # ship exactly what's there
    # a location with no stock cannot ship
    assert would_overdraw(mv, "SKU-1", "WH-B", "1") is True


def test_negative_issue_rejected():
    with pytest.raises(ValueError):
        would_overdraw([], "SKU-1", "WH-A", "-5")
