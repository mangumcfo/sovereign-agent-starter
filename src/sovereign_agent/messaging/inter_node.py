"""Inter-node messaging — a message is a governed, provenance-carrying object each peer validates independently.

Co-extrusion for s6_01 (Receipted Inter-Node Messaging, KM S6 GO 2026-08-05). Pure / structural, no crypto substrate
beyond the sealed hashlib object model (F-1 import-clean AND bare-clone-clean). Two sovereign nodes exchange messages
WITHOUT a central message broker, WITHOUT a hub, and WITHOUT any relay that takes custody of the meaning: a message is
registered by its sender as a governed object carrying its own author, source, and integrity identity; it is delivered
node-to-node as a SELF-VERIFYING packet; and the receiving node validates it INDEPENDENTLY, over the packet's own bytes,
with no sender registry, no network, and no central authority. Each node validates a peer's message for itself.

Two governed acts:
  * `send_message` registers a message as a governed, provenance-carrying object under one mandate -- composing the
    sealed object registry (`reg.append`, kind=ratify): the message body becomes an authored version carrying its
    `author`, its `source_ref` (provenance), and a `version_hash` (integrity identity), so a message is a receipt from
    the moment it is sent; an empty id or empty body is refused. `carry_to_peer` then packages the sending node's
    messages as a SELF-VERIFYING packet -- composing the sealed Federation Node Governance `share_node_state`
    (`cut_manifest` -> `build_packet`) -- which travels node-to-node with nothing in between.
  * `receive_from_peer` is the anti-hub core: the receiving node validates the delivered packet INDEPENDENTLY --
    composing the sealed Federation Node Governance `validate_received` (a pure, offline check over the packet's own
    bytes) -- FAIL-CLOSED: a packet that does not pass every check, or whose root does not match the peer-stated
    `expected_root`, is refused. Only a self-validated packet is accepted, so the federation needs no trusted central
    validator.

Human primacy and the sovereignty boundary hold: the message is the sender's governed object, the delivery carries no
custodian, and acceptance is the receiving node's own independent validation. This module builds no message broker, no
hub, no queue, and no transport of its own -- the receipt/provenance/integrity is the sealed object model's, and the
self-verifying delivery + independent validation is the sealed Federation Node Governance floor's, composed."""
from __future__ import annotations

from typing import Dict, Mapping, Optional

from ..objects.registry import ObjectRegistry  # noqa: F401  (type reference for the composed registry)
from ..federation.node_gov import share_node_state, validate_received


class MessagingError(ValueError):
    """Raised when an inter-node message cannot be sent or received honestly: a message with no id or no body, or a
    delivered packet that fails its own independent validation or whose root does not match the peer-stated expectation
    -- fail-closed, a message is a self-validating governed object each peer verifies for itself, or it is not accepted."""


def send_message(reg, message_id: str, body: Mapping, *, mandate: str, author: str,
                 source_ref: str, at: str) -> Dict[str, object]:
    """Register a message as a governed, provenance-carrying object under one mandate -- composing the sealed object
    registry. The `body` becomes the object's authored version, carrying the sending node's `author`, its `source_ref`
    (provenance), and a `version_hash` (integrity identity) from its first version, so the message is a receipt the
    moment it is sent -- not an anonymous packet on a broker. An empty `message_id` or empty `body` is refused; the
    sealed registry additionally requires a non-empty `source_ref` and a mandate. Returns the governed message object."""
    if not message_id:
        raise MessagingError("a message needs an id")
    if not body:
        raise MessagingError("a message needs a body to send")
    return reg.append(f"message:{message_id}", dict(body), author=author, source_ref=source_ref,
                      at=at, mandate=mandate, kind="ratify")


def carry_to_peer(reg, *, at: str) -> Dict[str, object]:
    """Package the sending node's governed messages as a SELF-VERIFYING packet for a peer -- composing the sealed
    Federation Node Governance `share_node_state` (`cut_manifest` -> `build_packet`). The packet validates from its own
    bytes, needs no access to this node's systems, and travels node-to-node with nothing in between -- no broker, no
    hub, no relay taking custody of the messages."""
    return share_node_state(reg, at=at)


def receive_from_peer(packet: Mapping, *, expected_root: Optional[str] = None) -> Dict[str, object]:
    """Validate a delivered packet INDEPENDENTLY -- the anti-hub core -- composing the sealed Federation Node
    Governance `validate_received` (a pure, offline function over the packet's own bytes: no sender registry, no
    network, no central authority). FAIL-CLOSED: a packet is accepted only if every check passes; a packet that fails
    validation, or whose root does not match a peer-stated `expected_root`, is refused. Returns the accepted message
    root and the fact that this node validated it for itself."""
    if not isinstance(packet, Mapping) or not packet:
        raise MessagingError("no packet to receive -- a message is delivered as a self-verifying governed packet")
    result = validate_received(packet)
    if not result.get("accepted"):
        raise MessagingError(
            f"message refused: the delivered packet failed independent validation -- {result.get('failures')}"
        )
    root = result.get("root")
    if expected_root is not None and str(root) != str(expected_root):
        raise MessagingError(
            f"message refused: validated root {root!r} does not match the peer-stated expected root {expected_root!r}"
        )
    return {"received": True, "message_root": root, "validated_by": "self", "failures": []}
