"""Private vs Shared Storage Governance — data classified private/shared/hybrid, each governed by a
declared scope, integrity-proven, shared only by a receipted, revocable, deny-by-default grant.

Co-extrusion for s7_05 (Private vs Shared Storage Governance, KM S7 wave 2026-08-06, lane B). The
distribution of a node's data across the private/shared boundary is not a central store's policy: each
datum is the owner's own governed object carrying a DECLARED classification (private | shared | hybrid)
and its Merkle integrity root, and a share exists only because the owner declared a scope rule for it —
private data is never shareable, no standing trust across data, no central store that owns or vouches.
This is the built topology behind the "distribution matrix / resonant shard" idea: which data is private
vs shared/federated is a governed classification on the sealed object model, not a convention.

Two governed acts:
  * `classify_datum` — record a datum as a governed object under the owner's OWN mandate (composing
    `reg.append` kind=ratify), carrying a declared `visibility` ('private' | 'shared' | 'hybrid') and its
    Merkle integrity root over the datum's canonical chunks (sealed P5 `MerkleTree`). An empty owner or
    chunks, or a visibility outside the three classes, is refused. This is the private/shared partition
    made a built classification.
  * `govern_shared_access` — DENY-BY-DEFAULT: grant a scoped read of a 'shared'/'hybrid' datum to a
    named peer ONLY by a node-declared scope rule (composing `node_gov.authorize_crossing`). A 'private'
    datum is NEVER shareable across mandates — refused regardless of any rule. Own-mandate access is
    whole. No standing trust: a rule for one datum never grants another, and a share is revoked simply by
    withdrawing the rule.

This module builds no store and no second classification authority — the record and the partition are
the sealed object registry, the scope is the sealed federation scope check, and the integrity is the
sealed P5 Merkle, each composed through the `_lazy_bp` boundary (fail-loud if the substrate is absent)."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..objects.scope import ScopeRefusal
from ..federation.node_gov import authorize_crossing
from .._lazy_bp import MerkleTree  # sealed P5 integrity substrate via the runtime boundary (fail-loud)

_VISIBILITIES = ("private", "shared", "hybrid")


class GovernanceError(ValueError):
    """Raised when a datum cannot be classified or shared honestly: an empty owner/chunks, a visibility
    outside private/shared/hybrid, a share of a private datum across mandates, or an access the node has
    not declared a scope rule for -- fail-closed, the private/shared boundary is a governed classification
    and a share is a declared, revocable grant, never a central store's standing trust."""


def _merkle_root(chunks: Sequence[bytes]) -> str:
    return MerkleTree([bytes(c) for c in chunks]).get_root().hex()


def classify_datum(reg, owner: str, chunks: Sequence[bytes], *, visibility: str, mandate: str, author: str,
                   source_ref: str, at: str) -> Dict[str, object]:
    """Classify a datum as a governed object under the owner's OWN mandate (composing `reg.append`
    kind=ratify), carrying a declared `visibility` ('private' | 'shared' | 'hybrid') and its Merkle
    integrity root over the datum's canonical `chunks` (sealed P5 `MerkleTree`). An empty `owner` or
    `chunks`, or a `visibility` outside the three classes, is refused. Returns the governed datum object
    (the private/shared partition as a built classification)."""
    if not owner:
        raise GovernanceError("a datum needs the owner classifying it")
    if not chunks:
        raise GovernanceError("a datum needs content chunks to classify (no empty datum)")
    if visibility not in _VISIBILITIES:
        raise GovernanceError(f"visibility must be one of {_VISIBILITIES}, not {visibility!r}")
    root = _merkle_root(chunks)
    payload = {"visibility": visibility, "owner": owner, "root": root}
    return reg.append(f"datum:{owner}:{root[:12]}", payload, author=author,
                      source_ref=source_ref, at=at, mandate=mandate, kind="ratify")


def govern_shared_access(reg, datum: Mapping, rules: Sequence, *, principal_mandate: str,
                         want: str = "read") -> Dict[str, object]:
    """Govern access to a classified datum -- DENY-BY-DEFAULT, fail-closed, per request:

      1. `datum` must be a real governed object (a `version_hash` + object id);
      2. own-mandate access (owner == principal) is whole;
      3. a 'private' datum is NEVER shareable across mandates -- refused regardless of any rule;
      4. a 'shared'/'hybrid' datum is granted ONLY by a node-declared scope rule naming exactly this datum
         and `principal_mandate` (composing `node_gov.authorize_crossing`) -- no standing trust across data;
         withdrawing the rule revokes the share.

    Returns the granted access descriptor only when the classification and the declared scope both allow."""
    if not (datum and datum.get("version_hash") and datum.get("object_id")):
        raise GovernanceError("access refused: no real governed datum")
    payload = datum.get("payload") or {}
    visibility, owner = payload.get("visibility"), payload.get("owner")
    if principal_mandate == owner:
        return {"granted": True, "datum": datum["object_id"], "visibility": visibility, "basis": "own-mandate"}
    if visibility == "private":
        raise GovernanceError("access refused: a private datum is never shareable across mandates "
                              "(the private/shared boundary holds -- re-classify to share)")
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=principal_mandate,
                                obj_id=datum["object_id"], want=want)
    except ScopeRefusal as e:
        raise GovernanceError(
            f"access refused: no declared scope rule authorizes {principal_mandate!r} to {want!r} the "
            f"shared datum {datum['object_id']!r} -- shared access is a declared, revocable grant ({e})")
    except ValueError as e:
        raise GovernanceError(f"access refused: {datum.get('object_id')!r} is not a governed datum on the record ({e})")
    if not ok:
        raise GovernanceError("access refused: the node has not declared a scope rule for this share (no standing trust)")
    return {"granted": True, "datum": datum["object_id"], "visibility": visibility, "basis": "declared-scope"}
