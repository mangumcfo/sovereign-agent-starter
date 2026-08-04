"""Consolidation invariants — co-extrusion for s5_18 (Multi-Entity & Consolidation), the volume's spine.

Pure/structural: NO sealed crypto substrate, runs green in a pure public clone (no skip). Proves the group view is a
value-conserving PROJECTION over governed entity ledgers: intercompany eliminated, foreign entities FX-translated with
a CTA plug, the group trial balance nets to zero, and re-running the projection changes nothing (read-only)."""
from decimal import Decimal

import pytest

from sovereign_agent.financials import Line, post
from sovereign_agent.consolidation import (
    consolidate, record_intercompany, ConsolidationError, CTA_ACCOUNT,
)

ENTITIES = {
    "Parent": {"parent": None, "ownership_pct": 0, "currency": "USD"},
    "Sub":    {"parent": "Parent", "ownership_pct": 100, "currency": "USD"},
    "Euro":   {"parent": "Parent", "ownership_pct": 80, "currency": "EUR"},
    "Assoc":  {"parent": "Parent", "ownership_pct": 40, "currency": "USD"},   # not controlled
}


def _ledgers():
    return {
        "Parent": [post([Line.dr("cash", "500"), Line.cr("equity", "500")])],
        "Sub":    [post([Line.dr("cash", "200"), Line.cr("revenue", "200")]),
                   post([Line.dr("expense", "200"), Line.cr("cash", "200")])],
        "Euro":   [post([Line.dr("cash", "100"), Line.cr("equity", "100")])],
        "Assoc":  [post([Line.dr("cash", "999"), Line.cr("equity", "999")])],
    }


def test_group_is_value_conserving_projection_excluding_non_controlled():
    r = consolidate(ENTITIES, "Parent", _ledgers(), "USD", fx_rates={"EUR": "1.10"})
    assert r["balances"] is True                       # group trial balance nets to zero
    assert "Assoc" not in r["members"]                 # 40% is an investment, not consolidated
    assert set(r["members"]) == {"Parent", "Sub", "Euro"}
    # Euro's 100 EUR cash translates at 1.10 -> 110.00 USD in the group
    assert r["group"]["cash"] == Decimal("500") + Decimal("110.00") - Decimal("0")  # Sub cash nets to 0


def test_intercompany_is_eliminated_at_the_group():
    led = _ledgers()
    ic = record_intercompany("IC1", "Sub", "Parent", "150", seller_account="revenue", buyer_account="expense")
    led["Sub"].append(ic["entries"]["Sub"])
    led["Parent"].append(ic["entries"]["Parent"])
    r = consolidate(ENTITIES, "Parent", led, "USD", fx_rates={"EUR": "1.10"},
                    intercompany_records=[ic])
    # the intercompany accounts are gone from the group, and recorded as eliminations
    assert not any(a.startswith("IC_") for a in r["group"])
    assert r["eliminations"]["IC_receivable:Parent"] == "150"
    assert r["eliminations"]["IC_payable:Sub"] == "-150"
    assert r["balances"] is True                       # elimination is value-conserving


def test_fx_translation_balances_via_cta_and_missing_rate_refused():
    # a rate chosen so per-account cent-rounding leaves a residual the CTA must absorb
    ent = {"P": {"parent": None, "ownership_pct": 0, "currency": "USD"},
           "F": {"parent": "P", "ownership_pct": 100, "currency": "GBP"}}
    led = {"P": [post([Line.dr("cash", "10"), Line.cr("equity", "10")])],
           "F": [post([Line.dr("a", "3.33"), Line.dr("b", "3.33"), Line.cr("equity", "6.66")])]}
    r = consolidate(ent, "P", led, "USD", fx_rates={"GBP": "1.115"})
    fbal = r["entity_balances"]["F"]
    assert sum((Decimal(v) for v in fbal.values()), Decimal("0")) == Decimal("0")  # translated entity balances
    assert r["balances"] is True
    # a group entity in a foreign currency with no supplied rate is refused, not silently blended
    with pytest.raises(ConsolidationError):
        consolidate(ent, "P", led, "USD", fx_rates={})


def test_group_view_is_a_projection_not_a_mutation():
    led = _ledgers()
    before = {e: len(p) for e, p in led.items()}
    a = consolidate(ENTITIES, "Parent", led, "USD", fx_rates={"EUR": "1.10"})
    b = consolidate(ENTITIES, "Parent", led, "USD", fx_rates={"EUR": "1.10"})
    assert a["group"] == b["group"]                          # deterministic, re-runnable
    assert {e: len(p) for e, p in led.items()} == before      # inputs untouched — no stored second truth
