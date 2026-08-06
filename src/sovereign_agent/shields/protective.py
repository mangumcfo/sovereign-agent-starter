"""Shields as Protective Layers — layered, independently-verifiable protections over a resource, deny-by-default.

Co-extrusion for s7_02 (Shields as Protective Layers, KM S7 wave 2026-08-06, lane A). Composes the sealed object model
(the shield as a governed object) and the sealed P5 shield substrate (now in-tree: `breathline_primitives` via the
`_lazy_bp` runtime boundary) for the cryptographic layers. A shield is not a central authority vouching for a resource:
it is a governed protective layer the resource's owner declares, and a request clears a resource only when EVERY declared
shield passes, in order -- defense in depth, deny-by-default. No second trust authority, no central attestation, no hub
that vouches; each shield is verified from the resource's own governed evidence.

Two governed acts:
  * `declare_shield` registers a protective shield over a resource as a governed, provenance-carrying object under the
    resource owner's OWN mandate -- composing the sealed object registry (`reg.append` kind=ratify). For the `integrity`
    shield it composes the sealed P5 Merkle tree: the shield carries the Merkle root over the resource's canonical chunks
    (computed via the sealed `MerkleTree` -- the ZK-held and WASM-parser-only P5 capacities are named at their homes, not
    over-read). An empty resource id, kind, or (for integrity) empty chunks is refused.
  * `pass_shield_stack` clears a request DENY-BY-DEFAULT, fail-closed, defense-in-depth: EVERY declared shield must pass,
    in order. An `integrity` shield passes only when the presented payload's Merkle root (recomputed via the sealed
    `MerkleTree`) equals the shield's declared root -- a tampered or altered payload is refused. A shield of an unknown
    kind, or any shield that does not pass, refuses the whole stack; an empty stack (no declared protection) refuses too
    (deny-by-default: an unshielded resource is not implicitly open).

This module builds no crypto of its own -- the Merkle integrity is the sealed P5 shield substrate, composed through the
`_lazy_bp` boundary (fail-loud if the substrate is absent). It builds no trust store, no attestation service, and no
vouching hub: a shield is the owner's own declared, governed protective layer, verified from the resource's own bytes."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from .._lazy_bp import MerkleTree  # sealed P5 shield substrate via the runtime boundary (fail-loud if absent)


class ShieldError(ValueError):
    """Raised when a resource cannot be shielded or cleared honestly: a shield with no resource id, kind, or (for
    integrity) no chunks, or a request that fails any declared shield, is of an unknown shield kind, or clears an empty
    (unshielded) stack -- fail-closed, a request clears a resource only when EVERY declared protective layer passes from
    the resource's own governed evidence, never a central authority's vouching."""


def _merkle_root(chunks: Sequence[bytes]) -> bytes:
    return MerkleTree([bytes(c) for c in chunks]).get_root()


def declare_shield(reg, resource_id: str, kind: str, chunks: Sequence[bytes], *, mandate: str, author: str,
                   source_ref: str, at: str) -> Dict[str, object]:
    """Declare a protective shield over a resource as a governed object under the owner's OWN mandate -- composing the
    sealed object registry (`reg.append` kind=ratify). For `kind='integrity'` it composes the sealed P5 `MerkleTree`,
    storing the Merkle root over the resource's canonical `chunks`, so the shield is a tamper-evident layer verifiable
    from the resource's own bytes. An empty `resource_id`, `kind`, or (for the integrity kind) empty `chunks` is refused.
    Returns the governed shield object (its payload carries `kind` and, for integrity, the `root`)."""
    if not resource_id:
        raise ShieldError("a shield needs the resource id it protects")
    if not kind:
        raise ShieldError("a shield needs a kind (the protection it applies)")
    payload: Dict[str, object] = {"kind": kind, "resource": resource_id}
    if kind == "integrity":
        if not chunks:
            raise ShieldError("an integrity shield needs the resource chunks to root over (no empty attestation)")
        payload["root"] = _merkle_root(chunks).hex()
    return reg.append(f"shield:{resource_id}:{kind}", payload, author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="ratify")


def pass_shield_stack(shields: Sequence[Mapping], payload_chunks: Sequence[bytes]) -> Dict[str, object]:
    """Clear a request against a resource's declared shields -- DENY-BY-DEFAULT, fail-closed, defense-in-depth: EVERY
    shield in `shields` must pass, in order. An `integrity` shield passes only when the Merkle root of `payload_chunks`
    (recomputed via the sealed P5 `MerkleTree`) equals the shield's declared `root`; a tampered payload is refused. A
    shield of an unknown kind refuses the stack. An empty stack refuses too -- an unshielded resource is not implicitly
    open (deny-by-default). Returns the pass receipt (the count of layers cleared) only when every layer passes."""
    if not shields:
        raise ShieldError("no declared shield to clear -- an unshielded resource is not implicitly open (deny-by-default)")
    cleared = []
    for s in shields:
        if not (s and s.get("version_hash") and s.get("payload")):
            raise ShieldError("shield refused: not a real governed shield object")
        kind = (s["payload"] or {}).get("kind")
        if kind == "integrity":
            declared = (s["payload"] or {}).get("root")
            if not declared:
                raise ShieldError("integrity shield refused: no declared root to verify against")
            if _merkle_root(payload_chunks).hex() != declared:
                raise ShieldError("shield refused: integrity layer failed -- payload Merkle root does not match the "
                                  "declared shield (tamper detected)")
            cleared.append(kind)
        else:
            raise ShieldError(f"shield refused: unknown shield kind {kind!r} -- deny-by-default, an unrecognized "
                              f"protection is not silently passed")
    return {"cleared": True, "layers": len(cleared), "kinds": cleared}
