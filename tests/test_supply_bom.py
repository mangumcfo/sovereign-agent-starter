"""BOM explosion + build-feasibility invariants — co-extrusion for s5_10 Manufacturing & Quality.

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the material
arithmetic a governed work order must satisfy — required components scale with build quantity, and a build is
feasible only when governed on-hand covers the requirement (shortfalls reported honestly) — independently of the
governance/provenance the ObligationLedger + object model supply."""
from decimal import Decimal

import pytest

from sovereign_agent.supply import explode_bom, can_build


BOM = {"steel-plate": "2", "bolt": "8", "coating-L": "0.5"}


def test_explode_scales_with_build_qty():
    req = explode_bom(BOM, "10")
    assert req["steel-plate"] == Decimal("20")
    assert req["bolt"] == Decimal("80")
    assert req["coating-L"] == Decimal("5.0")


def test_explode_rejects_bad_inputs():
    with pytest.raises(ValueError):
        explode_bom(BOM, "0")
    with pytest.raises(ValueError):
        explode_bom({}, "5")
    with pytest.raises(ValueError):
        explode_bom({"x": "-1"}, "5")


def test_can_build_feasible_when_stock_covers():
    mv = [
        {"item": "steel-plate", "location": "WH-A", "qty": "50"},
        {"item": "bolt", "location": "WH-A", "qty": "200"},
        {"item": "coating-L", "location": "WH-A", "qty": "20"},
    ]
    r = can_build(BOM, "10", mv, "WH-A")
    assert r["feasible"] is True and r["shortfalls"] == {}


def test_can_build_reports_shortfalls():
    mv = [
        {"item": "steel-plate", "location": "WH-A", "qty": "5"},   # need 20 -> short 15
        {"item": "bolt", "location": "WH-A", "qty": "200"},
        {"item": "coating-L", "location": "WH-A", "qty": "1"},     # need 5 -> short 4
    ]
    r = can_build(BOM, "10", mv, "WH-A")
    assert r["feasible"] is False
    assert r["shortfalls"]["steel-plate"] == Decimal("15")
    assert r["shortfalls"]["coating-L"] == Decimal("4.0")
    assert "bolt" not in r["shortfalls"]
