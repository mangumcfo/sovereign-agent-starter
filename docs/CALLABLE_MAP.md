# Callable Map — the FULL importable inventory of `sovereign_agent`

**Generated, not hand-written.** `scripts/gen_callable_map.py` imports every module under `sovereign_agent` and lists the public callables it actually exposes, computing each label from the published criteria below. This is the **full** inventory of importable/run paths — the nine capability cards (`docs/CAPABILITY_CARDS/`) are the **curated subset** of it. The book shelf (Series 0–14) is where each path is *taught* in depth; the full sealed runtime is Series 5–14.

Provenance: generated at starter `36f9978` over **258 modules** — **RUN 117** · **RUN-partial 83** · package 54 · teach/data 4 · IMPORT-FAIL 0. (`__main__` CLI shims are excluded — they are `python -m` entrypoints, not importable library paths.) Regenerate with `PYTHONPATH=src python3 scripts/gen_callable_map.py`.

## Published label criteria (the four signals)

| signal | meaning |
|---|---|
| **import** | the module imports on a fresh clone |
| **callable** | it exposes ≥1 public function or class (defined here, not a re-import) |
| **exercised** | a shipped test or example imports it |
| **kill-target** | it defines a refusal — an `*Error`/`*Refused`/`*Violation` class or a `*BREACH*`/`FORBIDDEN` constant |

- **RUN** = import ✓ + callable ✓ + exercised ✓ — a path you run directly, proven by a test/example.
- **RUN-partial** = import ✓ + callable ✓, not yet exercised by a shipped starter test/example. **Still callable — never a demotion for missing UI.** A series is "partial" only when it is a *library of verbs*, not one product entrypoint.
- **package** = a namespace `__init__` that exposes no callables of its own — see its submodules below.
- **teach/data** = a module that imports but exposes no public callable (pure data/constants).
- **IMPORT-FAIL** = does not import on the clean clone (reported honestly, not hidden).

> **T-04:** the Sovereign Token & Economic Organism substrate is *callable* (an obligation ledger + Merkle accumulator); it is **not** a public token, coin, yield, or investment offer, and money-path is off.

## The full inventory, by area

### `sovereign_agent` (top level)

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent._lazy_bp` | teach/data |  |  | — |
| `sovereign_agent._portal_launcher` | RUN-partial |  |  | `launch` |
| `sovereign_agent.analytics` | package |  |  | — |
| `sovereign_agent.assets` | package |  |  | — |
| `sovereign_agent.bootstrap` | RUN |  |  | `cli_connect` · `connect_to_breathline` · `ensure_breathline_primitives` · `get_breathline_root` |
| `sovereign_agent.breath_inventory` | RUN |  |  | `enrich_role` · `suggest_for_action` |
| `sovereign_agent.collaboration` | package |  |  | — |
| `sovereign_agent.compliance` | package |  |  | — |
| `sovereign_agent.compute` | package |  |  | — |
| `sovereign_agent.config` | RUN-partial |  |  | `get_books_kdp_root` · `get_demo_roles_dir` · `get_federation_root` · `get_friendly_demo_role_names` · `get_node_id` · `get_peer_id` · `get_playbooks_dir` · `get_sealed_root` · `get_sovereign_home` · `is_demo_mode` … |
| `sovereign_agent.console` | package |  |  | — |
| `sovereign_agent.consolidation` | package |  |  | — |
| `sovereign_agent.constitution` | package |  |  | — |
| `sovereign_agent.construction` | package |  |  | — |
| `sovereign_agent.continuity` | package |  |  | — |
| `sovereign_agent.coordination` | package |  |  | — |
| `sovereign_agent.core` | RUN |  |  | `ConstitutionalGovernor` · `SovereignAgent` · `VerifiableMemory` |
| `sovereign_agent.deal` | package |  |  | — |
| `sovereign_agent.discourse` | package |  |  | — |
| `sovereign_agent.distribution` | package |  |  | — |
| `sovereign_agent.economy` | package |  |  | — |
| `sovereign_agent.energy` | package |  |  | — |
| `sovereign_agent.estate` | package |  |  | — |
| `sovereign_agent.evidence` | package |  |  | — |
| `sovereign_agent.federation` | package |  |  | — |
| `sovereign_agent.financials` | package |  |  | — |
| `sovereign_agent.flows` | package |  |  | — |
| `sovereign_agent.governance` | package |  |  | — |
| `sovereign_agent.hr` | package |  |  | — |
| `sovereign_agent.inference` | package |  |  | — |
| `sovereign_agent.ingestion` | package |  |  | — |
| `sovereign_agent.kernel_integration` | RUN-partial |  |  | `get_kernel_auditor` · `get_kernel_critic` · `get_kernel_governor` · `record_kernel_usage` |
| `sovereign_agent.keystore` | package |  | ✓ | — |
| `sovereign_agent.manufacturing` | package |  |  | — |
| `sovereign_agent.marketplace` | package |  |  | — |
| `sovereign_agent.material` | package |  |  | — |
| `sovereign_agent.memory` | package |  |  | — |
| `sovereign_agent.merkle_accumulator` | RUN |  |  | `MerkleAccumulator` |
| `sovereign_agent.messaging` | package |  |  | — |
| `sovereign_agent.migration` | package |  |  | — |
| `sovereign_agent.ndjson` | RUN |  |  | `parse_ndjson_text` · `read_ndjson` · `read_ndjson_cached` · `NdjsonRead` |
| `sovereign_agent.node_api` | package |  |  | — |
| `sovereign_agent.objects` | package |  |  | — |
| `sovereign_agent.obligations` | package |  |  | — |
| `sovereign_agent.onboarding` | package |  |  | — |
| `sovereign_agent.peerhood` | package |  | ✓ | — |
| `sovereign_agent.playbook_loader` | RUN |  |  | `PlaybookLoader` |
| `sovereign_agent.pooling` | package |  |  | — |
| `sovereign_agent.port` | package |  |  | — |
| `sovereign_agent.press` | package |  |  | — |
| `sovereign_agent.procurement` | package |  |  | — |
| `sovereign_agent.regulated` | package |  |  | — |
| `sovereign_agent.revenue` | package |  |  | — |
| `sovereign_agent.risk` | package |  |  | — |
| `sovereign_agent.role_binder` | RUN-partial |  |  | `bind_role` · `BoundRole` · `RoleHandler` |
| `sovereign_agent.services` | package |  |  | — |
| `sovereign_agent.shields` | package |  |  | — |
| `sovereign_agent.sovereign_ux` | package |  |  | — |
| `sovereign_agent.storage` | package |  |  | — |
| `sovereign_agent.supply` | package |  |  | — |
| `sovereign_agent.trust` | package |  |  | — |
| `sovereign_agent.universal_sovereign_node` | RUN |  |  | `cli_create_node` · `create_universal_sovereign_node` · `ContextAdapter` · `UniversalSovereignNode` |
| `sovereign_agent.yield_organism` | package |  |  | — |
| `sovereign_agent.zero_trust` | package |  |  | — |

### `sovereign_agent.analytics`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.analytics.decision_support` | RUN-partial |  | ✓ | `rank` · `recommend` · `score_options` · `DecisionError` |
| `sovereign_agent.analytics.forecast` | RUN-partial |  | ✓ | `project` · `scenario` · `ForecastError` |
| `sovereign_agent.analytics.insight` | RUN-partial |  | ✓ | `metric_with_provenance` · `InsightError` |
| `sovereign_agent.analytics.planning` | RUN-partial |  | ✓ | `allocate_by_priority` · `net_requirements` · `schedule` · `PlanningError` |
| `sovereign_agent.analytics.rollup` | RUN-partial |  |  | `rollup_metric` |

