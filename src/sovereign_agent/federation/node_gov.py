"""Federation Node Governance (s5_26 / reading Vol 28) — cross-node validation, scoped sharing, reconciliation.

A federation is many sovereign nodes -- separate enterprises, entities, or regions -- that must share and validate
data across their boundaries without becoming one system. The legacy answer is a hub: a central node that all others
trust, that validates everyone's data and holds the authoritative copy. That hub is a capture point -- whoever runs
it governs the federation -- and a single point of failure and of trust. This module refuses it.

It builds **one new act -- governing a federation node-to-node, with no central hub and no second authority center**
-- by composing the sealed Sovereign Object Model, not by building a federation registry or a central validator:

  * `validate_received` -- the RECEIVING node validates a shared packet **independently**, composing the sealed
    `verify_packet`, a **pure, offline function over the packet's own bytes**: no sender registry, no network, no
    central authority. Each node validates for itself. This is the anti-hub core.
  * `authorize_crossing` -- a crossing is gated by a **peer-declared sharing rule**, composing the sealed
    `check_access`: own-mandate access is whole; a cross-node (cross-mandate) access needs a rule naming exactly this
    object, this peer, and a scope at least as strong -- refused otherwise. No central grant authority.
  * `node_root` + `reconcile_roots` -- two nodes reconcile by comparing **independently-computed** integrity roots
    (each node's own `mandate_root`); neither root is authoritative over the other -- alignment is mutual, and a
    divergence is surfaced for governance rather than silently reconciled to one side.
  * `share_node_state` -- the sending node packages its verifiable state as a self-verifying successor packet
    (composing `cut_manifest` + `build_packet`), which travels node-to-node and is validated by the receiver.

No hub, no second authority center, no federation registry of its own -- only the governance of a federation over the
sealed object model. Pure composition (the object model is hashlib-based): runs green on a bare clone."""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from ..objects.scope import check_access, mandate_root, ScopeRefusal  # noqa: F401  (re-exported)
from ..objects.inheritance import build_packet, verify_packet
from ..objects.manifest import cut_manifest


class FederationError(ValueError):
    """Raised when a federation act cannot proceed honestly. Scope refusals surface as the sealed object model's
    ScopeRefusal (re-exported), so a cross-node access is refused by the same law that governs every boundary."""


def share_node_state(reg, *, at: str) -> Dict[str, object]:
    """The sending node packages its verifiable state for a peer -- composing the sealed object model's manifest and
    successor packet (`cut_manifest` -> `build_packet`). The packet is SELF-VERIFYING: a peer validates it with only
    its own bytes, needing no access to this node's systems, and it travels node-to-node with no hub in between."""
    manifest = cut_manifest(reg, at=at)
    return build_packet(reg, manifest)


def validate_received(packet: Mapping) -> Dict[str, object]:
    """The RECEIVING node validates a shared packet INDEPENDENTLY -- composing the sealed `verify_packet`, a pure,
    offline function over the packet's own bytes: no sender registry, no network, and NO CENTRAL AUTHORITY. Returns
    `{accepted, failures, root}`; accepted is True only if every check passes (fail-closed). This is the anti-hub
    core: each node validates a peer's data for itself, so the federation needs no trusted central validator."""
    ok, fails = verify_packet(dict(packet))
    return {
        "accepted": bool(ok),
        "failures": list(fails),
        "root": (packet.get("manifest") or {}).get("root"),
    }


def authorize_crossing(reg, rules: Sequence, *, principal_mandate: str, obj_id: str, want: str = "read") -> bool:
    """Gate a cross-node access by a PEER-DECLARED sharing rule -- composing the sealed `check_access`: own-mandate
    access is whole; a cross-node (cross-mandate) access needs a `SharingRule` naming exactly this object, this peer
    mandate, and a scope at least as strong -- `ScopeRefusal` otherwise, nothing implicit and nothing wider. There is
    no central grant authority: a crossing exists only because a peer declared the rule for it."""
    return check_access(reg, list(rules), principal_mandate=principal_mandate, obj_id=obj_id, want=want)


def node_root(reg, mandate: str) -> str:
    """A node's own integrity root over exactly its mandate's objects -- composing the sealed `mandate_root`. Two
    nodes compute this INDEPENDENTLY and compare it (`reconcile_roots`); neither node's root is authoritative over
    the other."""
    return mandate_root(reg, mandate)


def reconcile_roots(node_root_value: str, peer_root_value: str) -> Dict[str, object]:
    """Reconcile two nodes by comparing INDEPENDENTLY-computed integrity roots -- agree, and the shared state is
    aligned; differ, and the divergence is surfaced for governance rather than silently reconciled to one side. No
    central truth: neither root is authoritative, so reconciliation is mutual agreement (or a flagged divergence),
    never one node's state overwriting another's."""
    aligned = node_root_value == peer_root_value
    return {
        "aligned": aligned,
        "node_root": node_root_value,
        "peer_root": peer_root_value,
        "divergence": None if aligned else "roots differ -- reconcile the underlying objects before sharing; "
                                           "neither node's state is authoritative over the other",
    }
