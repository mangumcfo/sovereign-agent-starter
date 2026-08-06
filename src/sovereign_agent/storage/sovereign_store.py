"""Sovereign Data Storage Model — data at rest as governed objects, private/shared by declared scope, integrity-proven.

Co-extrusion for s7_03 (Sovereign Data Storage Model, KM S7 wave 2026-08-06, lane B). Composes the sealed object model
(a datum as a governed object), the sealed cross-mandate scope check (private vs shared access), and the sealed P5 Merkle
integrity (now in-tree: `breathline_primitives` via the `_lazy_bp` runtime boundary). A node's data at rest is not held
in a store a central service owns and vouches for: each datum is a governed object under its owner's mandate, its
visibility is a declared scope, and it is retrievable only by a verified, scoped access whose integrity is checked from
the datum's own bytes. No second trust authority, no central attestation, no hub that vouches; no standing trust.

Two governed acts:
  * `store_datum` writes a datum as a governed, provenance-carrying object under the owner's OWN mandate -- composing the
    sealed object registry (`reg.append` kind=ratify) -- carrying a declared `visibility` ('private' | 'shared') and its
    Merkle integrity root over the datum's canonical chunks (composing the sealed P5 `MerkleTree`), so the datum's
    at-rest integrity is provable from its own bytes. An empty owner or empty chunks, or a visibility other than
    'private'/'shared', is refused.
  * `retrieve_datum` reads a datum DENY-BY-DEFAULT, fail-closed, per request: the access must be AUTHORIZED by a
    node-declared scope rule naming exactly this datum and requester (composing the sealed `node_gov.authorize_crossing`
    -- private data with no declared rule is refused; own-mandate is whole; no standing trust across data); AND the
    presented bytes must VERIFY against the datum's stored Merkle root (recomputed via the sealed `MerkleTree`) -- altered
    data at rest is refused. Only then is the datum returned.

This module builds no store of its own -- the record is the sealed object registry, the scoping is the sealed federation
scope check, and the integrity is the sealed P5 Merkle, composed through the `_lazy_bp` boundary (fail-loud if the
substrate is absent). No central storage service owns the data; the owner does, and access is verified per request."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..objects.scope import ScopeRefusal
from ..federation.node_gov import authorize_crossing
from .._lazy_bp import MerkleTree  # sealed P5 shield substrate via the runtime boundary (fail-loud if absent)


class StorageError(ValueError):
    """Raised when a datum cannot be stored or retrieved honestly: an empty owner or chunks, an invalid visibility, a
    retrieval of no real governed datum, an access the node has not declared a scope rule for, or bytes whose integrity
    does not match the stored Merkle root -- fail-closed, data at rest is the owner's own governed object, retrieved only
    by a verified, scoped, integrity-checked access, never a central store's vouching."""


def _merkle_root(chunks: Sequence[bytes]) -> str:
    return MerkleTree([bytes(c) for c in chunks]).get_root().hex()


def store_datum(reg, owner: str, chunks: Sequence[bytes], *, visibility: str, mandate: str, author: str,
                source_ref: str, at: str) -> Dict[str, object]:
    """Store a datum as a governed object under the owner's OWN mandate -- composing the sealed object registry
    (`reg.append` kind=ratify). It carries a declared `visibility` ('private' | 'shared') and its Merkle integrity root
    over the datum's canonical `chunks` (composing the sealed P5 `MerkleTree`), so the datum's at-rest integrity is
    provable from its own bytes. An empty `owner` or empty `chunks`, or a `visibility` other than 'private'/'shared', is
    refused. Returns the governed datum object (payload carries `visibility` and `root`)."""
    if not owner:
        raise StorageError("a datum needs the owner storing it")
    if not chunks:
        raise StorageError("a datum needs content chunks to store (no empty datum)")
    if visibility not in ("private", "shared"):
        raise StorageError(f"visibility must be 'private' or 'shared', not {visibility!r}")
    payload = {"visibility": visibility, "owner": owner, "root": _merkle_root(chunks)}
    return reg.append(f"datum:{owner}:{_merkle_root(chunks)[:12]}", payload, author=author,
                      source_ref=source_ref, at=at, mandate=mandate, kind="ratify")


def retrieve_datum(reg, datum: Mapping, rules: Sequence, presented_chunks: Sequence[bytes], *,
                   principal_mandate: str, want: str = "read") -> Dict[str, object]:
    """Retrieve a datum -- DENY-BY-DEFAULT, fail-closed, per request, in order:

      1. the `datum` must be a real governed object -- carrying a `version_hash` and object id; a retrieval of nothing is
         refused;
      2. the access must be AUTHORIZED by a node-declared scope rule naming exactly this datum and `principal_mandate`
         (composing the sealed `node_gov.authorize_crossing`): own-mandate access is whole; a cross-mandate access needs a
         declared `SharingRule`; private data with no declared rule is refused -- no standing trust across data;
      3. the `presented_chunks` must VERIFY against the datum's stored Merkle `root` (recomputed via the sealed
         `MerkleTree`) -- altered data at rest is refused.

    Only when the datum is real AND the access is scoped AND the integrity matches is the datum returned. No central
    store vouches for the data; the owner's own governed object and the node's own declared rule do, verified per
    request."""
    if not (datum and datum.get("version_hash") and datum.get("object_id")):
        raise StorageError("retrieval refused: no real governed datum to retrieve")
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=principal_mandate,
                                obj_id=datum["object_id"], want=want)
    except ScopeRefusal as e:
        raise StorageError(
            f"retrieval refused: no declared scope rule authorizes {principal_mandate!r} to {want!r} "
            f"{datum['object_id']!r} -- data is read only by a declared scope, never a standing trust ({e})"
        )
    except ValueError as e:  # datum not on the record -> deny-by-default
        raise StorageError(f"retrieval refused: {datum.get('object_id')!r} is not a governed datum on the record ({e})")
    if not ok:
        raise StorageError("retrieval refused: the node has not declared a scope rule for this access (no standing trust)")
    stored_root = (datum.get("payload") or {}).get("root")
    if not stored_root:
        raise StorageError("retrieval refused: the datum carries no integrity root")
    if _merkle_root(presented_chunks) != stored_root:
        raise StorageError("retrieval refused: presented bytes do not match the datum's stored Merkle root "
                           "(at-rest integrity failed -- data altered)")
    return {"retrieved": True, "datum": datum.get("object_id"),
            "visibility": (datum.get("payload") or {}).get("visibility"), "integrity": "verified"}
