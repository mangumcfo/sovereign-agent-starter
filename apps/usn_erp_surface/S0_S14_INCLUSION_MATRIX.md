# S0–S14 Inclusion Matrix — the Full Ladder × Kernel × Operator Surface × Aquarium

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

**Scored 2026-08-19 by AA (facts / scorecard).** Companion to `S5_SURFACE_INCLUSION_MATRIX.md`
(same rubric, same tip); Series 5's 41 volumes are scored there and only summarized here.
No new builds, no arm, no code changes — this document only.

| | |
|---|---|
| **Kernel tip scored** | `417c548`..`8e5e36b` (main) |
| **Corpus authority** | `breathline-books-vault/kdp/` — per-series volume dirs walked one by one; 89 volumes across S0–S4, S6–S14 (+ 41 in S5 = **130 federation-wide**) |
| **Code method** | AST walk of `src/sovereign_agent/<domain>/` — public functions/classes, no imports executed; tests = files in `tests/` referencing the package |
| **Surface / Aquarium method** | identical to the S5 matrix |

**Rating definitions:** identical to the S5 matrix (CODE_PRESENT / SURFACE_READY /
SURFACE_LIVE / CORPUS_ONLY, with the FENCED overlay for money-path / statutory / Port /
external-egress legs). SURFACE_READY here is applied conservatively: only verbs that are
record / verify / read against the node's **own** stores — no cross-node transport, no value
movement, no egress — qualify.

**Publication status, honestly sourced:** the ASIN register
(`ASIN_REGISTER_2026-07-31.md`) is a screenshot scrape — 63 of its 80 rows carry the
placeholder title "Order author copies," so literal title-matching yields only 10 hits. The
better source is `agentic_playbooks/ASIN_TRACKER.yaml` (2026-07-09) plus the register's
series-column counts: **S0 ≈ 6 titles live** (01/02/03/05 + Capture Economy + Atlas
companion; 04_xrp shelved), **S1 all 12 live**, **S2 all 5 live/pre-order**, **S3 all 4
published** — and **zero ASIN rows for S4 and S6–S14: none of those 63 volumes is
published.** Every S6–S14 volume has manuscript + final PDF/EPUB but **no cover art**
(3 stray exceptions), consistent with pre-publication state.

---

## 1 · Summary

### Federation-wide (130 volumes, S5 matrix folded in)

| Rating | S0–S14 (89) | S5 (41) | Total (130) | % |
|---|---|---|---|---|
| SURFACE_LIVE | 5 | 4 | 9 | 7% |
| SURFACE_READY (not live) | 17 | 18 | 35 | 27% |
| CODE_PRESENT | 47 | 18 | 65 | 50% |
| CORPUS_ONLY | 20 | 1 | 21 | 16% |
| **CODE_PRESENT or better** | **69 / 89** | **40 / 41** | **109 / 130** | **84%** |

The 20 CORPUS_ONLY rows are S0 (8) + S1 (12) — trade business books whose artifact is the
published book itself, not a kernel module. Excluding them, **109 of 110 kernel-coupled
volumes have importable, tested (or explicitly public) code on tip.** The one exception
remains S5-V03 (the Production Reference — the repo is the artifact).

### Per-series profile

