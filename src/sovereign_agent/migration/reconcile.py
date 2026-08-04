"""Migration — a governed, verifiable migration primitive: value-conserving reconciliation, provenance, and fail-closed
cutover, composing the sealed floors rather than reimplementing them.

Co-extrusion for s5_33 (The Migration Primitive, KM 2026-08-04). Pure / structural, no crypto substrate beyond the
sealed merkle accumulator it composes (which runs in a pure public clone -- its own tests are green here). Most ERP
migrations fail the same way: records are dropped, doubled, or silently altered on the way from a legacy system to the
new one, and the failure is discovered -- if ever -- long after cutover, when the two systems no longer agree and no one
can say which is right. This primitive makes a migration a verifiable, value-conserving act. Reconciliation proves the
migrated record set conserves the source: every source record has a migrated counterpart, none is dropped or injected,
the per-record values match, and the totals are equal -- so nothing is created or lost in the migration. Provenance
anchors the migrated set to a single merkle root (composing the sealed merkle accumulator), so the set that was
reconciled is provably the set that was cut over -- not a later, quietly-edited copy. And cutover is a fail-closed
lifecycle with rollback always available as a fork: a migration cannot be cut over until it has reconciled, and a
cutover can always be rolled back, so the transition is never a one-way door taken on faith. The primitive does not
re-implement the ledger, the object model, or the witness protocol it verifies against -- it composes them; its own new
act is the proof that the migration conserved the record."""
from __future__ import annotations

from decimal import Decimal
import json
from typing import Dict, List, Mapping, Sequence, Tuple, Union

from ..merkle_accumulator import MerkleAccumulator

Number = Union[int, float, str, Decimal]

# Cutover lifecycle -- fail-closed, with rollback always available as a fork from cutover
# (added to docs/DOMAIN_VOCAB_CARD.md per spine item 8).
_MIG_ALLOWED: Dict[str, set] = {
    "prepared": {"parallel", "cancelled"},
    "parallel": {"reconciled", "cancelled"},
    "reconciled": {"cutover", "cancelled"},
    "cutover": {"rolled_back"},   # rollback always available as a fork -- cutover is never a one-way door
    "rolled_back": set(),
    "cancelled": set(),
}


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


class MigrationError(ValueError):
    """Raised for an illegal cutover transition, or a cutover attempted before the migration reconciled -- fail-closed,
    never a migration cut over on an unproven record."""


def _canon(record: Mapping) -> bytes:
    """Canonical bytes for a record, so its merkle leaf is stable regardless of key order."""
    return json.dumps({k: str(v) for k, v in sorted(record.items())}, sort_keys=True, separators=(",", ":")).encode()


def manifest_root(records: Sequence[Mapping]) -> str:
    """The provenance root of a record set: the merkle root over the canonical records (composing the sealed merkle
    accumulator). The leaves are SORTED before the root is built, so the root depends on the SET of records, not the
    order they were supplied in -- the same records in any order produce the same root, and any added, dropped, or
    altered record produces a different one. The set that reconciles carries this root, so the set that is cut over can
    be proven to be the same set -- not a later, quietly-altered copy. Returns a hex root, or '' for an empty set."""
    leaves = sorted(_canon(r) for r in records)
    root = MerkleAccumulator.from_leaves(leaves).get_root() if leaves else None
    return root.hex() if root else ""


def reconcile(source: Sequence[Mapping], migrated: Sequence[Mapping]) -> Dict[str, object]:
    """Reconcile a migrated record set against its source, value-conserving. Each record maps an `id` to an `amount`.
    Returns a report: whether every source record has a migrated counterpart (none dropped), no record was injected
    (none added), the per-record amounts match (none mismatched), and the totals are equal (value conserved). The report
    carries the dropped / added / mismatched ids and the source and migrated provenance roots. This is the variance
    detector -- it does not raise; `assert_reconciled` is the fail-closed gate cutover runs through."""
    src = {r["id"]: _dec(r["amount"]) for r in source}
    mig = {r["id"]: _dec(r["amount"]) for r in migrated}
    dropped = sorted(k for k in src if k not in mig)
    added = sorted(k for k in mig if k not in src)
    mismatched = sorted(k for k in src if k in mig and src[k] != mig[k])
    src_total = sum(src.values(), Decimal("0"))
    mig_total = sum(mig.values(), Decimal("0"))
    conserves = src_total == mig_total
    reconciled = not dropped and not added and not mismatched and conserves
    return {"reconciled": reconciled, "source_total": src_total, "migrated_total": mig_total,
            "conserves": conserves, "dropped": dropped, "added": added, "mismatched": mismatched,
            "source_root": manifest_root(source), "migrated_root": manifest_root(migrated)}


def assert_reconciled(source: Sequence[Mapping], migrated: Sequence[Mapping]) -> Dict[str, object]:
    """Fail-closed reconciliation: raise MigrationError unless the migration conserves the source exactly (nothing
    dropped, added, mismatched, and totals equal). Returns the report on success. Cutover runs through this gate."""
    rep = reconcile(source, migrated)
    if not rep["reconciled"]:
        raise MigrationError(
            f"migration does not reconcile -- cutover refused: dropped={rep['dropped']} added={rep['added']} "
            f"mismatched={rep['mismatched']} source_total={rep['source_total']} migrated_total={rep['migrated_total']}")
    return rep


def open_migration(migration_id: str, source: Sequence[Mapping]) -> Dict[str, object]:
    """Open a migration for a source record set. Starts `prepared`, carrying the source and its provenance root."""
    return {"id": migration_id, "source": list(source), "source_root": manifest_root(source), "status": "prepared"}


def transition(migration: Mapping, to_status: str) -> Tuple[Dict, Dict]:
    """Move a migration to `to_status`, fail-closed: the lifecycle must permit the move (you cannot cut over a migration
    that has not reconciled). Rollback is always available as a fork from `cutover`. Returns (new_migration, event);
    input not mutated."""
    frm = migration.get("status", "prepared")
    if to_status not in _MIG_ALLOWED.get(frm, set()):
        raise MigrationError(f"migration {migration.get('id')!r}: illegal transition {frm!r} -> {to_status!r} "
                             f"(allowed from {frm!r}: {sorted(_MIG_ALLOWED.get(frm, set())) or 'none'})")
    nm = dict(migration)
    nm["status"] = to_status
    return nm, {"migration": migration.get("id"), "from": frm, "to": to_status}


def cutover(migration: Mapping, migrated: Sequence[Mapping]) -> Dict[str, object]:
    """Cut a migration over to the migrated record set, fail-closed: the migration must be in `reconciled` state and the
    migrated set must reconcile to the source exactly, or the cutover is refused. On success the migration moves to
    `cutover` carrying the reconciled provenance root -- the proof the record was conserved. Rollback remains available
    as a fork."""
    if migration.get("status") != "reconciled":
        raise MigrationError(f"migration {migration.get('id')!r}: cutover requires the reconciled state "
                             f"(is {migration.get('status')!r}) -- reconcile before cutover")
    rep = assert_reconciled(migration["source"], migrated)
    nm = dict(migration)
    nm["status"] = "cutover"
    nm["migrated_root"] = rep["migrated_root"]
    nm["reconciliation"] = rep
    return nm
