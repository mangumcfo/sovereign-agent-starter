"""Forecast invariants — co-extrusion for s5_17 (discharges the forecasting->S5-V17 debt).

Pure arithmetic: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves transparent, named
projections (moving average, linear trend) that carry their method + inputs (re-runnable, not black-box) and governed
scenarios that record the named adjustments applied."""
from decimal import Decimal

import pytest

from sovereign_agent.analytics import project, scenario, ForecastError, MOVING_AVERAGE, LINEAR_TREND


def test_moving_average_projects_flat_from_stable_history():
    r = project([100, 100, 100], periods=2, method=MOVING_AVERAGE, window=3)
    assert r["method"] == "moving_average"
    assert r["projections"] == [Decimal("100.00"), Decimal("100.00")]


def test_linear_trend_extrapolates_the_slope():
    # history 100,110,120 -> slope 10; next two = 130, 140
    r = project([100, 110, 120], periods=2, method=LINEAR_TREND)
    assert r["projections"] == [Decimal("130.00"), Decimal("140.00")]


def test_result_carries_method_and_history_for_reproducibility():
    r = project([10, 20], periods=1, method=LINEAR_TREND)
    assert r["history"] == [Decimal("10"), Decimal("20")] and r["method"] == "linear_trend"


def test_unknown_method_and_bad_horizon_refused():
    with pytest.raises(ForecastError):
        project([1, 2, 3], periods=1, method="neural-net")   # no black box
    with pytest.raises(ForecastError):
        project([1, 2, 3], periods=0)
    with pytest.raises(ForecastError):
        project([100], periods=1, method=LINEAR_TREND)        # too short for a trend


def test_scenario_applies_named_adjustments_reproducibly():
    base = project([100, 100, 100], periods=2, method=MOVING_AVERAGE)
    up = scenario(base, {"factor": "1.10"})
    assert up["projections"] == [Decimal("110.00"), Decimal("110.00")]
    assert up["adjustments"]["factor"] == Decimal("1.10")
    plus = scenario(base, {"delta": "25"})
    assert plus["projections"] == [Decimal("125.00"), Decimal("125.00")]


# ---- Option B+ named methods: weighted moving average + exponential moving average ----
from sovereign_agent.analytics import WEIGHTED_MOVING_AVERAGE, EXPONENTIAL_MOVING_AVERAGE


def test_weighted_moving_average_weights_recent_more():
    # history 10,20,30 window 3: weights 1,2,3 -> (10*1+20*2+30*3)/6 = 140/6 = 23.33
    r = project([10, 20, 30], periods=1, method=WEIGHTED_MOVING_AVERAGE, window=3)
    assert r["method"] == "weighted_moving_average"
    assert r["projections"][0] == Decimal("23.33")
    assert r["params"]["window"] == 3


def test_exponential_moving_average_holds_at_final_ema():
    # history 100,110,120 alpha 0.5: ema0=100; ema1=.5*110+.5*100=105; ema2=.5*120+.5*105=112.50 -> flat
    r = project([100, 110, 120], periods=2, method=EXPONENTIAL_MOVING_AVERAGE, alpha="0.5")
    assert r["projections"] == [Decimal("112.50"), Decimal("112.50")]
    assert r["params"]["alpha"] == Decimal("0.5")


def test_ema_alpha_out_of_range_refused():
    with pytest.raises(ForecastError):
        project([1, 2, 3], periods=1, method=EXPONENTIAL_MOVING_AVERAGE, alpha="0")
    with pytest.raises(ForecastError):
        project([1, 2, 3], periods=1, method=EXPONENTIAL_MOVING_AVERAGE, alpha="1.5")
