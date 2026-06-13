# GB Open-Series Merge Plan — 2026-06-11

Consolidated fold of G's open-series keyword batch (S3 2 titles, S5 32, S6 5, S7 6, S8 8) into `extracted_chapter_outlines_2026-06-08.json` -> `d['books']`. Payload: `GB_openseries_merge_payload_2026-06-11.json`. Apply in one verified step; KM ratifies.

## Counts per series

| Series | Titles | Chapters | Keywords (title+chapter) |
|---|---|---|---|
| S3 programmable_sovereign_erp | 2 | 16 | 78 |
| S5 full_production_erp | 32 | 256 | 1248 |
| S6 inter_node_sovereignty | 5 | 40 | 195 |
| S7 zero_trust_sovereignty | 6 | 48 | 234 |
| S8 sovereign_ux | 8 | 64 | 312 |
| **TOTAL** | **53** | **424** | **2067** |

Mapping confidence: exact=51, strong=2, weak=0.

## Mapping table (G title -> book_id)

| Series | G title | book_id | confidence | jac/cov | source file | source-won (richest) |
|---|---|---|---|---|---|---|
| S3 | The Immutable Core: Receipts, Cylinders & Constitutional Truth | `vol_01_immutable_core` | exact | 1.0/1.0 | checkpoint(S3) | beats/promise |
| S3 | Programmable Governance Skin: YAML Roles, Action Classes & Breath-Gates | `vol_02_programmable_governance_skin` | exact | 1.0/1.0 | checkpoint(S3) | beats/promise |
| S5 | The Immutable Core — Receipts, Cylinders & Constitutional Truth | `s5_01_immutable_core` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Programmable Governance Skin — Roles, Action Classes & Breath-Gates | `s5_02_governance_skin` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Helix — When the Book Literally Writes the Backend | `s5_03_helix` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Coherence as Living Ledger — Real-Time Drift Detection & Integrity | `s5_04_coherence_ledger` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Sovereign Object Model — Registry, Manifests & Merkle Integrity | `s5_05_sovereign_object_model` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Distribution Matrix Governance — Books as the Authoritative Join | `s5_06_distribution_matrix_gov` | exact | 1.0/1.0 | checkpoint(S5-PassA) | beats/promise |
| S5 | Sovereign Financials — General Ledger, Controlling & Reporting | `s5_07_sovereign_financials` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Treasury & Cash Management — Liquidity, Forecasting & Compliance | `s5_08_treasury_cash` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Supply Chain Execution — Procurement, Logistics & Inventory | `s5_09_supply_chain` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Manufacturing & Quality — Production, MES & Traceability | `s5_10_manufacturing_quality` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Project & Portfolio Management — Planning, Execution & Governance | `s5_11_project_portfolio` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Asset & Maintenance Management — Lifecycle & Reliability | `s5_12_asset_maintenance` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Human Capital & Sovereign Payroll — Roles, Compensation & Continuity | `s5_13_human_capital_payroll` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Compliance & Audit Automation — Standards Ingestion & Evidence | `s5_14_compliance_audit` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Revenue & Order-to-Cash — Contracts, Billing & Recognition | `s5_15_revenue_o2c` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Procurement-to-Pay — Sourcing, Contracts & Supplier Governance | `s5_16_procure_to_pay` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Analytics & Decision Intelligence — Real-Time Insights with Provenance | `s5_17_analytics_decision` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Multi-Entity & Consolidation — Global Structures & Intercompany | `s5_18_multi_entity_consolidation` | exact | 1.0/1.0 | S5_PassB | chapter_title |
| S5 | Manufacturing Sovereign ERP — Discrete & Process Operations | `s5_19_manufacturing_erp` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Distribution & Wholesale — Inventory, Logistics & Channel Management | `s5_20_distribution_wholesale` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Professional Services — Project Billing, Resource & Knowledge | `s5_21_professional_services` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Energy & Resources — Asset-Intensive Operations & Compliance | `s5_22_energy_resources` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Construction & Projects — Job Costing, Subcontractor & Safety | `s5_23_construction_projects` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Regulated Industries — Traceability, Quality & Audit Readiness | `s5_24_regulated_industries` | exact | 1.0/1.0 | S5_PassC | chapter_title |
| S5 | Multi-Standard Ingestion — Mapping External Boards into Sovereign Form | `s5_25_multi_standard_ingestion` | strong | 0.78/0.88 | S5_PassD | chapter_title |
| S5 | Federation Node Governance — Cross-Node Validation & Sharing | `s5_26_federation_node_gov` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Generational Continuity — Private Series, Handoff Rituals & Legacy | `s5_27_generational_continuity` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Private Series Templates — Family & Enterprise Constitutions | `s5_28_private_series_templates` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Exception & Governance Workflows — Human Gate Patterns at Scale | `s5_29_exception_gov_workflows` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Social & External Distribution — Content Propagation with Provenance | `s5_30_social_external_distribution` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Federation Marketplace — Shared Patterns & Verified Blueprints | `s5_31_federation_marketplace` | exact | 1.0/1.0 | S5_PassD | chapter_title |
| S5 | Sovereign ERP Operations Console — Atrium as the Single Operator Surface | `s5_32_erp_operations_console` | strong | 0.78/0.88 | S5_PassD | chapter_title |
| S6 | Receipted Inter-Node Messaging | `vol_01_receipted_inter_node_messaging` | exact | 1.0/1.0 | S6 | chapter_title |
| S6 | Sovereign Collaboration | `vol_02_sovereign_collaboration` | exact | 1.0/1.0 | S6 | chapter_title |
| S6 | Distributed Sovereign Compute | `vol_03_distributed_sovereign_compute` | exact | 1.0/1.0 | S6 | chapter_title |
| S6 | Resonance Coordination (not central control) | `vol_04_resonance_coordination` | exact | 1.0/1.0 | S6 | chapter_title |
| S6 | Inter-Node Trust Boundaries & Handoff | `vol_05_inter_node_trust_boundaries_handoff` | exact | 1.0/1.0 | S6 | chapter_title |
| S7 | Zero-Trust Node Architecture | `vol_01_zero_trust_node_architecture` | exact | 1.0/1.0 | S7 | chapter_title |
| S7 | Shields as Protective Layers | `vol_02_shields_protective_layers` | exact | 1.0/1.0 | S7 | chapter_title |
| S7 | Sovereign Data Storage Model | `vol_03_sovereign_data_storage` | exact | 1.0/1.0 | S7 | chapter_title |
| S7 | Verified Data Flows Across Nodes | `vol_04_verified_data_flows` | exact | 1.0/1.0 | S7 | chapter_title |
| S7 | Private vs Shared Storage Governance | `vol_05_private_shared_storage_governance` | exact | 1.0/1.0 | S7 | chapter_title |
| S7 | Resilience & Recovery Shields | `vol_06_resilience_recovery_shields` | exact | 1.0/1.0 | S7 | chapter_title |
| S8 | The Sovereign Lens — Content-Agnostic Rendering & Honest Views | `s8_01_sovereign_lens` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Breath-Gated Interfaces — Human Primacy in Every Pixel | `s8_02_breath_gated_interfaces` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Aesthetic Resonance — Beauty as Functional Attention | `s8_03_aesthetic_resonance` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Atrium as Living OS — The Sovereign Decision Cockpit | `s8_04_atrium_living_os` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Generational UX — Interfaces That Heirs Actually Want to Inherit | `s8_05_generational_ux` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Federation UX — Resonance Across Sovereign Nodes | `s8_06_federation_ux` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | Zero-Trust UX — Shields, Verification & Adversarial Clarity | `s8_07_zero_trust_ux` | exact | 1.0/1.0 | S8 | chapter_title |
| S8 | UX as Executable Covenant — The Living Proof | `s8_08_ux_executable_covenant` | exact | 1.0/1.0 | S8 | chapter_title |

