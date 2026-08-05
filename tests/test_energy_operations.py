"""Acceptance tests for the Energy vertical (s5_22, Vol 24) — a governed asset-intensive operation composing the sealed
asset registry + maintenance + supply on-hand + compliance human-gate + posting. Pure / structural (F-1 clean)."""
import pytest

from sovereign_agent.energy.operations import plan_operation, authorize_operation, EnergyError


ASSET = {"id": "TURBINE-7", "currency": "USD", "cost": 1_000_000, "salvage": 50_000,
         "useful_life": 20, "status": "acquired"}
# governed on-hand: 10 SEAL-KITs and 4 BEARINGs at PLANT-A
MOVEMENTS = [
    {"item": "SEAL-KIT", "location": "PLANT-A", "qty": 10},
    {"item": "BEARING", "location": "PLANT-A", "qty": 4},
]


def test_plan_operation_composes_registered_asset_and_governed_parts():
    op = plan_operation(ASSET, "preventive", [{"item": "SEAL-KIT", "qty": 2}], MOVEMENTS, location="PLANT-A")
    assert op["asset"] == "TURBINE-7"
    assert op["status"] == "planned"
    assert op["work_order"]["status"] == "open"
    assert op["parts"] == [{"item": "SEAL-KIT", "qty": __import__("decimal").Decimal("2")}]
    assert op["currency"] == "USD"


def test_plan_operation_refuses_unregistered_asset():
    bad = dict(ASSET); bad["cost"] = 0  # invalid governed asset
    with pytest.raises(Exception):  # AssetError from the sealed registry
        plan_operation(bad, "preventive", [{"item": "SEAL-KIT", "qty": 1}], MOVEMENTS, location="PLANT-A")


def test_plan_operation_refuses_phantom_parts_that_would_overdraw():
    with pytest.raises(EnergyError):
        plan_operation(ASSET, "preventive", [{"item": "BEARING", "qty": 5}], MOVEMENTS, location="PLANT-A")


def test_authorize_operation_posts_balanced_cost_with_named_human():
    op = plan_operation(ASSET, "preventive", [{"item": "SEAL-KIT", "qty": 2}], MOVEMENTS, location="PLANT-A")
    res = authorize_operation(op, 12_500, approver="ops-lead", approval_ref="WO-2026-0042 signed")
    assert res["authorized"] is True
    p = res["posting"]
    from decimal import Decimal
    assert p["balanced"] is True
    assert sum(Decimal(l["debit"]) for l in p["lines"]) == sum(Decimal(l["credit"]) for l in p["lines"]) == Decimal("12500")


def test_authorize_operation_refuses_without_named_approver_or_ref():
    op = plan_operation(ASSET, "preventive", [{"item": "SEAL-KIT", "qty": 1}], MOVEMENTS, location="PLANT-A")
    with pytest.raises(EnergyError):
        authorize_operation(op, 500, approver="   ", approval_ref="WO signed")
    with pytest.raises(EnergyError):
        authorize_operation(op, 500, approver="ops-lead", approval_ref="")


def test_authorize_operation_refuses_nonexistent_operation():
    with pytest.raises(EnergyError):
        authorize_operation({}, 500, approver="ops-lead", approval_ref="WO signed")
