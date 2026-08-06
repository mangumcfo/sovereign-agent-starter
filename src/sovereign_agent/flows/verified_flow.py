"""Verified data flows across nodes — every flow a receipted, integrity-proven, policy-governed event.

Co-extrusion for s7_04 (Verified Data Flows Across Nodes, KM S7 wave 2026-08-06, lane A). A data flow
from one node to another is not a trusted pipe: it is a governed object under the sender's own mandate,
carrying its Merkle integrity root, accepted at the receiver only by a node-declared policy and a
verified integrity check — deny-by-default, no standing trust across flows. Composes sealed floors only
(the object registry, the federation crossing-authorization, the sealed P5 Merkle), and — for the
zero-knowledge privacy option — the sealed P5 ZK (Pedersen + Schnorr + Range, PRESENT via the authorized
v1.0.3 overlay), which lets a flow prove a property (e.g. "this quantity clears the agreed minimum")
WITHOUT revealing the payload.

Four governed acts:
  * `declare_flow`   — a flow source→target as a governed, provenance-carrying object under the SENDER's
    OWN mandate (composing `reg.append` kind=ratify), carrying the Merkle integrity root over the flow's
    canonical chunks (sealed P5 `MerkleTree`). Empty source/target/chunks is refused.
  * `verify_flow`    — DENY-BY-DEFAULT at the receiver: a real governed flow AND authorized by a
    node-declared scope rule naming exactly this flow (composing `node_gov.authorize_crossing` — no
    standing trust across flows) AND the delivered bytes verify against the flow's Merkle root
    (integrity in transit). Only then accepted.
  * `attest_flow_clears` — the ZERO-KNOWLEDGE privacy option: commit a flow's private quantity (Pedersen)
    and prove it CLEARS a stated minimum WITHOUT revealing it — a range proof on the difference
    commitment `C − minimum·G` (sealed P5 ZK, authorized overlay). Discharges the s5_38/s5_39 range
    clause (prove a pool clears its minimum without exposing any member's budget).
  * `verify_flow_clears` — verify that ZK clears-the-minimum proof against the public commitment; the
    verifier learns only that the flow clears, never the quantity.

This module builds no transport, no store, no second trust authority, no central attestation, no hub
that vouches — the record is the sealed object registry, the policy is the sealed federation scope
check, the integrity is the sealed P5 Merkle, and the privacy is the sealed P5 ZK, each composed through
the `_lazy_bp` runtime boundary (fail-loud if the substrate is absent)."""
from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..objects.scope import ScopeRefusal
from ..federation.node_gov import authorize_crossing
from .._lazy_bp import MerkleTree  # sealed P5 integrity substrate via the runtime boundary (fail-loud)


class FlowError(ValueError):
    """Raised when a flow cannot be declared or verified honestly: an empty source/target/chunks, a
    verification of no real governed flow, an access the node has not declared a scope rule for, bytes
    whose integrity does not match the flow's Merkle root, or a zero-knowledge clears-proof that does
    not verify — fail-closed, a flow is a governed object accepted only by a declared policy and a
    verified integrity check, never a trusted pipe."""


def _merkle_root(chunks: Sequence[bytes]) -> str:
    return MerkleTree([bytes(c) for c in chunks]).get_root().hex()


def declare_flow(reg, source: str, target: str, chunks: Sequence[bytes], *, mandate: str, author: str,
                 source_ref: str, at: str) -> Dict[str, object]:
    """Declare a data flow `source` → `target` as a governed object under the SENDER's OWN mandate
    (composing `reg.append` kind=ratify), carrying the Merkle integrity root over the flow's canonical
    `chunks` (sealed P5 `MerkleTree`), so the flow's integrity is provable from its own bytes. An empty
    `source`/`target` or empty `chunks` is refused. Returns the governed flow object."""
    if not source:
        raise FlowError("a flow needs a source node")
    if not target:
        raise FlowError("a flow needs a target node")
    if not chunks:
        raise FlowError("a flow needs content chunks (no empty flow)")
    root = _merkle_root(chunks)
    payload = {"source": source, "target": target, "root": root}
    return reg.append(f"flow:{source}->{target}:{root[:12]}", payload, author=author,
                      source_ref=source_ref, at=at, mandate=mandate, kind="ratify")


