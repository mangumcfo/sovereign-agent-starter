"""Dimension-engine invariants — co-extrusion for s5_40 (Option B expansion).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the multi-dimensional
modeling floor -- validated dimensions, value-conserving roll-up by a dimension, and value-conserving slicing of the
same tagged amounts by any dimension. The BI/reporting layer over this is elsewhere (reporting -> S5-V14)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import (
    validate_dimension, roll_up_members, slice_amounts, DimensionError,
)

GEO = {
    "Global": {"parent": None},
    "NA": {"parent": "Global"},
    "EU": {"parent": "Global"},
    "US": {"parent": "NA"},
    "DE": {"parent": "EU"},
}


def test_validate_dimension_accepts_a_valid_hierarchy():
    validate_dimension(GEO)


def test_validate_dimension_rejects_missing_parent_and_cycle():
    with pytest.raises(DimensionError):
        validate_dimension({"US": {"parent": "Nowhere"}})
    with pytest.raises(DimensionError):
        validate_dimension({"A": {"parent": "B"}, "B": {"parent": "A"}})


def test_roll_up_members_conserves_value_to_roots():
    rolled = roll_up_members({"US": "100.00", "DE": "40.00"}, GEO)
    assert rolled["NA"] == Decimal("100.00")
    assert rolled["EU"] == Decimal("40.00")
    assert rolled["Global"] == Decimal("140.00")  # root == sum of all leaves


def test_slice_amounts_totals_a_member_and_its_descendants():
    tagged = [
        {"amount": "100.00", "coord": {"geo": "US", "product": "P1"}},
        {"amount": "40.00", "coord": {"geo": "DE", "product": "P1"}},
        {"amount": "25.00", "coord": {"geo": "US", "product": "P2"}},
    ]
    # slice at NA -> only US rows (US is under NA); DE is under EU
    assert slice_amounts(tagged, "geo", "NA", GEO) == Decimal("125.00")
    # slice at Global (root) totals everything -> value conservation across the dimension
    assert slice_amounts(tagged, "geo", "Global", GEO) == Decimal("165.00")


def test_slice_rejects_a_member_not_in_dimension():
    with pytest.raises(DimensionError):
        slice_amounts([], "geo", "Mars", GEO)


def test_slice_rejects_a_tagged_amount_with_unknown_member():
    bad = [{"amount": "10", "coord": {"geo": "Atlantis"}}]
    with pytest.raises(DimensionError):
        slice_amounts(bad, "geo", "Global", GEO)
