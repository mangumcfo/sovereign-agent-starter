"""Driver-model library invariants — co-extrusion for s5_40 (Option B expansion).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the driver library --
named drivers compute weights from a governed base measure, and allocate_by_driver feeds them to the sealed
value-conserving allocation so the spread still sums to the pool exactly. A predictive/learned driver is forecasting
(S5-V17), not here."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    weights_from_driver, allocate_by_driver, DriverError, PROPORTIONAL, EQUAL, FIXED,
)


def test_proportional_driver_weights_track_the_measure():
    w = weights_from_driver(PROPORTIONAL, {"CC-A": 30, "CC-B": 10})
    assert w == {"CC-A": Decimal("30"), "CC-B": Decimal("10")}


def test_equal_driver_ignores_the_measure():
    w = weights_from_driver(EQUAL, {"CC-A": 30, "CC-B": 10})
    assert w == {"CC-A": Decimal("1"), "CC-B": Decimal("1")}


def test_unknown_driver_and_negative_measure_are_refused():
    with pytest.raises(DriverError):
        weights_from_driver("crystal-ball", {"CC-A": 1})
    with pytest.raises(DriverError):
        weights_from_driver(PROPORTIONAL, {"CC-A": -5})
    with pytest.raises(DriverError):
        weights_from_driver(PROPORTIONAL, {"CC-A": 0, "CC-B": 0})


def test_allocate_by_driver_conserves_the_pool():
    # headcount driver: assembly (60) vs weld (20) vs paint (20) -> proportional split of 1000.00
    alloc = allocate_by_driver("1000.00", PROPORTIONAL, {"assembly": 60, "weld": 20, "paint": 20})
    assert sum(alloc.values(), Decimal("0")) == Decimal("1000.00")
    assert alloc["assembly"] == Decimal("600.00")
    assert alloc["weld"] == Decimal("200.00")
    assert alloc["paint"] == Decimal("200.00")


def test_equal_driver_splits_evenly_and_conserves_with_residual_placed():
    alloc = allocate_by_driver("1000.00", EQUAL, {"a": 1, "b": 1, "c": 1})
    assert sum(alloc.values(), Decimal("0")) == Decimal("1000.00")  # residual placed, nothing lost
