"""Portfolio-carve-in invariants — co-extrusion for s5_36 (Consuming the Giants, escape arc 3/4).

Pure/structural: composes the sealed floors — the migration primitive (per-record reconciliation, provenance, lifecycle),
the sealed QuickBooks opening-entry emitter, and the sealed balanced posting. Proves a carved-in enterprise ledger is
reconciled value-conserving (per-record; drop/inject/alter refused), that carve-in cutover is fail-closed per ledger
(an unreconciled ledger cannot cut over), that a portfolio cutover is refused unless EVERY ledger reconciles, that the
opening balances post as a balanced double-entry, and that the aggregate provenance root is order-independent."""
from decimal import Decimal
import pytest
from sovereign_agent.migration.carve_in import (
    open_carve_in, reconcile_carve_in, carve_in_cutover, portfolio_root, portfolio_cutover, CarveInError,
)
from sovereign_agent.financials.posting import trial_balance
from sovereign_agent.migration.reconcile import MigrationError

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD, KM 2026-08-05 — merkle provenance needs the substrate)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

# A carved-in enterprise ledger (signed trial balance, sums to zero).
SAP = {"1000-Cash": "5000", "1200-AR": "3000", "2000-AP": "-2000", "3000-Equity": "-6000"}
SAP_OK = dict(SAP)                                              # migrated identically -> conserves
NETSUITE = {"1000-Cash": "1000", "3000-Equity": "-1000"}


def test_carve_in_reconciles_and_cuts_over_balanced():
    ci = open_carve_in("SAP", SAP)
    assert ci["status"] == "prepared" and ci["source_root"]
    done = carve_in_cutover(ci, SAP_OK)
    assert done["status"] == "cutover" and done["migrated_root"]
    p = done["opening_posting"]
    assert p["balanced"] is True and Decimal(p["amount"]) == Decimal("8000")   # debit-normal total (Cash+AR)
    # the opening posting is the canonical {lines} shape (composed opening_entry -> from_entry), AA meta lane §1:
    assert [ln["account"] for ln in p["lines"]] == ["1000-Cash", "1200-AR", "2000-AP", "3000-Equity"]


def test_carve_in_cutover_fail_closed_on_unreconciled():
    ci = open_carve_in("SAP", SAP)
    dropped = {"1000-Cash": "5000", "1200-AR": "3000", "2000-AP": "-2000"}      # 3000-Equity dropped
    with pytest.raises(MigrationError):
        carve_in_cutover(ci, dropped)                                          # does not reconcile -> refused (assert_reconciled)


def test_portfolio_cutover_fail_closed_if_any_ledger_fails():
    good = {"system": "SAP", "source_tb": SAP, "migrated_tb": SAP_OK}
    bad = {"system": "NetSuite", "source_tb": NETSUITE,
           "migrated_tb": {"1000-Cash": "999", "3000-Equity": "-1000"}}        # altered -> does not reconcile
    with pytest.raises(CarveInError):
        portfolio_cutover("PORT-1", [good, bad])                              # one bad ledger refuses the whole portfolio


def test_portfolio_cutover_all_reconcile_aggregates():
    good1 = {"system": "SAP", "source_tb": SAP, "migrated_tb": SAP_OK}
    good2 = {"system": "NetSuite", "source_tb": NETSUITE, "migrated_tb": dict(NETSUITE)}
    port = portfolio_cutover("PORT-2", [good1, good2])
    assert port["systems"] == ["SAP", "NetSuite"] and port["aggregate_root"]
    assert all(c["status"] == "cutover" for c in port["carve_ins"])


def test_aggregate_root_order_independent():
    good1 = {"system": "SAP", "source_tb": SAP, "migrated_tb": SAP_OK}
    good2 = {"system": "NetSuite", "source_tb": NETSUITE, "migrated_tb": dict(NETSUITE)}
    r1 = portfolio_cutover("PORT-3", [good1, good2])["aggregate_root"]
    r2 = portfolio_cutover("PORT-4", [good2, good1])["aggregate_root"]         # reversed order, same set
    assert r1 == r2 and r1                                                     # aggregate root depends on the SET


def test_reconcile_carve_in_detects_variance():
    rep = reconcile_carve_in(SAP, {"1000-Cash": "5000", "1200-AR": "3000", "2000-AP": "-2000"})  # equity dropped
    assert rep["reconciled"] is False and "3000-Equity" in rep["dropped"]


def test_carve_in_posting_integrates_with_sealed_ledger():
    """SPINE integration step (AA meta lane §3): a carve-in's opening balances are a first-class sealed-ledger posting.
    Run carve_in_cutover's opening posting through the sealed ledger's trial_balance projection and confirm it
    reconstitutes the migrated ledger (signed) -- crossing migration.carve_in -> financials.posting."""
    done = carve_in_cutover(open_carve_in("SAP", SAP), SAP_OK)
    tb = trial_balance([done["opening_posting"]])
    assert tb == {"1000-Cash": Decimal("5000"), "1200-AR": Decimal("3000"),
                  "2000-AP": Decimal("-2000"), "3000-Equity": Decimal("-6000")}
    assert sum(tb.values(), Decimal("0")) == Decimal("0")                     # balances by construction
