"""Inter-node trust boundaries & handoff — a node's trust anchor is a governed object handed off by a receipted ceremony.

Co-extrusion for s6_05 (Inter-Node Trust Boundaries & Handoff, KM S6 wave 2026-08-05). Pure / structural, no crypto
substrate beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). A node's identity and trust
anchors -- its keys, its right to be recognized by peers -- must be able to rotate, be revoked, and be inherited across
a generational or ownership change WITHOUT a second recovery authority, WITHOUT a standing escrow, and WITHOUT any
central trust service holding the keys. A node declares its trust anchor as a governed object it owns, and a handoff of
that anchor to a successor is a receipted, human-gated CEREMONY composing the sealed generational-handoff floor -- not a
recovery a custodian performs and not an escrow a service holds.

Two governed acts:
  * `declare_trust_anchor` registers a node's trust anchor as a governed, provenance-carrying object -- composing the
    sealed object registry (`reg.append`, kind=ratify): the anchor (a key reference, an identity commitment) is authored
    under the node's own mandate, carrying its `author`, `source_ref` (provenance), and a `version_hash` (integrity), so
    the anchor is the node's own inheritable governed artifact, not a secret a custodian holds. An empty node id or empty
    anchor is refused.
  * `hand_off_trust` hands a node's trust anchors to a successor -- composing the sealed generational-handoff floor: it
    assembles the successor package over the node's governed objects (`assemble_successor_package`) and governs the
    handoff FAIL-CLOSED (`govern_handoff`) -- the package must VERIFY over its own bytes (a tampered succession refuses),
    and a NAMED human must approve (an approver and a non-empty approval reference naming the ceremony). No second
    recovery authority, no standing escrow, no central trust service: the handoff is the node's own governed ceremony,
    proven and human-gated, or it does not complete.

Human primacy and the sovereignty boundary hold: the trust anchor is the node's own governed object, and its handoff is
a named human's receipted ceremony over a verifying package. This module builds no key-recovery service, no escrow, and
no central trust authority of its own -- the anchor is the sealed object model's governed object, and the handoff is the
sealed generational-handoff floor's receipted, human-gated ceremony, composed."""
from __future__ import annotations

from typing import Dict, Mapping

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..continuity.handoff import assemble_successor_package, govern_handoff


class TrustError(ValueError):
    """Raised when a trust anchor cannot be declared or handed off honestly: an anchor with no node id or no body, or a
    handoff whose successor package does not verify or that no named human approved -- fail-closed, a node's trust anchor
    is its own governed object handed off only by a receipted, human-gated ceremony, never a custodian's recovery or an
    escrow's release."""


def declare_trust_anchor(reg, node_id: str, anchor: Mapping, *, mandate: str, author: str,
                         source_ref: str, at: str) -> Dict[str, object]:
    """Register a node's trust anchor as a governed, provenance-carrying object under the node's own mandate -- composing
    the sealed object registry. The `anchor` (a key reference, an identity commitment) becomes the object's authored
    payload, carrying the node's `author`, `source_ref` (provenance), and a `version_hash` (integrity), so the anchor is
    the node's own inheritable governed artifact -- not a secret a custodian holds. An empty `node_id` or empty `anchor`
    is refused. Returns the governed trust-anchor object."""
    if not node_id:
        raise TrustError("a trust anchor needs a node id")
    if not anchor:
        raise TrustError("a trust anchor needs a body (a key reference or identity commitment)")
    return reg.append(f"trust_anchor:{node_id}", dict(anchor), author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="ratify")


def hand_off_trust(reg, *, at: str, approver: str, approval_ref: str) -> Dict[str, object]:
    """Hand a node's trust anchors to a successor -- composing the sealed generational-handoff floor. It assembles the
    successor package over the node's governed objects (`assemble_successor_package`) and governs the handoff FAIL-CLOSED
    (`govern_handoff`): the package must VERIFY over its own bytes -- a tampered or malformed succession refuses the
    handoff -- AND a NAMED human must approve (an `approver` and a non-empty `approval_ref` naming the ceremony). No
    second recovery authority admits the handoff, no standing escrow holds the anchors, and no central trust service
    performs it: the handoff is the node's own governed, human-gated ceremony over a verifying package. Returns the
    receipted handoff (the package root, the approver, the approval reference)."""
    if not str(approver).strip():
        raise TrustError("trust handoff refused: a named human approver is required (no silent handoff, no custodian)")
    if not str(approval_ref).strip():
        raise TrustError("trust handoff refused: an approval reference naming the ceremony is required")
    package = assemble_successor_package(reg, at=at)
    return govern_handoff(package, approver=approver, approval_ref=approval_ref)
