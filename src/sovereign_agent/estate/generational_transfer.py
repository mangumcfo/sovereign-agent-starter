# -*- coding: utf-8 -*-
"""estate.generational_transfer — Generational Transfer (Series 12, Vol 1, the OPENER:
The Sovereign Estate That Executes Itself).

The most important transfer is not wealth — it is the ability to continue governing it. This opener builds a
generational handoff of keys, ledgers, ventures, and governance so that heirs inherit **working, verifiable
systems** rather than paperwork and disputes — and it does so by **executing** the transfer, composing the
sealed design layers of the stack below it and **re-implementing none of them.** The F3 boundary is the spine:
S10 V5 (`inherit_livelihood`) and S11 V05 (`inherit_protection`) — with the S9 material covenant
(`verify_under_covenant`) — **DESIGN and record** what is inheritable; **S12 EXECUTES the deep estate
transfer** by re-attributing ownership of the whole sovereign stack to the heir. `execute_transfer` is the
estate that executes itself: it composes the sealed inheritance checks over the decedent's estate — livelihood,
protection, and material — and, when the whole estate is intact and genuine, records the **re-attribution** to
the heir as a breath-gated governed act. `inheritance_package` assembles the verifiable inheritance package
(the Merkle-anchoring composes the sealed Object Model hashing; this layer rolls none). Key succession is the
family's own: `open_key_epoch` records the family's keyholders at an epoch (rotation), `family_quorum_recovery`
recovers access through an **M-of-N family quorum** (never a single custodian), and `breath_gated_key_transfer`
passes a key handoff through the sealed gate.

**The SUCCESSION-FENCE** (composition-not-engine · no second succession authority · no standing escrow):
`ESTATE_BREACH_FIELDS` refuses any escrow, held/escrowed estate, custodian, recovery authority, or second
succession authority — **inheritance is re-attribution of ownership records, not an estate an authority holds
and releases.** And the **SEAL-KEY-CLOSED law is untouched**: key succession is the family's own sovereign keys
(breath-gated, family-quorum), **never the press seal key, never a key off the sealing iron** — a `seal_key` /
`press_key` field is refused. KILL-TARGET: the executor / trust-company / key-custodian that owns the estate's
keys and rations the inheritance — refused. Weakest-party: **an heir with no second device verifies the estate
passed to them intact and theirs from a receipt they hold — not an executor's word.** NO TOKEN · no yield ·
holds no value · money-path OFF · rolls no cryptography.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..economy.livelihood_covenant import inherit_livelihood                          # S10 V5 (design layer)
from ..risk.protection_covenant import inherit_protection                             # S11 V05 (design layer)
from ..material.provision_covenant import verify_under_covenant                       # S9 material (design layer)
from ..economy.contribution import record_contribution, verify_contribution           # S10 V1 (governed record)

__all__ = ["execute_transfer", "verify_transfer", "inheritance_package", "open_key_epoch",
           "family_quorum_recovery", "breath_gated_key_transfer", "TransferStatus", "InheritancePackage",
           "KeyEpoch", "ESTATE_STACK_KINDS", "ESTATE_BREACH_FIELDS", "EstateRefused"]


class EstateRefused(Exception):
    """A generational-transfer act was refused (deny-by-default / the SUCCESSION-FENCE / seal-key-closed)."""


# The three sealed design layers an estate is made of — each verified by its own sealed covenant. S12 COMPOSES
# these; it re-implements none of them (livelihood = S10 V5, protection = S11 V05, material = S9).
ESTATE_STACK_KINDS = ("livelihood", "protection", "material")

# THE SUCCESSION-FENCE + SEAL-KEY-CLOSED: inheritance is re-attribution of ownership records — NOT an estate an
# authority holds and releases. Any escrow, custodian, recovery/succession authority, or second authority is a
# breach; and the family's key succession is NEVER the press seal key or a key off the sealing iron.
ESTATE_BREACH_FIELDS = frozenset({
    "escrow", "standing_escrow", "escrowed_estate", "held_estate", "custodian", "key_custodian",
    "release_authority", "second_authority", "succession_authority", "recovery_authority", "recovery_engine",
    "trust_company", "executor_authority", "held_value", "seal_key", "press_key", "sealing_key",
})


def _fence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in ("seal_key", "press_key", "sealing_key"):
            raise EstateRefused(
                f"key succession must carry no press/seal key field ('{k}') — this is the family's OWN "
                f"sovereign keys (breath-gated, family-quorum), NEVER the press seal key and never a key off "
                f"the sealing iron (the seal-key-closed law is untouched)")
        if kl in ESTATE_BREACH_FIELDS:
            raise EstateRefused(
                f"a generational-transfer act must carry no succession-authority/escrow field ('{k}') — S12 "
                f"EXECUTES by re-attribution of ownership records, composing the sealed design layers (S10 V5 / "
                f"S11 V05 / S9); it holds no escrow, appoints no custodian, and invents no recovery engine")


# --- Key lifecycle & secure succession (Ch 2) --------------------------------------------------------------

@dataclass(frozen=True)
class KeyEpoch:
    """A record of a family's keyholders at an epoch — the family's OWN sovereign keys, rotated by opening a new
    epoch. It is a governed record of who holds keys, not key material, and never the press seal key. Recovery
    is a family quorum; there is no custodian."""
    family_id: str
    epoch: int
    keyholders: tuple


def open_key_epoch(family_id: str, epoch: int, keyholders: Sequence[str], *,
                   extra: Optional[Mapping[str, Any]] = None) -> KeyEpoch:
    """Open a key epoch — record the family's keyholders at a point in time (rotation opens a new epoch). The
    family's OWN sovereign keys; the seal-key-closed law is untouched (a press/seal key field is refused).
    Deny-by-default: an epoch needs an id and at least one keyholder."""
    _fence(extra, "a key epoch")
    if not str(family_id).strip():
        raise EstateRefused("a key epoch needs a family id")
    ks = tuple(dict.fromkeys(str(k) for k in keyholders if str(k).strip()))
    if not ks:
        raise EstateRefused("a key epoch needs at least one keyholder — the family's own keys")
    return KeyEpoch(family_id=str(family_id), epoch=int(epoch), keyholders=ks)


def family_quorum_recovery(epoch: KeyEpoch, approvers: Sequence[str], *, quorum: int) -> bool:
    """Recover access through an M-of-N FAMILY QUORUM — never a single custodian. Returns True iff at least
    `quorum` distinct approvers are keyholders of the epoch. Deny-by-default: a quorum below two is refused (a
    single approver is a custodian, not a family quorum). Composition-not-engine: a quorum check over the
    family's own keyholders, not a custodial recovery authority."""
    if int(quorum) < 2:
        raise EstateRefused("family-quorum recovery needs a quorum of at least two — a single approver is a "
                            "custodian, not a family quorum (no custodial recovery authority)")
    present = {str(a) for a in approvers} & set(epoch.keyholders)
    return len(present) >= int(quorum)


