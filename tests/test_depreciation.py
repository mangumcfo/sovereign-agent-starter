"""Depreciation invariants — co-extrusion for s5_12 (Asset & Maintenance).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the depreciation
schedule is VALUE-CONSERVING -- the period charges sum exactly to the depreciable base and the net book value ends at
exactly the salvage value -- for both named methods, with the last period absorbing any rounding residual."""
from decimal import Decimal

import pytest

from sovereign_agent.assets import (
    straight_line, units_of_production, schedule, STRAIGHT_LINE, UNITS_OF_PRODUCTION, DepreciationError,
)


def test_straight_line_conserves_value_and_ends_at_salvage():
    s = schedule("100000", "10000", life=10, method=STRAIGHT_LINE)
    assert sum(s["charges"], Decimal("0")) == Decimal("90000")     # charges sum to cost - salvage
    assert s["net_book_value"][-1] == Decimal("10000")             # ends at salvage
    assert len(s["charges"]) == 10


def test_straight_line_last_period_absorbs_rounding():
    # base 100.00 over 3 periods = 33.33 each, last absorbs -> 33.33 + 33.33 + 33.34 = 100.00
    ch = straight_line("100", "0", 3)
    assert ch == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(ch, Decimal("0")) == Decimal("100.00")


def test_units_of_production_conserves_value():
    ch = units_of_production("50000", "5000", period_units=[100, 300, 100])   # base 45000 over 500 units
    assert sum(ch, Decimal("0")) == Decimal("45000.00")
    assert ch[1] > ch[0]                                            # the heavy-use period depreciates more


def test_bad_inputs_refused():
    with pytest.raises(DepreciationError):
        straight_line("100", "200", 5)                             # salvage > cost
    with pytest.raises(DepreciationError):
        straight_line("100", "0", 0)                               # life < 1
    with pytest.raises(DepreciationError):
        units_of_production("100", "0", period_units=[])           # no units
    with pytest.raises(DepreciationError):
        schedule("100", "0", method="declining_balance")          # unknown method