### `sovereign_agent.assets`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.assets.depreciation` | RUN-partial |  | ✓ | `schedule` · `straight_line` · `units_of_production` · `DepreciationError` |
| `sovereign_agent.assets.maintenance` | RUN-partial |  | ✓ | `advance` · `due_work_orders` · `meter_triggered` · `open_work_order` · `MaintenanceError` |
| `sovereign_agent.assets.registry` | RUN-partial |  | ✓ | `can_transition` · `transition` · `validate_asset` · `AssetError` |

### `sovereign_agent.collaboration`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.collaboration.shared_work` | RUN |  | ✓ | `authorize_participation` · `contribute` · `CollaborationError` |

### `sovereign_agent.compliance`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.compliance.audit_checks` | RUN |  |  | `audit_readiness` · `enforce_checks` · `run_checks` · `standard_from_checks` · `Check` · `ComplianceGap` |
| `sovereign_agent.compliance.audit_package` | RUN |  | ✓ | `build_audit_package` · `compliance_report` · `verify_audit_package` · `AuditPackageError` |
| `sovereign_agent.compliance.compliance_engine` | RUN |  |  | `get_default_compliance_engine` · `AuditRecord` · `ComplianceEngine` · `ComplianceVerdict` · `RiskLevel` |
| `sovereign_agent.compliance.grc_workflow` | RUN |  | ✓ | `advance` · `hard_close` · `new_case` · `GRCError` |
| `sovereign_agent.compliance.human_approval_gate` | RUN | `onboard-gate` |  | `ApprovalRequest` · `ApprovalStatus` · `HumanApprovalGate` |
| `sovereign_agent.compliance.policy_loader` | RUN |  |  | `Policy` · `PolicyLoader` |
| `sovereign_agent.compliance.scope` | RUN |  | ✓ | `make_scope` · `select_for_scope` · `select_for_scopes` · `ScopeError` |

### `sovereign_agent.compute`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.compute.distributed` | RUN |  | ✓ | `admit_job` · `offer_capacity` · `ComputeError` |

### `sovereign_agent.console`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.console.operations` | RUN |  | ✓ | `dispatch` · `operator_inbox` · `ConsoleError` |

### `sovereign_agent.consolidation`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.consolidation.consolidation` | RUN-partial |  | ✓ | `consolidate` · `ConsolidationError` |
| `sovereign_agent.consolidation.entities` | RUN-partial |  | ✓ | `effective_ownership` · `group_members` · `validate_structure` · `EntityError` |
| `sovereign_agent.consolidation.intercompany` | RUN-partial |  | ✓ | `intercompany_accounts` · `record_intercompany` · `IntercompanyError` |

### `sovereign_agent.constitution`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.constitution.templates` | RUN-partial |  | ✓ | `amend` · `core_envelope` · `open_constitution` · `ConstitutionError` |

