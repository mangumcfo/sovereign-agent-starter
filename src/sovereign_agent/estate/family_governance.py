# -*- coding: utf-8 -*-
"""estate.family_governance — Generational Transfer (Series 12, Vol 4:
Family Governance, Disputes & Dignity Preservation).

The hardest part of a generational handoff is not the keys or the ventures — it is the family. Most
succession conflict is preventable with the right governance, and this volume builds it: a family
constitutional governance for succession, dispute resolution on receipted evidence with human mediation, a
dignified exit that lets any member decline, fork, or leave with a fair share and no penalty, and — loudest of
all — a **weakest-party** check that lets the least-powerful member confirm the rules protect them. It does so
by **composing** the sealed layers below and **re-implementing none of them**: the family constitution is the
sealed policy-as-code governance skin (Sovereign Risk & Mutual Protection, Vol 4); every governed decision and
every dispute resolution passes the sealed human gate (Compliance & Audit, S5 Vol 16); a dignified fork of a
venture composes the sealed fork (Generational Transfer, Vol 3); and it is anchored in the sealed Constitutions
(S5 Vol 30).

**The SUCCESSION-FENCE holds, sharpened for disputes and dignity:** the family governs and resolves its own
affairs — there is no second succession authority, no standing escrow, no recovery engine, and (the V4
sharpening) **no arbitration authority or dispute custodian** that owns the family's disputes and rations the
resolution. And dignity is enforced in code: a dignified exit carries **no penalty, forfeiture, or clawback** —
a member who leaves keeps a fair share. `FAMILY_GOVERNANCE_BREACH_FIELDS` refuses every one of those, plus (seal-
key-closed) any press/seal key. KILL-TARGET: the family-office / arbitration firm that inserts itself between a
family and its own succession decisions and profits from the conflict — refused. **Weakest-party (loud):** the
least-powerful member reads one honest indicator — every decision that could override them passes a human gate,
so no faction and no authority can strip them quietly. NO TOKEN · no yield · holds no value · money-path OFF ·
rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence

from .generational_transfer import EstateRefused                                         # S12 V1 (sealed)
from ..risk.governance import (                                                          # S11 V4 (governance skin)
    load_governance_skin, fork_governance_skin, enforce_decision, GovernanceSkin,
)

__all__ = ["load_family_constitution", "fork_family_constitution", "govern_decision", "resolve_dispute",
           "dignified_exit", "WeakestPartyCheck", "weakest_party_protected", "FAMILY_GOVERNANCE_BREACH_FIELDS"]


# THE SUCCESSION-FENCE, sharpened for family governance: the family governs and resolves its OWN affairs — no
# second succession authority, no escrow, no recovery engine, and (the V4 sharpening) no arbitration authority
# or dispute custodian that owns the disputes. Dignity is enforced: no penalty/forfeiture/clawback on an exit.
# And (seal-key-closed) no press/seal key.
FAMILY_GOVERNANCE_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "custodian", "second_authority", "succession_authority", "recovery_authority",
    "recovery_engine", "arbitration_authority", "dispute_custodian", "arbitration_firm",
    "penalty", "forfeiture", "clawback", "exit_penalty", "seal_key", "press_key", "sealing_key",
})


def _ffence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in ("seal_key", "press_key", "sealing_key"):
            raise EstateRefused(
                f"family governance must carry no press/seal key field ('{k}') — a family's key succession is "
                f"its OWN keys, never the press seal key")
        if kl in ("penalty", "forfeiture", "clawback", "exit_penalty"):
            raise EstateRefused(
                f"family governance must carry no penalty/forfeiture field ('{k}') — dignity is enforced: a "
                f"member who declines, forks, or exits keeps a fair share and is never penalized for leaving")
        if kl in FAMILY_GOVERNANCE_BREACH_FIELDS:
            raise EstateRefused(
                f"family governance must carry no second-authority/escrow/arbitration field ('{k}') — the "
                f"family governs and resolves its OWN affairs; no arbitration authority or dispute custodian "
                f"owns the disputes, and no succession authority stands over the family (composition-not-engine)")


# --- Family constitutional governance design (Ch 2) --------------------------------------------------------

def load_family_constitution(family_id: str, *, gated_decisions: Sequence[str],
                             limits: Optional[Mapping[str, Any]] = None,
                             extra: Optional[Mapping[str, Any]] = None) -> GovernanceSkin:
    """Load a family constitution — the family's own policy-as-code for succession, naming which decision
    classes require a human gate (composes the sealed governance skin, Sovereign Risk & Mutual Protection Vol 4,
    anchored in the sealed Constitutions S5 Vol 30). Deny-by-default: a constitution needs a family id and at
    least one gated decision (a family that gates nothing governs nothing); a second-authority / arbitration /
    penalty field is refused. Enforcement only — it prices and underwrites nothing (the inherited fence)."""
    _ffence(extra, "a family constitution")
    if not str(family_id).strip():
        raise EstateRefused("a family constitution needs a family id")
    return load_governance_skin(f"family:{family_id}", gated_classes=gated_decisions, limits=limits)


def fork_family_constitution(constitution: GovernanceSkin, heir_generation: str, *,
                             add_gated: Sequence[str] = (), remove_gated: Sequence[str] = (),
                             extra: Optional[Mapping[str, Any]] = None) -> GovernanceSkin:
    """Fork the family constitution into the next generation's — governance is inherited and adapted, not frozen
    (composes the sealed `fork_governance_skin`, Sovereign Risk & Mutual Protection Vol 4). The next generation
    adds or removes gated decisions to fit how it will govern; history is preserved by keeping both. The
    inherited fence still refuses a pricing/underwriting rule, and a second-authority/penalty field is refused
    here."""
    _ffence(extra, "a constitution fork")
    if not str(heir_generation).strip():
        raise EstateRefused("a constitution fork needs an heir-generation id")
    return fork_governance_skin(constitution, f"{constitution.skin_id}:{heir_generation}",
                                add_gated=add_gated, remove_gated=remove_gated)


# --- Governed decisions, dispute resolution & dignified exit (Ch 4 / Ch 5) ---------------------------------

def govern_decision(constitution: GovernanceSkin, decision_class: str, member: str, work_ref: str, *, gate: Any,
                    at: str, author: str, source_ref: str, registry: Any, approver: Optional[str] = None,
                    approval_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Route a family succession decision through the family constitution and the sealed human gate (composes
    the sealed `enforce_decision`, Sovereign Risk & Mutual Protection Vol 4). A decision whose class the
    constitution gates is refused without a named human's approval — human primacy over the consequential
    family decisions. Returns the decision's receipt (the family owns it). A second-authority / penalty field is
    refused."""
    _ffence(extra, "a family decision")
    ex = dict(extra or {}); ex["family_governed"] = True
    return enforce_decision(constitution, str(decision_class), member, work_ref, gate=gate, at=at, author=author,
                            source_ref=source_ref, registry=registry, approver=approver,
                            approval_ref=approval_ref, extra=ex)


