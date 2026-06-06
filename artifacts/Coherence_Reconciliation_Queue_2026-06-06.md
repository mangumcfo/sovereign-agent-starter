# Coherence Reconciliation Queue — Partial + Missing → governed proposals

**Source:** G's 2026-05-30 review harvest (`coherence_capabilities.json`). **Gaps:** 37 (16 partial + 21 missing), deduped into **13** cross-cutting platform capabilities.
**Flow (KM 2026-06-06):** ideation → KM review/accept (one gate) → Tiger updates the relevant book passages + raises the platform-promotion → monitor re-pins. Books stay source; gaps flow back.
**Fence:** Tiger authors + opens atrium_review obligations; GB owns roadmap; KM ratifies.

## [HIGH] Tiered + qualified-reviewer breath-gates (materiality/audience/role)
- **ref:** `recon:tiered-qualified-gates` · **books:** 01_cfos_finance, 05_hr_talent, 06_compliance_audit, 07_sales_revenue, 02_executives_decisions
- **leverage:** 5 books — the single highest-leverage harness primitive; turns the binary gate into materiality/audience/role-aware.
- **proposed reconciliation:** Promote tiered/qualified-reviewer gate types in breath-gate + role_spec (with receipt attribution); update the cited book passages to reference the real gate tiers; re-pin.

## [HIGH] Source-citation + methodology lineage in the receipt envelope
- **ref:** `recon:source-citation-lineage` · **books:** 01_cfos_finance
- **leverage:** Constitutional per Book 1 ('every number cites its source'); strengthens every financial receipt.
- **proposed reconciliation:** Add first-class source-citation + methodology-version fields to the receipt envelope; update Book 1 passages; pin to compliance_engine.py.

## [HIGH] Queryable .actions[] projection over Merkle leaves
- **ref:** `recon:actions-projection` · **books:** 10_scaling_enterprise
- **leverage:** One fix, three consumers (books + SDK + Atrium audit); also clears the B10-12 verify-command drift.
- **proposed reconciliation:** Add an .actions[] projection over core.py Merkle leaves; update the B10-12 Runtime-Exercise verify passages; re-pin to core.py.

## [HIGH] Cross-role review / veto primitive (joint_attestation)
- **ref:** `recon:cross-role-veto` · **books:** 11_ma_due_diligence, 09_multi_agent
- **leverage:** Supports Book 11 (compliance vetoes CFO per Charter) + Series 2 Vol 3 governed dev loop.
- **proposed reconciliation:** First-class cross-role veto with joint_attestation receipts + escalation; update Book 11 passage; pin to compliance_engine.py.

## [HIGH] Standardized evidence-packet exports (verification/decision/deal/communication)
- **ref:** `recon:evidence-packet-exports` · **books:** 06_compliance_audit, 07_sales_revenue, 09_multi_agent, 11_ma_due_diligence
- **leverage:** 4 books — auditor/regulator/board-facing proof export; one packet primitive serves all.
- **proposed reconciliation:** One standardized evidence-packet export (receipt + chain + optional ledger anchor); update the 4 books' passages; pin to node_api.

## [MED] Always-on monitoring companions (data-quality / safety / regulatory / bias)
- **ref:** `recon:monitoring-companions` · **books:** 04_supply_chain, 08_manufacturing_ops, 06_compliance_audit, 05_hr_talent
- **leverage:** 4 books — a persistent-monitor companion pattern (receipted) generalizes across domains.
- **proposed reconciliation:** A receipted monitoring-companion primitive (domain-parameterized); update the 4 books' passages; pin once built.

## [MED] Trust calibration + override-rate feedback + promotion history
- **ref:** `recon:trust-calibration` · **books:** 02_executives_decisions, 03_leading_agents
- **leverage:** 2 books — 5-level calibration + shadow→production advancement; leadership-grade tooling.
- **proposed reconciliation:** Per-agent/per-person trust level + override-rate feedback + promotion history; update Books 2/3; pin.

## [MED] First-class bind_role action class on node.load_role()
- **ref:** `recon:bind-role-action` · **books:** 10_scaling_enterprise
- **leverage:** Small, clean governance-event win; clears a B10 verify gap.
- **proposed reconciliation:** Emit a bind_role governance action class on load_role(); update Book 10 passage; pin to core.py.

## [MED] Structured Agent Brief / decision-handoff-protocol (with 'unknowns') as receipted artifact
- **ref:** `recon:agent-brief-artifact` · **books:** 02_executives_decisions, 03_leading_agents
- **leverage:** 2 books — delegation discipline as a versionable, receipted artifact type.
- **proposed reconciliation:** Receiptable Agent-Brief / handoff artifact (incl. 'what the agent does not know'); update Books 2/3; pin.

## [MED] Role Definition Matrix + layered domain roles (accountability-first)
- **ref:** `recon:role-matrix` · **books:** 03_leading_agents, 04_supply_chain, 08_manufacturing_ops
- **leverage:** 3 books — accountability-classified roles + domain layering on role_spec.
- **proposed reconciliation:** Extend role_spec with accountability class + domain layers (incl. non-overridable safety); update Books 3/4/8; pin to role_spec.

## [MED] Domain cockpit surfaces (Sales / Safety / Compliance / Governor / Ops)
- **ref:** `recon:domain-cockpits` · **books:** 07_sales_revenue, 08_manufacturing_ops, 06_compliance_audit, 09_multi_agent
- **leverage:** 4 books — Atrium domain lenses (UI-heavy); group + sequence after primitives land.
- **proposed reconciliation:** Atrium domain-lens framework; update the 4 books' surface passages; pin to atrium surfaces (next-edition).

## [MED] Data-subject access / individual transparency (HR)
- **ref:** `recon:data-subject-access` · **books:** 05_hr_talent
- **leverage:** Book 5 — controlled subject access; an ethics-critical HR gap.
- **proposed reconciliation:** Controlled data-subject access + no-suppression enforcement; update Book 5; pin.

## [MED] Component registry for reusable patterns (ARET template) + clean-room constraints
- **ref:** `recon:component-registry` · **books:** 09_multi_agent, 11_ma_due_diligence
- **leverage:** Reuse-case foundation (Book 9) + diligence clean-room (Book 11).
- **proposed reconciliation:** Versionable ARET template registry + clean-room/info-volume constraint primitives; update Books 9/11; pin.

∞Δ∞ Bidirectional reconciliation — book as source, code informs refinement, one gate. ∞Δ∞