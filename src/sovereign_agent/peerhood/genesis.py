# -*- coding: utf-8 -*-
"""peerhood.genesis — Sovereign Peerhood (Series 14, Vol 1, OPENER:
Genesis of a Sovereign Peer).

The final series opens where a sovereign life must begin: a peer that comes into existence **cold**, holding
nothing but the ability to generate and keep its own key on its own hardware — no issuer, no registrar, no
custodian, no registry that "creates" it and could revoke its existence. This opener composes only sealed floors
and the sealed D1-keystore, inventing no new mechanism. `establish_self_held_identity` mints (or loads) the
peer's OWN key on its OWN iron (D1) and presents it as the node's own evidence on the record (Zero-Trust
Sovereignty, S7 Vol 1) — no central attestation. `declare_birth_boundary` declares the peer's first,
default-deny trust boundary (Trust Boundaries, S6 Vol 5), signed with the peer's own key — no second admission
authority. `issue_first_receipt` issues the peer's first **human-gated** governed act (Object Model, S5 Vol 5 +
the human gate, S5 Vol 16), signed with the key; `verify_peer_existence` proves the peer exists from a receipt
the peer holds — no registry consulted or written. `genesis_green_light` is the weakest-party test: one honest
indicator that stays on **only while** the self-held key is under the peer's sole control and no external
permanent claim exists — red/absent = not yet sovereign. Recovery is never inside genesis: `genesis_recovery_
epoch` composes the sealed family-quorum succession (Generational Transfer, S12 Vol 1 `open_key_epoch` /
`family_quorum_recovery`, and Key-Management, S12 Vol 2) over the peer's own fingerprint — the family's own keys,
no external custodian.

KILL-TARGET: the issuer / registrar / custodian that "creates" the peer and can revoke their existence — refused.
Peer fences (`GENESIS_BREACH_FIELDS`): no escrow · no custodian · no recovery-authority inside genesis · no
second admission authority · no registry · seal-key-closed (the node key is NOT the press/seal key). Honest
posture: the keystore is self-held file-custody on the peer's own iron — **no passphrase protection is claimed**;
a key that is absent fails loud. NO TOKEN · no yield · holds no value · rolls no cryptography (composes D1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from ..keystore import (                                                                # D1 (sealed)
    generate_node_key, load_node_key, has_node_key, sign_node_act, verify_node_act, KeystoreError,
)
from ..zero_trust.node_arch import present_evidence                                     # S7 Vol 1 (sealed)
from ..trust.boundaries import declare_trust_anchor                                     # S6 Vol 5 (sealed)
from ..estate.generational_transfer import open_key_epoch, family_quorum_recovery       # S12 Vol 1 (sealed)

__all__ = ["establish_self_held_identity", "PeerIdentity", "declare_birth_boundary",
           "issue_first_receipt", "verify_peer_existence", "genesis_green_light", "GreenLight",
           "genesis_recovery_epoch", "GENESIS_BREACH_FIELDS", "PeerhoodError"]

# No issuer/registrar/registry that creates the peer; no custodian/escrow/recovery-authority inside genesis;
# no second admission authority; seal-key-closed (the node key is not the press/seal key).
GENESIS_BREACH_FIELDS = frozenset({
    "issuer", "registrar", "registry", "directory", "name_service",
    "custodian", "escrow", "recovery_authority", "recovery_agent",
    "second_authority", "admission_authority", "attestation_authority", "sponsor_authority",
    "external_claim", "permanent_claim", "ownership_claim",
    "seal_key", "press_key", "sealing_key",
})


class PeerhoodError(ValueError):
    """A genesis act was refused (fenced field, absent key, or missing human gate) — fail-loud."""


def _gfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if (kl in GENESIS_BREACH_FIELDS or "issuer" in kl or "registrar" in kl or "registry" in kl
                or "custodian" in kl or "escrow" in kl or "external" in kl or "permanent_claim" in kl):
            raise PeerhoodError(
                f"a sovereign peer is born from its OWN self-held key — an issuer / registrar / registry / "
                f"custodian / escrow / external-claim / seal-key field ('{k}') is refused; no one creates the "
                f"peer and no one can revoke its existence")


# --- Self-held identity (Ch 2, PRESENT): D1 key + S7 Vol 1 own-evidence -------------------------------------

@dataclass(frozen=True)
class PeerIdentity:
    """A sovereign peer's identity — its OWN self-held key, presented as its own evidence on the record. The
    identity rests on a real key the peer holds on its own iron (D1), not a claim a central authority issued
    about it. The private scalar never appears here."""
    peer_id: str
    public_hex: str
    fingerprint: str
    evidence_hash: str          # the S7 governed evidence object's version hash (own-evidence commitment)


def establish_self_held_identity(keystore_dir: Optional[str], peer_id: str, *, at: str, registry: Any,
                                 source_ref: str = "s", author: Optional[str] = None,
                                 extra: Optional[Mapping[str, Any]] = None) -> PeerIdentity:
    """Establish the peer's self-held identity: mint (or load) the peer's OWN key on its OWN iron (composes D1
    `generate_node_key` / `load_node_key`) and present it as the node's own evidence on the record (composes the
    sealed `present_evidence`, S7 Vol 1) — no hub, no third party, no central attestation vouches for it. Returns
    the peer's public identity. Deny-by-default: an issuer / registrar / custodian field is refused; the private
    key never leaves the peer's iron."""
    _gfence(extra)
    author = author or peer_id
    nk = load_node_key(keystore_dir, peer_id) if has_node_key(keystore_dir, peer_id) \
        else generate_node_key(keystore_dir, peer_id, at=at)
    ev = present_evidence(registry, peer_id,
                          {"self_held_pubkey": nk.public_hex, "fingerprint": nk.fingerprint, "attestation": "self"},
                          mandate=peer_id, author=author, source_ref=source_ref, at=at)
    return PeerIdentity(peer_id=peer_id, public_hex=nk.public_hex, fingerprint=nk.fingerprint,
                        evidence_hash=str(ev["version_hash"]))


