# -*- coding: utf-8 -*-
"""peerhood.bridging — Sovereign Peerhood (Series 14, Vol 4:
Bridging into Pools & Federations).

A sovereign peer must be able to enter value pools and federations — and leave them — without any of it becoming
a platform dependency: no bridging hub that mediates every bridge, no permanent membership token a third party
holds, and no central settlement. This volume composes only sealed floors and the sealed peerhood layers (S14
V01-V03), inventing no new mechanism: every bridge, join, attribution, and vote is signed with the peer's OWN
self-held key, and value settles ONLY across the sealed Sovereign Port. `form_peer_pool` forms or joins a value
pool that is itself a set of receipted, governed peer acts (composing the sealed Networked Value Pools, Sovereign
Livelihood, S10 V2 `form_pool`) — the pool holds no value and appoints no custodian; membership is the peer's own
reversible record, signed. `bridge_into_pool` executes a receipted bridge (composing the sealed inter-node
messaging, Inter-Node Sovereignty, S6 V1) both sides can verify (`verify_bridge`, public-only) and reverse.
`federate_without_directory` participates in federation discovery with NO central directory (composing the sealed
directory-free recognition, S14 V02). `attribute_pool_value` records earned value as the member's OWN receipt
that travels with the peer (composing the sealed pool contribution over the income primitive, S10 V2 / V1) —
value settles ONLY via the Port (`settle_pool_on_port` composes the sealed `pool_settlement`, no in-node
netting). `pool_vote` participates in pool decisions through HUMAN-GATED, receipted votes (composing the sealed
pool governance, Sovereign Risk & Mutual Protection, S11 V4, over the sealed gate, S5 V16).

KILL-TARGET: the bridging hub that mediates every bridge, holds a membership token you cannot leave with, and
settles in the middle — refused. Fences (`BRIDGING_BREACH_FIELDS`): no bridging hub · no permanent membership
token · no central settlement / netting / pool balance (value rides the Port ONLY) · no registry / directory ·
no custodian / escrow · seal-key-closed. Weakest-party: a peer with nothing but its own key enters and leaves
pools freely. NO passphrase claim (self-held file-custody). Holds no value; rolls no cryptography.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .genesis import PeerIdentity, PeerhoodError                                        # S14 Vol 1 (sealed)
from .recognition import directory_free_discovery                                       # S14 Vol 2 (sealed)
from ..keystore import has_node_key, sign_node_act, verify_node_act                      # D1 (sealed)
from ..messaging.inter_node import send_message                                          # S6 Vol 1 (sealed)
from ..economy.pool import form_pool, contribute_to_pool, pool_settlement, Pool          # S10 Vol 2 (sealed)
from ..risk.governance import load_governance_skin, enforce_decision                     # S11 Vol 4 (sealed)

__all__ = ["form_peer_pool", "bridge_into_pool", "verify_bridge", "federate_without_directory",
           "attribute_pool_value", "settle_pool_on_port", "pool_vote",
           "BRIDGING_BREACH_FIELDS", "PeerhoodError"]

# No bridging hub, no permanent membership token, no central settlement/netting, no registry; seal-key-closed.
BRIDGING_BREACH_FIELDS = frozenset({
    "bridging_hub", "hub", "bridge_authority", "pool_operator", "pool_hub",
    "membership_token", "permanent_membership", "permanent_token", "membership_authority",
    "central_settlement", "settlement_authority", "settle_in_node", "netting", "net_balance",
    "pool_balance", "held_value", "custodian", "escrow",
    "registry", "directory", "second_authority",
    "seal_key", "press_key", "sealing_key",
})


def _bfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if (kl in BRIDGING_BREACH_FIELDS or "bridging_hub" in kl or "membership_token" in kl
                or "central_settlement" in kl or "netting" in kl or "pool_balance" in kl
                or "held_value" in kl or "custodian" in kl or "registry" in kl):
            raise PeerhoodError(
                f"bridging is signed peer-to-peer and value rides the Port only — a bridging-hub / membership-"
                f"token / central-settlement / netting / pool-balance / registry / custodian field ('{k}') is "
                f"refused; no hub mediates the bridge, no token holds you, nothing settles in the middle")


# --- Peer pools by construction (Ch 2, PRESENT): S10 V2, a pool of receipted peer acts ---------------------

def form_peer_pool(keystore_dir: Optional[str], pool_id: str, members: Sequence[str], joined_by: str, *,
                   extra: Optional[Mapping[str, Any]] = None):
    """Form or join a value pool that is itself a set of receipted, governed peer acts — composing the sealed
    `form_pool` (Networked Value Pools, Sovereign Livelihood, S10 V2): the pool holds NO value, has no balance,
    and appoints no custodian; it is only who is in. `joined_by` signs its membership with its OWN key, so
    membership is the peer's own reversible record — not a token a hub holds. Deny-by-default: the joining peer
    must hold its own key; a bridging-hub / membership-token field is refused. Returns (Pool, membership dict)."""
    _bfence(extra)
    if not has_node_key(keystore_dir, joined_by):
        raise PeerhoodError(f"peer '{joined_by}' must hold its OWN key to join a pool — no key on this iron")
    pool = form_pool(str(pool_id), [str(m) for m in members])                 # S10 V2: no value, no custodian
    membership_sig = sign_node_act(keystore_dir, joined_by, f"member:{pool.pool_id}:{joined_by}".encode("utf-8"))
    return pool, {"pool_id": pool.pool_id, "member": str(joined_by), "membership_sig": membership_sig,
                  "reversible": True, "token_held_by_third_party": None}


# --- Bridging ceremony (Ch 3, PRESENT): S6 V1, receipted + verifiable + reversible -------------------------

def bridge_into_pool(keystore_dir: Optional[str], peer_id: str, pool_id: str, *, at: str, registry: Any,
                     source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Execute a receipted bridge into a pool or federation both sides can verify and reverse — a bridge message
    (composes the sealed `send_message`, Inter-Node Sovereignty, S6 V1) signed with the peer's OWN key. Deny-by-
    default: the peer must hold its own key (no key → fail-loud); a bridging-hub field is refused. Returns the
    governed bridge + signature; the bridge is first-class REVERSIBLE (a signed unbridge undoes it)."""
    _bfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a bridge must be signed by the peer's OWN key — no key on this iron")
    msg = send_message(registry, f"bridge:{peer_id}:{pool_id}", {"bridge": str(pool_id), "peer": str(peer_id),
                                                                  "reversible": True},
                       mandate=peer_id, author=peer_id, source_ref=source_ref, at=at)
    sig = sign_node_act(keystore_dir, peer_id, str(msg["version_hash"]).encode("utf-8"))
    return {"bridge": msg, "signature": sig, "peer_id": peer_id, "reversible": True, "hub": None}


