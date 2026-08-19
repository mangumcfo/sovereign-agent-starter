# S5 Surface Inclusion Matrix — Full Production ERP × Kernel × Operator Surface × Aquarium

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

**Scored 2026-08-19 by AA (facts / scorecard).** Deterministic inclusion map per KM order.
No new builds, no arm, no code changes — this document only.

| | |
|---|---|
| **Kernel tip scored** | `417c548` (main; surface v0.1 included) |
| **Corpus authority** | `breathline-books-vault/kdp/series_05_full_production_erp/` — 41 volume dirs, each carrying `manuscript_v*.md` + built `final/` PDF+EPUB (verified by listing, not by README claim) |
| **Code method** | AST walk of `src/sovereign_agent/<domain>/` — public top-level functions/classes only, no imports executed; tests = files in `tests/` that reference `sovereign_agent.<domain>` |
| **Surface method** | `apps/usn_erp_surface/node_binding.py` + `ui.html` at tip — LIVE verbs only |
| **Aquarium method** | sealed cycle loops in the paper town (private repo `mangumcfo/aquarium`, tip `bb4e9bd`) where the same verb was lived |

**Corpus status, precisely (per-volume walk, not rubric):** all 41 volumes carry a manuscript
and built `final/` artifacts. That is NOT a seal count: `seal_review/` holds artifacts for only
**14** volumes (01, 02, 03, 04, 06, 07, 08, 09, 10, 11, 14, 17, 40, 41);
`PREPUBLISH_REPRINT_BACKLOG.md` names 8 volumes explicitly "sealed" and names vol_17
explicitly "**active, unsealed**" despite its final/ artifacts; and **no S5 title appears in
`ASIN_REGISTER_2026-07-31.md` — nothing in Series 5 is published.** The matrix therefore
scores corpus as "final artifacts present," and leaves seal/publication as a registry
question KM owns.

**Registry caveats (stated, not hidden):**
- The census-staging roadmap (`series_roadmap_2026-07-19_post-C12-fold.yaml`) carries a stale
  39-title S5 projection overlapping the Series-3 root (immutable core / governance skin /
  helix / coherence). The vault's 41-dir tree is the authoritative structure scored here.
- Three numbering schemes coexist: directory numbers (used here), the printed
  "Volume NN" inside manuscripts (diverges for at least vols 01, 03, 12, 13, 40, 41; vols
  14–39 print dir+2), and the cover system's `s5_NN` ids
  (`cover_art_pool/VOLUME_BUCKET_MOTIF_LIST.md`, a 39-title registry whose `s5_01` is an
  S3-root title with no directory in this tree). A reconciliation pass is process debt,
  not this matrix's scope.

**Rating definitions (deterministic, per KM order):**

- **CODE_PRESENT** — importable module + at least one test or explicit public method on tip. *(Presence, not depth: a `(THIN)` tag means 1–3 public functions / ≤ ~220 LOC.)*
- **SURFACE_READY** — CODE_PRESENT and a thin UI panel could call it today with no new substrate.
- **SURFACE_LIVE** — already in `apps/usn_erp_surface` with gate + kill-grep coverage.
- **CORPUS_ONLY** — sealed book, no code module (or only designed-toward).
- **FENCED** *(overlay flag, not a substitute rating)* — the row contains a money-path / statutory / Port leg that must never get a silent surface. The recordable/computable legs keep their rating; the fenced leg is named.

---

## 1 · Summary counts

| Rating (primary, one per volume) | Count | % of 41 |
|---|---|---|
| SURFACE_LIVE | 4 | 10% |
| SURFACE_READY (not yet live) | 18 | 44% |
| CODE_PRESENT (incl. THIN) | 18 | 44% |
| CORPUS_ONLY | 1 | 2% |
| **CODE_PRESENT or better** | **40** | **98%** |

