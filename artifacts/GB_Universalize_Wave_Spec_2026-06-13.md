# Universalize Wave — break the 82 plateau (GB spec, 2026-06-13)
*KM directive: run the universalize wave. The reactive loop plateaued at 82 because each sweep peels the next propagation-debt sibling. This wave stops chasing named findings and applies each proven discipline to EVERY site at once — so the next sweep has no siblings left to find. Tiger builds uninterrupted; GB audits + confirming-sweeps at completion. Freeze-allowed (all remediation, zero net-new). Baseline: 82/100, 0 CRITICAL, suite 227.*

## The mandate that makes this different
For each discipline below: **grep the whole tree for EVERY site of the pattern — fix all of them in one pass.** Do not fix only the sites the audit named; the audit names samples. The goal is: *after this wave, the discipline is universal, and an adversarial sweep cannot find an un-wired instance.*

## v2 GUARDS (Lumen, binding — the wave fails without these)
- **G1 · Universalize by EXTRACTING THE PRIMITIVE, not by copy-paste.** The hidden rot: 14 similar patches = the next generation of propagation debt. RULE: *one* tolerant-ndjson reader · *one* file-stat memoizer · *one* chain-read gateway · *one* root resolver · *one* append-only store — every caller ROUTES THROUGH IT. The wave must leave behind FEWER patterns, not safer-repeated ones. **Success = the disciplines become primitives, not patches; the pattern has ONE home.**
- **G2 · Tolerant parse = diagnose, not erase.** Distinguish a **truncated TRAILING line** (quarantine + repair, survive) from a **corrupt MIDDLE line** (LOUD: `chain_corrupt=true`, `repair_required=true`, routes degrade — NEVER silent-skip). Tolerance means *survive corruption long enough to report and repair it,* not "the chain forgets politely." Constitutional.
- **G3 · NEW discipline — single gateway / single resolver.** Several prior findings weren't parse/perf — they were *modules inventing their own view of the same chain* (private `_entries()` consumers, hand-parsed `obligations.ndjson` across modules, split-brain roots). UNIVERSALIZE: one chain-read gateway + one root resolver; **no module reaches the substrate directly.** Omit this and sibling findings survive. Law: *"every module knowing too much about the substrate"* is the disease.
- **G4 · Pattern-regression guards (after the wave, lightweight).** Small pattern tests so the disease can't reappear: no request-path `sys.path` insert · no raw `json.loads(line)` in route/script code · no whole-file-rewrite append · no direct `ObligationLedger._entries()` outside the approved gateway · no uncached polled file loader. Plus the law: **scripts may call package code; package code must NOT depend on scripts.**
- **G5 · VerifiableMemory is the riskiest change — migration test required.** legacy JSON memory → new NDJSON leaf log must yield the SAME root / SAME attestation meaning. No root drift, no receipt drift, no silent historical incompatibility.
- **FREEZE NOTE:** Gate 7 + Parity Pulse net-new builds stay POST-95 (freeze). This wave HARDENS the substrate they'll build on (the gateway + memoized projections are parity's foundation — "polled surfaces consume projections, not raw files") but does NOT build the net-new surfaces.

## Build order (Lumen-revised — gateway/resolver FIRST so everything routes through them)
1. **Shared chain/NDJSON gateway** (tolerant parse · loud middle-corruption · no private `_entries()` consumers).
2. **Shared ledger/root resolver** (no split-brain roots).
3. **Memoized projections** (polled surfaces + refs consume projections, not raw files).
4. **Append-only VerifiableMemory** (with migration/root-equivalence test).
5. **Package runtime imports** (scripts become wrappers; package never imports scripts).
6. **Deps + bounded-growth hygiene** (constraints regen from green env + record cmd/platform; audit-trail bounded-AND-persisted).
7. **Pattern-regression tests** (G4 — prevent reintroduction).

## The disciplines to universalize

1. **Tolerant ndjson parse (no single bad line bricks a chain).**
   - Owning fix: `ledger._entries()` (and `verify_chain`, `repair_chain`) — a truncated/partial trailing line currently raises and bricks the whole ledger AND blocks `repair_chain` itself (HIGH).
   - UNIVERSALIZE: every raw `json.loads`-per-line over an ndjson file (ledger, thread_channel, hopper feed, any other) gets per-line tolerance (skip/quarantine the incomplete tail, loud-log it), mirroring `_jsonstore`/`yaml_repair` resilience. `repair_chain` must survive a truncated tail.

2. **Memoize every polled read on a stat key.**
   - Named: `/hopper` (the one polled lens never cached, MED) + `ledger.refs()` (the one chain-view not memoized on `_stat_key`, MED).
   - UNIVERSALIZE: grep every route handler + every chain-derived view; any that reads a file or re-scans the chain per request gets `_filecache.memoize_on(...)` or `_stat_key` memo, matching series/coherence/dialogue. No polled path re-parses unchanged data.

3. **Append-only + incremental, not full-rebuild-per-write.**
   - Owning fix: `VerifiableMemory.append/get_root` (core.py) — full Merkle rebuild + full JSON rewrite per append, fires every obligation close → O(n²), 5,573 live leaves (HIGH).
   - UNIVERSALIZE: incremental/memoized Merkle root on a version key + append-only NDJSON leaf log (mirror the ledger). Grep for any other "rebuild-the-world-on-write" or "rewrite-whole-file-per-append" site and give it the same treatment.

4. **Package what's imported (no `scripts/` on sys.path at runtime).**
   - Named: `/export/packet` (R22-1) + `/actions` (R22-2) inject `scripts/` and import export_packet/actions_projection — breaks in container/non-editable install (HIGH).
   - UNIVERSALIZE: move runtime-imported scripts into the installed package (`src/sovereign_agent/...`); grep for every `sys.path` inject + `import` of a `scripts/` module from a request path and convert to proper module imports.

5. **Honest deps + bounded growth (hygiene tail).**
   - `constraints.txt` regenerated from the actual green env (PyYAML 6.0.3, pytest 8.4.2, count 227) — stop hand-editing provenance.
   - `ComplianceEngine._audit_trail` bounded/persisted (unbounded in-process list).

## Cadence (KM-set)
Uninterrupted: per discipline → grep all sites → fix → suite-green → commit; cards surface as you go; no per-discipline gate. When the whole wave is done, hand to GB → GB rigor-audit the full delta + run ONE confirming sweep → land (target: 90s, ideally 95, with the next sweep finding no propagation siblings).

## Done-definition
Each discipline universal (grep shows zero un-wired sites) · suite green throughout · `repair_chain` survives a truncated tail (test) · VerifiableMemory append O(1)-amortized (test) · /export+/actions import as packaged modules · no freeze-violation (all remediation). GB confirming sweep is the proof.

∞Δ∞ SEAL: spec — stop fixing the samples; fix the pattern everywhere. The plateau breaks when the discipline is universal, not when the named list is empty.
