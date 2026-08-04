"""Asset registry / lifecycle invariants — co-extrusion for s5_12 (Asset & Maintenance).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the asset lifecycle is
a fail-closed state machine and that a malformed asset is refused."""
import pytest

from sovereign_agent.assets import validate_asset, can_transition, transition, AssetError

ASSET = {"id": "PRESS-01", "cost": "100000", "salvage": "10000", "useful_life": 10, "currency": "USD"}


def test_lifecycle_allows_only_governed_transitions():
    a = dict(ASSET, status="acquired")
    a2, ev = transition(a, "in_service", period="2026-01")
    assert a2["status"] == "in_service" and ev["from"] == "acquired" and ev["to"] == "in_service"
    assert a["status"] == "acquired"                    # input not mutated
    a3, _ = transition(a2, "retired", period="2030-01")
    a4, _ = transition(a3, "disposed", period="2030-02")
    assert a4["status"] == "disposed"


def test_illegal_transition_is_refused():
    a = dict(ASSET, status="in_service")
    with pytest.raises(AssetError):
        transition(a, "disposed", period="2026-06")     # must retire before disposing
    with pytest.raises(AssetError):
        transition(dict(ASSET, status="disposed"), "in_service", period="2026-06")  # no reviving a disposed asset
    assert can_transition("acquired", "in_service") and not can_transition("acquired", "retired")


def test_malformed_asset_refused():
    with pytest.raises(AssetError):
        validate_asset({"id": "X", "cost": "0", "salvage": "0", "useful_life": 5, "currency": "USD"})   # cost>0
    with pytest.raises(AssetError):
        validate_asset({"id": "X", "cost": "100", "salvage": "200", "useful_life": 5, "currency": "USD"})  # salvage<=cost
    with pytest.raises(AssetError):
        validate_asset({"id": "X", "cost": "100", "salvage": "0", "useful_life": 0, "currency": "USD"})   # life>=1
    with pytest.raises(AssetError):
        validate_asset({"id": "X", "cost": "100", "salvage": "0", "useful_life": 5})                      # no currency