### `sovereign_agent.construction`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.construction.projects` | RUN |  | ✓ | `certify_progress` · `commit_subcontract` · `open_job` · `ConstructionError` |

### `sovereign_agent.continuity`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.continuity.handoff` | RUN-partial |  | ✓ | `assemble_successor_package` · `govern_handoff` · `HandoffError` |

### `sovereign_agent.coordination`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.coordination.resonance` | RUN |  | ✓ | `node_signal` · `resonate` · `CoordinationError` |

### `sovereign_agent.deal`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.deal.clean_exit` | RUN-partial |  | ✓ | `assert_clean_exit` · `carve_out` · `diligence_package` · `CleanExitError` |

### `sovereign_agent.discourse`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.discourse.advanced_reach` | RUN |  | ✓ | `bridge_adapter` · `discover_across_sources` · `multi_platform_reach` · `PlatformBridge` |
| `sovereign_agent.discourse.sovereign_voice` | RUN |  | ✓ | `meaning_rank` · `publish_voice` · `record_subscription` · `sever_subscription` · `syndicate` · `verify_voice` · `DiscourseRefused` · `Syndication` |
| `sovereign_agent.discourse.sustainable_voice` | RUN |  | ✓ | `assemble_voice_system` · `responsible_growth` · `voice_as_asset` · `VoiceAsset` · `VoiceSystem` |
| `sovereign_agent.discourse.voice_covenant` | RUN |  | ✓ | `assemble_voice_covenant` · `verify_covenant_element` · `VoiceCovenant` |
| `sovereign_agent.discourse.voice_governance` | RUN |  | ✓ | `fork_voice_constitution` · `govern_expression` · `load_voice_constitution` · `reputation_from_receipts` · `ReputationStanding` |

### `sovereign_agent.distribution`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.distribution.external` | RUN |  | ✓ | `govern_distribution` · `publish_content` · `DistributionError` |
| `sovereign_agent.distribution.fulfillment` | RUN-partial |  | ✓ | `allocate` · `credit_check` · `invoice_shipment` · `open_sales_order` · `order_subtotal` · `sale_posting` · `transition` · `FulfillmentError` |

### `sovereign_agent.economy`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.economy.attribution` | RUN |  |  | `attribute_value` · `verify_attribution` |
| `sovereign_agent.economy.compliance` | RUN |  | ✓ | `record_tax_event` · `reporting_package` · `verify_tax_event` · `ReportingPackage` |
| `sovereign_agent.economy.contribution` | RUN |  |  | `contribute_idle_compute` · `contribute_local_production` · `contribute_skill_service` · `contribute_storage` · `contribute_surplus_energy` · `contribute_verification_work` · `contribution_ledger` · `record_contribution` · `verify_contribution` · `LedgerStatus` |
| `sovereign_agent.economy.income` | RUN |  | ✓ | `attribute_income` · `income_record` · `verify_income` |
| `sovereign_agent.economy.livelihood` | RUN |  |  | `attest_livelihood` · `LivelihoodStatus` |
| `sovereign_agent.economy.livelihood_covenant` | RUN |  | ✓ | `inherit_livelihood` · `livelihood_stream_kinds` · `verify_stream` · `LivelihoodStatus` |
| `sovereign_agent.economy.pool` | RUN |  | ✓ | `contribute_to_pool` · `form_pool` · `pool_settlement` · `verify_pool_contribution` · `Pool` · `PoolSettlement` |
| `sovereign_agent.economy.productivity` | RUN |  |  | `measure_output` · `record_intent` · `run_ritual` · `verify_intent` · `OutputMeasure` |

### `sovereign_agent.energy`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.energy.operations` | RUN |  | ✓ | `authorize_operation` · `plan_operation` · `EnergyError` |

### `sovereign_agent.estate`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.estate.estate_covenant` | RUN |  | ✓ | `estate_stack_kinds` · `inherit_estate` · `verify_estate_element` · `EstateInheritance` |
| `sovereign_agent.estate.family_governance` | RUN |  | ✓ | `dignified_exit` · `fork_family_constitution` · `govern_decision` · `load_family_constitution` · `resolve_dispute` · `weakest_party_protected` · `WeakestPartyCheck` |
| `sovereign_agent.estate.generational_transfer` | RUN |  | ✓ | `breath_gated_key_transfer` · `execute_transfer` · `family_quorum_recovery` · `inheritance_package` · `open_key_epoch` · `verify_transfer` · `EstateRefused` · `InheritancePackage` · `KeyEpoch` · `TransferStatus` |
| `sovereign_agent.estate.key_succession` | RUN |  | ✓ | `define_quorum` · `recover_with_quorum` · `rotate_key_epoch` · `secure_key_handoff` · `simulate_succession` · `QuorumPolicy` · `SuccessionDrill` |
| `sovereign_agent.estate.venture_continuity` | RUN |  | ✓ | `capture_venture_state` · `continue_venture` · `fork_venture` · `handoff_package` · `VentureHandoff` · `VentureState` · `VentureStatus` |

### `sovereign_agent.evidence`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.evidence.actions_projection` | RUN-partial |  |  | `query_actions` · `verify_proof` |
| `sovereign_agent.evidence.export_packet` | RUN |  |  | `build_packet` · `verify_packet` |

