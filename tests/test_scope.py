"""Scope invariants — co-extrusion for s5_14 (Option B+).

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves jurisdiction/standard
scope as a first-class object -- selecting standards and packs by scope, refusing an unknown scope or member, and
multi-jurisdiction selection as the union across scopes."""
import pytest

from sovereign_agent.compliance.scope import make_scope, select_for_scope, select_for_scopes, ScopeError

STANDARDS = {"SOX-lite": {"v": "1"}, "ISO-27001": {"v": "1"}, "EU-VAT": {"v": "1"}}
PACKS = {"management": [], "statutory": []}
US = make_scope("US", "United States", ["SOX-lite"], ["management", "statutory"])
EU = make_scope("EU", "European Union", ["ISO-27001", "EU-VAT"], ["statutory"])
REG = {"US": US, "EU": EU}


def test_make_scope_refuses_empty_binding():
    with pytest.raises(ScopeError):
        make_scope("X", "Nowhere", [], [])


def test_select_for_scope_resolves_members():
    sel = select_for_scope(US, STANDARDS, PACKS)
    assert set(sel["standards"]) == {"SOX-lite"}
    assert set(sel["packs"]) == {"management", "statutory"}


def test_select_refuses_unknown_member():
    bad = make_scope("BAD", "Bad", ["NONEXISTENT"], [])
    with pytest.raises(ScopeError):
        select_for_scope(bad, STANDARDS, PACKS)


def test_multi_jurisdiction_selection_is_the_union():
    sel = select_for_scopes(["US", "EU"], REG, STANDARDS, PACKS)
    assert set(sel["standards"]) == {"SOX-lite", "ISO-27001", "EU-VAT"}
    assert set(sel["packs"]) == {"management", "statutory"}
    assert sel["scopes"] == ["US", "EU"]


def test_unknown_scope_id_refused():
    with pytest.raises(ScopeError):
        select_for_scopes(["US", "MARS"], REG, STANDARDS, PACKS)
    with pytest.raises(ScopeError):
        select_for_scopes([], REG, STANDARDS, PACKS)