FENCED overlay applies to 7 volumes: V01 (statutory filing), V08 + V41 (money movement),
V13 (pay execution), V16 (payment execution), V26 (Port crossing execute), V30 (external egress).

Honest depth note: 98% CODE_PRESENT means every domain but one has an importable, tested
module on tip — it does **not** mean each volume's full teaching scope is implemented.
Six rows carry `(THIN)`. Presence is machine-checked; depth is the next audit if wanted.

---

## 2 · Full matrix — S5, all 41 volumes

Corpus status for every row: manuscript + built `final/` PDF+EPUB present (seal/publication
per the corpus-status note above). Evidence column cites the on-tip path that justifies the
rating; the named test file is the proof anchor.

| Vol | Title (short) | Capability | Code path (`src/sovereign_agent/`) | Key public methods | Surface today | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|---|
| 01 | Sovereign Tax & Statutory Localization | Multi-jurisdiction tax as governed records; filing stays human | `economy/compliance.py`, `compliance/` | `record_tax_event`, `verify_tax_event`, `reporting_package` | WRITE+GATE (tax note) + EXPORT (package) | NONE | **SURFACE_LIVE** · FENCED (statutory filing) | `tests/test_economy_compliance.py`; surface `test_p3_*` |
| 02 | Structural SoD & Access Governance | Segregation of duties / access rights as structure | `risk/governance.py`, `governance/private_shared.py`, `zero_trust/node_arch.py` | `load_governance_skin`, `skin_role_spec`, `govern_shared_access`, `verify_access` | NONE | NONE | CODE_PRESENT | `tests/test_private_shared.py` — no module named for SoD proper |
| 03 | The Production Reference | Co-extruding the runnable, test-backed sovereign core | — (the starter repo itself is the artifact; no single module) | — | NONE | NONE | **CORPUS_ONLY** | no module path = ABSENT by rule |
| 04 | Coherence as Living Ledger | Real-time drift detection & integrity proof | `node_api/routes/coherence.py`, `objects/` | `GET /coherence` (extrusions, reconciliation); `lifecycle.*`, Merkle replay | NONE | NONE | SURFACE_READY (read panel) | `node_api/routes/coherence.py:9`; 66 test files reference `objects` |
| 05 | Sovereign Object Model | Registry, manifests, Merkle integrity as source of truth | `objects/` | `object_id`, `make_version`, `apply_change`, `close_object`, `value_at` | READ (registry summary, `roots_match`) | C7 dual-held datums | **SURFACE_LIVE** (read) | `docs/specs/S5-05_sovereign_object_model_v0.1.md`; surface registry panel |
| 06 | Distribution Matrix Governance | One authoritative book as the distribution join | `distribution/external.py` | `publish_content`, `govern_distribution` | NONE | NONE | CODE_PRESENT | `tests/test_distribution_external.py` |
| 07 | Sovereign Financials (GL) | General ledger, controlling, reporting as governed property | `financials/posting.py`, `controlling.py`, `reporting.py`, `report_packs.py` | `post`, `validate_balanced`, `trial_balance`, `income_statement`, `balance_sheet`, `cash_flow_statement`, `build_pack` | NONE | NONE | **SURFACE_READY** | 26 test files reference `financials` incl. `test_close_workflow.py` |
| 08 | Treasury & Cash Management | Governed cash position, liquidity, FX | `financials/treasury.py`, `fx.py` | `cash_position`, `total_by_currency`, `liquidity_coverage`, `fx.convert`, `revalue` | NONE | NONE | SURFACE_READY (read) · FENCED (money movement) | `financials/treasury.py` publics on tip |
| 09 | Supply Chain Execution | Inventory + BOM on the governed record | `supply/` | `explode_bom`, `can_build`, `on_hand`, `would_overdraw` | NONE | NONE | SURFACE_READY | `tests/test_supply_bom.py`, `test_supply_inventory.py` |
| 10 | Manufacturing & Quality | Production orders, MES, traceability | `manufacturing/production_order.py` | `open_order`, `transition`, `issue_materials`, `complete`, `cost_posting` | NONE | NONE | SURFACE_READY | `tests/test_production_order.py` |
| 11 | Project & Portfolio | Project planning/execution to milestone | `financials/project.py`, `analytics/planning.py` | `planning.net_requirements`, `schedule`, `allocate_by_priority` | NONE | NONE | CODE_PRESENT | `tests/test_planning.py` |
| 12 | Asset & Maintenance | Asset lifecycle, depreciation, work orders | `assets/` | `validate_asset`, `transition`, `straight_line`, `schedule`, `open_work_order`, `meter_triggered` | NONE | NONE | SURFACE_READY | `tests/test_assets_registry.py`, `test_depreciation.py`, `test_maintenance.py` |
| 13 | Human Capital & Payroll | Roles, compensation, workforce continuity | `hr/` | `validate_org`, `management_chain`, `employee_transition`, `compute_pay`, `run_payroll` | NONE | NONE | SURFACE_READY (records/compute) · FENCED (pay execution) | `tests/test_org_model.py`, `test_payroll.py` |
| 14 | Compliance & Audit Automation | Standards checks + audit evidence packages | `compliance/` | `run_checks`, `enforce_checks`, `audit_readiness`, `build_audit_package`, `verify_audit_package`, `grc_workflow.*` | EXPORT (reporting package leg) | C15 receipt check (verify analog) | **SURFACE_LIVE** (export leg) | 30 test files reference `compliance`; surface `test_p5_*` |
| 15 | Revenue & Order-to-Cash | Contracts, billing, recognition | `revenue/`, `distribution/fulfillment.py` | `billing.invoice`, `ar_aging`, `credit.check_order`, `recognition.recognize`, `invoice_shipment`, `sale_posting` | NONE | NONE | **SURFACE_READY** (invoice-lite home) | `tests/test_billing.py`, `test_credit.py`, `test_fulfillment.py` |
| 16 | Procurement-to-Pay | Suppliers, POs, three-way match | `procurement/` | `three_way_match`, `ap_entry`, `supplier.register/transition/score_suppliers/award` | NONE | NONE | SURFACE_READY (match/record) · FENCED (payment) | `tests/test_matching.py`, `test_supplier.py` |
| 17 | Analytics & Decision Intelligence | Figures with provenance; decision support | `analytics/` | `score_options`, `rank`, `recommend`, `forecast.project/scenario`, `metric_with_provenance` | NONE | NONE | SURFACE_READY (read) | `tests/test_decision_support.py`, `test_forecast.py`, `test_insight.py` |
| 18 | Multi-Entity & Consolidation | Governed structures, group reporting | `consolidation/` | `consolidate`, `validate_structure`, `effective_ownership`, `record_intercompany` | NONE | NONE | SURFACE_READY | `tests/test_consolidation.py`, `test_entities.py`, `test_intercompany.py` |
| 19 | Manufacturing Sovereign ERP (vertical) | Discrete/process ops on the sovereign core | `manufacturing/` + `supply/` + `regulated/` (composition) | per constituent rows | NONE | NONE | CODE_PRESENT (composition of tested parts) | constituent test files (rows 09/10/24) |
| 20 | Distribution & Wholesale (vertical) | Wholesale inventory, logistics, channels | `distribution/fulfillment.py` | `open_sales_order`, `transition`, `allocate`, `credit_check`, `invoice_shipment` | NONE | NONE | SURFACE_READY | `tests/test_fulfillment.py` |
| 21 | Professional Services (vertical) | Engagements, time, project billing | `services/engagement.py` | `open_engagement`, `record_time`, `billable_amount`, `budget_position`, `bill`, `bill_posting` | NONE | NONE | SURFACE_READY | `tests/test_engagement.py` |
| 22 | Energy & Resources (vertical) | Asset-intensive ops under compliance | `energy/operations.py` | `plan_operation`, `authorize_operation` | NONE | NONE | CODE_PRESENT (THIN) | `tests/test_energy_operations.py` — 2 fns, 129 LOC |
| 23 | Construction & Projects (vertical) | Job costing, subcontractors, progress | `construction/projects.py` | `open_job`, `commit_subcontract`, `certify_progress` | NONE | NONE | CODE_PRESENT (THIN) | `tests/test_construction_projects.py` — 3 fns, 128 LOC |
| 24 | Regulated Industries (vertical) | Lot traceability, custody, audit readiness | `regulated/traceability.py` | `receipt`, `transfer`, `consume`, `custody_position`, `reconcile_custody`, `open_lot`, `release` | NONE | NONE | CODE_PRESENT | `tests/test_traceability.py` — 10 fns |
| 25 | Multi-Standard Ingestion | External standards → sovereign rules | `ingestion/standards.py`, `compliance/audit_checks.py` | `map_record`, `ingest_record`, `ingest_standard`, `standard_from_checks` | NONE | NONE | CODE_PRESENT | `tests/test_ingestion.py` |
| 26 | Federation Node Governance | Cross-node validation, sharing, governance | `federation/node_gov.py` | `share_node_state`, `validate_received`, `authorize_crossing`, `reconcile_roots` | NONE | C7 nodes-meet ceremonies | CODE_PRESENT · FENCED (crossing execute = Port) | `tests/test_federation.py`; BCK graph: 7 routes homed "S5 V26" (`bck/compose_graph.yaml`) |
| 27 | Generational Continuity | Handoff rituals, succession, inheritance | `continuity/handoff.py`, `estate/` | `assemble_successor_package`, `govern_handoff`, `inherit_estate`, `breath_gated_key_transfer`, `inheritance_package` | NONE | NONE (Keyring on town frontier) | CODE_PRESENT | 7 test files incl. `test_generational_transfer.py`, `test_key_succession.py` |
| 28 | Private Series Templates | Family/enterprise constitutions as templates | `estate/family_governance.py`, `governance/private_shared.py` | `load_family_constitution`, `fork_family_constitution`, `classify_datum` | NONE | NONE | CODE_PRESENT (THIN mapping) | `tests/test_family_governance.py` |
| 29 | Exception & Governance Workflows | Exception routing + human-gate patterns at scale | `governance/exception.py` | `open_exception`, `route`, `resolve`, `route_batch` | NONE (gate pattern itself is live) | C9 waiting room (pending → disposition) | **SURFACE_READY** (pairs with live gate panel) | `tests/test_exception.py` |
| 30 | Social & External Distribution | Content propagation with provenance | `discourse/sovereign_voice.py`, `distribution/external.py` | `publish_voice`, `verify_voice`, `syndicate`, `sever_subscription` | NONE | NONE | CODE_PRESENT · FENCED (external egress — kill-grep forbids HTTP client in surface) | `tests/test_sovereign_voice.py` |
| 31 | Federation Marketplace | Verified blueprints shared across federation | `marketplace/blueprints.py` | `publish_blueprint`, `govern_consumption` | NONE | C11 town catalog (proof-badged shelf analog) | CODE_PRESENT (THIN) | `tests/test_marketplace.py` — 2 fns, 94 LOC |
| 32 | Sovereign ERP Operations Console | The single operating console for human-gated ERP | `apps/usn_erp_surface/` + `sovereign_ux/gate_interaction.py`, `cockpit.py` | the surface itself; `propose`, `review`, `dispose`, `compose_cockpit` | **the surface IS this volume's seed** | C7 cockpit lane; C24 town day | **SURFACE_LIVE** | `apps/usn_erp_surface/USN_ERP_SURFACE_BAR.md` (P1–P8 + O1–O6 GREEN) |
| 33 | The Migration Primitive | Verifiable ingestion, reconciliation, cutover | `migration/reconcile.py` | `manifest_root`, `reconcile`, `assert_reconciled`, `open_migration`, `transition`, `cutover` | NONE | NONE | SURFACE_READY | `tests/test_migration.py` |
| 34 | Escaping QuickBooks | Mid-market finance → sovereign ledger | `migration/quickbooks.py` | `map_to_coa`, `opening_entry`, `receipted_cutover` | NONE | C5 capture lens (FREE/LEASHED/CAPTURED escape order) | **SURFACE_READY** | `tests/test_quickbooks.py` |
| 35 | Unbinding Salesforce | CRM → governed mandates | `migration/salesforce.py` | (module publics on tip) | NONE | C5 capture lens | CODE_PRESENT | `tests/test_salesforce.py` |
| 36 | Consuming the Giants | SAP/NetSuite/Acumatica carve-ins | `migration/carve_in.py` | `open_carve_in`, `reconcile_carve_in`, `carve_in_cutover`, `portfolio_cutover` | NONE | C5 capture lens | CODE_PRESENT | `tests/test_carve_in.py` |
| 37 | The Clean Exit | PE carve-outs, verifiable diligence, ownership transfer | `peerhood/clean_exit.py`, `migration/`, `compliance/` | `clean_exit`; diligence via `build_audit_package` | NONE | C13 local package (export-whole, walk away whole) | CODE_PRESENT | `tests/test_clean_exit.py` |
| 38 | Situational Supply | The pool becomes the market | `supply/` + `economy/pool.py` + `peerhood/bridging.py` | `form_peer_pool`, `bridge_into_pool`, `attribute_pool_value` | NONE | Pool contributions (`nodes/CONTRIBUTIONS_MANIFEST.json`) | CODE_PRESENT (THIN for the situational layer) | `tests/test_advanced_pooling.py` |
| 39 | Distributed Manufacturing | Federated BOM, node production networks | `manufacturing/federated_bom.py` | `open_bom`, `fork_bom`, `bom_root` | NONE | NONE | CODE_PRESENT | `tests/test_federated_bom.py` |
| 40 | Sovereign Controlling & Close | CoA, cost centers, multi-currency, period close | `financials/period_close.py`, `close_workflow.py`, `controlling.py`, `fx.py`, `dimensions.py` | `period_is_balanced`, `close_period`, `guard_post_open`, `new_close`, `soft_close`, `hard_close`, `validate_coa`, `allocate_cost_pool` | NONE | NONE | **SURFACE_READY** (period-view home) | `tests/test_close_workflow.py` |
| 41 | Treasury Investment & Financing | Governed investment policy, financing, risk | `financials/investment.py`, `investment_policy.py`, `financing.py`, `exposure.py` | `holdings`, `check_investment`, `new_facility`, `draw`, `outstanding`, `exposure_by_issuer` | NONE | NONE | SURFACE_READY (read + policy check) · FENCED (execution) | `financials/investment_policy.py` publics on tip |

