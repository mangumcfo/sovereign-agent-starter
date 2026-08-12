# Receipted inter-node messaging (no hub)

- **id:** `messaging`
- **sealed home:** Inter-Node Sovereignty (Series 6) V01 — Receipted Inter-Node Messaging
- **callable path:** `sovereign_agent.messaging.inter_node`
- **gate required:** **N**

## Verbs
- `send_message`
- `carry_to_peer`
- `receive_from_peer`

## Inputs / outputs
- **in:** registry, message_id, body, mandate, author, source_ref, at; a delivered packet (to receive)
- **out:** a governed message object (a receipt on send) · receive -> {received, message_root, validated_by:'self'}

## Receipt shape
message object {object_id, version_hash, author, source_ref}; a self-verifying packet each peer validates over its own bytes; wrong stated root or tamper -> refused

## Kill-targets (an app on this MUST NOT violate)
- no broker / hub / relay takes custody of the message
- no central validator — each node validates for itself
- fail-closed: a packet that fails its checks or root is refused

## Anti-patterns
- routing all messages through a server that can read/alter them
- trusting a central service's 'valid' instead of validating bytes
- accepting a packet whose root you did not check

## App patterns
- exchange signed, provenance-carrying messages between two nodes
- verify a received message offline before acting on it
- build a chat/notification client where the server can't forge messages
