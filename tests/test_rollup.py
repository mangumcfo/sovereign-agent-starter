"""Dimensional-rollup invariants — co-extrusion for s5_17 (Option B+).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves a thin analytic rollup
over the sealed dimension engine -- aggregate tagged amounts to members, roll up value-conserving, projection only."""
from decimal import Decimal

import pytest

from sovereign_agent.analytics import rollup_metric
from sovereign_agent.financials import DimensionError

GEO = {
    "Global": {"parent": None},
    "NA": {"parent": "Global"},
    "EU": {"parent": "Global"},
    "US": {"parent": "NA"},
    "DE": {"parent": "EU"},
}
TAGGED = [
    {"amount": "100.00", "coord": {"geo": "US"}},
    {"amount": "40.00", "coord": {"geo": "DE"}},
    {"amount": "25.00", "coord": {"geo": "US"}},
]


def test_rollup_aggregates_and_conserves_to_roots():
    rolled = rollup_metric(TAGGED, "geo", GEO)
    assert rolled["US"] == Decimal("125.00")     # 100 + 25 aggregated to the leaf
    assert rolled["NA"] == Decimal("125.00")     # rolled up
    assert rolled["Global"] == Decimal("165.00") # root == sum of all tagged leaves (125 + 40)


def test_rollup_refuses_unknown_member():
    with pytest.raises(DimensionError):
        rollup_metric([{"amount": "10", "coord": {"geo": "Mars"}}], "geo", GEO)


def test_untagged_item_is_skipped():
    rolled = rollup_metric(TAGGED + [{"amount": "999", "coord": {}}], "geo", GEO)
    assert rolled["Global"] == Decimal("165.00")  # untagged 999 not counted