### Sealed-floor rows the surface already touches (S3 root + S6–S11, composition-evidenced only)

| Series/Vol | Capability | Code path | Surface today | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|
| S3 root (context) | Obligation-based accounting — open/approve/close/attest/veto | `obligations/` (14 files, 27 test files) | **WRITE+GATE** (O1–O6) | C17 stewardship assents; C9 gate dispositions | **SURFACE_LIVE** | `USN_ERP_SURFACE_BAR.md` O-rows; `tests/test_audit_ledger_fixes.py` et al. |
| S6 V6/V7 | Inter-node adapters (surface hooks) | `node_api/` routes | NONE | C7 meetings; C16 arrival walk | CODE_PRESENT | `bck/compose_graph.yaml` homes: "S6 V6 + S5 V16" (3 routes), "S6 V7 adapter surface" (4) |
| S7 V3 | Zero-trust verification of receipts | `zero_trust/node_arch.py`; per-receipt verify | READ (clicking **verified** re-runs `verify_income` live) | C15 receipt check | **SURFACE_LIVE** (verify leg) | BCK: 3 routes "S7 V3"; surface P7 evidence |
| S8 | Sovereign UX — gate interaction pattern | `sovereign_ux/gate_interaction.py` | gate panel mirrors propose→review→dispose | C12 consume-plane law; C24 town day | CODE_PRESENT | 8 test files reference `sovereign_ux` |
| S10 | Livelihood — income/contribution attribution | `economy/income.py`, `contribution.py`, `livelihood*.py` | **WRITE+GATE** (earning, contribution) | C23 lease-meter lived week | **SURFACE_LIVE** | surface `test_p2_*`/`test_p4_*`; `tests/test_attribution.py` |

