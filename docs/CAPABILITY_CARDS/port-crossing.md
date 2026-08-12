# The Sovereign Port — governed external attach

- **id:** `port-crossing`
- **sealed home:** Inter-Node Sovereignty (Series 6) V07 — The Sovereign Port
- **callable path:** `sovereign_agent.port.crossing`
- **gate required:** **Y**

## Verbs
- `open_crossing`
- `sanction_crossing`

## Inputs / outputs
- **in:** registry, node_id, external target, instruction (a directive/reference, never value), a declared SharingRule, a NAMED human approver + approval_ref
- **out:** a governed crossing object · sanction -> {crossed:True, crossing_root, boundary, approver, approval_ref}

## Receipt shape
crossing receipt naming the boundary + the named human; DENY-BY-DEFAULT: undeclared boundary or no named approver -> refused; the Port records that a crossing happened, never the value

## Kill-targets (an app on this MUST NOT violate)
- Port is the ONLY blessed path to any external AI / browser tool / SaaS / rail
- no value held or moved; money-path OFF — the Port carries a directive, not funds
- no central settlement authority sanctions the reach — the node does, by its own declared rule + a named human

## Anti-patterns
- an app calling an external API directly, bypassing the Port
- auto-approving a crossing with no named human
- the Port holding balances or settling value

## App patterns
- route every outbound call to a SaaS / model / rail through a sanctioned crossing
- require a named human to approve the first reach to a new external target
- produce an audit receipt for each external attach
