# Audit → Series Pipeline Placement Map v1.0 (GB, 2026-06-11)

> **Task (KM):** map audit-report-2026-06-10.md findings into the series pipeline as **derived extrusions** — the code taught us; the books absorb it; no parallel canon. **Status: PROPOSED — awaits KM Atrium ratify before GB folds into series_roadmap.yaml.** Every placement extends an EXISTING volume (no new books, no new series — rail before volume).
> **Principle check:** each entry derives from a sealed fix (Tiger's commits = the source events), pins to code (coherence_pin), states LGP alignment, preserves the one human gate.

## A. Placement table (priority order = KM's: integrity → cockpit → perf → tests → rigor)

| # | Finding cluster (audit refs) | Series · Volume | Placement (derived extrusion) | Pri |
|---|---|---|---|---|
| 1 | **CRITICAL write fence** — ledger `_append` race forks chain; proposals.json same class; 3rd hash-chain impl in gb_meta_cylinder | **S2 · vol_01** (Immutable Core / receipted cockpit) | New section **"The Write Fence — one chain, one writer at a moment"**: why append-only ≠ safe-concurrent; flock pattern; chain-repair; the two-appender test as constitutional conformance. Cross-pin: S6 (two writers IS the two-node problem at process scale) | P1 |
| 2 | **Actor binding** — principal spoofing via request body into immutable chain | **S7 · zero-trust** | Section **"The Actor Is Who Authenticated"**: identity from the verified channel, never the payload; `requested_by` vs cryptographic actor. Cross-pin: S2 vol_02 (K-invariant: breath-gate meaning depends on actor truth) | P1 |
| 3 | **Authorization gap** — authn≠authz on code-exec routes (/produce /apply /recompile); loopback auto-auth | **S7 · zero-trust** | Section **"Authentication Is Not Authorization — shields at the execution boundary"**: owner-gating, principal tiers, why dev/loopback principals never reach exec routes | P1 |
| 4 | **Gate bypass** — human approval auto-simulated in all modes (deps.py); replay flips denied→approved | **S2 · vol_03** (Governed Loop) | Section **"The Gate Must Be Real in Every Mode"**: simulation-drift as the quiet killer of Propose→Approve→Execute; replay-is-law (deny stays denied). The breath-gate's integrity as code, not docstring | P1 |
| 5 | **Cockpit closure twins** — proposals.json silent-wipe on corruption; inconsistent error envelopes; vocab drift between modules; zero tests on disposition routes | **S8 · sovereign_ux** | Section **"Loops That Close Loudly"**: the five pilot findings + their code-side twins as one lesson — derived state, announced transitions, one vocabulary, loud unknowns, dispositions as packets | P2 |
| 6 | **Perf/scale band** — 6× re-parse per GET; O(n) verify per poll; O(n) Merkle rebuild; unbounded payloads; O(n) appends | **S5 · full_production_erp** (hardening vol) | Section **"Scaling the Receipted Engine"**: mtime-keyed caching that preserves truth; incremental chain verification; pagination as sovereignty (bounded responses); when O(n) is constitutional debt. Cross-pin: S2 vol_01 incremental verify | P3 |
| 7 | **Test-coverage band** — zero tests on feedback/proposals/contract/board_rigor/atrium_apply; untested failure paths (torn NDJSON, orphan credits, concurrency) | **S2 · vol_03** (Governed Loop) + WORKFLOW canon | Section **"Every Gate Earns a Test"**: constitutional conformance testing — each gate, each failure path, each replay rule; co-extrusion already mandates tests, this codifies *which* (gates + failure paths first). WORKFLOW DoD line added | P4 |
| 8 | **Portability/reproducibility band** — broken Dockerfile; hardcoded machine paths; ignored env var; unpinned deps; undeclared imports | **S5 · full_production_erp** + S3 (sovereign configuration) | Section **"Runs Anywhere or It Isn't Sovereign"**: reproducibility pinning, config seams over hardcoded paths, the works-on-this-machine failure class | P4 |
| 9 | **The Night Watch itself** — recurring self-audit, delta+sweep cadence, adversarial verification of findings | **S2 · vol_03** (Governed Loop) | Section **"The Night Watch — the system audits itself"**: the governed loop applied to the engine's own health; watched-systems doctrine; this week as the case study | P5 |

## B. YAML-ready blocks (fold targets for series_roadmap.yaml on KM ratify)
```yaml
# Under agentic_harness vol_01 (immutable core):
audit_extrusions:
  - id: write_fence
    section: "The Write Fence — one chain, one writer at a moment"
    derived_from: "audit-report-2026-06-10 CRITICAL + Tiger fix (flock + chain-repair + concurrency test)"
    coherence_pin: "src/sovereign_agent/obligations/ledger.py:_append (flock critical section)"
    lgp_alignment: "high — the chain a generation inherits must be unforkable"
    status: proposed_extrusion
# Under zero_trust_sovereignty:
  - id: actor_binding
    section: "The Actor Is Who Authenticated"
    coherence_pin: "node_api/routes/obligations.py (current_principal unconditional)"
    lgp_alignment: "high — sovereignty IS actor truth (CONSTITUTION §1)"
    status: proposed_extrusion
  - id: authz_boundary
    section: "Authentication Is Not Authorization"
    coherence_pin: "node_api/auth.py owner-gate on exec routes"
    lgp_alignment: "high — execution boundary shields"
    status: proposed_extrusion
# Under agentic_harness vol_03 (governed loop):
  - id: real_gates_every_mode
    section: "The Gate Must Be Real in Every Mode"
    coherence_pin: "node_api/deps.py approval path; ledger replay semantics"
    lgp_alignment: "high — one human gate, never simulated away"
    status: proposed_extrusion
  - id: every_gate_earns_a_test
    section: "Every Gate Earns a Test"
    coherence_pin: "tests/ conformance suite (gates + failure paths)"
    lgp_alignment: "med-high — trust compounds only on tested gates"
    status: proposed_extrusion
  - id: night_watch
    section: "The Night Watch — the system audits itself"
    coherence_pin: "scripts/cron/* + artifacts/audit_reports/"
    lgp_alignment: "high — hardening every chance, receipted"
    status: proposed_extrusion
# Under sovereign_ux:
  - id: loops_close_loudly
    section: "Loops That Close Loudly"
    coherence_pin: "node_api/routes/feedback.py awaiting_km; pipeline_stage_labels.yaml"
    lgp_alignment: "high — the cockpit the heir can trust"
    status: proposed_extrusion
# Under full_production_erp (+ S3 config cross-ref):
  - id: scaling_receipted_engine
    section: "Scaling the Receipted Engine"
    coherence_pin: "ledger mtime cache + incremental verify_chain"
    lgp_alignment: "med — truth that stays fast stays used"
    status: proposed_extrusion
  - id: runs_anywhere
    section: "Runs Anywhere or It Isn't Sovereign"
    coherence_pin: "pyproject pinning; config.py seams; Dockerfile"
    lgp_alignment: "med-high — portability = generational survivability"
    status: proposed_extrusion
```

## C. Guard rails honored
- **No parallel canon:** every entry extends an existing volume; the audit report stays an *artifact*, the books stay the *source* — these sections render FROM the sealed fixes and their tests (seeit/coherence lens can then cite them).
- **One human gate:** nothing folds until KM's Atrium ratify; after fold, chapters flow the normal rail (boards → rigor → fidelity → Brief).
- **Vol_04 caution:** S2 vol_04 deliberately NOT targeted (6 chapters still pending G re-map — no placements onto unstable ground).
- **MEDIUM/LOW residue:** the remaining ~30 findings fold into bands 5–8 as supporting examples inside the same sections — no finding orphaned; full traceability table stays in the audit report (TRUTH: report ↔ map ↔ roadmap pins all resolve).

∞Δ∞ SEAL: proposed — the engine's scars become the books' chapters; the books then guard the engine. That's the loop closing at the highest altitude.