**Source-won note:** S3 (2) and S5 Pass A (6) carry full beats/promise (richest) from the Tiger FOLD CHECKPOINT file and win over the keywords-only versions in `G_S3_keywords` / `G_S5_keywords`. S5 Pass B/C/D + S6/S7/S8 are chapter_title+keywords spine (beats live in G's transcript). Per the prompt rule beats/promise > chapter_title > keywords-only, the checkpoint set won every conflict; staging files contributed no gap-fills (all titles present in checkpoint/pass files).

## Flags applied (enrichment_note)

- `overlap_pending_km_ruling_a` (S5 dual-manufacturing, PassB Manufacturing & Quality vs PassC Manufacturing Sovereign ERP): **2** entries.
- `overlap_pending_km_ruling_b` (S3<->S5 foundation overlap: Immutable Core / Governance Skin / Helix in both series): **5** entries.
- `beats_pending_transcript_backfill` (spine-only depth, beats absent): **45** entries.

### overlap_pending_km_ruling_b entries (the six)
- `vol_01_immutable_core` — S3 The Immutable Core: Receipts, Cylinders & Constitutional Truth
- `vol_02_programmable_governance_skin` — S3 Programmable Governance Skin: YAML Roles, Action Classes & Breath-Gates
- `s5_01_immutable_core` — S5 The Immutable Core — Receipts, Cylinders & Constitutional Truth
- `s5_02_governance_skin` — S5 Programmable Governance Skin — Roles, Action Classes & Breath-Gates
- `s5_03_helix` — S5 Helix — When the Book Literally Writes the Backend

### overlap_pending_km_ruling_a entries
- `s5_10_manufacturing_quality` — S5 Manufacturing & Quality — Production, MES & Traceability
- `s5_19_manufacturing_erp` — S5 Manufacturing Sovereign ERP — Discrete & Process Operations

## Mechanical cleans

- Keywords de-duplicated WITHIN each title and within each chapter (case-insensitive).
- Internal-jargon keyword flags (NOT auto-replaced — GB/KM to rule): 2.

| book_id | location | keyword | jargon term |
|---|---|---|---|
| `s5_05_sovereign_object_model` | TITLE | Merkle ERP integrity | merkle |
| `s5_05_sovereign_object_model` | 4 | Merkle ERP integrity | merkle |

## NEEDS_GB

- (none) — every G title mapped to a unique roadmap book_id at exact/strong confidence.

