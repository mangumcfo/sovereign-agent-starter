"""Consuming the Giants — a governed, receipted portfolio carve-in from enterprise incumbents (SAP, NetSuite,
Acumatica) onto the sovereign core, composing the sealed floors rather than reimplementing them.

Co-extrusion for s5_36 (Consuming the Giants, KM 2026-08-05 — escape arc 3/4; sibling to migration/quickbooks.py and
migration/salesforce.py). Pure / structural. A large enterprise does not leave a giant ERP in one leap; it carves in one
ledger at a time -- an entity, a subsidiary, a module -- running the new system in parallel and cutting each over only
when it is proven. The risk is multiplied by scale: many ledgers, each a chance to drop an account, alter a balance, or
cut over unproven, and a portfolio migration that patches discrepancies at the end is a portfolio that never really
reconciled. This module makes a carve-in a governed, value-conserving act and a PORTFOLIO of carve-ins a governed whole:
each incumbent's ledger is reconciled value-conserving against its migrated form (composing the migration primitive's
per-record reconciliation), anchored to a provenance root, and cut over fail-closed per ledger -- a carve-in that does
not reconcile cannot cut over, and it does not drag the others down or get dragged along by them. The opening balances of
each carved-in ledger post as a balanced double-entry (composing the sealed posting), and the whole portfolio anchors to
an aggregate provenance root over every carve-in, so a multi-ledger migration is provable ledger by ledger and in
aggregate. The module does not re-implement the ledger, the posting, the consolidation, or the migration primitive it
composes -- nor does it invent a mega-suite; its own new act is the phased, per-ledger fail-closed carve-in and the
portfolio that governs many of them at once.

Composes: `migration.reconcile` (per-record reconciliation, manifest_root provenance, lifecycle -- The Migration
Primitive, Vol 35) · `migration.quickbooks.opening_entry` (the opening-balance emitter shape, the sealed QuickBooks
escape) · `financials.posting.from_entry` (the sealed balanced double-entry, Sovereign Financials, Vol 7 -- the
posting-shape spine). The carved-in ledgers land in the sealed ERP stack and the Multi-Entity & Consolidation surface
(Vol 20); the enterprise connectors (SAP/NetSuite/Acumatica APIs) are the sovereign port's (S6-V07)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

from .reconcile import assert_reconciled, reconcile, manifest_root, MigrationError
from .quickbooks import opening_entry
from ..financials.posting import from_entry

Number = Union[int, float, str, Decimal]


class CarveInError(ValueError):
    """Raised when a carve-in cannot be cut over -- a ledger that does not reconcile value-conserving -- or a portfolio
    cutover is attempted while any constituent carve-in has not reconciled. Fail-closed, per ledger, never an enterprise
    ledger cut over on an unproven balance."""


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _records(tb: Mapping[str, Number]) -> List[Dict[str, str]]:
    """A trial balance {account: signed_balance} as canonical id/amount records, so a carved-in ledger can be reconciled
    per-record and anchored to a provenance root (composing the migration primitive)."""
    return [{"id": a, "amount": str(_dec(b))} for a, b in tb.items()]


def open_carve_in(system: str, source_tb: Mapping[str, Number]) -> Dict[str, object]:
    """Open a carve-in of one incumbent enterprise ledger (e.g. 'SAP', 'NetSuite', 'Acumatica'). Anchors the source
    trial balance to a provenance root; starts `prepared`."""
    src = _records(source_tb)
    return {"system": system, "source": src, "source_root": manifest_root(src), "status": "prepared"}


def reconcile_carve_in(source_tb: Mapping[str, Number], migrated_tb: Mapping[str, Number]) -> Dict[str, object]:
    """Reconcile one carved-in ledger value-conserving, composing the migration primitive's per-record reconciliation:
    every source account has a migrated counterpart (none dropped), no account was injected, the per-account balances
    match, and the totals are equal. Returns the reconciliation report; does not raise (the gate is `carve_in_cutover`)."""
    return reconcile(_records(source_tb), _records(migrated_tb))


def carve_in_cutover(carve_in: Mapping, migrated_tb: Mapping[str, Number],
                     revenue_memo: str = "carve-in opening balances") -> Dict[str, object]:
    """Cut over one carved-in ledger, fail-closed per ledger. The migrated ledger must reconcile to the source exactly
    (composing the migration primitive's `assert_reconciled`) or the cutover is refused -- a giant's ledger is never
    carried across on an unproven balance. On success the opening balances post as one balanced double-entry (composing
    the sealed opening-entry emitter and posting), and the carve-in moves to `cutover` carrying its migrated provenance
    root. This is the phased unit: one incumbent ledger, cut over only when its own balance is proven, independent of the
    other carve-ins in the portfolio."""
    rep = assert_reconciled(carve_in["source"], _records(migrated_tb))   # per-ledger fail-closed gate (Vol 35)
    posting = from_entry(opening_entry(migrated_tb), memo=f"{carve_in.get('system')}: {revenue_memo}")
    nm = dict(carve_in)
    nm["status"] = "cutover"
    nm["migrated_root"] = manifest_root(_records(migrated_tb))
    nm["opening_posting"] = posting
    nm["reconciliation"] = rep
    return nm


def portfolio_root(carve_ins: Sequence[Mapping]) -> str:
    """The aggregate provenance root of a portfolio: the merkle root over the carve-ins' migrated roots (composing the
    migration primitive), so a multi-ledger migration carries one aggregate fingerprint over every ledger cut over. The
    root is order-independent -- the same set of carved-in ledgers in any order gives the same aggregate root."""
    leaves = [{"id": c["system"], "amount": str(c.get("migrated_root", ""))} for c in carve_ins]
    return manifest_root(leaves)


def portfolio_cutover(portfolio_id: str, carve_ins: Sequence[Mapping]) -> Dict[str, object]:
    """Cut over a portfolio of carve-ins, fail-closed per ledger. Each entry is {system, source_tb, migrated_tb}. Every
    carve-in is reconciled first; if ANY ledger does not reconcile value-conserving, the whole portfolio cutover is
    refused, naming the failing systems -- a giant is consumed only when every one of its ledgers is proven, never with
    an unreconciled ledger quietly patched. On success each carve-in cuts over (posting its balanced opening entry), and
    the portfolio anchors to an aggregate provenance root over all of them. Returns the portfolio receipt: the aggregate
    root and the per-ledger carve-in receipts."""
    failing = []
    for e in carve_ins:
        rep = reconcile(_records(e["source_tb"]), _records(e["migrated_tb"]))
        if not rep["reconciled"]:
            failing.append(e["system"])
    if failing:
        raise CarveInError(f"portfolio {portfolio_id!r}: refused -- these ledgers do not reconcile value-conserving: "
                           f"{failing}. Every carve-in must reconcile before the portfolio cuts over (fail-closed per "
                           "ledger).")
    done = []
    for e in carve_ins:
        ci = open_carve_in(e["system"], e["source_tb"])
        done.append(carve_in_cutover(ci, e["migrated_tb"]))
    return {"portfolio": portfolio_id, "systems": [c["system"] for c in done],
            "aggregate_root": portfolio_root(done), "carve_ins": done}