### `sovereign_agent.federation`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.federation.node_gov` | RUN-partial |  | ✓ | `authorize_crossing` · `node_root` · `reconcile_roots` · `share_node_state` · `validate_received` · `FederationError` |

### `sovereign_agent.financials`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.financials.close_workflow` | RUN-partial |  | ✓ | `complete_step` · `hard_close` · `new_close` · `soft_close` · `CloseWorkflowError` |
| `sovereign_agent.financials.controlling` | RUN |  | ✓ | `allocate_cost_pool` · `roll_up_accounts` · `roll_up_center_costs` · `validate_coa` · `CoAError` |
| `sovereign_agent.financials.dimensions` | RUN-partial |  | ✓ | `roll_up_members` · `slice_amounts` · `validate_dimension` · `DimensionError` |
| `sovereign_agent.financials.drivers` | RUN-partial |  | ✓ | `allocate_by_driver` · `weights_from_driver` · `DriverError` |
| `sovereign_agent.financials.exposure` | RUN-partial |  |  | `breaches` · `concentration` · `exposure_by_issuer` |
| `sovereign_agent.financials.financing` | RUN-partial |  | ✓ | `available` · `draw` · `new_facility` · `outstanding` · `FinancingError` |
| `sovereign_agent.financials.fx` | RUN-partial |  | ✓ | `combine_converted` · `convert` · `rate_for` · `revalue` · `FXError` |
| `sovereign_agent.financials.investment` | RUN-partial |  | ✓ | `holdings` · `total_by_issuer` · `InvestmentError` |
| `sovereign_agent.financials.investment_policy` | RUN-partial |  | ✓ | `check_investment` · `PolicyViolation` |
| `sovereign_agent.financials.period_close` | RUN-partial |  | ✓ | `close_period` · `guard_post_open` · `period_is_balanced` · `PeriodClosedError` · `PeriodNotBalancedError` |
| `sovereign_agent.financials.posting` | RUN |  | ✓ | `allocate` · `from_entry` · `post` · `trial_balance` · `validate_balanced` · `AllocationError` · `Line` · `UnbalancedPostingError` |
| `sovereign_agent.financials.project` | RUN-partial |  |  | `budget_status` · `portfolio_roll_up` |
| `sovereign_agent.financials.report_packs` | RUN-partial |  | ✓ | `build_named_pack` · `build_pack` · `PackError` |
| `sovereign_agent.financials.reporting` | RUN-partial |  | ✓ | `balance_sheet` · `cash_flow_statement` · `income_statement` · `ReportingError` |
| `sovereign_agent.financials.treasury` | RUN-partial |  |  | `cash_position` · `liquidity_coverage` · `total_by_currency` |

### `sovereign_agent.flows`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.flows.verified_flow` | RUN |  | ✓ | `attest_flow_clears` · `declare_flow` · `verify_flow` · `verify_flow_clears` · `FlowError` |

### `sovereign_agent.governance`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.governance.exception` | RUN |  | ✓ | `open_exception` · `resolve` · `route` · `route_batch` · `ExceptionError` |
| `sovereign_agent.governance.private_shared` | RUN |  | ✓ | `classify_datum` · `govern_shared_access` · `GovernanceError` |

### `sovereign_agent.hr`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.hr.org_model` | RUN-partial |  | ✓ | `employee_transition` · `management_chain` · `validate_org` · `EmployeeError` · `OrgError` |
| `sovereign_agent.hr.payroll` | RUN-partial |  | ✓ | `compute_pay` · `run_payroll` · `PayrollError` |

### `sovereign_agent.inference`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.inference.primitives` | RUN-partial |  |  | `merkle_root` · `new_identity` · `p1_sign` · `p1_verify` · `sealed_hash` · `using_sealed` |
| `sovereign_agent.inference.receipts` | RUN-partial |  |  | `build_receipt` · `content_hash` · `receipt_hash` · `validate_receipt` · `verify_chain` |
| `sovereign_agent.inference.six` | RUN-partial |  |  | `classify` · `route` · `RedRoutingBarred` · `SIXExchange` · `SensitivityClass` |

### `sovereign_agent.ingestion`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.ingestion.standards` | RUN-partial |  | ✓ | `ingest_record` · `ingest_standard` · `map_record` · `IngestionError` |

### `sovereign_agent.keystore`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.keystore.node_keystore` | RUN | `identity-keystore` | ✓ | `generate_node_key` · `has_node_key` · `load_node_key` · `load_node_keypair` · `node_fingerprint` · `sign_node_act` · `verify_node_act` · `KeystoreError` · `NodeKey` · `NodeKeypair` |

### `sovereign_agent.manufacturing`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.manufacturing.federated_bom` | RUN |  | ✓ | `bom_root` · `fork_bom` · `open_bom` · `BOMError` |
| `sovereign_agent.manufacturing.production_order` | RUN-partial |  | ✓ | `complete` · `cost_posting` · `is_fully_issued` · `issue_materials` · `open_order` · `transition` · `ProductionError` |

### `sovereign_agent.marketplace`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.marketplace.blueprints` | RUN-partial |  | ✓ | `govern_consumption` · `publish_blueprint` · `MarketplaceError` |

