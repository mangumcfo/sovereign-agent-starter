# Recognize / refuse a peer (no registry)

- **id:** `peer-recognition`
- **sealed home:** Sovereign Peerhood (Series 14) V02 — Recognition Without a Registry
- **callable path:** `sovereign_agent.peerhood.recognition`
- **gate required:** **N**

## Verbs
- `mutual_recognition`
- `verify_recognition`
- `refuse_recognition`
- `scoped_visibility`
- `recognition_as_receipt`

## Inputs / outputs
- **in:** keystore_dir, two peer ids, at, registry
- **out:** a signed recognition receipt · refuse -> {residual_claim:None, hostage_free:True, signature}

## Receipt shape
recognition receipt {parties, signature} verifiable public-only by both parties and no one else; refuse -> hostage-free signed act

## Kill-targets (an app on this MUST NOT violate)
- no central registry / directory / name-service / scored-authority (refused)
- refusing a peer leaves NO residual claim (hostage-free)
- recognition verifies for the two parties only, never a third

## Anti-patterns
- a central directory that lists or ranks peers
- a reputation score used as authority
- a refusal that leaves a lingering claim on the refused peer

## App patterns
- let two users establish a mutual, verifiable relationship with no server
- show a peer's scoped, self-declared profile (not a central lookup)
- let a user cleanly refuse another with no residue
