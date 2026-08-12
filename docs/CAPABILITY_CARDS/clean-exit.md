# Clean exit — sever grants, walk with keys

- **id:** `clean-exit`
- **sealed home:** Sovereign Peerhood (Series 14) V05 — The Clean-Exit Covenant
- **callable path:** `sovereign_agent.peerhood.clean_exit`
- **gate required:** **N**

## Verbs
- `clean_exit`
- `exit_green_light`
- `walk_with_keys_and_records`
- `membership_is_live`
- `sever_pool_link`

## Inputs / outputs
- **in:** keystore_dir, peer id, its recognitions / delegations / memberships, at, registry
- **out:** CleanExit{grants_severed, grants_total, no_residual, severances} · ExitLight{on, reason}

## Receipt shape
CleanExit (executable severance signed with the peer's own key; sever-kills-live — prior grants verify DEAD); exit_green_light -> ON only when every grant severed, keys sole-held, no claim retained

## Kill-targets (an app on this MUST NOT violate)
- exit is EXECUTABLE, not prose-reversible — severance kills the live grant
- no exit-with-hostage / residual-grant / escrow / custodian (refused)
- the peer walks with its keys + records, no retained claim

## Anti-patterns
- 'deactivation' that a central party can undo
- holding a user's records or keys after they leave
- an exit that leaves a grant live somewhere

## App patterns
- give every user a one-act, verifiable way to leave with their data
- prove to a leaving user that no grant survives their exit
- run a generational hand-off under a family quorum