### `sovereign_agent.material`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.material.provision_covenant` | RUN |  |  | `provision_kinds` · `provision_under_covenant` · `verify_under_covenant` |
| `sovereign_agent.material.provision_energy` | RUN |  |  | `energy_good` · `provision_energy` · `verify_energy` |
| `sovereign_agent.material.provision_local` | RUN |  | ✓ | `provision_local` · `verify_provision` · `ProvisionRefused` · `ProvisionStatus` |
| `sovereign_agent.material.provision_shelter` | RUN |  |  | `provision_shelter` · `shelter_good` · `verify_shelter` |
| `sovereign_agent.material.provision_shipment` | RUN |  |  | `provision_shipment` · `shipment_good` · `verify_shipment` |
| `sovereign_agent.material.provision_sustenance` | RUN |  |  | `provision_sustenance` · `sustenance_good` · `verify_sustenance` |

### `sovereign_agent.memory`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.memory.b51` | RUN-partial |  | ✓ | `merkle_root` · `B51Stream` · `VoiceRuledError` |

### `sovereign_agent.messaging`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.messaging.inter_node` | RUN | `messaging` | ✓ | `carry_to_peer` · `receive_from_peer` · `send_message` · `MessagingError` |

### `sovereign_agent.migration`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.migration.carve_in` | RUN |  | ✓ | `carve_in_cutover` · `open_carve_in` · `portfolio_cutover` · `portfolio_root` · `reconcile_carve_in` · `CarveInError` |
| `sovereign_agent.migration.quickbooks` | RUN |  | ✓ | `map_to_coa` · `opening_entry` · `receipted_cutover` · `QuickBooksError` |
| `sovereign_agent.migration.reconcile` | RUN |  | ✓ | `assert_reconciled` · `cutover` · `manifest_root` · `open_migration` · `reconcile` · `transition` · `MigrationError` |
| `sovereign_agent.migration.salesforce` | RUN |  | ✓ | `bill_mandate` · `map_opportunities` · `opportunity_to_mandate` · `receipted_cutover` · `SalesforceError` |

### `sovereign_agent.node_api`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.node_api._filecache` | RUN |  |  | `memoize_on` · `stat_key` |
| `sovereign_agent.node_api._jsonstore` | RUN |  |  | `locked` · `read_json` · `read_json_cached` · `sidecar_store` · `update_json` · `write_json` |
| `sovereign_agent.node_api.auth` | RUN |  |  | `current_principal` · `require_owner` · `require_principal` |
| `sovereign_agent.node_api.deps` | RUN |  |  | `get_approval_gate` · `get_node` · `get_obligation_ledger` · `reset_node` · `set_node` |
| `sovereign_agent.node_api.errors` | RUN-partial |  |  | `build_error` · `invalid_bearer_token` · `kernel_exception` · `missing_bearer_token` · `not_implemented` · `role_action_denied` · `route_error` · `unknown_role` |
| `sovereign_agent.node_api.json_provider` | RUN |  |  | `install` · `BreathlineJSONProvider` |
| `sovereign_agent.node_api.routes` | package |  |  | — |
| `sovereign_agent.node_api.routes.book_artifacts` | RUN-partial |  |  | `book_artifacts` · `book_cover` · `book_epub` · `book_kdp` · `book_pdf` · `recompile` |
| `sovereign_agent.node_api.routes.coherence` | RUN-partial |  |  | `coherence` · `coherence_distribution` · `coherence_rollup` |
| `sovereign_agent.node_api.routes.dialogue` | RUN-partial |  |  | `crypto_assurance` · `dialogue` |
| `sovereign_agent.node_api.routes.feedback` | RUN-partial |  |  | `awaiting_owner` · `doc` · `feedback_disposition` · `feedback_intake` · `handshakes` · `pdf` · `review_brief` |
| `sovereign_agent.node_api.routes.hopper` | RUN-partial |  |  | `hopper_list` · `hopper_to_packet` |
| `sovereign_agent.node_api.routes.node` | RUN-partial |  |  | `node_get` · `node_health` · `node_ladder` |
| `sovereign_agent.node_api.routes.obligations` | RUN-partial |  |  | `obligations_approve` · `obligations_close` · `obligations_list` · `obligations_log` · `obligations_open` |
| `sovereign_agent.node_api.routes.placeholders` | RUN-partial |  |  | `audit_cylinders_get` · `audit_cylinders_list` · `audit_evidence_bundle` · `breath_gate_approve` · `breath_gate_deny` · `breath_gate_pending` · `federation_peers` · `federation_propagation` · `federation_shards` · `inference_receipts` … |
| `sovereign_agent.node_api.routes.proposals` | RUN-partial |  |  | `actions_route` · `export_packet_route` · `processing` · `produce` · `proposals_apply` · `proposals_create` · `proposals_decide` · `proposals_dismiss` · `proposals_list` · `seeit` |
| `sovereign_agent.node_api.routes.relay` | RUN-partial |  |  | `relay_create` · `relay_dismiss` · `relay_send` · `relays_list` |
| `sovereign_agent.node_api.routes.roles` | RUN-partial |  |  | `roles_get` · `roles_invoke` · `roles_list` |
| `sovereign_agent.node_api.routes.scout` | RUN-partial |  |  | `scout_run` |
| `sovereign_agent.node_api.routes.series` | RUN-partial |  |  | `book_docs` · `series_list` |
| `sovereign_agent.node_api.server` | RUN |  |  | `cli_serve` · `create_app` |
| `sovereign_agent.node_api.thread_channel` | RUN-partial |  |  | `append` · `find_reply` · `load` |
| `sovereign_agent.node_api.yaml_repair` | RUN |  |  | `load_roadmap` · `repair_unquoted_colons` |