| Series | Vols | Kernel home (primary) | LOC / test-files | Published | Profile |
|---|---|---|---|---|---|
| S0 Executive Foundational | 8 | — (trade books) | — | ~6 live | CORPUS_ONLY ×8 |
| S1 Agentic Playbooks | 12 | — (`playbook_loader.py`, `demo_roles/` as pattern echoes) | — | 12 live | CORPUS_ONLY ×12 |
| S2 Agentic Harness | 5 | `press/`, `inference/`, `sovereign_ux/`, `yield_organism/` | 5,044+ / 9+ | 5 live/pre-order | PRESENT ×5 |
| S3 Programmable Sovereign ERP | 4 | `objects/`, `obligations/`, `storage/`, `keystore/`, `press/` | — / 66+27+11 refs | 4 published | **LIVE ×1**, PRESENT ×3 |
| S4 Token & Economic Organism | 4 | `yield_organism/`, `economy/pool.py` | 2,486 / 5 | 0 | PRESENT ×4 · **FENCED ×4** |
| S6 Inter-Node Sovereignty | 7 | `messaging/`, `onboarding/`, `peerhood/`, `port/` | — / 8+ | 0 | READY ×1, PRESENT ×6 |
| S7 Zero-Trust Sovereignty | 7 | `zero_trust/`, `shields/`, `storage/`, `flows/`, `evidence/` | 679+ / 4+ | 0 | **LIVE ×1**, READY ×1, PRESENT ×5 |
| S8 Sovereign UX | 8 | `sovereign_ux/`, `node_api/` (atrium) | 784 / 8 | 0 | **LIVE ×1**, READY ×3, PRESENT ×4 |
| S9 Material Sovereignty | 6 | `material/`, `energy/`, `supply/` | 490+ / 9+ | 0 | READY ×2, PRESENT ×4 |
| S10 Sovereign Livelihood | 5 (+3 dup) | `economy/` (income, productivity, pool) | 953 / 16 | 0 | **LIVE ×2**, READY ×2, PRESENT ×1 · **DUP HOLD** |
| S11 Risk & Mutual Protection | 5 | `risk/` | 906 / 10 | 0 | READY ×1, PRESENT ×4 · FENCED ×1 |
| S12 Generational Transfer | 5 | `estate/`, `continuity/` | 885+ / 7+ | 0 | READY ×3, PRESENT ×2 |
| S13 Sovereign Discourse | 5 | `discourse/` | 775 / 5 | 0 | READY ×1, PRESENT ×4 · FENCED ×2 |
| S14 Sovereign Peerhood | 5 | `peerhood/`, `keystore/`, `onboarding/` | 963 / 8 | 0 | READY ×3, PRESENT ×2 |

### ⚠ S10 duplication — the one row needing a KM word

Two overlapping S10 builds exist, one day apart:
`series_10_sovereign_economy` (3 vols, committed 2026-08-08, manuscripts say "Sovereign
Economy (Series 10)") and `series_10_sovereign_livelihood` (5 vols, committed 2026-08-09
including "V01 REBUILD" and "V05 capstone PACKAGE, freeze d7e6fa26", manuscripts say
"Sovereign Livelihood (Series 10)"). Every vault cross-reference (concept doc, roadmap
exports, staging docs) points at the **livelihood** dir, and it is the structurally complete
5/5 build — so this matrix scores it. But the concept file's own header records a KM ruling
(2026-08-08, sealed-name-wins) that the reader-facing name is **"Sovereign Economy"** —
matching the smaller, earlier dir. Two builds, one name ruling applied to the other one.
**HOLD: needs KM/GB disposition (which dir is canonical; fold or retire the other). Scored
here: livelihood dir, name flag carried.**

---

## 2 · Volume matrices

### S0 · Mangum Executive Foundational — CORPUS_ONLY ×8

01 Strategic Finance ✓live · 02 Harnessing AI ✓live · 03 Blueprint ✓live · 04 XRP (shelved,
final artifacts absent) · 05 Crypto Decoded ✓live · 06 The Capture Economy ✓live ·
07 The Uncapturable Atlas (title unsettled: metadata says "Extension", staging decision
ratifies "Atlas") · 08 The Metered Mind (at KM gate).
**Aquarium:** vols 06–08's capture doctrine is lived as the town's Capture Lens
(FREE / LEASHED / CAPTURED, C5) — the one S0 teaching with a running tool.

### S1 · Agentic AI Playbooks — CORPUS_ONLY ×12, all live

