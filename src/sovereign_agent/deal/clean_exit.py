"""The Clean Exit — a governed, verifiable carve-out and diligence package for a clean exit (a PE carve-out, a sale, or a
generational handoff), composing the sealed floors rather than reimplementing them.

Co-extrusion for s5_37 (The Clean Exit, KM 2026-08-05 — escape arc 4/4, the terminal and the LGP culmination of the
displacement arc). Pure / structural. The last displacement is the mirror of every migration in this arc: not a move
onto the sovereign core but a move off the business entirely -- a unit sold to a buyer, a company handed to a successor.
The risk is the mirror image too. Where a migration's buyer of risk is the business receiving its own records, an exit's
is a stranger: a purchaser or an heir who must decide whether the ledger they are being handed is complete and
unaltered, usually on the strength of a data room and a diligence report assembled by the seller. This module makes the
exit a verifiable act. A carve-out separates a subset of the group's entities value-conserving: the carved-out unit and
the remaining business together conserve the whole, so nothing is created in, or quietly stripped from, the unit being
sold. A diligence package anchors the carved-out ledger to a merkle provenance root (composing the migration primitive)
and assembles it as a self-verifying audit package (composing the sealed audit package), so the deal ledger is a
receipted artifact the buyer re-verifies independently rather than takes on the seller's word. And a clean exit is
fail-closed: it is clean only if the carve-out conserves value AND the diligence package verifies. The module does not
re-implement the ledger, the consolidation, or the audit package it composes -- its own new act is the value-conserving
carve-out and the verifiable diligence package that make an exit provable to the party that receives it.

Composes: `migration.reconcile.manifest_root` (provenance -- The Migration Primitive, Vol 35) · `compliance.audit_package`
(the sealed self-verifying audit package -- Compliance & Audit, Vol 16). The group the carve-out separates is the
consolidated structure (Multi-Entity & Consolidation, Vol 20) and its ledger is the sovereign ledger (Sovereign
Financials, Vol 7), composed and named. The buyer's data-room connectors are the sovereign port's (S6-V07)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Mapping, Optional, Sequence, Union

from ..migration.reconcile import manifest_root
from ..compliance.audit_package import build_audit_package, verify_audit_package, compliance_report

Number = Union[int, float, str, Decimal]


class CleanExitError(ValueError):
    """Raised when an exit is not clean -- a carve-out that names an entity not in the group, a carve-out that does not
    conserve value, or a diligence package that does not verify. Fail-closed, never an exit handed to a buyer on an
    unproven or unverifiable ledger."""


def _dec(x: Number) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _entities_total(entities: Mapping[str, Mapping[str, Number]]) -> Decimal:
    return sum((_dec(b) for accts in entities.values() for b in accts.values()), Decimal("0"))


def _ledger_records(entities: Mapping[str, Mapping[str, Number]]) -> List[Dict[str, str]]:
    """Flatten a set of entities' ledgers to canonical id/amount records (entity:account -> balance), so the carved-out
    ledger can be anchored to a provenance root (composing the migration primitive)."""
    return [{"id": f"{e}:{a}", "amount": str(_dec(b))}
            for e in sorted(entities) for a, b in sorted(entities[e].items())]


def carve_out(group: Mapping[str, Mapping[str, Number]], carve_ids: Sequence[str]) -> Dict[str, object]:
    """Separate a subset of a consolidated group's entities into a carved-out unit, value-conserving. `group` maps each
    entity to its ledger {account: balance}. `carve_ids` names the entities leaving; every one must be in the group (an
    unknown entity is refused). The carved-out unit and the remaining business partition the group, and the carved total
    plus the remaining total conserve the whole group total -- nothing created in, or stripped from, the unit sold.
    Returns the carved and remaining ledgers, the three totals, and whether value is conserved."""
    missing = [e for e in carve_ids if e not in group]
    if missing:
        raise CleanExitError(f"cannot carve out entities not in the group: {missing}")
    carved = {e: dict(group[e]) for e in carve_ids}
    remaining = {e: dict(group[e]) for e in group if e not in set(carve_ids)}
    carved_total, remaining_total, group_total = _entities_total(carved), _entities_total(remaining), _entities_total(group)
    return {"carved": carved, "remaining": remaining, "conserves": carved_total + remaining_total == group_total,
            "carved_total": carved_total, "remaining_total": remaining_total, "group_total": group_total}


def diligence_package(deal_id: str, carved: Mapping[str, Mapping[str, Number]], evidence_refs: Sequence[str],
                      generated_utc: str,
                      domain_readiness: Optional[Mapping[str, Mapping]] = None) -> Dict[str, object]:
    """Build a verifiable diligence package for a carved-out unit. The carved-out ledger is anchored to a merkle
    provenance root (composing the migration primitive) -- a fingerprint of exactly that unit's ledger. A self-verifying
    audit package is assembled over the compliance domains the seller attests (composing the sealed audit package):
    `domain_readiness` maps each sealed audit domain (financials, treasury, supply, manufacturing, project) to its
    readiness {ready, gaps}; it defaults to a single financials report marked ready. The package carries a content hash a
    buyer recomputes to confirm it was not altered since it was built. Returns the deal id, the ledger provenance root,
    the audit package, and whether it verifies. Gaps are disclosed in the package, not hidden -- an honest diligence
    package that verifies whether or not it is fully ready."""
    ledger_root = manifest_root(_ledger_records(carved))
    dr = dict(domain_readiness) if domain_readiness else {"financials": {"ready": True, "gaps": []}}
    reports = [compliance_report(dom, rd, list(evidence_refs)) for dom, rd in dr.items()]
    pkg = build_audit_package(reports, generated_utc)
    return {"deal": deal_id, "ledger_root": ledger_root, "audit_package": pkg, "verified": verify_audit_package(pkg)}


def assert_clean_exit(deal_id: str, group: Mapping[str, Mapping[str, Number]], carve_ids: Sequence[str],
                      evidence_refs: Sequence[str], generated_utc: str,
                      domain_readiness: Optional[Mapping[str, Mapping]] = None) -> Dict[str, object]:
    """A clean exit, fail-closed: the carve-out must conserve value AND the diligence package must verify, or the exit is
    refused. Raises CleanExitError otherwise. Returns the deal artifact -- the carve-out, the diligence package, and the
    proof (conservation + verification) that lets a buyer or heir receive the unit on evidence, not the seller's word."""
    co = carve_out(group, carve_ids)
    if not co["conserves"]:
        raise CleanExitError(f"exit not clean: carve-out does not conserve value (carved {co['carved_total']} + "
                             f"remaining {co['remaining_total']} != group {co['group_total']})")
    dp = diligence_package(deal_id, co["carved"], evidence_refs, generated_utc, domain_readiness)
    if not dp["verified"]:
        raise CleanExitError("exit not clean: the diligence package does not verify (tampered or truncated)")
    return {"deal": deal_id, "carve_out": co, "diligence": dp, "clean": True}
