"""Maintenance invariants — co-extrusion for s5_12 (Asset & Maintenance).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the work-order
lifecycle is fail-closed (no step skipped) and that preventive work orders are a deterministic consequence of meter
readings, not a planner's discretion."""
import pytest

from sovereign_agent.assets import (
    open_work_order, advance, meter_triggered, due_work_orders, MaintenanceError,
)


def test_work_order_lifecycle_is_fail_closed():
    wo = open_work_order("PRESS-01", "corrective")
    wo = advance(wo, "approved")
    wo = advance(wo, "executed")
    wo = advance(wo, "closed")
    assert wo["status"] == "closed"


def test_work_order_cannot_skip_a_step():
    wo = open_work_order("PRESS-01", "corrective")
    with pytest.raises(MaintenanceError):
        advance(wo, "executed")            # cannot execute an unapproved order
    with pytest.raises(MaintenanceError):
        advance(advance(wo, "approved"), "closed")   # cannot close an unexecuted order


def test_meter_trigger_is_deterministic():
    assert meter_triggered("10000", "10000") is True      # reaching the threshold triggers
    assert meter_triggered("9999.99", "10000") is False
    readings = [
        {"asset": "PUMP-1", "reading": "12000", "threshold": "10000"},
        {"asset": "PUMP-2", "reading": "8000", "threshold": "10000"},
        {"asset": "PUMP-3", "reading": "10000", "threshold": "10000"},
    ]
    due = due_work_orders(readings)
    assert {w["asset"] for w in due} == {"PUMP-1", "PUMP-3"}       # only those at/over threshold, deterministically
    assert all(w["status"] == "open" and w["kind"] == "preventive" for w in due)


def test_malformed_reading_refused():
    with pytest.raises(MaintenanceError):
        due_work_orders([{"asset": "X", "reading": "5"}])          # missing threshold
