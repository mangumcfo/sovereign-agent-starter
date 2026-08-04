"""Migration-primitive invariants — co-extrusion for s5_33 (The Migration Primitive, pivot volume).

Pure/structural: composes the sealed merkle accumulator (whose own tests are green in a pure public clone). Proves the
migration is value-conserving (reconciliation confirms source == migrated: nothing dropped, injected, mismatched, and
totals equal), that provenance anchors the migrated set to a merkle root, and that cutover is fail-closed (a migration
that does not reconcile cannot be cut over; an illegal lifecycle jump is refused; rollback is always available as a
fork)."""
from decimal import Decimal
import pytest
from sovereign_agent.migration import (
    reconcile, assert_reconciled, manifest_root, open_migration, transition, cutover, MigrationError,
)

from _substrate import substrate_available  # noqa: E402  (F-1 GUARD, KM 2026-08-04 — merkle provenance needs the substrate)
pytestmark = pytest.mark.skipif(not substrate_available(),
    reason="breathline_primitives (sealed crypto substrate) absent — honest skip, not a broken clone")

SOURCE = [{"id": "AR-1", "amount": "1000"}, {"id": "AR-2", "amount": "250.50"}, {"id": "AP-1", "amount": "-400"}]
GOOD = [{"id": "AR-1", "amount": "1000"}, {"id": "AR-2", "amount": "250.50"}, {"id": "AP-1", "amount": "-400"}]


def test_clean_migration_reconciles_and_conserves():
    rep = reconcile(SOURCE, GOOD)
    assert rep["reconciled"] is True
    assert rep["source_total"] == rep["migrated_total"] == Decimal("850.50")   # value conserved
    assert rep["dropped"] == [] and rep["added"] == [] and rep["mismatched"] == []


def test_dropped_record_refused():
    dropped = [{"id": "AR-1", "amount": "1000"}, {"id": "AR-2", "amount": "250.50"}]   # AP-1 lost
    rep = reconcile(SOURCE, dropped)
    assert rep["reconciled"] is False and rep["dropped"] == ["AP-1"]
    with pytest.raises(MigrationError):
        assert_reconciled(SOURCE, dropped)


def test_injected_and_mismatched_records_refused():
    tampered = [{"id": "AR-1", "amount": "1500"},                                   # mismatched amount
                {"id": "AR-2", "amount": "250.50"}, {"id": "AP-1", "amount": "-400"},
                {"id": "GHOST", "amount": "0"}]                                     # injected
    rep = reconcile(SOURCE, tampered)
    assert rep["mismatched"] == ["AR-1"] and rep["added"] == ["GHOST"]
    with pytest.raises(MigrationError):
        assert_reconciled(SOURCE, tampered)


def test_provenance_root_order_independent_and_distinguishes_sets():
    r1 = manifest_root(SOURCE)
    reordered = list(reversed(SOURCE))
    assert r1 and manifest_root(reordered) == r1                # SAME records in ANY order -> SAME root
    r3 = manifest_root(SOURCE[:2])
    assert r3 != r1                                              # a different set -> a different root
    altered = [{"id": "AR-1", "amount": "1000"}, {"id": "AR-2", "amount": "999"}, {"id": "AP-1", "amount": "-400"}]
    assert manifest_root(altered) != r1                         # any altered record -> a different root


def test_cutover_fail_closed_on_unreconciled():
    m = open_migration("MIG-1", SOURCE)
    m, _ = transition(m, "parallel")
    m, _ = transition(m, "reconciled")
    bad = [{"id": "AR-1", "amount": "9999"}, {"id": "AR-2", "amount": "250.50"}, {"id": "AP-1", "amount": "-400"}]
    with pytest.raises(MigrationError):
        cutover(m, bad)                                          # does not reconcile -> cutover refused
    done = cutover(m, GOOD)                                      # reconciles -> cutover
    assert done["status"] == "cutover" and done["migrated_root"] == manifest_root(GOOD)


def test_lifecycle_fail_closed_and_rollback_is_a_fork():
    m = open_migration("MIG-2", SOURCE)
    with pytest.raises(MigrationError):
        transition(m, "cutover")                                # prepared -> cutover is not an allowed edge
    m, _ = transition(m, "parallel")
    m, _ = transition(m, "reconciled")
    m = cutover(m, GOOD)
    rolled, ev = transition(m, "rolled_back")                   # rollback always available as a fork from cutover
    assert rolled["status"] == "rolled_back" and ev["from"] == "cutover"