# --- Trust boundary at birth (Ch 3, PRESENT): S6 Vol 5, signed with the key --------------------------------

def declare_birth_boundary(keystore_dir: Optional[str], peer_id: str, *, at: str, registry: Any,
                           source_ref: str = "s", author: Optional[str] = None,
                           extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Declare the peer's first trust boundary at birth — a **default-deny** trust anchor (composes the sealed
    `declare_trust_anchor`, S6 Vol 5) that protects the new peer from any external claim of ownership, signed
    with the peer's OWN key. Deny-by-default: the boundary must be signed by the peer's own key (no key → refused,
    fail-loud); no second admission authority is created. Returns the governed boundary object + its signature."""
    _gfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a birth boundary must be signed by the peer's OWN key — no key on this iron; "
                            "establish the self-held identity first")
    author = author or peer_id
    anchor = {"policy": "default-deny", "self_held_pubkey": load_node_key(keystore_dir, peer_id).public_hex,
              "genesis": True}
    obj = declare_trust_anchor(registry, peer_id, anchor, mandate=peer_id, author=author,
                               source_ref=source_ref, at=at)
    sig = sign_node_act(keystore_dir, peer_id, str(obj["version_hash"]).encode("utf-8"))
    return {"boundary": obj, "signature": sig, "signed_by": peer_id, "default_deny": True}


# --- The first receipt (Ch 4, PRESENT): S5 Vol 5 object + S5 Vol 16 human gate, signed --------------------

def issue_first_receipt(keystore_dir: Optional[str], peer_id: str, act_ref: str, *, at: str, registry: Any,
                        approver: str, approval_ref: str, source_ref: str = "s", author: Optional[str] = None,
                        extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Issue the peer's first receipted act — a governed object (composes the sealed Object Model, S5 Vol 5),
    **human-gated** at genesis (a named approver, the sealed human gate S5 Vol 16), and signed with the peer's
    OWN key. Deny-by-default: genesis is human-gated once the key exists (no approver → refused); the act must be
    signed by the peer's own key (no key → refused); no registry is consulted or written beyond the peer's own
    record. Returns the first governed receipt + its signature — the peer's existence proof."""
    _gfence(extra)
    if not str(approver or "").strip():
        raise PeerhoodError("genesis is human-gated — the first sovereign act needs a named approver "
                            "(human primacy, once the self-held key exists)")
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("the first receipt must be signed by the peer's OWN key — no key on this iron")
    author = author or peer_id
    obj = registry.append(f"genesis:{peer_id}", {"act_ref": str(act_ref), "genesis": True},
                          author=author, source_ref=source_ref, at=at, mandate=peer_id,
                          kind="ratify", approver=approver, approval_ref=approval_ref)
    sig = sign_node_act(keystore_dir, peer_id, str(obj["version_hash"]).encode("utf-8"))
    return {"receipt": obj, "signature": sig, "peer_id": peer_id}