def breath_gated_key_transfer(from_holder: str, to_heir: str, family_id: str, work_ref: str, *, gate: Any,
                              at: str, author: str, source_ref: str, registry: Any,
                              approver: Optional[str] = None, approval_ref: Optional[str] = None,
                              extra: Optional[Mapping[str, Any]] = None, mode: str = "corporate_regulated") -> dict:
    """Record a key-succession transfer as a governed act the heir OWNS, passing the sealed HumanApprovalGate
    (breath-gated; composes `record_contribution` + a role_spec that forbids the transfer without a human). The
    family's own sovereign keys; the seal-key-closed law is untouched (a press/seal key field is refused).
    Returns the heir's receipt."""
    _fence(extra, "a key transfer")
    ex = dict(extra or {}); ex["family_id"] = str(family_id); ex["from_holder"] = str(from_holder)
    ex["key_transfer"] = True
    return record_contribution(to_heir, "key_transfer", work_ref, contribution_class="attested",
                               mandate=to_heir, author=author, source_ref=source_ref, at=at, registry=registry,
                               extra=ex, approver=approver, approval_ref=approval_ref, gate=gate,
                               action_class="breath_gated_key_transfer",
                               role_spec={"charter_v7_forbidden_classes": ["breath_gated_key_transfer"]},
                               mode=mode)


# --- Verifiable inheritance package (Ch 3) -----------------------------------------------------------------

@dataclass(frozen=True)
class InheritancePackage:
    """A verifiable inheritance package: the decedent's whole estate — livelihood, protection, material — each
    verified by its own sealed covenant. Complete only when every present sub-stack is intact and genuine; it
    holds no value and files nothing. The Merkle-anchoring composes the sealed Object Model hashing; this layer
    rolls no cryptography of its own."""
    decedent: str
    complete: bool
    verified: Dict[str, bool] = field(default_factory=dict)
    reason: str = "a verifiable inheritance package of the decedent's own intact estate"


def _verify_estate(decedent: str, estate: Mapping[str, Any]) -> Dict[str, bool]:
    _fence(estate, "an estate")
    for k in estate:
        if str(k).lower() not in ESTATE_STACK_KINDS:
            raise EstateRefused(
                f"unknown estate sub-stack {k!r} — an estate composes {list(ESTATE_STACK_KINDS)} "
                f"(sealed S10 V5 / S11 V05 / S9); S12 invents no new design layer")
    out: Dict[str, bool] = {}
    if "livelihood" in estate:
        out["livelihood"] = inherit_livelihood(decedent, estate["livelihood"]).inherited      # S10 V5
    if "protection" in estate:
        out["protection"] = inherit_protection(decedent, estate["protection"]).inherited       # S11 V05
    if "material" in estate:
        out["material"] = all(verify_under_covenant(g["receipt"], g["good"]).provisioned       # S9
                              for g in estate["material"])
    return out