def resolve_dispute(constitution: GovernanceSkin, dispute_ref: str, member: str, work_ref: str, *,
                    evidence: Sequence[str], gate: Any, at: str, author: str, source_ref: str, registry: Any,
                    mediator: Optional[str] = None, approval_ref: Optional[str] = None,
                    extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Resolve a family dispute on **receipted evidence** with **human mediation** — a resolution is a governed
    decision (`resolve_dispute` class) routed through the sealed gate, so it is refused without a named human
    mediator. Deny-by-default: a resolution needs at least one piece of receipted evidence, and the constitution
    must gate `resolve_dispute` (a family that does not human-mediate its disputes has no dispute resolution).
    No arbitration authority owns the dispute — the family resolves its own, on evidence it holds. Returns the
    resolution receipt."""
    _ffence(extra, "a dispute resolution")
    if not [e for e in evidence if str(e).strip()]:
        raise EstateRefused("a dispute resolution needs at least one piece of receipted evidence — disputes are "
                            "settled on records the family holds, not on who argues hardest")
    if "resolve_dispute" not in constitution.gated_classes:
        raise EstateRefused("the family constitution must gate 'resolve_dispute' — dispute resolution is always "
                            "human-mediated through the sealed gate, never automated or delegated to an authority")
    ex = dict(extra or {}); ex["dispute_ref"] = str(dispute_ref); ex["evidence_count"] = len([e for e in evidence])
    return govern_decision(constitution, "resolve_dispute", member, work_ref, gate=gate, at=at, author=author,
                           source_ref=source_ref, registry=registry, approver=mediator,
                           approval_ref=approval_ref, extra=ex)


def dignified_exit(constitution: GovernanceSkin, member: str, share_ref: str, work_ref: str, *, gate: Any,
                   at: str, author: str, source_ref: str, registry: Any, approver: Optional[str] = None,
                   approval_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Record a member's **dignified exit** — a member who declines, forks, or leaves does so with a fair share
    and **no penalty** (a governed `dignified_exit` decision through the sealed gate; the fork of a venture
    composes Generational Transfer Vol 3). Dignity is enforced in code: a penalty / forfeiture / clawback field
    is refused, so no member is ever penalized for leaving. Deny-by-default: an exit names the member's fair
    share. Returns the exit receipt the member owns."""
    _ffence(extra, "a dignified exit")
    if not str(share_ref).strip():
        raise EstateRefused("a dignified exit names the member's fair share — a member never leaves empty-handed "
                            "or under penalty (dignity is enforced)")
    ex = dict(extra or {}); ex["share_ref"] = str(share_ref); ex["dignified_exit"] = True
    return govern_decision(constitution, "dignified_exit", member, work_ref, gate=gate, at=at, author=author,
                           source_ref=source_ref, registry=registry, approver=approver,
                           approval_ref=approval_ref, extra=ex)


# --- Weakest-party protection: balancing individual sovereignty with family unity (Ch 6) -------------------

@dataclass(frozen=True)
class WeakestPartyCheck:
    """The one honest indicator the least-powerful family member reads: *the rules protect me.* `protected` is
    true only when every decision class that could override a member passes a human gate — so no faction and no
    authority can strip a member quietly. `ungated` names any protective class the constitution fails to gate
    (the gaps that leave a member exposed), so the family can close them before they matter."""
    protected: bool
    ungated: tuple
    reason: str = ""


def weakest_party_protected(constitution: GovernanceSkin, affecting_classes: Sequence[str]) -> WeakestPartyCheck:
    """THE weakest-party check (loud): given the decision classes that could override or remove a member against
    their will, confirm the family constitution gates **every one of them** with a human. `protected` is true
    only when none is ungated — the least-powerful member is protected, because nothing that could harm them can
    happen without a named human at a gate they can see. Any ungated class is surfaced by name, not hidden: an
    exposed member is told exactly where the rules fail them. This balances individual sovereignty with family
    unity — unity never comes at the cost of a member's protection."""
    ungated = tuple(str(c) for c in affecting_classes if str(c) not in constitution.gated_classes)
    protected = not ungated
    reason = ("every decision that could override a member passes a human gate — the least-powerful member is "
              "protected; no faction or authority can strip them quietly" if protected
              else f"{len(ungated)} decision class(es) could override a member with no human gate "
                   f"({list(ungated)}) — the weakest party is exposed until the constitution gates them")
    return WeakestPartyCheck(protected=protected, ungated=ungated, reason=reason)
