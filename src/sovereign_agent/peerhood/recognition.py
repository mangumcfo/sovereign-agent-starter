# -*- coding: utf-8 -*-
"""peerhood.recognition — Sovereign Peerhood (Series 14, Vol 2:
Recognition Without a Registry).

A sovereign peer must be able to recognize others and be recognized — without a central registry, directory, or
name service that mediates recognition and could delist it. This volume composes only sealed floors and the
sealed genesis layer (S14 Vol 1), inventing no new mechanism: every recognition is signed with each peer's OWN
self-held key. `directory_free_discovery` introduces two peers by reconciling their INDEPENDENT roots (composing
the sealed Federation directory-free discovery, Interface Sovereignty, S8 Vol 6) — opt-in and local, no central
index. `mutual_recognition` is a bilateral, receipted ceremony: a recognition is a governed message (composing
the sealed inter-node messaging, Inter-Node Sovereignty, S6 Vol 1) that BOTH peers sign with their own keys, and
`verify_recognition` confirms it public-only, with no third party. `scoped_visibility` is a human-gated
(composing the sealed gate, Full Production ERP, S5 Vol 16), reversible, minimal-disclosure grant signed with the
key. `recognition_as_receipt` treats a recognition as an owned record the peer carries (a tally, never a score —
scored reputation homes OUT to Sovereign Risk & Mutual Protection, S11 Vol 1). `refuse_recognition` refuses or
revokes recognition as a first-class signed act that leaves NO residual claim.

KILL-TARGET: the registry / directory / name service that mediates recognition and can delist you — refused.
Fences (`RECOGNITION_BREACH_FIELDS`): no registry · no directory / name service / central index · no second
admission authority · no scored reputation authority · no custodian/escrow · seal-key-closed (the node key is
not the press/seal key). Weakest-party: a peer with nothing but its own key recognizes and is recognized, and
can refuse without becoming a hostage. NO passphrase claim (self-held file-custody). Holds no value; rolls no
cryptography (composes the sealed self-held key).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from .genesis import PeerIdentity, PeerhoodError                                        # S14 Vol 1 (sealed)
from ..keystore import has_node_key, sign_node_act, verify_node_act                      # D1 (sealed)
from ..federation.node_gov import reconcile_roots                                        # S8 Vol 6 (sealed)
from ..messaging.inter_node import send_message                                          # S6 Vol 1 (sealed)

__all__ = ["directory_free_discovery", "mutual_recognition", "verify_recognition",
           "scoped_visibility", "recognition_as_receipt", "refuse_recognition",
           "RECOGNITION_BREACH_FIELDS", "PeerhoodError"]

# No registry/directory that mediates recognition; no second authority; no scored reputation; seal-key-closed.
RECOGNITION_BREACH_FIELDS = frozenset({
    "registry", "directory", "name_service", "name_registry", "central_index", "index_authority",
    "second_authority", "admission_authority",
    "scored_authority", "reputation_score", "rating_authority", "recognition_authority",
    "custodian", "escrow", "seal_key", "press_key", "sealing_key",
})


def _rfence(mapping: Optional[Mapping[str, Any]]) -> None:
    for k in (mapping or {}):
        kl = str(k).lower()
        if (kl in RECOGNITION_BREACH_FIELDS or "registry" in kl or "directory" in kl
                or "name_service" in kl or "central_index" in kl or "score" in kl or "custodian" in kl):
            raise PeerhoodError(
                f"recognition is signed peer-to-peer with each peer's OWN key — a registry / directory / name-"
                f"service / scored-authority / custodian field ('{k}') is refused; no hub mediates recognition "
                f"and none can delist you")


# --- Directory-free discovery (Ch 2, PRESENT): S8 Vol 6, opt-in + local ------------------------------------

def directory_free_discovery(peer_a_root: str, peer_b_root: str, *,
                             extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Discover a peer without a central directory — two peers introduce themselves by reconciling their
    INDEPENDENTLY-computed roots (composes the sealed `reconcile_roots`, Interface Sovereignty, S8 Vol 6): agree,
    and they are aligned; differ, and the divergence is surfaced, never silently resolved to one side. Opt-in and
    local: no central index is read or written; neither root is authoritative. Deny-by-default: a registry /
    directory field is refused."""
    _rfence(extra)
    rec = reconcile_roots(str(peer_a_root), str(peer_b_root))
    return {"discovered": True, "aligned": bool(rec.get("aligned")), "via": "independent-root-reconcile",
            "central_index": None}


# --- Mutual recognition ceremony (Ch 3, PRESENT): S6 Vol 1 + both sign with their keys --------------------

