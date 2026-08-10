# -*- coding: utf-8 -*-
"""risk.protection_covenant — Sovereign Risk & Mutual Protection (Series 11, Vol 5, the CAPSTONE:
Generational Continuity & Full Synthesis).

Protection that ends when its founder does was never protection — it was a subscription. This capstone brings
the whole series together into a protection stack that outlasts its founder, and it does so by composing the
sealed S11 volumes and **inventing no new engine**. `inherit_protection` is the one covenant an heir reads: it
dispatches every element of a protection stack — pool premiums (V1), claims (V1), group premiums (V3),
attestation chains (V2), and governance skins (V4) — to that element's own sealed verifier, and returns **one
uniform indicator**, `this is mine now`, true only when every element verifies as owned and intact. A whole
protection stack becomes inheritable in a single honest green light: the heir needs no second device, no
expertise, and no permission — just the receipts they hold. Inheritance of the protection stack is
**re-attribution of owned records** — pool memberships, credit history, reputation, and the governance skin —
**not an escrowed obligation released by an authority.**

**The SUCCESSION-FENCE** (the capstone's sharpest constraint, inherited and sharpened for protection): **no
second succession authority · no standing escrow of protection obligations · composition-not-engine.** A stack
element carrying an escrow, a held/escrowed obligation, a recovery/succession engine, or a second authority
vouching the handoff is refused in code (`PROTECTION_SUCCESSION_BREACH_FIELDS`). Kill-target: the succession
authority that holds your family's protection obligations in escrow and releases them on its terms — refused;
inheritance is records the heir verifies, not obligations an authority releases. Weakest-party: **a
resourceless heir verifies the inherited protection stack is intact and theirs on a single honest indicator.**
The deep estate transfer homes OUT: **S11 designs and records protection continuity; Generational Transfer
(S12) executes the deep estate transfer** (the F3 boundary), with Generational Continuity (S5 Vol 29) the
continuity floor. NO TOKEN · no yield · holds no value · no underwriting/pricing/optimization · rolls no
cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from .mutual_protection import verify_premium, verify_claim, IncomeRefused, IncomeStatus, Pool   # S11 V1
from .advanced_pooling import verify_attestation_chain                                            # S11 V2
from .group_applications import verify_group_premium                                              # S11 V3
from .governance import load_governance_skin, GovernanceSkin, GOVERNANCE_BREACH_FIELDS            # S11 V4

__all__ = ["inherit_protection", "verify_stack_element", "protection_stream_kinds",
           "ProtectionStatus", "PROTECTION_STREAM_KINDS", "PROTECTION_SUCCESSION_BREACH_FIELDS",
           "IncomeRefused", "IncomeStatus", "Pool"]

# The elements of a protection stack, each verified by its own sealed S11 floor. The covenant COMPOSES these;
# it re-implements none of them.
PROTECTION_STREAM_KINDS = ("premium", "claim", "group_premium", "attestation_chain", "governance_skin")

# THE SUCCESSION-FENCE for protection: inheritance is re-attribution of owned records — NOT a held/escrowed
# obligation released by an authority. Any escrow, standing-held obligation, recovery/succession engine, or
# second authority vouching the handoff is a breach — refused.
PROTECTION_SUCCESSION_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "escrowed_obligation", "held_obligation", "obligation_escrow",
    "release_authority", "releasing_authority", "second_authority", "succession_authority",
    "recovery_engine", "succession_engine", "vouching_authority", "custodian", "held_value",
})


def protection_stream_kinds() -> List[str]:
    """The stack element kinds a protection covenant composes — one per sealed S11 surface (V1–V4)."""
    return list(PROTECTION_STREAM_KINDS)


@dataclass(frozen=True)
class ProtectionStatus:
    """The one honest indicator an heir reads: *this is mine now* — inherited iff every element of the
    protection stack verifies as owned and intact. Holds no value; a by-kind tally shows the shape of the
    inherited protection. A resourceless heir needs nothing but this single green light."""
    inherited: bool
    reason: str
    owner: str
    verified_count: int
    by_kind: Dict[str, int] = field(default_factory=dict)


def _fence_element(element: Mapping[str, Any]) -> None:
    for k in element:
        if str(k).lower() in PROTECTION_SUCCESSION_BREACH_FIELDS:
            raise IncomeRefused(
                f"a protection-stack element must carry no succession-authority/escrow field ('{k}') — "
                f"inheritance is re-attribution of owned RECORDS (pool memberships, credit history, "
                f"reputation, governance), not a held/escrowed obligation released by an authority; the "
                f"covenant composes the sealed S11 V1–V4 surfaces + Continuity, it invents no succession engine")


def verify_stack_element(owner: str, element: Mapping[str, Any]) -> bool:
    """Verify ONE element of a protection stack by composing its own sealed S11 verifier. `element` is
    `{kind, ...}` where kind ∈ premium|claim|group_premium|attestation_chain|governance_skin and the rest are
    the args that kind's sealed surface needs. The SUCCESSION-FENCE refuses any escrow / second-authority /
    recovery-engine field — inheritance is a verified record, not a released obligation."""
    kind = str(element.get("kind", "")).strip().lower()
    if kind not in PROTECTION_STREAM_KINDS:
        raise IncomeRefused(
            f"unknown protection-stack element kind {element.get('kind')!r} — a covenant composes one of "
            f"{list(PROTECTION_STREAM_KINDS)} (sealed S11 V1–V4); it invents no new element")
    _fence_element(element)
    if kind == "premium":
        return verify_premium(element["receipt"], element["pool"], owner, element["work_ref"],
                              contribution_class=element["contribution_class"], amount=element.get("amount"),
                              extra=element.get("extra")).provisioned
    if kind == "claim":
        return verify_claim(element["receipt"], owner, element["pool"], element["work_ref"],
                            claim_class=element["claim_class"], amount=element.get("amount"),
                            extra=element.get("extra")).provisioned
    if kind == "group_premium":
        return verify_group_premium(element["receipt"], element["pool"], owner, element["work_ref"],
                                    group_class=element["group_class"],
                                    contribution_class=element["contribution_class"],
                                    amount=element.get("amount")).provisioned
    if kind == "attestation_chain":
        return verify_attestation_chain(element["chain"], owner, element["pool"], element["work_ref"],
                                        claim_class=element["claim_class"], attestors=element["attestors"],
                                        amount=element.get("amount"))
    # kind == "governance_skin": the governance transfers intact iff its policy-as-code re-derives (composes
    # load_governance_skin, S11 V4) — a skin with a pricing/underwriting/optimization rule never transfers.
    reloaded = load_governance_skin(element["skin_id"], gated_classes=element["gated_classes"],
                                    limits=element.get("limits"), version=element.get("version", "v1"))
    return isinstance(reloaded, GovernanceSkin) and bool(reloaded.gated_classes)


def inherit_protection(owner: str, stack: Sequence[Mapping[str, Any]]) -> ProtectionStatus:
    """The Sovereign Protection Covenant: verify that a WHOLE protection stack is intact and inheritable by
    composing each element's own sealed S11 verifier (V1–V4) — one uniform check over any element kind. Returns
    ONE honest indicator, `inherited`, true iff every element verifies as `owner`'s own and intact (*this is
    mine now*), with a by-kind tally. It records nothing, holds no value, invents no engine, rolls no
    cryptography, and underwrites/prices nothing. Deny-by-default: an empty stack is not inherited; a foreign or
    tampered element fails the whole; an escrow/second-authority field is refused (the SUCCESSION-FENCE); an
    unknown kind is refused. The deep estate transfer homes OUT to Generational Transfer (S12); this covenant
    proves the protection stack is intact and inheritable (Generational Continuity, S5 Vol 29), it does not
    perform the estate transfer (the F3 boundary)."""
    by_kind = {k: 0 for k in PROTECTION_STREAM_KINDS}
    verified = 0
    reason: List[str] = []
    for i, element in enumerate(stack):
        if verify_stack_element(owner, element):     # composes the sealed floor; raises on fence/kind breach
            verified += 1
            by_kind[str(element.get("kind")).strip().lower()] += 1
        else:
            reason.append(f"element {i} ({element.get('kind')}) does not verify as {owner}'s own/intact")
    ok = bool(stack) and not reason
    return ProtectionStatus(inherited=ok,
                            reason="; ".join(reason) or "this is mine now — the whole protection stack verifies",
                            owner=owner, verified_count=verified, by_kind=by_kind)