def inheritance_package(decedent: str, estate: Mapping[str, Any]) -> InheritancePackage:
    """Assemble a verifiable inheritance package from the decedent's whole estate (composes the sealed design
    layers: livelihood → `inherit_livelihood` S10 V5, protection → `inherit_protection` S11 V05, material →
    `verify_under_covenant` S9). Complete iff every present sub-stack is intact and genuine; deny-by-default: an
    empty estate is not complete; an unknown sub-stack or an escrow/custodian field is refused. Holds no value,
    files nothing; the Merkle-anchoring composes the sealed Object Model hashing."""
    verified = _verify_estate(decedent, estate)
    complete = bool(verified) and all(verified.values())
    reason = ("a verifiable inheritance package of the decedent's own intact estate" if complete
              else "; ".join(f"{k} sub-stack not intact/genuine" for k, v in verified.items() if not v)
                   or "an empty estate is not a complete inheritance package")
    return InheritancePackage(decedent=decedent, complete=complete, verified=verified, reason=reason)


# --- The estate that executes itself (Ch 8) ----------------------------------------------------------------

@dataclass(frozen=True)
class TransferStatus:
    """The one honest indicator an heir reads: *this estate is mine now* — transferred iff the whole estate
    verified as intact and genuine and ownership was re-attributed to the heir. Holds no value; the deep estate
    transfer is a re-attribution of ownership records, not a released escrow."""
    transferred: bool
    heir: str
    decedent: str
    by_stack: Dict[str, bool] = field(default_factory=dict)
    receipt: Optional[dict] = None
    reason: str = ""


def execute_transfer(decedent: str, heir: str, estate: Mapping[str, Any], work_ref: str, *, at: str,
                     author: str, source_ref: str, registry: Any, gate: Any = None,
                     approver: Optional[str] = None, approval_ref: Optional[str] = None,
                     extra: Optional[Mapping[str, Any]] = None, mode: str = "live") -> TransferStatus:
    """The Sovereign Estate That Executes Itself: EXECUTE the deep estate transfer by **re-attributing
    ownership** of the whole sovereign stack to the heir, composing the sealed inheritance checks over the
    decedent's estate (livelihood → S10 V5, protection → S11 V05, material → S9). When the whole estate is
    intact and genuine, it records the re-attribution to the heir as a governed act (breath-gated if a gate is
    supplied) and returns `transferred=True` with the heir's receipt. Composition-not-engine: it composes the
    sealed design layers, re-implements none, and invents no recovery/escrow engine. The SUCCESSION-FENCE
    refuses any escrow/custodian/second-authority field; the seal-key-closed law is untouched. Deny-by-default:
    an empty or unverified estate does not transfer."""
    _fence(extra, "an estate transfer")
    by_stack = _verify_estate(decedent, estate)
    intact = bool(by_stack) and all(by_stack.values())
    if not intact:
        return TransferStatus(transferred=False, heir=heir, decedent=decedent, by_stack=by_stack, receipt=None,
                              reason="; ".join(f"{k} not intact" for k, v in by_stack.items() if not v)
                                     or "an empty estate does not transfer")
    ex = dict(extra or {}); ex["from_decedent"] = str(decedent); ex["estate_reattributed"] = True
    role_spec = {"charter_v7_forbidden_classes": ["execute_transfer"]} if (gate is not None) else None
    receipt = record_contribution(heir, "estate_transfer", work_ref, contribution_class="attested",
                                  mandate=heir, author=author, source_ref=source_ref, at=at, registry=registry,
                                  extra=ex, approver=approver, approval_ref=approval_ref, gate=gate,
                                  action_class="execute_transfer", role_spec=role_spec,
                                  mode=("corporate_regulated" if gate is not None else mode))
    return TransferStatus(transferred=True, heir=heir, decedent=decedent, by_stack=by_stack, receipt=receipt,
                          reason="this estate is mine now — the whole estate re-attributed to the heir")


def verify_transfer(receipt: Mapping[str, Any], heir: str, decedent: str, work_ref: str, *,
                    extra: Optional[Mapping[str, Any]] = None) -> bool:
    """Weakest-party check: an heir with no second device confirms the estate passed to them — intact and
    theirs — from the receipt they hold (composes `verify_contribution`, S10 V1), not an executor's word. A
    tampered decedent or work reference flips the light."""
    ex = dict(extra or {}); ex["from_decedent"] = str(decedent); ex["estate_reattributed"] = True
    return verify_contribution(receipt, heir, work_ref, contribution_class="attested", source="estate_transfer",
                               extra=ex).provisioned
