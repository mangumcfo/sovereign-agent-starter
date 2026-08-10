# -*- coding: utf-8 -*-
"""estate.key_succession — Generational Transfer (Series 12, Vol 2:
Advanced Key Management, Recovery & Secure Succession).

Basic key handoff breaks in real family scenarios — a single point of failure, an incapacity nobody planned
for, many heirs and no coordination. This volume designs the **advanced key lifecycle** on top of the sealed
opener: key epochs and rotation, quorum-threshold recovery, secure receipted handoff, and a dry-run that
stress-proofs a succession plan **before it is needed** — and it does so by **composing** the sealed key
primitives of the opener (`open_key_epoch`, `KeyEpoch`, `family_quorum_recovery`, `breath_gated_key_transfer`,
S12 V1) and **re-implementing none of them.** It rolls no cryptography and stores no key material.

**This is the sharpest test of the SEAL-KEY-CLOSED law in the whole runway — because it *is* key management.**
The keys a family rotates, recovers, and hands off are the **family's OWN sovereign keys**: recovery is an
**M-of-N family quorum**, never a custodian; a rotation opens the family's next epoch; a handoff passes the
sealed human gate. There is **no custodial recovery authority, no key-escrow, no recovery engine, and nothing
of the press seal key** — `KEY_SUCCESSION_BREACH_FIELDS` refuses a custodial-recovery / key-escrow / recovery-
engine / stored-key-material field, and (inherited from the opener) any `seal_key` / `press_key` / `sealing_key`
field. KILL-TARGET: the key-custodian / recovery service that can lock a family out of its own keys — refused.
Weakest-party: a family recovers access through its own quorum, from records it holds, with no second authority.
NO TOKEN · no yield · holds no value · money-path OFF · rolls no cryptography · stores no key material.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence

from .generational_transfer import (                                                   # S12 V1 (sealed opener)
    KeyEpoch, open_key_epoch, family_quorum_recovery, breath_gated_key_transfer, EstateRefused,
)

__all__ = ["rotate_key_epoch", "QuorumPolicy", "define_quorum", "recover_with_quorum", "secure_key_handoff",
           "SuccessionDrill", "simulate_succession", "KEY_SUCCESSION_BREACH_FIELDS"]


# THE SEAL-KEY-CLOSED FENCE, SHARPENED for the key-management volume: a family's key succession NEVER routes
# through a custodial recovery authority, a key-escrow, a recovery engine, a backup-custody service, stored key
# material, or (inherited) the press seal key. Every advanced key act refuses these in code.
KEY_SUCCESSION_BREACH_FIELDS = frozenset({
    "custodial_recovery", "custodian", "key_custodian", "key_escrow", "escrow", "recovery_authority",
    "recovery_engine", "recovery_service", "backup_custodian", "key_backup_service", "key_material",
    "private_key", "seed_phrase_store", "second_authority", "seal_key", "press_key", "sealing_key",
})


def _kfence(mapping: Optional[Mapping[str, Any]], where: str) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if kl in ("seal_key", "press_key", "sealing_key"):
            raise EstateRefused(
                f"key succession must carry no press/seal key field ('{k}') — a family rotates, recovers, and "
                f"hands off its OWN sovereign keys, NEVER the press seal key and never a key off the sealing "
                f"iron (the seal-key-closed law is untouched)")
        if kl in KEY_SUCCESSION_BREACH_FIELDS:
            raise EstateRefused(
                f"advanced key succession must carry no custodial-recovery/key-escrow/recovery-engine field "
                f"('{k}') — recovery is an M-of-N FAMILY QUORUM over the family's own keys; there is no "
                f"custodian, no key-escrow, and no recovery engine (composition, not a custody service)")


# --- Advanced key lifecycle design (Ch 2) ------------------------------------------------------------------

def rotate_key_epoch(prev: KeyEpoch, new_keyholders: Sequence[str], *,
                     extra: Optional[Mapping[str, Any]] = None) -> KeyEpoch:
    """Rotate the family's keys by opening the NEXT epoch — advanced key lifecycle as versioned rotation
    (composes the sealed `open_key_epoch`, S12 V1). The new epoch is `prev.epoch + 1` for the same family; the
    family's OWN keyholders, never a custodian and never the press seal key. Deny-by-default: a rotation needs
    at least one keyholder; a custodial-recovery / key-escrow / seal-key field is refused."""
    _kfence(extra, "a key rotation")
    if not isinstance(prev, KeyEpoch):
        raise EstateRefused("a key rotation rotates an existing epoch — the family's prior KeyEpoch")
    return open_key_epoch(prev.family_id, int(prev.epoch) + 1, new_keyholders, extra=extra)


# --- Quorum recovery & multi-party protocols (Ch 3 / Ch 5) -------------------------------------------------

@dataclass(frozen=True)
class QuorumPolicy:
    """A family recovery quorum policy: the M-of-N threshold the family sets for recovering access. Threshold is
    at least two — a single approver is a custodian, not a family quorum. It is a governed rule, not a custody
    service; it holds no key material."""
    family_id: str
    threshold: int


def define_quorum(epoch: KeyEpoch, *, threshold: int, extra: Optional[Mapping[str, Any]] = None) -> QuorumPolicy:
    """Define the family's recovery quorum threshold for an epoch. Deny-by-default: a threshold below two is
    refused (a single approver is a custodian, not a family quorum); a threshold above the number of keyholders
    can never be met and is refused; a custodial-recovery / key-escrow field is refused."""
    _kfence(extra, "a quorum policy")
    if int(threshold) < 2:
        raise EstateRefused("a family recovery quorum needs a threshold of at least two — a single approver is "
                            "a custodian, not a family quorum (no custodial recovery authority)")
    if int(threshold) > len(epoch.keyholders):
        raise EstateRefused("a recovery quorum threshold cannot exceed the family's keyholder count — it could "
                            "never be met (define a reachable family quorum, not an unrecoverable one)")
    return QuorumPolicy(family_id=epoch.family_id, threshold=int(threshold))


def recover_with_quorum(epoch: KeyEpoch, approvers: Sequence[str], policy: QuorumPolicy) -> bool:
    """Recover access through the family's M-of-N quorum (composes the sealed `family_quorum_recovery`, S12 V1).
    Returns True iff at least `policy.threshold` distinct approvers are keyholders of the epoch. Deny-by-default:
    a policy for a different family cannot recover this epoch. No custodian is ever consulted — the family
    recovers itself."""
    if policy.family_id != epoch.family_id:
        raise EstateRefused("a recovery quorum policy binds to its own family — it cannot recover another "
                            "family's epoch")
    return family_quorum_recovery(epoch, approvers, quorum=policy.threshold)


# --- Secure key handoff & transfer protocols (Ch 4) --------------------------------------------------------

def secure_key_handoff(from_holder: str, to_heir: str, epoch: KeyEpoch, work_ref: str, *, gate: Any, at: str,
                       author: str, source_ref: str, registry: Any, approver: Optional[str] = None,
                       approval_ref: Optional[str] = None, extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Hand off a key to an heir as a secure, receipted, human-gated act (composes the sealed
    `breath_gated_key_transfer`, S12 V1). The handoff must be from a current keyholder of the epoch — a stranger
    cannot hand off the family's key. Passes the sealed HumanApprovalGate (breath-gated); a custodial-recovery /
    key-escrow / seal-key field is refused. Returns the heir's receipt (the heir owns it)."""
    _kfence(extra, "a key handoff")
    if str(from_holder) not in set(epoch.keyholders):
        raise EstateRefused("a secure key handoff must come from a current keyholder of the epoch — the "
                            "family's own key, not a custodian's")
    return breath_gated_key_transfer(from_holder, to_heir, epoch.family_id, work_ref, gate=gate, at=at,
                                     author=author, source_ref=source_ref, registry=registry, approver=approver,
                                     approval_ref=approval_ref, extra=extra)


