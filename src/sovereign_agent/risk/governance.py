# -*- coding: utf-8 -*-
"""risk.governance — Sovereign Risk & Mutual Protection (Series 11, Vol 4:
Governance, Compliance & Integrated Risk Systems).

Verifiable math is only half of protection; the other half is governance you can trust and compliance you can
defend. This volume builds that durable layer — **constitutional governance skins, human-primacy risk
frameworks, and audit-ready proof systems** — and it does so by composing the sealed floors, **inventing no new
engine**. The sharpest constraint sits exactly here, because a governance/risk volume is where an underwriting
engine would try to sneak in: **policy-as-code is ENFORCEMENT, not optimization.** A governance skin
(`load_governance_skin`) is a loadable, versioned, forkable set of rules naming which decision classes require a
human gate and what limits apply — enforced by composing the sealed HumanApprovalGate (S5 V16), the mandate
(S5 V28), and the Constitutions (S5 V30). `enforce_decision` routes a material governed decision through that
sealed gate: a gated class is refused without a named human's approval. `escalate_if_over_limit` flags a
decision above a skin's limit for human escalation. `audit_ready_package` assembles an audit-ready receipt
package from a principal's own verified records — claims, premiums, group premiums, and attestation chains
(composing S11 V1–V3) — complete only when every one verifies.

**The fence (inherited + sharpened) — `GOVERNANCE_BREACH_FIELDS`:** the seven-part S11 fence PLUS no in-node
**underwriting, risk-pricing, or optimization**. A synthetic premium-pricing / underwriting / optimizer path is
refused in code — policy-as-code enforces the members' rules; it does not price their risk. **Risk MODELING
(scenario, stress-testing, analytics) homes OUT to Analytics & Decision Intelligence (S5 Vol 19)** — the same
enforcement-not-optimization boundary the sealed analytics floor draws; this layer runs governance views and
human gates, not a pricing model. KILL-TARGET: the risk-governance authority that owns your pool's rules and
prices your risk — refused. NO TOKEN · no yield · holds no value · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .mutual_protection import (verify_claim, verify_premium, _fence, RISK_BREACH_FIELDS,
                                IncomeRefused, IncomeStatus, Pool)                          # S11 V1
from .advanced_pooling import verify_attestation_chain                                     # S11 V2
from .group_applications import verify_group_premium                                       # S11 V3
from ..economy.contribution import record_contribution                                     # S10 V1

__all__ = ["load_governance_skin", "skin_role_spec", "fork_governance_skin", "enforce_decision",
           "escalate_if_over_limit", "audit_ready_package", "GovernanceSkin", "PolicyVerdict",
           "AuditPackage", "AUDIT_KINDS", "GOVERNANCE_BREACH_FIELDS", "IncomeRefused", "IncomeStatus", "Pool"]

# policy-as-code is ENFORCEMENT, not optimization. The S11 fence PLUS: no in-node underwriting / risk-pricing /
# optimization rule. A governance skin gates and limits; it never prices risk or optimizes a pool.
GOVERNANCE_BREACH_FIELDS = RISK_BREACH_FIELDS | frozenset({
    "premium_pricing", "price_risk", "pricing_engine", "underwriting_model", "actuarial_price",
    "optimize", "optimizer", "optimization", "maximize", "profit",
})

# The records an audit-ready package composes — each verified by its own sealed S11 floor.
AUDIT_KINDS = ("claim", "premium", "group_premium", "attestation_chain")


def _gfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    """The sharpened S11 fence: refuse any underwriting / risk-pricing / optimization field. Policy-as-code
    enforces rules; it does not price risk (that would be the underwriting engine this volume forbids)."""
    for k in (mapping or {}):
        if str(k).lower() in GOVERNANCE_BREACH_FIELDS:
            raise IncomeRefused(
                f"a governance rule must carry no underwriting/pricing/optimization field ('{k}') — "
                f"policy-as-code is ENFORCEMENT, not optimization; the node gates and limits, it does not "
                f"price your risk (risk modeling homes OUT to Analytics & Decision Intelligence, S5 Vol 19)")


@dataclass(frozen=True)
class GovernanceSkin:
    """A loadable, versioned, forkable policy-as-code governance skin: it names which decision classes require a
    human gate (`gated_classes`) and what per-class limits apply (`limits`) — pure ENFORCEMENT, no pricing or
    optimization. It composes the sealed gate (S5 V16) + mandate (S5 V28) + Constitutions (S5 V30); the members
    load it, fork it, and audit it. It holds no value and prices nothing."""
    skin_id: str
    version: str
    gated_classes: tuple
    limits: Dict[str, Any] = field(default_factory=dict)


def load_governance_skin(skin_id: str, *, gated_classes: Sequence[str], limits: Optional[Mapping[str, Any]] = None,
                         version: str = "v1") -> GovernanceSkin:
    """Load a governance skin — policy-as-code the members set: which decision classes require a human gate and
    what limits apply. Enforcement only: a `gated_classes` name or a `limits` key that is an underwriting /
    pricing / optimization field is refused (the sharpened fence). Deny-by-default: a skin needs an id and at
    least one gated class (a skin that gates nothing governs nothing)."""
    if not str(skin_id).strip():
        raise IncomeRefused("a governance skin needs an id")
    gc = tuple(dict.fromkeys(str(c) for c in gated_classes if str(c).strip()))
    if not gc:
        raise IncomeRefused("a governance skin must gate at least one decision class — enforcement, not decoration")
    for c in gc:
        if str(c).lower() in GOVERNANCE_BREACH_FIELDS:
            raise IncomeRefused(f"a governed class must not be a pricing/underwriting/optimization rule ('{c}')")
    lim = dict(limits or {})
    _gfence(lim, "a governance skin")
    return GovernanceSkin(skin_id=str(skin_id), version=str(version), gated_classes=gc, limits=lim)


def skin_role_spec(skin: GovernanceSkin) -> Dict[str, Any]:
    """Emit the role_spec the SEALED gate consumes — the skin's gated classes become the gate's forbidden
    classes. This is policy-as-code expressed in the sealed gate's enforcement vocabulary (S5 V16): the skin
    does not enforce itself; it is enforced by the sealed gate."""
    return {"charter_v7_forbidden_classes": list(skin.gated_classes)}


def fork_governance_skin(skin: GovernanceSkin, new_id: str, *, add_gated: Sequence[str] = (),
                         remove_gated: Sequence[str] = (), limits: Optional[Mapping[str, Any]] = None,
                         version: str = "v1") -> GovernanceSkin:
    """Fork a governance skin into a new versioned one — governance is forkable and version-controlled. The
    members add or remove gated classes and set limits; the sharpened fence still refuses any
    pricing/underwriting/optimization rule. History is preserved by keeping both skins."""
    remove = {str(c) for c in remove_gated}
    gated = [c for c in skin.gated_classes if c not in remove] + [str(c) for c in add_gated]
    return load_governance_skin(new_id, gated_classes=gated,
                                limits=(dict(limits) if limits is not None else dict(skin.limits)),
                                version=version)


def enforce_decision(skin: GovernanceSkin, action_class: str, principal: str, work_ref: str, *, gate: Any,
                     at: str, author: str, source_ref: str, registry: Any, approver: Optional[str] = None,
                     approval_ref: Optional[str] = None, amount: Any = None,
                     extra: Optional[Mapping[str, Any]] = None, mode: str = "live") -> dict:
    """Enforce a governance skin over a material decision by routing it through the SEALED human gate (composes
    `record_contribution`, S10 V1, with the skin's role_spec). A decision whose `action_class` is gated by the
    skin is refused without a named human's approval — policy-as-code enforced by the sealed gate, not a new
    engine. The sharpened fence refuses any underwriting/pricing/optimization field. Returns the governed
    decision's receipt (the principal owns it)."""
    _gfence(extra, "a governed decision")
    gated = str(action_class) in skin.gated_classes
    ex = dict(extra or {}); ex["skin"] = skin.skin_id; ex["skin_version"] = skin.version
    ex["governed_class"] = str(action_class)
    return record_contribution(principal, "governance", work_ref, contribution_class="attested",
                               mandate=principal, author=author, source_ref=source_ref, at=at, registry=registry,
                               amount=amount, unit="credits", extra=ex, approver=approver,
                               approval_ref=approval_ref, gate=gate, action_class=str(action_class),
                               role_spec=skin_role_spec(skin),
                               mode=("corporate_regulated" if gated else mode))


@dataclass(frozen=True)
class PolicyVerdict:
    """The result of a policy check: whether a decision is within a skin's limit, or must escalate to a human.
    It informs a governed decision; it never prices or optimizes."""
    action_class: str
    escalate: bool
    limit: Any = None
    reason: str = ""


def escalate_if_over_limit(skin: GovernanceSkin, action_class: str, amount: Any) -> PolicyVerdict:
    """ROE-style limit check: if a decision's amount exceeds the skin's limit for its class, it must escalate to
    a human principal (who decides through the sealed gate). This is enforcement — a threshold the members set —
    not a pricing model. Returns a plain verdict; the escalation itself is a human gate (`enforce_decision`)."""
    lim = skin.limits.get(str(action_class))
    over = lim is not None and amount is not None and float(amount) > float(lim)
    return PolicyVerdict(action_class=str(action_class), escalate=bool(over), limit=lim,
                         reason=(f"amount {amount} exceeds limit {lim} — escalate to a human" if over
                                 else "within limit"))


@dataclass(frozen=True)
class AuditPackage:
    """An audit-ready package: a principal's own verified records — claims, premiums, group premiums, and
    attestation chains — assembled so an audit or dispute is a matter of reading, not reconstructing. Complete
    only when every record verifies as the principal's own; it holds no value and files nothing."""
    principal: str
    complete: bool
    verified_count: int
    by_kind: Dict[str, int] = field(default_factory=dict)
    reason: str = "an audit-ready package of your own verified records"


def _verify_audit_record(principal: str, rec: Mapping[str, Any]) -> bool:
    kind = str(rec.get("kind", "")).strip().lower()
    if kind == "claim":
        return verify_claim(rec["receipt"], principal, rec["pool"], rec["work_ref"],
                            claim_class=rec["claim_class"], amount=rec.get("amount"),
                            extra=rec.get("extra")).provisioned
    if kind == "premium":
        return verify_premium(rec["receipt"], rec["pool"], principal, rec["work_ref"],
                              contribution_class=rec["contribution_class"], amount=rec.get("amount"),
                              extra=rec.get("extra")).provisioned
    if kind == "group_premium":
        return verify_group_premium(rec["receipt"], rec["pool"], principal, rec["work_ref"],
                                    group_class=rec["group_class"], contribution_class=rec["contribution_class"],
                                    amount=rec.get("amount")).provisioned
    if kind == "attestation_chain":
        return verify_attestation_chain(rec["chain"], principal, rec["pool"], rec["work_ref"],
                                        claim_class=rec["claim_class"], attestors=rec["attestors"],
                                        amount=rec.get("amount"))
    raise IncomeRefused(f"unknown audit record kind {rec.get('kind')!r} — a package composes {list(AUDIT_KINDS)} "
                        f"(sealed S11 V1–V2 records); it invents no new record")


def audit_ready_package(principal: str, records: Sequence[Mapping[str, Any]]) -> AuditPackage:
    """Assemble an audit-ready package from a principal's OWN verified records — claims and premiums (S11 V1),
    group premiums (S11 V3), and attestation chains (S11 V2) — composing each record's sealed verifier. Complete
    iff every record verifies as the principal's own; a foreign or tampered record breaks it; an unknown kind is
    refused. Deny-by-default: an empty package is not complete. It holds no value and files nothing — audit
    readiness is owned, verifiable records, not a computed liability."""
    by_kind = {k: 0 for k in AUDIT_KINDS}
    verified = 0
    reason: List[str] = []
    for i, rec in enumerate(records):
        _gfence(rec, "an audit record")
        if _verify_audit_record(principal, rec):
            verified += 1
            by_kind[str(rec.get("kind")).strip().lower()] += 1
        else:
            reason.append(f"record {i} ({rec.get('kind')}) does not verify as {principal}'s own")
    ok = bool(records) and not reason
    return AuditPackage(principal=principal, complete=ok, verified_count=verified, by_kind=by_kind,
                        reason="; ".join(reason) or "an audit-ready package of your own verified records")