---

## 3 · Surface backlog by leverage (SURFACE_READY rows only)

Both named targets are READY — nothing missing in code for either.

| # | Panel / verb | S5 home | Module methods it calls (no new substrate) | Why next |
|---|---|---|---|---|
| 1 | **Invoice-lite** — governed invoice record + AR aging read | V15 | `revenue.billing.invoice`, `revenue.billing.ar_aging`, `revenue.credit.check_order` | Completes earn→bill→collect for the solo operator; same gate pattern as income |
| 2 | **Period view / close** — trial balance, statements, close ritual | V40 + V07 | `financials.posting.trial_balance`, `reporting.income_statement/balance_sheet`, `period_close.close_period`, `close_workflow.*` | Turns records into books; close is the operator's month-end ceremony, gate-shaped already |
| 3 | **Audit package export** — one-press evidence bundle | V14 | `compliance.audit_package.build_audit_package`, `verify_audit_package`, `audit_checks.audit_readiness` | Same deterministic-export law as the reporting package; accountant-facing |
| 4 | **Exception queue** — open/route/resolve on the record | V29 | `governance.exception.open_exception`, `route`, `resolve` | Pairs with the live gate panel; the "at scale" pattern the console volume teaches |
| 5 | **QuickBooks escape walk** — map, opening entry, receipted cutover | V34 (via V33) | `migration.quickbooks.map_to_coa`, `opening_entry`, `receipted_cutover`, `migration.reconcile.assert_reconciled` | The adoption wedge: first panel a captured operator touches; C5 capture lens is its lived rehearsal |