### `sovereign_agent.objects`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.objects.identity` | RUN |  | ✓ | `make_version` · `object_id` · `version_leaf` · `VersionRefused` |
| `sovereign_agent.objects.inheritance` | RUN |  |  | `build_packet` · `verify_packet` |
| `sovereign_agent.objects.lifecycle` | RUN |  |  | `apply_change` · `close_object` · `value_at` · `Closed` · `Envelope` · `EnvelopeRefusal` |
| `sovereign_agent.objects.manifest` | RUN |  |  | `cut_manifest` · `verify_chain` · `verify_manifest` |
| `sovereign_agent.objects.migrate` | RUN |  | ✓ | `promote_to_sealed` · `reconcile` · `stamp_cutover` · `ReconciliationError` · `SealRefused` |
| `sovereign_agent.objects.proofs` | RUN |  |  | `issue_proof` · `proof_only_check` · `replay_root` · `tree_root` · `verify_proof` |
| `sovereign_agent.objects.registry` | RUN | `object-model` | ✓ | `root_from_object_list` · `MandateViolation` · `ObjectRegistry` |
| `sovereign_agent.objects.scope` | RUN | `object-model` |  | `check_access` · `mandate_root` · `ScopeRefusal` · `SharingRule` |

### `sovereign_agent.obligations`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.obligations._locking` | teach/data |  |  | — |
| `sovereign_agent.obligations._util` | teach/data |  |  | — |
| `sovereign_agent.obligations.arc_guardrail` | RUN |  |  | `arc_candidates` · `arc_eligible` · `arc_guardrail` · `cadence_ok` |
| `sovereign_agent.obligations.cross_node` | RUN |  |  | `import_remote_approval` |
| `sovereign_agent.obligations.evidence` | RUN-partial |  |  | `classify_evidence` · `EvidenceTier` |
| `sovereign_agent.obligations.ledger` | RUN |  | ✓ | `AlreadyClosedError` · `ObligationLedger` |
| `sovereign_agent.obligations.mandate_guard` | RUN-partial |  |  | `approval_holds_mandate` · `obligation_mandate` · `resolve_held_mandates` |
| `sovereign_agent.obligations.node_integration` | RUN |  |  | `make_attestor` · `make_gate` · `wire_node_ledger` |
| `sovereign_agent.obligations.projection` | RUN-partial |  |  | `attestation_status` · `by_owner` · `by_status` · `full_log` · `is_approved` · `is_closed` · `manifest` · `open_obligations` · `recompute_chain` · `refs` … |
| `sovereign_agent.obligations.provenance` | teach/data |  |  | — |
| `sovereign_agent.obligations.quorum_guard` | RUN-partial |  |  | `class_quorum_floor` · `effective_quorum` · `required_quorum` |
| `sovereign_agent.obligations.roots` | RUN-partial |  | ✓ | `get_ledger_root` · `LedgerBoundaryError` |
| `sovereign_agent.obligations.witness` | RUN-partial |  |  | `originate` · `receive` · `validate_witness_ref` · `witness_seal` |

### `sovereign_agent.onboarding`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.onboarding.admission` | RUN |  | ✓ | `admit_node` · `propose_onboarding` · `OnboardingError` |
| `sovereign_agent.onboarding.onboard` | RUN | `onboard-gate` | ✓ | `cli_onboard` · `run_onboard` · `verify_onboard_receipt` · `OnboardError` · `OnboardOutcome` · `OnboardReceipt` · `OnboardTurn` |

### `sovereign_agent.peerhood`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.peerhood.bridging` | RUN |  | ✓ | `attribute_pool_value` · `bridge_into_pool` · `federate_without_directory` · `form_peer_pool` · `pool_vote` · `settle_pool_on_port` · `verify_bridge` |
| `sovereign_agent.peerhood.clean_exit` | RUN | `clean-exit` | ✓ | `clean_exit` · `exit_green_light` · `generational_exit_epoch` · `membership_is_live` · `sever_pool_link` · `walk_with_keys_and_records` · `CleanExit` · `ExitLight` |
| `sovereign_agent.peerhood.delegation` | RUN |  | ✓ | `delegate_governed` · `join_mutual_protection` · `mandate_and_quorum` · `revoke_delegation` · `sponsor_without_claim` · `verify_delegation` |
| `sovereign_agent.peerhood.genesis` | RUN |  | ✓ | `declare_birth_boundary` · `establish_self_held_identity` · `genesis_green_light` · `genesis_recovery_epoch` · `issue_first_receipt` · `verify_peer_existence` · `GreenLight` · `PeerIdentity` · `PeerhoodError` |
| `sovereign_agent.peerhood.recognition` | RUN | `peer-recognition` | ✓ | `directory_free_discovery` · `mutual_recognition` · `recognition_as_receipt` · `refuse_recognition` · `scoped_visibility` · `verify_recognition` |