def verify_bridge(bridge: Mapping[str, Any], identity: PeerIdentity) -> bool:
    """Verify a bridge PUBLIC-ONLY — its signature checks against the bridging peer's OWN public key, so both
    sides (and anyone) can confirm the bridge is genuinely the peer's, with no hub attesting it."""
    h = str((bridge.get("bridge") or {}).get("version_hash", "")).encode("utf-8")
    return verify_node_act(identity.public_hex, h, str(bridge.get("signature", "")))


# --- Federation without a directory (Ch 4, PRESENT): composes the sealed S14 V02 recognition ---------------

def federate_without_directory(peer_a_root: str, peer_b_root: str, *,
                               extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Participate in federation discovery and introduction with NO central directory — composing the sealed
    directory-free discovery of Recognition (S14 V02, `directory_free_discovery`): federating peers reconcile
    their independent roots, opt-in and local, with no central index. Deny-by-default: a registry / directory
    field is refused."""
    _bfence(extra)
    intro = directory_free_discovery(str(peer_a_root), str(peer_b_root))      # S14 V02 (sealed)
    return {"federated": bool(intro.get("discovered")), "aligned": bool(intro.get("aligned")),
            "central_directory": None}


# --- Value attribution on the record (Ch 5, PRESENT): S10 V2/V1 owned receipt, Port-only settlement --------

def attribute_pool_value(pool: Pool, member: str, source: str, work_ref: str, *, at: str, registry: Any,
                         contribution_class: str = "attested", amount: Any = None, unit: str = "credits",
                         port_ref: Optional[str] = None, author: Optional[str] = None, source_ref: str = "s",
                         extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Record earned value as an owned receipt that travels with the peer — composing the sealed pool
    contribution over the income primitive (`contribute_to_pool`, S10 V2, → `record_contribution`, S10 V1): the
    pool holds nothing, the MEMBER owns the receipt. Any cross-node value rides the sealed Port (`port_ref`);
    a held-value / pool-balance field is refused. Returns the member's OWN value-attribution receipt."""
    _bfence(extra)
    author = author or str(member)
    return contribute_to_pool(pool, str(member), str(source), str(work_ref), contribution_class=str(contribution_class),
                              author=author, source_ref=source_ref, at=at, registry=registry,
                              amount=amount, unit=unit, port_ref=port_ref)


def settle_pool_on_port(pool: Pool, member_shares: Sequence, *, port_ref_of=None,
                        extra: Optional[Mapping[str, Any]] = None) -> Any:
    """Settle a pool back to its members ONLY via the sealed Port — composing the sealed `pool_settlement`
    (S10 V2): per-member Port directives, NO in-node netting, NO pool balance, NO central settlement (the
    elevated money-fence refuses any in-node pool-value field). Value rides the Port; the node settles nothing."""
    _bfence(extra)
    return pool_settlement(pool, member_shares, port_ref_of=port_ref_of)


# --- Pool governance under human primacy (Ch 6, PRESENT): S11 V4 over S5 V16 gate --------------------------

def pool_vote(keystore_dir: Optional[str], peer_id: str, pool_id: str, decision_class: str, work_ref: str, *,
              at: str, registry: Any, gate: Any, approver: str, approval_ref: str, source_ref: str = "s",
              extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Participate in a pool decision through a HUMAN-GATED, receipted vote — composing the sealed pool
    governance (`enforce_decision` over a governance skin, Sovereign Risk & Mutual Protection, S11 V4) and the
    sealed human gate (Full Production ERP, S5 V16). Deny-by-default: a gated pool decision needs a named human
    (no approver → refused); the peer must hold its own key; and the vote is signed with the peer's OWN key.
    Returns the governed vote decision + signature."""
    _bfence(extra)
    if not str(approver or "").strip():
        raise PeerhoodError("a pool vote is human-gated — it needs a named approver (human primacy)")
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a pool vote must be signed by the peer's OWN key — no key on this iron")
    skin = load_governance_skin(f"pool:{pool_id}", gated_classes=[str(decision_class)])   # S11 V4
    decision = enforce_decision(skin, str(decision_class), peer_id, str(work_ref), gate=gate, at=at,
                                author=peer_id, source_ref=source_ref, registry=registry,
                                approver=approver, approval_ref=approval_ref)
    vote_hash = str(decision.get("version_hash") or decision.get("receipt_sha256") or work_ref)
    sig = sign_node_act(keystore_dir, peer_id, vote_hash.encode("utf-8"))
    return {"vote": decision, "signature": sig, "peer_id": peer_id, "pool_id": str(pool_id), "human_gated": True}
