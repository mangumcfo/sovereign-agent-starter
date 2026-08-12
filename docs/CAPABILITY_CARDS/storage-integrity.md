# Sovereign datum storage (owner-scoped, Merkle-bound)

- **id:** `storage-integrity`
- **sealed home:** Zero-Trust Sovereignty (Series 7) V03 — Sovereign Data Storage Model
- **callable path:** `sovereign_agent.storage.sovereign_store`
- **gate required:** **N**

## Verbs
- `store_datum`
- `retrieve_datum`

## Inputs / outputs
- **in:** registry, owner, content chunks, visibility ('private'|'shared'), mandate; a SharingRule + presented chunks (to retrieve cross-mandate)
- **out:** a governed datum {object_id, version_hash, payload{visibility, root}} · retrieve -> {retrieved, integrity:'verified'}

## Receipt shape
datum carries a Merkle root over its own bytes; retrieval is deny-by-default, scoped, integrity-checked — altered bytes or an undeclared access are refused

## Kill-targets (an app on this MUST NOT violate)
- no central store owns or vouches for the data — the owner does
- no silent public bucket — absence of a rule is a refusal
- no altered data served — integrity checked from the datum's own bytes

## Anti-patterns
- uploading user data to a bucket a central service controls
- serving bytes without checking them against the stored root
- widening access without the owner declaring a SharingRule

## App patterns
- store user files as owner-scoped, integrity-bound objects
- share a file with exactly one party via a governed rule
- detect at-rest tampering on every read