### `sovereign_agent.pooling`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.pooling.situational` | RUN-partial |  | ✓ | `gate_formation` · `pool_demand` · `SituationalError` |

### `sovereign_agent.port`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.port.crossing` | RUN | `port-crossing` | ✓ | `open_crossing` · `sanction_crossing` · `CrossingError` |

### `sovereign_agent.press`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.press.adversary` | RUN |  |  | `chapter_end_lawful` · `l0_check` · `l1_check` · `load_cards` · `main` · `validate_seed_unit` |
| `sovereign_agent.press.assembler` | RUN |  |  | `assemble` · `load_volume` · `AssemblyRefusal` |
| `sovereign_agent.press.board_stage1` | RUN-partial |  |  | `build_board_package` · `continuity_check` · `continuity_check_assembled` · `main` |
| `sovereign_agent.press.co_extrude` | RUN-partial |  |  | `main` · `run` |
| `sovereign_agent.press.editions` | RUN-partial |  |  | `cmd_check_trigger` · `cmd_status` · `compute_changelog` · `main` · `render_changelog_md` |
| `sovereign_agent.press.engine` | RUN |  |  | `build_volume` · `cmd_build` · `cmd_build_offline` · `cmd_bundle` · `cmd_cycle` · `cmd_harden` · `cmd_publish` · `cmd_run` · `cmd_seal` · `cmd_selftest` … |
| `sovereign_agent.press.fixer` | RUN-partial |  |  | `main` |
| `sovereign_agent.press.prescreen` | RUN |  |  | `apparatus_leaks` · `bare_numeral_ends` · `design_target_frame` · `full_name_density` · `gate_card` · `gloss_ledger` · `heading_not_beat` · `intra_paragraph_redundancy` · `main` · `repeated_hinge` … |
| `sovereign_agent.press.publish` | RUN-partial |  |  | `publish` · `render_card` |
| `sovereign_agent.press.report` | RUN-partial |  |  | `main` |
| `sovereign_agent.press.review_state` | RUN-partial |  |  | `append_event` · `derive` · `detail_lines` · `load_events` · `main` · `summary` |
| `sovereign_agent.press.seal` | RUN-partial |  | ✓ | `check_supersede` · `is_sealed` · `latest_for` · `load_chain` · `make_receipt` · `principal` · `read_word` · `receipt_sig_scheme` · `sign` · `superseded_ids` … |
| `sovereign_agent.press.seal_summary` | RUN-partial |  |  | `generate` · `main` · `OpenBlockingHolds` · `SummaryRefusal` |

### `sovereign_agent.procurement`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.procurement.matching` | RUN-partial |  | ✓ | `ap_entry` · `three_way_match` · `MatchError` |
| `sovereign_agent.procurement.supplier` | RUN-partial |  | ✓ | `award` · `register` · `score_suppliers` · `transition` · `SupplierError` |

### `sovereign_agent.regulated`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.regulated.traceability` | RUN-partial |  | ✓ | `assert_custody` · `consume` · `custody_position` · `lot_transition` · `open_lot` · `receipt` · `reconcile_custody` · `release` · `trace_root` · `transfer` … |

### `sovereign_agent.revenue`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.revenue.billing` | RUN-partial |  | ✓ | `ar_aging` · `invoice` · `BillingError` |
| `sovereign_agent.revenue.credit` | RUN-partial |  | ✓ | `available_credit` · `check_order` · `CreditError` |
| `sovereign_agent.revenue.recognition` | RUN-partial |  | ✓ | `recognize` · `RecognitionError` |

### `sovereign_agent.risk`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.risk.advanced_pooling` | RUN |  | ✓ | `bridge_settlement` · `build_attestation_chain` · `federate_pools` · `selective_disclosure` · `verify_attestation_chain` · `DisclosedCredit` · `Federation` |
| `sovereign_agent.risk.governance` | RUN |  | ✓ | `audit_ready_package` · `enforce_decision` · `escalate_if_over_limit` · `fork_governance_skin` · `load_governance_skin` · `skin_role_spec` · `AuditPackage` · `GovernanceSkin` · `PolicyVerdict` |
| `sovereign_agent.risk.group_applications` | RUN |  | ✓ | `cross_entity_match` · `form_group_pool` · `group_claim` · `group_premium` · `group_reputation` · `verify_group_premium` · `GroupReputation` |
| `sovereign_agent.risk.mutual_protection` | RUN |  | ✓ | `credit_history` · `form_protection_pool` · `match_by_reputation` · `record_claim` · `record_premium` · `reputation_package` · `settle_claim` · `verify_claim` · `verify_premium` · `CreditHistory` … |
| `sovereign_agent.risk.protection_covenant` | RUN |  | ✓ | `inherit_protection` · `protection_stream_kinds` · `verify_stack_element` · `ProtectionStatus` |

### `sovereign_agent.services`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.services.engagement` | RUN-partial |  | ✓ | `bill` · `bill_posting` · `billable_amount` · `billable_by_resource` · `budget_position` · `open_engagement` · `record_time` · `transition` · `EngagementError` |

### `sovereign_agent.shields`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.shields.protective` | RUN |  | ✓ | `declare_shield` · `pass_shield_stack` · `ShieldError` |
| `sovereign_agent.shields.resilience` | RUN |  | ✓ | `declare_recovery_plan` · `recover_authority` · `snapshot_resource` · `ResilienceError` |
| `sovereign_agent.shields.wasm_sandbox` | RUN |  |  | `WasmSandbox` · `WasmTrap` |

