"""Multi-entity structure invariants — co-extrusion for s5_18 (Multi-Entity & Consolidation).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the entity registry
validates fail-closed and that the group under a root is the set control implies -- ownership > 50% consolidates,
50%-or-less does not."""
from decimal import Decimal

import pytest

from sovereign_agent.consolidation import (
    validate_structure, group_members, effective_ownership, EntityError,
)

GROUP = {
    "Parent": {"parent": None, "ownership_pct": 0, "currency": "USD"},
    "Sub60":  {"parent": "Parent", "ownership_pct": 60, "currency": "USD"},   # controlled
    "SubSub": {"parent": "Sub60", "ownership_pct": 100, "currency": "EUR"},   # controlled via Sub60
    "Assoc40": {"parent": "Parent", "ownership_pct": 40, "currency": "USD"},  # NOT controlled (<=50)
}


def test_group_members_follow_control_not_mere_ownership():
    m = group_members(GROUP, "Parent")
    assert m == {"Parent", "Sub60", "SubSub"}     # Assoc40 (40%) is an investment, not consolidated


def test_effective_ownership_is_the_chain_product():
    # Parent -> Sub60 (60%) -> SubSub (100%) => 0.60
    assert effective_ownership(GROUP, "Parent", "SubSub") == Decimal("0.60")
    assert effective_ownership(GROUP, "Parent", "Parent") == Decimal("1")


def test_validate_refuses_bad_structure():
    with pytest.raises(EntityError):
        validate_structure({"A": {"parent": "ghost", "ownership_pct": 100, "currency": "USD"}})
    with pytest.raises(EntityError):
        validate_structure({"A": {"parent": None, "ownership_pct": 150, "currency": "USD"}})
    with pytest.raises(EntityError):
        validate_structure({"A": {"parent": None, "ownership_pct": 100}})   # no currency
    # ownership cycle
    with pytest.raises(EntityError):
        validate_structure({
            "A": {"parent": "B", "ownership_pct": 100, "currency": "USD"},
            "B": {"parent": "A", "ownership_pct": 100, "currency": "USD"},
        })
