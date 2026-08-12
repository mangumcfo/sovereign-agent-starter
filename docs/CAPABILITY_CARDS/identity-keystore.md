# Self-held node identity (D1 keystore)

- **id:** `identity-keystore`
- **sealed home:** D1 keystore — Sovereign Peerhood (Series 14) substrate
- **callable path:** `sovereign_agent.keystore.node_keystore`
- **gate required:** **N**

## Verbs
- `generate_node_key`
- `load_node_key`
- `load_node_keypair`
- `sign_node_act`
- `verify_node_act`
- `node_fingerprint`
- `has_node_key`

## Inputs / outputs
- **in:** keystore_dir, node_id, payload bytes (to sign), public_hex + sig_hex (to verify)
- **out:** NodeKey{public_hex, fingerprint} · signature hex · verify -> bool

## Receipt shape
NodeKey(public_hex, fingerprint); sign -> hex signature; verify_node_act -> bool; stable fingerprint across reload

## Kill-targets (an app on this MUST NOT violate)
- no custodian / escrow / KMS / seal-key field (refused)
- no key minted before the sovereign's own act
- fail-loud if the key is absent — never a silent stub

## Anti-patterns
- app stores or transmits the private key
- a cloud service holds the key 'for convenience'
- a recovery service that can reconstruct the key

## App patterns
- derive the node's stable identity for your app's session
- sign an app action so a third party can verify it without you
- verify a counterparty's signed act offline, no account