### `sovereign_agent.sovereign_ux`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.sovereign_ux.cockpit` | RUN |  |  | `compose_cockpit` · `Cockpit` |
| `sovereign_agent.sovereign_ux.federated_view` | RUN |  |  | `federated_view` · `verify_federated` · `FederatedView` |
| `sovereign_agent.sovereign_ux.gate_interaction` | RUN |  |  | `dispose` · `propose` · `review` · `session_view` · `GateDenied` |
| `sovereign_agent.sovereign_ux.lens` | RUN |  |  | `render_view` · `show` · `verify_view` · `LensDrift` · `View` · `ViewStatus` |
| `sovereign_agent.sovereign_ux.progressive_view` | RUN |  |  | `handoff_view` · `progressive_view` · `verify_level` · `LevelSet` |
| `sovereign_agent.sovereign_ux.render_covenant` | RUN |  |  | `inspect_article` · `render_covenant` · `verify_covenant` |
| `sovereign_agent.sovereign_ux.tokens` | RUN |  |  | `apply_tokens` · `validate_drift` · `TokenDrift` · `TokenSet` |
| `sovereign_agent.sovereign_ux.verify_surface` | RUN |  |  | `evidence_view` · `is_verified` · `verify_surface` · `VerifyStatus` |

### `sovereign_agent.storage`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.storage.sovereign_store` | RUN | `storage-integrity` | ✓ | `retrieve_datum` · `store_datum` · `StorageError` |

### `sovereign_agent.supply`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.supply.bom` | RUN-partial |  |  | `can_build` · `explode_bom` |
| `sovereign_agent.supply.inventory` | RUN-partial |  | ✓ | `on_hand` · `on_hand_for` · `would_overdraw` · `NegativeStockError` |

### `sovereign_agent.trust`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.trust.boundaries` | RUN |  | ✓ | `declare_trust_anchor` · `hand_off_trust` · `TrustError` |

### `sovereign_agent.yield_organism`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.yield_organism._sealed_host_seam` | RUN |  |  | `is_verified` · `sign_value_flow` · `verify_economic_bundle` |
| `sovereign_agent.yield_organism.alignment_scorer` | RUN |  |  | `AlignmentPosture` · `AlignmentScorer` · `ComponentScore` |
| `sovereign_agent.yield_organism.compounding` | RUN |  | ✓ | `BoundedCompounder` · `BrakeSignal` · `CompoundingRecord` · `CompoundingRefused` · `DriftBrake` · `PeriodInput` · `ResumeRefused` · `RollUp` |
| `sovereign_agent.yield_organism.economic_actions` | RUN |  | ✓ | `distribute_via_payout` · `ledger_leg_balance` · `payout_allocations` · `recirc_allocations` · `swap_via_pool` · `ActionLeg` · `DistributionRecord` · `EconomicActionRefused` · `SwapRecord` |
| `sovereign_agent.yield_organism.economic_export` | RUN |  | ✓ | `BundleVerification` · `EconomicBundle` · `EconomicBundleExporter` · `EconomicExportRefused` |
| `sovereign_agent.yield_organism.engines` | package |  |  | — |
| `sovereign_agent.yield_organism.engines.amm_pool` | RUN |  |  | `load_test_boundaries` · `self_test` · `AMMPool` |
| `sovereign_agent.yield_organism.engines.payout_engine` | RUN |  |  | `self_test` · `MintEngine` · `Recipient` |
| `sovereign_agent.yield_organism.engines.recirc_allocator` | RUN |  |  | `self_test` · `AllocationBand` · `RecircAllocator` |
| `sovereign_agent.yield_organism.value_flow` | RUN |  | ✓ | `ValueFlow` · `ValueFlowProjector` · `ValueFlowRefused` · `WeightBasis` |

### `sovereign_agent.zero_trust`

| module | label | card | kill-target | public callables |
|---|---|---|---|---|
| `sovereign_agent.zero_trust.node_arch` | RUN |  | ✓ | `present_evidence` · `verify_access` · `ZeroTrustError` |

## Reading-path callability (Series 2–4, KM-audited)

Series 2–4 each resolve to a real callable path on the public clone (not teach-only):
- **RUN:** Building the Agentic Harness (S2) V1 · Programmable Sovereign ERP (S3) V1, V2 · Sovereign Token & Economic Organism (S4) V1, V2.
- **RUN-partial:** Building the Agentic Harness (S2) V2/V3/V4/V5 · Programmable Sovereign ERP (S3) V3/V4 · Sovereign Token & Economic Organism (S4) V3/V4.
- **teach:** Series 0–1 (the lens and the executive playbooks) are reading, not runtime.
- Series 5–14 are the sealed executable runtime the cards and the inventory above are drawn from.

## How to use this map

1. Start from `docs/NODE_INTEGRATION_GUIDE.md` (the mental model) and the **nine cards** (the curated subset).
2. Need something a card doesn't cover? Find the **module path** here and import it.
3. Want the depth behind a path? Read its volume on the shelf (`docs/READING_PATH_S0_S4.md` for the arc; the sealed Series 5–14 for the runtime).
