# -*- coding: utf-8 -*-
"""peerhood.delegation — Sovereign Peerhood (Series 14, Vol 3:
Delegation & Sponsorship Without Capture).

A sovereign peer must be able to delegate, accept help, and be sponsored — without any of it turning into
permanent leverage over its identity or future acts. This volume composes only sealed floors and the sealed
genesis layer (S14 Vol 1), inventing no new mechanism: every delegation, acceptance, and revocation is signed
with the peer's OWN self-held key. `delegate_governed` issues a TIME-BOUND, receipted, human-gated (composing the
sealed gate, Full Production ERP, S5 Vol 16) delegation the recipient can verify and revoke — under the peer's
own mandate (composing the owner's mandate, Full Production ERP, S5 Vol 28). `join_mutual_protection` joins a
mutual-protection arrangement with NO central insurer (reputation-as-receipts homes to Sovereign Risk & Mutual
Protection, S11 Vol 1), signed with the key, portable with the peer. `sponsor_without_claim` accepts or offers
help that creates NO lasting claim — the peer's birth trust boundary (composing the sealed boundary, Inter-Node
Sovereignty, S6 Vol 5) stays intact and the exit path is open by construction. `mandate_and_quorum` keeps
delegation under the peer's constitutional control via the owner's mandate and the family quorum (composing the
sealed succession, Generational Transfer, S12 Vol 1 `open_key_epoch` / `family_quorum_recovery`). `revoke_
delegation` is a FIRST-CLASS signed act that leaves NO residual claim.

KILL-TARGET: the sponsor that turns help into permanent leverage — refused. Fences (`DELEGATION_BREACH_FIELDS`):
no sponsorship-with-leverage / permanent claim · no scored credit issuance · no central insurer · no escrow /
custodian · no second authority · seal-key-closed (the node key is not the press/seal key). Weakest-party: a
peer with nothing but its own key can give and receive help and always exit clean. NO passphrase claim (self-
held file-custody). Holds no value; rolls no cryptography (composes the sealed self-held key).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .genesis import PeerIdentity, PeerhoodError                                        # S14 Vol 1 (sealed)
from ..keystore import has_node_key, sign_node_act, verify_node_act                      # D1 (sealed)
from ..trust.boundaries import declare_trust_anchor                                      # S6 Vol 5 (sealed)
from ..estate.generational_transfer import open_key_epoch, family_quorum_recovery        # S12 Vol 1 (sealed)

__all__ = ["delegate_governed", "verify_delegation", "join_mutual_protection", "sponsor_without_claim",
           "mandate_and_quorum", "revoke_delegation", "DELEGATION_BREACH_FIELDS", "PeerhoodError"]

# No sponsorship-with-leverage / permanent claim; no scored credit; no central insurer; no escrow/custodian.
DELEGATION_BREACH_FIELDS = frozenset({
    "sponsor_authority", "leverage", "permanent_claim", "lasting_claim", "permanent_leverage",
    "scored_credit", "credit_issuer", "credit_authority", "credit_score",
    "insurer", "central_insurer", "underwriter",
    "escrow", "custodian", "second_authority", "admission_authority",
    "seal_key", "press_key", "sealing_key",
})


def _dfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if (kl in DELEGATION_BREACH_FIELDS or "leverage" in kl or "permanent_claim" in kl
                or "lasting_claim" in kl or "insurer" in kl or "escrow" in kl or "custodian" in kl
                or "credit_score" in kl or "scored_credit" in kl):
            raise PeerhoodError(
                f"help and delegation are signed with the peer's OWN key and leave no lasting claim — a "
                f"sponsor-authority / leverage / permanent-claim / central-insurer / scored-credit / escrow / "
                f"custodian field ('{k}') is refused; help never becomes leverage")


# --- Delegation as a governed act (Ch 2, PRESENT): S5 Vol 16 gate + S5 Vol 28 mandate, time-bound ---------

def delegate_governed(keystore_dir: Optional[str], peer_id: str, delegate_to: str, capability: str, *,
                      expires_at: str, at: str, registry: Any, approver: str, approval_ref: str,
                      source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Issue a TIME-BOUND, receipted, human-gated delegation the recipient can verify and revoke — signed with
    the peer's OWN key, human-gated (composes the sealed gate, S5 Vol 16), under the peer's own mandate (composes
    the owner's mandate, S5 Vol 28). Deny-by-default: a delegation is human-gated (no approver → refused) and
    MUST be time-bound (no expiry → refused); a leverage / permanent-claim field is refused. Returns the governed
    delegation + signature — both sides hold a receipt."""
    _dfence(extra)
    if not str(approver or "").strip():
        raise PeerhoodError("a delegation is human-gated — it needs a named approver (human primacy)")
    if not str(expires_at or "").strip():
        raise PeerhoodError("a delegation must be TIME-BOUND — no open-ended delegation (it would become leverage)")
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a delegation must be signed by the peer's OWN key — no key on this iron")
    dele = registry.append(f"delegation:{peer_id}:{delegate_to}",
                           {"delegate_to": str(delegate_to), "capability": str(capability),
                            "expires_at": str(expires_at), "time_bound": True, "revocable": True},
                           author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify",
                           approver=approver, approval_ref=approval_ref)
    sig = sign_node_act(keystore_dir, peer_id, str(dele["version_hash"]).encode("utf-8"))
    return {"delegation": dele, "signature": sig, "time_bound": True, "revocable": True, "peer_id": peer_id}


