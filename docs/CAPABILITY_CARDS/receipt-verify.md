# Offline receipt / signature verification

- **id:** `receipt-verify`
- **sealed home:** Full Production ERP (Series 5) V26 — pure offline validate; no registry, no network (GB ratified 2026-08-11)
- **callable path:** `sovereign_agent.keystore.node_keystore.verify_node_act; sovereign_agent.onboarding.onboard.verify_onboard_receipt; sovereign_agent.peerhood.recognition.verify_recognition`
- **gate required:** **N**

## Verbs
- `verify_node_act`
- `verify_onboard_receipt`
- `verify_recognition`

## Inputs / outputs
- **in:** a receipt/packet + the relevant public key or identity
- **out:** bool (True = genuine, verified from bytes alone)

## Receipt shape
bool — computed from the receipt's own bytes and a public key; no AI, no cloud, no account

## Kill-targets (an app on this MUST NOT violate)
- verification is the holder's, never 'verified by us'
- no network, no central authority in the check
- public-only — the verifier never needs a private key

## Anti-patterns
- 'trust our server said it's valid' instead of verifying bytes
- requiring an account or API call to verify
- verifying with anything other than the stated public key

## App patterns
- let a recipient confirm a receipt is genuine on their own machine
- gate a workflow on a real signature check, not a claim
- audit a chain of receipts after the fact, offline