# --- Testing, simulation & stress-proofing succession (Ch 7) -----------------------------------------------

@dataclass(frozen=True)
class SuccessionDrill:
    """A dry-run of a family's recovery plan under a loss scenario — does the remaining quorum still recover?
    It moves NO key and touches no key material; it is a stress-proofing simulation the family runs before a
    succession is ever needed. `recoverable` is the honest indicator; `remaining`/`needed` show the margin."""
    recoverable: bool
    remaining: int
    needed: int
    reason: str = ""


def simulate_succession(epoch: KeyEpoch, policy: QuorumPolicy, *, lost: Sequence[str] = ()) -> SuccessionDrill:
    """Stress-proof a succession plan: given a scenario where `lost` keyholders are unavailable, report whether
    the family's remaining keyholders can still meet the recovery quorum — WITHOUT moving any key or touching
    key material (composition, not a recovery engine). Deny-by-default: a policy for another family cannot be
    drilled against this epoch. This is the dry-run every plan should pass before it is needed."""
    if policy.family_id != epoch.family_id:
        raise EstateRefused("a succession drill runs a family's own policy against its own epoch")
    remaining = [k for k in epoch.keyholders if str(k) not in {str(x) for x in lost}]
    ok = len(remaining) >= int(policy.threshold)
    reason = ("the remaining family quorum still recovers under this loss scenario" if ok
              else f"only {len(remaining)} keyholders remain; the recovery quorum of {policy.threshold} cannot "
                   f"be met — widen the family quorum before this scenario is real")
    return SuccessionDrill(recoverable=ok, remaining=len(remaining), needed=int(policy.threshold), reason=reason)
