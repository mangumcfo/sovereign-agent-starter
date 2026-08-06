"""Zero-Trust Node Architecture — never trust, always verify; no standing trust between requests.

Co-extrusion for s7_01 (Zero-Trust Node Architecture, KM S7 residual 2026-08-06, MUST-SOLO). Pure / structural, no crypto
substrate beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). A node does not trust a request
because a central authority attested to the requester, or because a hub vouched, or because a grant was standing: it
VERIFIES each access, per request, from first principles -- against the requester's OWN presented governed evidence and a
node-DECLARED rule for exactly this resource. Nothing is trusted by default; everything is verified. No second trust
authority, no central attestation service, no hub that vouches.

Two governed acts:
  * `present_evidence` registers a node's SELF-presented evidence bundle as a governed, provenance-carrying object under
    the node's OWN mandate -- composing the sealed object registry (`reg.append` kind=ratify): the `claims` a node
    presents to be verified (which anchor it holds, which constitution it adopted, what it asserts) become an authored,
    provenance-carrying governed object, so what is verified is the node's own evidence on the record, NOT an attestation
    a central authority issued about it. An empty node id or empty claims is refused.
  * `verify_access` decides an access DENY-BY-DEFAULT, fail-closed, per request, in order: the presented `evidence` must
    be a real governed object (carrying a `version_hash` -- verified over its own bytes, so tampered evidence is
    refused); and the access must be AUTHORIZED by a node-DECLARED rule naming exactly THIS resource and requester
    (composing the sealed `node_gov.authorize_crossing` -- no standing trust: a rule for one resource never grants
    another, and an undeclared access is refused). Only when the evidence verifies AND the node has declared a rule for
    exactly this request is access granted, returning a decision that names what it verified against -- never a
    vouching. No second trust authority grants access; the node does, by verifying evidence and its own declared rule,
    every request.

Human primacy and the sovereignty boundary hold: what is verified is the node's own presented evidence, and the
authorization is the node's own declared rule -- re-verified each request. This module builds no trust store, no
attestation service, no standing-grant table, and no vouching hub of its own -- the identity the evidence presents is the
sealed trust anchor, the per-request authorization is the sealed cross-mandate rule, and the human gate for material
access is the sealed compliance gate, composed. Trust is earned per request, never vouched."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..objects.scope import ScopeRefusal
from ..federation.node_gov import authorize_crossing


class ZeroTrustError(ValueError):
    """Raised when an access cannot be granted honestly: evidence with no node id or no claims, or a verification of no
    real governed evidence, or an access the node has not declared a rule for -- fail-closed, a node grants access only
    by verifying the requester's own presented evidence and its own declared rule for exactly this resource, never a
    central attestation, a standing grant, or a hub's vouching."""


def present_evidence(reg, node_id: str, claims: Mapping, *, mandate: str, author: str,
                     source_ref: str, at: str) -> Dict[str, object]:
    """Present a node's SELF-presented evidence bundle as a governed object under the node's OWN mandate -- composing the
    sealed object registry (`reg.append` kind=ratify). The `claims` the node presents to be verified (which anchor it
    holds, which constitution it adopted, what it asserts) become an authored, provenance-carrying governed object, so
    what a verifier checks is the node's own evidence on the record, NOT an attestation a central authority issued about
    it. An empty `node_id` or empty `claims` is refused. Returns the governed evidence object."""
    if not node_id:
        raise ZeroTrustError("evidence needs the node id presenting it")
    if not claims:
        raise ZeroTrustError("evidence needs the claims the node presents to be verified (no empty attestation)")
    return reg.append(f"evidence:{node_id}", dict(claims), author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="ratify")


def verify_access(reg, evidence: Mapping, rules: Sequence, *, principal_mandate: str, obj_id: str,
                  want: str = "read") -> Dict[str, object]:
    """Decide an access DENY-BY-DEFAULT, fail-closed, per request, in order:

      1. the presented `evidence` must be a real governed object -- carrying a `version_hash` (verified over its own
         bytes) and an object id; a verification of nothing, or of ungoverned/tampered evidence, is refused;
      2. the access must be AUTHORIZED by a node-DECLARED rule naming exactly this `obj_id`, this `principal_mandate`,
         and a scope at least as strong as `want` -- composing the sealed `node_gov.authorize_crossing`: own-mandate
         access is whole, a cross-mandate access needs a declared `SharingRule`; NO standing trust -- a rule for one
         resource never grants another, and an undeclared access is refused.

    Only when the evidence verifies AND the node has declared a rule for exactly this request is access granted,
    returning a decision that names what it verified against (the evidence root, the resource, the scope) -- never a
    vouching. No second trust authority, no central attestation, and no standing grant is consulted: the node re-verifies
    the requester's own evidence and its own declared rule every request."""
    if not (evidence and evidence.get("version_hash") and evidence.get("object_id")):
        raise ZeroTrustError("access denied: no real governed evidence to verify (deny-by-default)")
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=principal_mandate, obj_id=obj_id, want=want)
    except ScopeRefusal as e:
        raise ZeroTrustError(
            f"access denied: no declared rule authorizes {principal_mandate!r} to {want!r} {obj_id!r} -- a node grants "
            f"access only by its own declared rule for exactly this resource, never a standing trust ({e})"
        )
    except ValueError as e:  # unknown resource -> deny-by-default (never trust a resource that is not on the record)
        raise ZeroTrustError(
            f"access denied: {obj_id!r} is not a governed resource on the record -- deny-by-default, a node verifies, "
            f"it does not assume ({e})"
        )
    if not ok:
        raise ZeroTrustError("access denied: the node has not declared a rule for this request (no standing trust)")
    return {"granted": True, "verified_against": evidence.get("version_hash"),
            "evidence": evidence.get("object_id"), "resource": obj_id, "scope": want}