def verify_flow(reg, flow: Mapping, rules: Sequence, presented_chunks: Sequence[bytes], *,
                principal_mandate: str, want: str = "read") -> Dict[str, object]:
    """Verify a flow at the receiver — DENY-BY-DEFAULT, fail-closed, per request, in order:

      1. `flow` must be a real governed object (a `version_hash` + object id) — a verification of nothing
         is refused;
      2. the acceptance must be AUTHORIZED by a node-declared scope rule naming exactly this flow and
         `principal_mandate` (composing `node_gov.authorize_crossing`) — own-mandate is whole, a
         cross-node acceptance needs a declared rule, no standing trust across flows;
      3. the `presented_chunks` must VERIFY against the flow's stored Merkle `root` (sealed `MerkleTree`)
         — a flow whose bytes were altered in transit is refused.

    Only when the flow is real AND the acceptance is scoped AND the integrity matches is it accepted."""
    if not (flow and flow.get("version_hash") and flow.get("object_id")):
        raise FlowError("verification refused: no real governed flow to verify")
    try:
        ok = authorize_crossing(reg, list(rules), principal_mandate=principal_mandate,
                                obj_id=flow["object_id"], want=want)
    except ScopeRefusal as e:
        raise FlowError(
            f"verification refused: no declared scope rule authorizes {principal_mandate!r} to accept "
            f"{flow['object_id']!r} -- a flow is accepted only by a declared policy, never a standing trust ({e})")
    except ValueError as e:  # flow not on the record -> deny-by-default
        raise FlowError(f"verification refused: {flow.get('object_id')!r} is not a governed flow on the record ({e})")
    if not ok:
        raise FlowError("verification refused: the node has not declared a scope rule for this flow (no standing trust)")
    stored_root = (flow.get("payload") or {}).get("root")
    if not stored_root:
        raise FlowError("verification refused: the flow carries no integrity root")
    if _merkle_root(presented_chunks) != stored_root:
        raise FlowError("verification refused: presented bytes do not match the flow's Merkle root "
                        "(in-transit integrity failed -- flow altered)")
    return {"accepted": True, "flow": flow.get("object_id"), "integrity": "verified"}


def attest_flow_clears(zk, quantity: int, *, minimum: int, bits: int = 32):
    """The ZERO-KNOWLEDGE privacy option (composes the sealed P5 ZK, authorized overlay): commit a flow's
    PRIVATE `quantity` (Pedersen) and prove it CLEARS `minimum` WITHOUT revealing it — a range proof that
    the difference `quantity - minimum` is in `[0, 2^bits)`, carried on the difference commitment
    `C - minimum*G`. Returns `(commitment, proof)`; the verifier learns only that the flow clears.
    Refuses a quantity below the minimum (an honest prover cannot prove a false clearance)."""
    if quantity < minimum:
        raise FlowError(f"cannot attest clearance: quantity {quantity} does not clear the minimum {minimum}")
    commitment, r = zk.pedersen_commitment(quantity)
    diff_commit = zk.curve.add(commitment, zk.curve.neg(zk.curve.mul(minimum % zk.n, zk.G)))
    proof = zk.range_proof(quantity - minimum, diff_commit, r, bits=bits)
    return commitment, proof


def verify_flow_clears(zk, commitment, proof, *, minimum: int, bits: int = 32) -> bool:
    """Verify a zero-knowledge clears-the-minimum proof against the public `commitment`: reconstruct the
    difference commitment `C - minimum*G` and verify the range proof. True iff the flow provably clears
    the minimum; the verifier never learns the quantity. Fail-closed on any malformed/short proof."""
    try:
        diff_commit = zk.curve.add(commitment, zk.curve.neg(zk.curve.mul(minimum % zk.n, zk.G)))
        return bool(zk.verify_range_proof(diff_commit, proof, bits=bits))
    except Exception:
        return False
