# Governed object model + mandate scope

- **id:** `object-model`
- **sealed home:** Full Production ERP (Series 5) V05 object registry; Zero-Trust Sovereignty (Series 7) V05 declared scope
- **callable path:** `sovereign_agent.objects.registry.ObjectRegistry; sovereign_agent.objects.scope.SharingRule, check_access`
- **gate required:** **N**

## Verbs
- `ObjectRegistry.append`
- `ObjectRegistry.versions`
- `ObjectRegistry.current`
- `ObjectRegistry.population_root`
- `SharingRule`
- `check_access`

## Inputs / outputs
- **in:** root_dir; obj_id, payload, author, source_ref, at, mandate; SharingRule(obj_id, to_mandate, scope)
- **out:** an append-only version {object_id, version_hash, seq, mandate, payload} · population_root hex

## Receipt shape
each object is an authored, hash-chained version under exactly one mandate; state is derived by replay; cross-mandate access needs a declared SharingRule or is refused (deny-by-default)

## Kill-targets (an app on this MUST NOT violate)
- an object belongs to exactly one mandate — a second registration refuses
- no cross-mandate access without a declared rule (no standing trust)
- state is replayed from the record, never asserted by a current-value row

## Anti-patterns
- mutating an object in place instead of appending a version
- reading across mandates with no declared SharingRule
- trusting a 'current value' field over a replay of the chain

## App patterns
- model your app's business objects as governed, auditable versions
- derive one integrity root over a whole population for a proof
- grant exactly one other party exactly one scope on one object