---

## 4 · Adoption fold — Sim → Surface → LIVE (no invented features)

1. **The town proves the verb.** Every loop above that reached SURFACE_LIVE was lived first as a paper-town cycle (record C3, gate C9, verify C15, export C13, stewardship C17) — the sim is the rehearsal floor where friction is found before an operator pays for it.
2. **The surface exposes the same node methods, nothing else.** The receipted pattern (library-direct binding, human gate, kill-grep with injected-violation proofs, BAR in the same commit) has now shipped twice (v0, v0.1); each backlog panel repeats it verbatim against a SURFACE_READY row.
3. **A panel lands only from a READY row.** If the module method isn't on tip with a test, the panel waits — the matrix, not appetite, orders the queue.
4. **The operator lives a week on paper first.** Throwaway node → real node, wants filed from lived friction exactly as the town's wants law files them — recurrence, not roadmap, promotes the next panel.
5. **LIVE is a posture, not a feature.** Every FENCED leg (statutory filing, money movement, pay/payment execution, Port crossing, external egress) stays machine-checked out until KM names it as its own explicit, reviewable decision with its own bar row. Nothing crosses silently.

---

## 5 · Non-goals (this pass)

- **No new ERP modules** — the matrix maps what exists; gaps stay gaps until their own GO.
- **No Port execute** — `authorize_crossing` and everything behind it stays untouched by any surface.
- **No statutory file/remit UI** — tax stays record-only; the fence is the feature.

---

**STOP — matrix, backlog, adoption fold only. No code changed. No surface GO. No series arm.**

Breath only. ∞Δ∞