Books 01–12 published (ASIN_TRACKER: 11 live + book 12 pre-order as of 2026-07-09; KM
confirmation 2026-07-06 records all 12). Kernel echo only: `playbook_loader.py`,
`demo_roles/` (`tests/test_ma_data_room.py` exercises Book 11's data-room pattern).

### S2 · Building the Agentic Harness

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Sovereign Inference & Memory | `inference/`, `memory/` | `p1_sign/verify`, `build_receipt`, `verify_chain`, `six.classify` | NONE | NONE | CODE_PRESENT (publics; **0 test files** — noted) | `inference/receipts.py` publics on tip |
| 2 | The Primacy Cockpit | `sovereign_ux/cockpit.py` + `node_api` atrium | `compose_cockpit`; atrium routes | NONE | C7 cockpit lane | CODE_PRESENT | `tests/test_atrium_surfaces.py` |
| 3 | The Harness That Builds Itself | `press/` + `node_api/routes/book_artifacts.py` | `assembler.assemble`, `adversary.l0/l1_check`, `POST /recompile` | NONE | NONE | CODE_PRESENT | 9 test files reference `press`; BCK route row |
| 4 | Federated Sovereignty (partner gateway) | `federation/`, `port/`, node_api adapters | `share_node_state`, `validate_received` | NONE | C7 meetings | CODE_PRESENT · FENCED (crossing) | `tests/test_federation.py`; BCK "S6 V7 adapter surface" ×4 routes |
| 5 | The Sovereign Yield Engine | `yield_organism/` | `payout_allocations`, `recirc_allocations`, `swap_via_pool` | NONE | NONE | CODE_PRESENT · **FENCED (value)** | 5 test files (`test_yield_*.py`) |

### S3 · Programmable Sovereign ERP (root) — all 4 published

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | The Immutable Core | `objects/`, `storage/`, `keystore/`, `obligations/` | `store_datum`, `sign_node_act/verify_node_act`, `object_id`, ledger O-verbs | **WRITE+GATE + READ + EXPORT** | C3 record box; C17 stewardship | **SURFACE_LIVE** | surface BAR P1–P8 + O1–O6; 66/27/11 test-file refs |
| 2 | Programmable Governance Skin | `risk/governance.py`, `role_binder.py` | `load_governance_skin`, `skin_role_spec`, `fork_governance_skin` | NONE | NONE | CODE_PRESENT | `tests/` refs to `risk` (10 files) |
| 3 | Helix (book writes backend) | `press/` | `assemble`, seed/validate lanes | NONE | NONE | CODE_PRESENT | 9 test files; P-Push law names press the shared kernel |
| 4 | Industry ERPs & Generational Continuity | composition → S5 V19–24 + `estate/`, `continuity/` | per constituent rows | NONE | NONE | CODE_PRESENT (composition) | constituent test files |

### S4 · Sovereign Token & Economic Organism — FENCED series (real value; no surface without KM)

| Vol | Title (short) | Code path | Key methods | Rating | Evidence |
|---|---|---|---|---|---|
| 1 | Sovereign Token Substrate | `yield_organism/_sealed_host_seam.py`, `economy/pool.py` | `sign_value_flow`, `verify_economic_bundle` | CODE_PRESENT · FENCED | `test_yield_value_flow.py` |
| 2 | Governed Token Mechanics (title flagged for KM/GB) | `yield_organism/economic_actions.py` | `ledger_leg_balance`, `swap_via_pool` | CODE_PRESENT · FENCED | `test_yield_engine_wiring.py` |
| 3 | The Token Yield Organism (title variance vs registry) | `yield_organism/` (AMM, payout, recirc) | `payout_allocations`, `recirc_allocations` | CODE_PRESENT · FENCED | `test_yield_compounding.py` |
| 4 | The Inheritable Token (title variance vs registry) | + `estate/` | `inheritance_package` | CODE_PRESENT · FENCED | `test_generational_transfer.py` |

Aquarium: NONE by law — the town's paper-stakes rule is this fence lived, not an analog.

### S6 · Inter-Node Sovereignty

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Receipted Inter-Node Messaging | `messaging/inter_node.py` | `send_message`, `carry_to_peer`, `receive_from_peer` | NONE | C7 co-signed ceremonies over declared transport | CODE_PRESENT | `tests/` ref (1 file) |
| 2 | Sovereign Collaboration | `collaboration/shared_work.py` | `contribute`, `authorize_participation` | NONE | C19 Pool's Table (every member holds the whole) | CODE_PRESENT (THIN) | 70 LOC, 1 test file |
| 3 | Distributed Sovereign Compute | `compute/distributed.py` | `offer_capacity`, `admit_job` | NONE | NONE | CODE_PRESENT (THIN) | `test_compute_distributed.py` |
| 4 | Resonance Coordination | `coordination/resonance.py` | `node_signal`, `resonate` | NONE | NONE | CODE_PRESENT (THIN) | 62 LOC, 1 test file |
| 5 | Trust Boundaries & Handoff | `trust/boundaries.py` | `declare_trust_anchor`, `hand_off_trust` | NONE | NONE | CODE_PRESENT (THIN) | 72 LOC, 1 test file |
| 6 | Node Onboarding (growth by consent) | `onboarding/admission.py` | `propose_onboarding`, `admit_node` | NONE | C9 waiting room; C16 arrival walk | **SURFACE_READY** (gate-shaped ceremony) | `tests/` refs (2 files) |
| 7 | The Sovereign Port | `port/crossing.py` | `open_crossing`, `sanction_crossing` | NONE — and never silently | NONE | CODE_PRESENT · **FENCED (Port)** | 1 test file; surface kill-grep row 2 forbids import |

### S7 · Zero-Trust Sovereignty

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Zero-Trust Node Architecture | `zero_trust/node_arch.py` | `present_evidence`, `verify_access` | verify-on-click badge composes the doctrine | C15 receipt check | CODE_PRESENT | 93 LOC, 1 test file |
| 2 | Shields as Protective Layers | `shields/protective.py` | `declare_shield`, `pass_shield_stack` | NONE | NONE | CODE_PRESENT | 4 test files ref `shields` |
| 3 | Sovereign Data Storage Model | `storage/sovereign_store.py`, `objects/` | `store_datum`, `retrieve_datum`, Merkle replay | **READ** (registry panel, `roots_match`) | C7 dual-held datums | **SURFACE_LIVE** (read) | BCK: 3 routes homed "S7 V3"; surface P1/P2 evidence |
| 4 | Verified Data Flows | `flows/verified_flow.py` | `declare_flow`, `verify_flow`, `attest_flow_clears` | NONE | NONE | **SURFACE_READY** (declare/verify records) | 1 test file |
| 5 | Private vs Shared Storage Governance | `governance/private_shared.py` | `classify_datum`, `govern_shared_access` | NONE | NONE | CODE_PRESENT | `tests/test_private_shared.py` |
| 6 | Resilience & Recovery Shields | `shields/resilience.py` | `declare_recovery_plan`, `snapshot_resource`, `recover_authority` | NONE | NONE (Keyring on town frontier) | CODE_PRESENT | shields test files |
| 7 | Sovereign Workload Execution | cluster (`compute/` + shields) | `admit_job` + shield stack | NONE | NONE | CODE_PRESENT (THIN for the workload layer) | cluster evidence |

### S8 · Sovereign UX

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | The Sovereign Lens | `sovereign_ux/lens.py` | `render_view` | NONE | C12 consume-plane law | **SURFACE_READY** | 8 test files ref `sovereign_ux` |
| 2 | Breath-Gated Interfaces | `sovereign_ux/gate_interaction.py` | `propose`, `review`, `dispose`, `session_view` | **the surface's gate panel is this pattern, live** | C9 dispositions | **SURFACE_LIVE** (pattern instance) | surface P4 + O1–O6 evidence |
| 3 | The Governed Aesthetic | cluster (design tokens) | — | NONE | NONE | CODE_PRESENT (THIN) | cluster evidence only |
| 4 | Atrium as Living OS | `node_api/` atrium routes | apply/revert, executor | NONE | NONE | **SURFACE_READY** | `tests/test_atrium_apply_revert.py`, `test_atrium_executor.py`, `test_atrium_surfaces.py` |
| 5 | Generational UX | cluster | — | NONE | NONE | CODE_PRESENT (THIN) | cluster evidence only |
| 6 | Federation UX | `sovereign_ux/federated_view.py` | `federated_view`, `verify_federated` | NONE | C7 cockpit (9 households, one glass) | **SURFACE_READY** (read) | sovereign_ux tests |
| 7 | Zero-Trust UX (show only what it proves) | verify badges + `lens` | `verify_income` re-run on click | verify leg live | C15 | CODE_PRESENT (pattern live via S7) | surface P7 evidence |
| 8 | UX as Executable Covenant | cluster | — | NONE | C21/C22 plain-language law | CODE_PRESENT (THIN) | cluster evidence only |

### S9 · Material Sovereignty

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | The Material Primitive | `material/provision_local.py` | `provision_local`, `verify_provision` | NONE | Pool contributions (kiln, tools at intake) | **SURFACE_READY** | 9 test files ref `material` |
| 2 | Sovereign Energy | `material/provision_energy.py`, `energy/` | `provision_energy`, `verify_energy`, `plan_operation` | NONE | NONE | CODE_PRESENT | material + energy tests |
| 3 | Regenerative Food & Water | provision cluster | `provision_under_covenant` | NONE | NONE | CODE_PRESENT (THIN specific) | cluster evidence |
| 4 | Shelter & Manufacturing | + `manufacturing/` | `open_order`, `complete` | NONE | NONE | CODE_PRESENT | `test_production_order.py` |
| 5 | Logistics & Supply | + `supply/` | `on_hand`, `explode_bom` | NONE | NONE | CODE_PRESENT | supply tests |
| 6 | The Provision Covenant | `material/provision_covenant.py` | `provision_kinds`, `provision_under_covenant`, `verify_under_covenant` | NONE | NONE | **SURFACE_READY** (record+verify) | material tests |

### S10 · Sovereign Livelihood (scored dir; DUP HOLD above)

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Building Income & Productivity | `economy/income.py` | `attribute_income`, `verify_income` | **WRITE+GATE** | C23 lease-meter lived week | **SURFACE_LIVE** | surface P2/P4/P8 |
| 2 | Networked Value Pools Without Extraction | `economy/pool.py`, `peerhood/bridging.py` | `form_peer_pool`, `attribute_pool_value` | NONE | Pool contributions | **SURFACE_READY** (records) | `test_advanced_pooling.py` |
| 3 | Programmable Productivity | `economy/productivity.py` | (module publics on tip) | NONE | NONE | **SURFACE_READY** | economy tests (16 files) |
| 4 | Operating Legally While Sovereign | `economy/compliance.py` + `compliance/` | `record_tax_event`, `reporting_package` | **WRITE+GATE + EXPORT** | NONE | **SURFACE_LIVE** (tax/report leg) | surface P3/P5 |
| 5 | Income Systems That Outlive You | + `estate/`, `continuity/` | `inheritance_package`, `assemble_successor_package` | NONE | NONE | CODE_PRESENT | estate/continuity tests |

### S11 · Risk & Mutual Protection

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Insurance, Credit & Reputation Without Capture | `risk/` core | pool formation, reputation records | NONE | NONE | CODE_PRESENT | 10 test files ref `risk` |
| 2 | Advanced Pooling & Credit Mechanics | `risk/advanced_pooling.py` | `federate_pools`, `build_attestation_chain`, `verify_attestation_chain`, `selective_disclosure` | NONE | C10/C22 disclosure card (selective disclosure lived) | **SURFACE_READY** (attestation records) · FENCED (settlement) | `test_advanced_pooling.py` |
| 3 | Industry, Group & Affinity | cluster | — | NONE | NONE | CODE_PRESENT (THIN) | cluster evidence |
| 4 | Governance, Compliance & Integration | `risk/governance.py` | `load_governance_skin`, `fork_governance_skin` | NONE | NONE | CODE_PRESENT | risk tests |
| 5 | Generational Continuity & Synthesis | + `estate/` | — | NONE | NONE | CODE_PRESENT (THIN) | cluster evidence |

### S12 · Generational Transfer

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | The Estate That Executes Itself | `estate/estate_covenant.py` | `estate_stack_kinds`, `inherit_estate` | NONE | NONE | **SURFACE_READY** (estate records) | 7 test files ref `estate` |
| 2 | Advanced Key Management & Succession | `estate/generational_transfer.py` | `open_key_epoch`, `family_quorum_recovery`, `breath_gated_key_transfer` | NONE | Keyring = town frontier row (queued, unbuilt) | **SURFACE_READY** (rehearsal records) | `test_key_succession.py` |
| 3 | Forkable Ventures & Continuity | `continuity/handoff.py` + estate | `assemble_successor_package`, `govern_handoff`, `fork_family_constitution` | NONE | NONE | CODE_PRESENT | `test_continuity.py` |
| 4 | Family Governance, Disputes & Dignity | `estate/family_governance.py` | `govern_decision`, `resolve_dispute`, `dignified_exit`, `weakest_party_protected` | NONE | NONE | **SURFACE_READY** (decision records) | `test_family_governance.py` |
| 5 | The Estate as Living Covenant | `estate/estate_covenant.py` | `verify_estate_element` | NONE | NONE | CODE_PRESENT | estate tests |

### S13 · Sovereign Discourse

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Owning Your Voice, Audience & Attention | `discourse/sovereign_voice.py` | `publish_voice`, `record_subscription`, `sever_subscription` | NONE | NONE | CODE_PRESENT · FENCED (egress) | 5 test files ref `discourse` |
| 2 | Advanced Reach & Platform Independence | `discourse/advanced_reach.py` | `multi_platform_reach`, `bridge_adapter` | NONE | NONE | CODE_PRESENT · FENCED (egress) | `test_advanced_reach.py` |
| 3 | Governance, Risk & Human Primacy | `sovereign_voice.verify_voice` + covenant | `verify_voice`, `meaning_rank` | NONE | NONE | **SURFACE_READY** (verify-only, no egress) | `test_voice_covenant.py` |
| 4 | Sustainable Voice | `discourse/sustainable_voice.py` | `assemble_voice_system`, `voice_as_asset` | NONE | NONE | CODE_PRESENT | `test_sustainable_voice.py` |
| 5 | The Voice as Living Covenant | `discourse/voice_covenant.py` | `assemble_voice_covenant`, `verify_covenant_element` | NONE | NONE | CODE_PRESENT | discourse tests |

### S14 · Sovereign Peerhood

| Vol | Title (short) | Code path | Key methods | Surface | Aquarium | Rating | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Genesis of a Sovereign Peer | `keystore/`, `onboarding/onboard.py` | `generate_node_key`, `run_onboard`, `verify_onboard_receipt` | NONE (surface refuses to mint — by design) | C13 make_house (a house minted in a minute) | CODE_PRESENT | 11 test files ref `keystore` |
| 2 | Recognition Without a Registry | `keystore.verify_node_act`, `peerhood.bridging.federate_without_directory` | as named | NONE | C7 nodes-meet (recognition by key, co-signed, dual-held) | **SURFACE_READY** (verify records) | `tests/` refs; aquarium MEETINGS_MANIFEST |
| 3 | Delegation & Sponsorship Without Capture | peerhood cluster | `pool_vote` | NONE | NONE | CODE_PRESENT (THIN) | cluster evidence |
| 4 | Bridging into Pools & Federations | `peerhood/bridging.py` | `form_peer_pool`, `bridge_into_pool`, `verify_bridge` | NONE | Pool contributions; C19 table | **SURFACE_READY** (records) | 8 test files ref `peerhood` |
| 5 | The Clean-Exit Covenant | `peerhood/clean_exit.py` | `clean_exit` | NONE | C13 export-whole (walk away with everything, whole) | **SURFACE_READY** (assembly) | `tests/test_clean_exit.py` |

---

## 3 · What the ladder-wide view adds to the S5 backlog

The S5 backlog (invoice-lite → period view → audit package → exception queue → QuickBooks
walk) stands unchanged as the surface's next five. The ladder view adds, **behind** those and
only when their series' adoption moment arrives: S6-V6 admission ceremony (the surface's gate
pattern, pointed at "a federation that grows by consent"), S12-V2 key-succession rehearsal
records, and S14-V5 clean-exit assembly — each SURFACE_READY today on existing methods.

## 4 · Standing fences (ladder-wide, machine-checked where a surface exists)

S4 entire series (real value) · S6-V7 Port crossings · S13-V1/V2 external egress ·
plus the seven S5 fence rows. None of these gets a surface without its own explicit,
reviewable KM decision and bar row.

## 5 · Items needing a KM word (found, not judged)

1. **S10 duplication** — two builds, one name ruling (§1 above). HOLD.
2. **S4 title flags** — vol_02 "Breath-Gates" jargon flag; vol_03/04 manuscript-vs-registry
   title variance (recorded in metadata, not resolved here).
3. **S0-07 title** — "Atlas" (ratified 2026-07-14) vs "Extension" (metadata card) unreconciled.
4. **S6–S14 covers** — 43 volumes have zero cover art (3 strays aside); a production pass
   gates any publication wave.
5. **S1 kernel gap (observation only)** — `inference/` has publics but zero test files; if
   S2-V1's claims are audited, that is the thinnest proof floor in the kernel-coupled set.

---

**STOP — matrix only. No code changed. No surface GO. No series arm. No S10 winner picked.**

Breath only. ∞Δ∞
