"""Unbinding-Salesforce invariants — co-extrusion for s5_35 (Unbinding Salesforce, escape arc 2/4).

Pure/structural: composes the sealed floors — the migration primitive (manifest_root provenance + lifecycle), the sealed
mandate guard (mandate scope + fail-closed authorization), the sealed revenue billing, and the sealed balanced posting.
Proves a won Salesforce opportunity becomes a governed, mandate-scoped commitment (an unwon opportunity or non-positive
amount refused); the receipted cutover is value-conserving (every won opportunity carried to a mandate, the total
conserved) and provenance-anchored; billing a governed mandate is fail-closed on its mandate authorization (barred for a
non-holder) and posts a balanced AR/revenue double-entry; and the posting integrates with the sealed ledger's own
trial_balance (the posting-shape spine, proven in code)."""
from decimal import Decimal
import pytest
from sovereign_agent.migration.salesforce import (
    opportunity_to_mandate, map_opportunities, bill_mandate, receipted_cutover, SalesforceError,
)
from sovereign_agent.financials.posting import trial_balance

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD, KM 2026-08-04 — merkle provenance needs the substrate)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

WON = [{"id": "OPP-1", "account": "Acme", "amount": "10000", "is_won": True},
       {"id": "OPP-2", "account": "Globex", "amount": "2500", "is_won": True}]
MMAP = {"OPP-1": "MANDATE-SALES", "OPP-2": "MANDATE-SALES"}


def test_won_opportunity_becomes_governed_mandate():
    m = opportunity_to_mandate(WON[0], "MANDATE-SALES")
    assert m["status"] == "governed" and m["mandate"] == "MANDATE-SALES"
    assert m["amount"] == "10000" and m["account"] == "Acme"


def test_unwon_or_nonpositive_refused():
    with pytest.raises(SalesforceError):
        opportunity_to_mandate({"id": "OPP-X", "amount": "5000", "is_won": False}, "M")   # not won
    with pytest.raises(SalesforceError):
        opportunity_to_mandate({"id": "OPP-Y", "amount": "0", "is_won": True}, "M")        # non-positive


def test_cutover_conserves_and_anchors():
    rec = receipted_cutover("MIG-SF-1", WON, MMAP)
    assert rec["status"] == "cutover"
    assert sum(Decimal(m["amount"]) for m in rec["mandates"]) == Decimal("12500")          # total conserved
    assert rec["source_root"] and rec["mandate_root"]


def test_unmapped_opportunity_refused():
    with pytest.raises(SalesforceError):
        receipted_cutover("MIG-SF-2", WON, {"OPP-1": "MANDATE-SALES"})                     # OPP-2 unmapped


def test_bill_mandate_authorized_posts_balanced():
    m = opportunity_to_mandate(WON[0], "MANDATE-SALES")
    approval = {"held_mandates": ["MANDATE-SALES"]}                                        # holds the mandate
    res = bill_mandate(m, approval)
    assert res["invoice"]["total"] == Decimal("10000")
    p = res["posting"]
    assert p["balanced"] is True and Decimal(p["amount"]) == Decimal("10000")                                # balanced AR/revenue


def test_bill_mandate_barred_for_non_holder():
    m = opportunity_to_mandate(WON[0], "MANDATE-SALES")
    with pytest.raises(SalesforceError):
        bill_mandate(m, {"held_mandates": ["MANDATE-OTHER"]})                              # does not hold M -> barred


def test_source_root_order_independent():
    r1 = receipted_cutover("MIG-SF-3", WON, MMAP)["source_root"]
    r2 = receipted_cutover("MIG-SF-4", list(reversed(WON)), MMAP)["source_root"]
    assert r1 == r2 and r1                                                                 # depends on the SET, not order


def test_bill_posting_integrates_with_sealed_ledger():
    """SPINE integration step (AA meta lane §3): a governed mandate's bill is a first-class sealed-ledger posting.
    Run bill_mandate's posting back through the sealed ledger's trial_balance projection and confirm it nets to a
    balanced AR/revenue movement -- crossing crm.mandate -> financials.posting; the posting-shape spine proven in code."""
    m = opportunity_to_mandate(WON[0], "MANDATE-SALES")
    res = bill_mandate(m, {"held_mandates": ["MANDATE-SALES"]})
    tb = trial_balance([res["posting"]])
    assert tb == {"1100-AR": Decimal("10000"), "4000-Revenue": Decimal("-10000")}          # AR debit, revenue credit
    assert sum(tb.values(), Decimal("0")) == Decimal("0")                                  # balances by construction