def mutual_recognition(keystore_dir: Optional[str], peer_a: str, peer_b: str, *, at: str, registry: Any,
                       source_ref: str = "s", extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Complete a receipted, BILATERAL recognition — a recognition message (composes the sealed `send_message`,
    Inter-Node Sovereignty, S6 Vol 1) that BOTH peers sign with their OWN self-held keys (composes D1). No third
    party issues or witnesses it. Deny-by-default: each peer must hold its own key (no key → fail-loud); a
    registry / recognition-authority field is refused. Returns the governed recognition + both signatures."""
    _rfence(extra)
    for p in (peer_a, peer_b):
        if not has_node_key(keystore_dir, p):
            raise PeerhoodError(f"peer '{p}' must hold its OWN key to recognize or be recognized — no key on "
                                f"this iron; establish its self-held identity first")
    msg = send_message(registry, f"recognition:{peer_a}:{peer_b}", {"recognize": [peer_a, peer_b], "bilateral": True},
                       mandate=peer_a, author=peer_a, source_ref=source_ref, at=at)
    h = str(msg["version_hash"]).encode("utf-8")
    return {"recognition": msg, "sig_a": sign_node_act(keystore_dir, peer_a, h),
            "sig_b": sign_node_act(keystore_dir, peer_b, h), "peers": [peer_a, peer_b], "third_party": None}


def verify_recognition(recognition: Mapping[str, Any], id_a: PeerIdentity, id_b: PeerIdentity, *,
                       revocations: Sequence[Mapping[str, Any]] = ()) -> bool:
    """Verify a mutual recognition PUBLIC-ONLY — both peers' signatures check against their OWN public keys, with
    no third party. True only when BOTH sides verify: recognition is bilateral, held by both, owned by both.
    **A revocation KILLS a live recognition:** if any refusal in `revocations` names these two peers (in either
    order), the recognition no longer verifies — a peer's signed refusal (`refuse_recognition`) actually ends the
    relationship, it is not a dead letter."""
    pair = {id_a.peer_id, id_b.peer_id}
    for r in revocations:
        if {str(r.get("by", "")), str(r.get("of", ""))} == pair:
            return False                                                 # a signed refusal kills the live recognition
    h = str((recognition.get("recognition") or {}).get("version_hash", "")).encode("utf-8")
    return (verify_node_act(id_a.public_hex, h, str(recognition.get("sig_a", "")))
            and verify_node_act(id_b.public_hex, h, str(recognition.get("sig_b", ""))))


# --- Scoped visibility (Ch 4, PRESENT): S5 Vol 16 gate, reversible, minimal --------------------------------

def scoped_visibility(keystore_dir: Optional[str], peer_id: str, viewer: str, scope: Sequence[str], *,
                      at: str, registry: Any, approver: str, approval_ref: str, source_ref: str = "s",
                      extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Control exactly what another peer can see about you — a visibility grant signed with the peer's OWN key
    and human-gated (composes the sealed gate, Full Production ERP, S5 Vol 16), scoped to a minimal disclosure
    and reversible by the peer. Deny-by-default: the grant is human-gated (no approver → refused); default is
    minimal; a registry / scored field is refused. Returns the governed grant + signature."""
    _rfence(extra)
    if not str(approver or "").strip():
        raise PeerhoodError("a scoped-visibility grant is human-gated — it needs a named approver (human primacy)")
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a visibility grant must be signed by the peer's OWN key — no key on this iron")
    grant = registry.append(f"visibility:{peer_id}:{viewer}",
                            {"viewer": str(viewer), "scope": [str(s) for s in scope], "reversible": True,
                             "minimal": True},
                            author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify",
                            approver=approver, approval_ref=approval_ref)
    sig = sign_node_act(keystore_dir, peer_id, str(grant["version_hash"]).encode("utf-8"))
    return {"grant": grant, "signature": sig, "scope": [str(s) for s in scope], "reversible": True}


# --- Recognition as receipt (Ch 5, PRESENT): an owned tally, NOT a score (S11 Vol 1 home) ------------------

def recognition_as_receipt(party: str, recognitions: Sequence[Mapping[str, Any]], *,
                           extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Treat every recognition as a permanent, exportable receipt the peer OWNS — the peer's standing is a
    transparent TALLY of the recognitions it holds that name it, re-derivable by anyone, NEVER a score an
    authority issues (scored reputation homes OUT to Sovereign Risk & Mutual Protection, S11 Vol 1, reputation-
    as-verified-receipts). Deny-by-default: a scored-authority field is refused. Returns the owned tally."""
    _rfence(extra)
    count = 0
    for r in recognitions:
        _rfence(r)
        peers = r.get("peers") or []
        if party in peers:
            count += 1
    return {"party": party, "recognitions": count, "is_score": False,
            "reason": "recognition is an owned record you carry — a re-derivable tally, not a score an authority issues"}


# --- Refusal without penalty (Ch 6, PRESENT): a first-class signed act, no residual claim -----------------

def refuse_recognition(keystore_dir: Optional[str], peer_id: str, other: str, *, at: str, registry: Any,
                       reason: str = "", source_ref: str = "s",
                       extra: Optional[Mapping[str, Any]] = None) -> dict:
    """Refuse recognition, or revoke it, as a FIRST-CLASS signed act that leaves NO residual claim — signed with
    the peer's OWN key, so the peer is never held hostage by a recognition it no longer wants. Deny-by-default:
    the refusal must be signed by the peer's own key (no key → fail-loud); a registry / leverage field is
    refused. Weakest-party protected: refusing costs the peer nothing and creates no leverage over it."""
    _rfence(extra)
    if not has_node_key(keystore_dir, peer_id):
        raise PeerhoodError("a refusal must be signed by the peer's OWN key — no key on this iron")
    rev = registry.append(f"refusal:{peer_id}:{other}",
                          {"refuse": str(other), "residual_claim": None, "reason": str(reason)},
                          author=peer_id, source_ref=source_ref, at=at, mandate=peer_id, kind="ratify")
    sig = sign_node_act(keystore_dir, peer_id, str(rev["version_hash"]).encode("utf-8"))
    return {"refusal": rev, "signature": sig, "residual_claim": None, "hostage_free": True,
            "by": str(peer_id), "of": str(other)}