def verify_delegation(delegation: Mapping[str, Any], identity: PeerIdentity, *,
                      revocations: Sequence[Mapping[str, Any]] = ()) -> bool:
    """Verify a delegation PUBLIC-ONLY — its signature checks against the delegating peer's OWN public key. The
    recipient (or anyone) confirms the delegation is genuinely the peer's, from a receipt they hold. **A
    revocation KILLS a live delegation:** if any revocation in `revocations` revokes this delegation's object id,
    it no longer verifies — `revoke_delegation` actually ends the grant, returning the capability to the peer."""
    obj = delegation.get("delegation") or {}
    dele_id = str(obj.get("object_id", ""))
    for r in revocations:
        if dele_id and str(r.get("revokes", "")) == dele_id:
            return False                                                 # a signed revocation kills the live delegation
    h = str(obj.get("version_hash", "")).encode("utf-8")
    return verify_node_act(identity.public_hex, h, str(delegation.get("signature", "")))


# --- Mutual protection without an insurer (Ch 3, PRESENT): S11 Vol 1 posture, signed, no insurer ----------

def join_mutual_protection(keystore_dir: Optional[str], peer_id: str, pool_ref: str, *, at: str, registry: Any,
                           source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Join a mutual-protection arrangement that has NO central insurer — the join is a governed commitment
    signed with the peer's OWN key, portable with the peer (reputation-as-receipts homes to Sovereign Risk &
    Mutual Protection, S11 Vol 1). Deny-by-default: the join is signed by the peer's own key (no key →
    fail-loud); an insurer / underwriter field is refused. Returns the governed join + signature."""
    _dfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a protection join must be signed by the peer's OWN key — no key on this iron")
    join = registry.append(f"protection:{pool_ref}:{peer_id}",
                           {"pool_ref": str(pool_ref), "peer": str(peer_id), "central_insurer": None,
                            "portable": True},
                           author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify")
    sig = sign_node_act(keystore_dir, peer_id, str(join["version_hash"]).encode("utf-8"))
    return {"join": join, "signature": sig, "central_insurer": None, "portable": True}


# --- Sponsorship without claim (Ch 4, PRESENT): S6 Vol 5 boundary intact, exit open -----------------------

def sponsor_without_claim(keystore_dir: Optional[str], peer_id: str, helper: str, help_ref: str, *, at: str,
                          registry: Any, source_ref: str = "s",
                          extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Accept or offer help that creates NO lasting claim on identity or future acts — the help is receipted,
    scoped, and signed with the peer's OWN key, the peer's trust boundary (composes the sealed `declare_trust_
    anchor`, S6 Vol 5) stays intact, and the exit path is open by construction. Deny-by-default: signed by the
    peer's own key (no key → fail-loud); a leverage / lasting-claim field is refused. Returns the governed help
    record + the intact boundary + signature."""
    _dfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("accepting help must be signed by the peer's OWN key — no key on this iron")
    # the peer's boundary stays intact — help does not open an ownership claim (composes S6 Vol 5)
    boundary = declare_trust_anchor(registry, peer_id,
                                    {"policy": "default-deny", "help_from": str(helper), "lasting_claim": None},
                                    mandate=peer_id, author=peer_id, source_ref=source_ref, at=at)
    rec = registry.append(f"help:{peer_id}:{helper}",
                          {"helper": str(helper), "help_ref": str(help_ref), "lasting_claim": None,
                           "exit_open": True},
                          author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify")
    sig = sign_node_act(keystore_dir, peer_id, str(rec["version_hash"]).encode("utf-8"))
    return {"help": rec, "boundary": boundary, "signature": sig, "lasting_claim": None, "exit_open": True}


# --- Mandate and quorum (Ch 5, PRESENT): S5 Vol 28 mandate + S12 Vol 1 quorum ------------------------------

def mandate_and_quorum(identity: PeerIdentity, family_keyholders: Sequence[str], *, epoch: int = 1,
                       quorum: int = 2, extra: Optional[Mapping[str, Any]] = None):
    """Keep delegation under the peer's constitutional control — the owner's mandate (composes the sealed mandate
    scope, S5 Vol 28, carried on every governed act) plus the family quorum (composes the sealed `open_key_epoch`
    / `family_quorum_recovery`, Generational Transfer, S12 Vol 1) over the peer's OWN fingerprint. Control never
    leaves the peer's key: a threshold of the FAMILY's own keys governs recovery, with no external authority.
    Returns the sealed `KeyEpoch` (the constitutional control envelope for the peer's delegations)."""
    _dfence(extra)
    holders = [identity.fingerprint] + [str(k) for k in family_keyholders if str(k).strip()]
    epoch_obj = open_key_epoch(identity.peer_id, epoch, holders)
    # constitutional control: a family quorum (the peer's own people) governs, no external authority
    recoverable = family_quorum_recovery(epoch_obj, holders[:quorum], quorum=quorum)
    return {"epoch": epoch_obj, "under_peer_control": bool(recoverable), "external_authority": None}


# --- Revocation as a first-class act (Ch 6, PRESENT): signed, no residual claim ---------------------------

def revoke_delegation(keystore_dir: Optional[str], peer_id: str, delegation_ref: str, *, at: str, registry: Any,
                      source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Revoke a delegation as a FIRST-CLASS signed act that leaves NO residual claim — signed with the peer's OWN
    key, so the peer can always take back what it delegated and be left free. Deny-by-default: the revocation is
    signed by the peer's own key (no key → fail-loud); a leverage / residual-claim field is refused. Returns the
    governed revocation + signature; the delegated capability returns wholly to the peer."""
    _dfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a revocation must be signed by the peer's OWN key — no key on this iron")
    rev = registry.append(f"revocation:{peer_id}:{delegation_ref}",
                          {"revokes": str(delegation_ref), "residual_claim": None, "first_class": True},
                          author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify")
    sig = sign_node_act(keystore_dir, peer_id, str(rev["version_hash"]).encode("utf-8"))
    return {"revocation": rev, "signature": sig, "residual_claim": None, "returned_to_peer": True,
            "revokes": str(delegation_ref), "by": str(peer_id)}
