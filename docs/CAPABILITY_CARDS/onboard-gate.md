# Five-turn human onboard + gated acts

- **id:** `onboard-gate`
- **sealed home:** Inter-Node Sovereignty (Series 6) V6 + Full Production ERP (Series 5) V16 gate — composes the sealed gate; no new admission authority (GB ratified 2026-08-11)
- **callable path:** `sovereign_agent.onboarding.onboard`
- **gate required:** **Y**

## Verbs
- `run_onboard`
- `cli_onboard`
- `verify_onboard_receipt`
- `DEFAULT_GATED_ACTS`

## Inputs / outputs
- **in:** keystore_dir, a prompter callback (AI proposes / human disposes), at
- **out:** OnboardReceipt (signed over turns 1-5) · verify_onboard_receipt -> bool

## Receipt shape
OnboardReceipt{node_id, name, fingerprint, gated_acts, first_act, first_gate, signature}; no key written before the turn-1 accept

## Kill-targets (an app on this MUST NOT violate)
- no key until the human accepts at turn 1
- AI proposes, human disposes — default-deny on gated acts
- no telemetry / no phone-home / no default peers / no account

## Anti-patterns
- auto-accepting the key ceremony on the human's behalf
- removing the human hand from an act the operator chose to gate
- shipping a default peer list or a home-server URL

## App patterns
- run a first-boot ceremony where your user accepts their own key
- let the user pick which of your app's actions always need their hand
- hand the user a signed receipt they can verify without your app