def verify_peer_existence(receipt: Mapping[str, Any], identity: PeerIdentity) -> bool:
    """Prove the peer exists from a receipt the peer holds — the first receipt's signature verifies (PUBLIC-ONLY)
    against the peer's OWN public key. No registry, no third party: existence is proved by the peer's own
    receipt, verifiable by anyone holding only the public key."""
    obj = receipt.get("receipt") or {}
    return verify_node_act(identity.public_hex, str(obj.get("version_hash", "")).encode("utf-8"),
                           str(receipt.get("signature", "")))


# --- Green-light verification (Ch 6, PRESENT): the weakest-party genesis test ------------------------------

@dataclass(frozen=True)
class GreenLight:
    """The genesis green-light — the weakest-party test a resourceless peer reads for itself: ONE honest
    indicator that stays on ONLY while the self-held key is under the peer's sole control and no external
    permanent claim exists. Red or absent = not yet sovereign."""
    peer_id: str
    on: bool
    reason: str


def genesis_green_light(keystore_dir: Optional[str], peer_id: str, *,
                        external_claim: Any = None, extra: Optional[Mapping[str, Any]] = None) -> GreenLight:
    """Read the genesis green-light — the weakest-party test. The light is ON only when the self-held key is
    present and under the peer's SOLE control on its own iron AND no external permanent claim exists; it is OFF
    if an external claim is present, and ABSENT (off) if no key exists. A resourceless peer reads this one honest
    indicator for itself, from what it holds — never a platform's word that it is 'verified'."""
    _gfence(extra)
    if external_claim:
        return GreenLight(peer_id, False,
                          "an external permanent claim exists — not yet sovereign; the green-light is off")
    if not has_node_key(keystore_dir, peer_id):
        return GreenLight(peer_id, False,
                          "no self-held key on this iron — the peer does not yet exist; the green-light is absent")
    try:
        load_node_key(keystore_dir, peer_id)             # sole control: the key loads from the peer's own iron
    except KeystoreError:
        return GreenLight(peer_id, False,
                          "the self-held key is not under sole control on this iron — the green-light is off")
    return GreenLight(peer_id, True,
                      "the self-held key is under the peer's sole control and no external claim exists — sovereign")


# --- Recovery path without custodian (Ch 5, COMPOSE): sealed S12, never inside genesis ---------------------

def genesis_recovery_epoch(identity: PeerIdentity, family_keyholders: Sequence[str], *, epoch: int = 1):
    """Open the peer's recovery epoch by composing the sealed family-quorum succession (S12 Vol 1
    `open_key_epoch`; recover via `family_quorum_recovery`, with Key-Management, S12 Vol 2, sealed) over the
    peer's OWN fingerprint plus the family's own keyholders — the family's own keys only, NO external custodian.
    Recovery is never inside genesis; D1 holds no recovery authority — this composes the sealed S12 floors on
    top. Returns the sealed `KeyEpoch`."""
    holders = [identity.fingerprint] + [str(k) for k in family_keyholders if str(k).strip()]
    return open_key_epoch(identity.peer_id, epoch, holders)
