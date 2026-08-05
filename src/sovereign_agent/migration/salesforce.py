"""Unbinding Salesforce — a governed, receipted cutover from Salesforce won opportunities onto governed mandates,
composing the sealed floors rather than reimplementing them.

Co-extrusion for s5_35 (Unbinding Salesforce, KM 2026-08-04 — escape arc 2/4; sibling to migration/quickbooks.py). Pure /
structural. A growing sales team runs on Salesforce until the CRM's picture of a deal and the business's governed
commitment to deliver and bill it drift apart: an opportunity anyone can edit, a stage anyone can advance, a forecast
told beside the ledger rather than a commitment the ledger enforces. This module makes the DESTINATION a won opportunity
becomes a governed mandate: a mandate-scoped commitment (composing the sealed mandate guard) that carries the deal's
amount and can be acted on -- billed, recognized -- only by a principal who holds its mandate, fail-closed. It does NOT
build a CRM: there is no pipeline, no lead management, no forecasting here (those are Analytics & Decision Intelligence's
concern). What it builds is the mandate a deal lands on, and the receipted cutover that carries Salesforce's won
opportunities onto it -- value-conserving (every won opportunity carried to a mandate, the total amount conserved),
provenance-anchored, and lifecycle-governed (composing the migration primitive). Billing a governed mandate is
fail-closed on its mandate authorization and posts a balanced AR/revenue double-entry (composing the sealed revenue
billing and posting). The Salesforce connector/API export is NOT here -- that is the sovereign port's (S6-V07); this act
begins from an already-ingested set of won opportunities.

Composes: `migration.reconcile` (manifest_root provenance + lifecycle, The Migration Primitive, Vol 35) ·
`obligations.mandate_guard` (the sealed mandate scope + fail-closed authorization, Structural SoD & Access Governance,
Vol 2) · `revenue.billing.invoice` (the sealed value-conserving invoice, Revenue & Order-to-Cash, Vol 17) ·
`financials.posting.from_entry` (the sealed balanced double-entry, Sovereign Financials, Vol 7 -- the posting-shape spine)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Sequence, Union

from .reconcile import manifest_root, open_migration, transition
from ..obligations.mandate_guard import approval_holds_mandate
from ..revenue.billing import invoice
from ..financials.posting import from_entry

Number = Union[int, float, str, Decimal]


class SalesforceError(ValueError):
    """Raised when a Salesforce won opportunity cannot become a governed mandate, or a governed mandate cannot be
    billed -- an unwon opportunity, a non-positive amount, an unmapped mandate, or a billing not authorized under the
    mandate scope -- fail-closed, never a commitment carried across or acted on unauthorized."""


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _records(opps: Sequence[Mapping]) -> List[Dict[str, str]]:
    """Won opportunities as canonical id/amount records, so the ingested set can be anchored to a provenance root
    (composing the migration primitive) -- the set that reconciled is provably the set that is cut over."""
    return [{"id": str(o["id"]), "amount": str(_dec(o["amount"]))} for o in opps]


def opportunity_to_mandate(opp: Mapping, mandate_id: str) -> Dict[str, object]:
    """A won Salesforce opportunity becomes a governed mandate: a commitment scoped to `mandate_id` (composing the
    sealed mandate guard), carrying the account and the deal amount. Refuses an opportunity that is not won, or a
    non-positive amount -- a governed mandate is a real, won commitment, not a hopeful pipeline entry. The mandate scope
    is what makes it governed: acting on it (billing, recognition) is authorized only for a principal who holds the
    mandate."""
    if not opp.get("is_won"):
        raise SalesforceError(f"opportunity {opp.get('id')!r} is not won -- only a won opportunity becomes a governed "
                              "mandate (pipeline/forecast are not this destination's concern)")
    amt = _dec(opp["amount"])
    if amt <= 0:
        raise SalesforceError(f"opportunity {opp.get('id')!r}: amount must be > 0 (got {amt})")
    return {"opportunity": str(opp["id"]), "account": opp.get("account"), "amount": str(amt),
            "mandate": mandate_id, "status": "governed"}


def map_opportunities(sf_won: Sequence[Mapping], mandate_map: Mapping[str, str]) -> List[Dict[str, object]]:
    """Map a set of Salesforce won opportunities onto governed mandates, value-conserving. Every opportunity must name a
    mandate in `mandate_map` (an unmapped opportunity is refused, so no commitment is carried across without a governed
    home); each becomes a governed mandate via `opportunity_to_mandate`; and the total mandate amount equals the total
    won-opportunity amount -- no value created or lost in the crossing. Returns the governed mandates."""
    mandates: List[Dict[str, object]] = []
    for opp in sf_won:
        oid = str(opp["id"])
        if oid not in mandate_map:
            raise SalesforceError(f"opportunity {oid!r} has no mandate mapping -- refused (every won opportunity must "
                                  "name the mandate it is governed under before cutover)")
        mandates.append(opportunity_to_mandate(opp, mandate_map[oid]))
    src_total = sum((_dec(o["amount"]) for o in sf_won), Decimal("0"))
    mapped_total = sum((_dec(m["amount"]) for m in mandates), Decimal("0"))
    if src_total != mapped_total:  # guards the invariant explicitly
        raise SalesforceError(f"crossing did not conserve value: won total {src_total} != mandate total {mapped_total}")
    return mandates


def bill_mandate(mandate: Mapping, approval: Mapping, revenue_account: str = "4000-Revenue",
                 ar_account: str = "1100-AR") -> Dict[str, object]:
    """Bill a governed mandate, fail-closed on its mandate authorization. The billing `approval` must hold the mandate
    the commitment is scoped to (composing the sealed mandate guard, Vol 2) -- a principal who does not hold the mandate
    is BARRED, so a deal governed under mandate B cannot be billed by someone acting under mandate A. On authorization,
    the mandate's amount bills through the sealed value-conserving invoice (Vol 17) and posts a balanced AR/revenue
    double-entry through the sealed posting (Vol 7). Returns the invoice and the balanced posting."""
    debit = {"mandate": mandate.get("mandate")}
    if not approval_holds_mandate(debit, dict(approval)):
        raise SalesforceError(f"billing barred: the approval does not hold mandate {mandate.get('mandate')!r} the "
                              "commitment is scoped to -- a governed mandate is billable only by a mandate-holder")
    inv = invoice([{"description": f"opportunity {mandate.get('opportunity')}", "quantity": 1,
                    "unit_price": mandate["amount"]}])
    total = inv["total"]
    posting = from_entry({"debits": [{"account": ar_account, "amount": str(total)}],
                          "credits": [{"account": revenue_account, "amount": str(total)}]},
                         memo=f"bill governed mandate {mandate.get('opportunity')}")
    return {"mandate": mandate.get("opportunity"), "invoice": inv, "posting": posting}


def receipted_cutover(migration_id: str, sf_won: Sequence[Mapping],
                      mandate_map: Mapping[str, str]) -> Dict[str, object]:
    """The receipted cutover from Salesforce onto governed mandates, fail-closed end to end. It maps the won
    opportunities onto governed mandates value-conserving (composing the sealed mandate guard); anchors the source and
    mandate sets to merkle provenance roots (composing the migration primitive, so the set that reconciled is provably
    the set cut over); and governs the move through the migration lifecycle (prepared -> parallel -> reconciled ->
    cutover). The value-conserving map refuses an unmapped opportunity or a non-conserving crossing BEFORE the lifecycle
    advances -- so the move reaches cutover only because the mandates conserved the won opportunities. The Salesforce
    connector is the sovereign port's (S6-V07); this begins from an already-ingested set of won opportunities. Returns
    the receipt: the cutover state, the source and mandate provenance roots, and the governed mandates."""
    mandates = map_opportunities(sf_won, mandate_map)           # value-conserving, or refused (before the lifecycle)
    source_root = manifest_root(_records(sf_won))
    mandate_root = manifest_root([{"id": m["opportunity"], "amount": m["amount"]} for m in mandates])
    m = open_migration(migration_id, _records(sf_won))          # prepared -- the migration lifecycle (composed)
    m, _ = transition(m, "parallel")                            # the parallel run alongside Salesforce
    m, _ = transition(m, "reconciled")                          # value conserved -> reconciled
    m, _ = transition(m, "cutover")                             # cut over onto governed mandates
    return {"migration": m["id"], "status": m["status"], "source_root": source_root, "mandate_root": mandate_root,
            "mandates": mandates}
