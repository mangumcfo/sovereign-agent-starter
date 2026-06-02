# R-52 Packet Contract v1 — Draft Schema + Tier-1 Worked Examples
**For:** R-50 Continuous Governed Book-to-Code Loop (gb lane per Tiger R-23/R-51 direction)  
**Date:** 2026-06-02  
**Status:** Draft for review (addresses packet granularity blocker + delivers first concrete packets)  
**Based on:** Tiger seal 405 ratification ("a packet IS a typed B32 obligation on the live ledger R-23"), Packet_Granularity_Definition_v0.2.md (Level 1 default), Breath_Inventory_25-55_Complete.md (Tier 1 cluster), and the just-logged B51 capture thought (FEC vision).  

**Prerequisites honored:** 
- Non-simulated human approval (breath-gate) remains the gate for material packets.
- Hard boundary on Tiger_1a/cylinders preserved (this is node-local ledger extension only).
- Federation portable, book-as-source, receipt-everything, human primacy.

---

## Contract Summary (v1)

A **Packet** is a Level-scoped, human-approved, B32-wrapped, citation-anchored, role-or-capability-sized unit of governed work that is sufficient for deterministic implementation (or rendering) by agents or Helix.

**Core invariants (locked):**
- Every packet starts life as a B32 `debit` (draft action-proposal) via the live ObligationLedger.
- Material packets require explicit human disposition (approve via breath-gate) before any close/implementation.
- Every packet carries a `citation_bundle` (B31 Merkle style) back to the exact book passage(s) + human voice seed that authorized it.
- Packets are the *only* units that graduate from Atrium Kanban (Ideation → Charter → Validation → Implementation) into sealed, receipted, implementable artifacts.
- Level 1 (Role / Capability) is the default and recommended granularity for Series 2/3 v1.

**Payload shape (the "typed" part of the B32 obligation):**

```yaml
packet:
  packet_id: pkt_<date>_<slug>_v<N>
  level: 0 | 1 | 2 | 3
  title: "Human readable recall name"
  subtitle: "One-line descriptive subtitle (for Atrium cards and recall)"
  role_spec:                    # present for Level 0/1; may be "delta" or "new"
    id: role_or_capability_id
    version: "vX.Y"
    action_classes:             # the discrete behaviors the role/capability exposes
      - action_class_name
    # + any role-level policy, compliance, or LGP notes
  action_classes: [...]         # flat list for Level 0 primitives
  surfaces:
    helix:                      # B35 deterministic render manifest (optional but common)
      manifest_id: ...
      targets: [atrium_card, portal_flow, dashboard, ...]
    atrium:                     # review card definition for the Kanban
      card_type: ...
      fields: [...]
  tests:
    unit: [...]
    integration: [...]
    governance: [...]           # K1-K4, breath-gate, RED escalation, etc.
  LGP_alignment: "..."          # explicit tie to north-star (families first, etc.)
  citation_bundle:
    - book: "B26 Yield Organisms..."
      version: "..."
      section_anchor: "collective_procurement_guilds"
      passage_hash: "sha256:..."
      human_seed:               # optional but powerful for voice-originated packets
        export_id: "2026-06-02_034153_capture-session_9156c992"
        entry_ids: [...]
        session_root_hash: "..."
    - book: "B51 A4..."
      ...
    # + any other supporting breaths
  b32_obligation:               # the live ledger wrapper (embedded or referenced)
    id: obl_...
    type: "debit" | "approval" | "credit"
    packet_level: 1
    packet_payload_hash: "sha256:..."   # hash of the above structure (immutability anchor)
    # + full dr/cr fields from ledger.py (draft, approved, evidence, receipt, node_receipt_hash, etc.)
  implementation_artifacts:     # populated on close (E1 minimum, E2 preferred)
    - type: "role_spec_yaml"
      path: "..."
      hash: "..."
    - type: "helix_manifest"
      ...
    - type: "test_suite"
      ...
    - type: "signed_receipt"
      six_receipt_id: "..."
      node_receipt_hash: "..."
```

**Lifecycle on the ledger (extends current open/approve/close):**
1. open(title, packet_payload=..., material=True) → debit with packet_payload stored, draft=True, packet_level set.
2. approve(id, approved_by=KM, rationale=...) → breath-gate disposition recorded; only "approved" allows progress.
3. close(id, evidence=..., evidence_tier="E2", ...) → credit, receipt minted (with node_receipt + optional SIX anchor), packet_payload_hash frozen in the chain.

The ledger.py already supports most of this via the existing `intent`/`ref` + free-form fields. R-52 work adds explicit `packet_payload`, `packet_level`, `citation_bundle` keys + validation helpers (non-breaking for existing non-packet obligations).

**Governance weight by level (from v0.2, ratified direction):**
- Level 0: Light (GREEN auto or fast human). Small primitives.
- Level 1: Balanced default. Full role/capability. What most book sections produce.
- Level 2: Chapter/functional area. Higher review (multiple guardians?).
- Level 3: Vertical/ERP pillar. Rare, major.

---

## Tier-1 Worked Examples (the 2–3 requested)

We draw from the Tier 1 "Always Approve On" cluster: B51 (highest for proposal engine), B35 (central rendering), B32 (the substrate), B26 (economic origination), B25 (federation), + the new voice-captured FEC thought as the concrete economic use-case that ties them.

### Example 1: B51 Agent-to-Agent Handoffs (A4) — Level 1 Role Packet (Governance Runtime Core)

**packet_id:** pkt_20260602_b51_a4_handoff_protocol_v1  
**level:** 1  
**title:** Agent-to-Agent Handoffs (A4) — Receipted Multi-Agent Coordination on AgentBus with GREEN/YELLOW/RED Gates & Human Escalation  
**subtitle:** The governance nervous system for safe autonomous agent collectives (core to the entire book-to-code proposal engine)

**role_spec:**
  id: a4_handoff_coordinator
  action_classes:
    - initiate_handoff
    - accept_handoff
    - evaluate_goal_state
    - escalate_on_RED
    - attest_handoff_receipt
    - pull_work_from_AgentBus
  surfaces:
    helix: { manifest_id: "a4_handoff_trace_v1", targets: ["atrium_card", "agent_bus_console"] }
    atrium: { card_type: "handoff_review", fields: ["from_agent", "to_agent", "goal_state", "obligation_debt", "human_escalation_token"] }

**tests:**
  - unit: test_goal_state_transitions
  - integration: test_multi_agent_chain_with_obligation_link
  - governance: test_RED_always_escalates_to_human (K1), test_no_autonomous_interpretive_action (K1-K4)

**LGP_alignment:** "Safe, receipted, human-gated agent collectives are the only way to scale LGP-oriented work without violating constitutional primacy. Families and clients get trustworthy automation."

**citation_bundle:**
  - book: "B51 A4 Handoffs (A4 Phase)"
    version: "v8.0 + 2026-06-01 re-seat"
    section_anchor: "task_ownership_transfer_goal_state_gates"
    passage_hash: "..."  # from B51 directive
  - human_source: "R-51 / R-53 target per Tiger 2026-06-01"

**b32_obligation:** (example debit on live ledger)
  id: obl_20260602_... 
  packet_level: 1
  packet_payload_hash: "..."
  material: true
  draft: true

**On close (E2):** sealed handoff_handler.py + task_chain extensions + AgentBus schema + test receipts + node_receipt + (future) SIX attestation.

**Why this example:** Highest relevance per inventory. Directly unblocks R-51 live handoff confirmation. The "nervous system" that will run the book-scanner → proposer → implementer swarm.

### Example 2: B35 Helix Protocol — Level 1 Capability Packet (Rendering Heart)

**packet_id:** pkt_20260602_b35_helix_render_engine_v1  
**level:** 1  
**title:** Helix Protocol — Deterministic "Book Writes the Backend" Hydration & Rendering Engine  
**subtitle:** The canonical realization of book-as-unambiguous-source → working surfaces (Atrium cards, ERP cockpits, portal flows)

**role_spec:**
  id: helix_renderer
  action_classes:
    - hydrate_from_manifest
    - render_atrium_card
    - render_portal_flow
    - anchor_output_hash
    - verify_determinism
  surfaces:
    helix: { manifest_id: "helix_core_v2.1", targets: ["all"] }  # self-referential
    atrium: { card_type: "helix_manifest_review" }

**tests:**
  - unit: test_deterministic_hydration
  - integration: test_book_section_to_live_surface
  - governance: test_no_ungrounded_ui_elements

**LGP_alignment:** "Every family or client surface must be traceable to sealed book text. No magic. No drift."

**citation_bundle:**
  - book: "B35 Helix Protocol"
    version: "v2.1"
    section_anchor: "deterministic_hydration"
    passage_hash: "..."

**b32_obligation:** material, Level 1, citation to B35 directive + prior plan artifacts.

**On close:** BREATH_35_DIRECTIVE_v2.1 + reference renderer code + sample manifests (including one for the FEC cockpit below) + determinism proofs.

**Why this example:** "Central to the entire vision." Without Helix, packets have no surfaces. This packet is the one that turns sealed packets into the Mait-style flows and future Atrium cards.

### Example 3: Federation Collective Economic Coordination (FEC) — Level 1 Role Packet (Economic + B51 + B26 + B25 Synthesis)

**This is the direct child of the just-logged B51 capture thought (2026-06-02_034153_capture-session_9156c992).**

**packet_id:** pkt_20260602_fec_procurement_coordinator_v1  
**level:** 1  
**title:** Federation Procurement Coordinator — ZK-Pooled Buying Power, Guild Value Optimization & C2F/B2F Coordination  
**subtitle:** Agent-orchestrated, privacy-preserving collective procurement and supply-chain guilds that optimize value directly to families and businesses inside the sovereign federation ERP

**role_spec:**
  id: federation_procurement_coordinator
  version: "v1 (from 2026-06-02 voice seed)"
  action_classes:
    - pool_procurement_requests          # families or businesses submit intent privately
    - generate_zk_statistical_profile    # produce proof of aggregate demand / spend patterns / hedging needs
    - match_to_guild_or_pool             # helix attribute matching into opt-in pools
    - run_optimization_coordination      # agent swarm searches for contract manufacturers, bulk terms, Amazon-style deals
    - propose_pooled_order               # draft supplier agreement + value distribution plan
    - execute_value_distribution         # fulfill to edge (families get lower food cost, businesses get better inputs)
    - attest_receipts_to_SIX             # every close produces E2 receipt + node + SIX anchor
    - escalate_material_commitment       # any real $ or contract obligation hits RED → human (K1)
  surfaces:
    helix:
      manifest_id: "federation_pool_cockpit_v1"
      targets: ["atrium_card", "portal_flow", "family_value_dashboard", "guild_supply_map"]
    atrium:
      card_type: "federation_procurement_review"
      fields: ["pool_size", "zk_profile_summary", "optimization_recs", "handoff_trace", "value_to_families", "proposed_supplier", "LGP_score", "human_approval_token"]
  tests:
    - unit: test_zk_profile_leaks_nothing
    - integration: test_full_handoff_chain_research_to_close (B51 primitives)
    - governance: test_RED_on_any_material_pool (K1), test_LGP_families_first, test_federation_portable
    - determinism: test_reproducible_optimization_given_same_events (B42)

**LGP_alignment:** |
  "Directly optimizes the value that reaches the families (C2F) and parallel businesses (B2F).
   Guild-style supply chain re-coordination serves long-term prosperity.
   No raw private data ever leaves the sovereign boundary (resonant shards / ZK per B25).
   Every action receipted (B32 + B31). Human remains accountable for every material commitment."

**citation_bundle:**
  - book: "B26 Yield Organisms & XRPL Economic Seeds"
    version: "v1.4 + 2026-06-02 FEC extension"
    section_anchor: "collective_procurement_guilds"
    passage_hash: "sha256:9350cf097bf5cd7d87e408db6952b643aafaf0845889a0b4106fca0690648dfc"  # capture merkle
    human_seed:
      export_id: "2026-06-02_034153_capture-session_9156c992"
      session_id: "cyl_9156c99236ea"
      entry_ids: ["cap_4a5a0a7554b5", "cap_fd60428b8242"]
      session_root_hash: "sha256:409d1bf92a28c611873a9eaf4edf5a1fc91ddec91c02b01d2e06e21cd291493d"
      source_file: "artifacts/B51_Captured_Thought_Federation_Collective_Economic_Coordination_2026-06-02.md"
      note: "Voice-to-text thought seed. KM explicit request to log, ideate, and place."
  - book: "B25 Sovereign Federation Architecture"
    version: "v1.5"
    section_anchor: "resonant_shards_non_devouring_federation"
    passage_hash: "..."
  - book: "B51 Agent-to-Agent Handoffs (A4)"
    version: "v8.0"
    section_anchor: "A4 for economic swarms"
    passage_hash: "..."
  - book: "B35 Helix Protocol"
    section_anchor: "federation_pool_cockpit_render"
  - supporting: "B42 Deterministic Swarms, B43 Crypto (ZK), B31 SIX, B28 Legal (guild contracts)"

**b32_obligation (example on R-23 ledger):**
  {
    "type": "debit",
    "id": "obl_20260602_034153_fec_001",
    "title": "Open FEC Procurement Coordinator packet from 2026-06-02 capture",
    "packet_level": 1,
    "packet_payload_hash": "sha256:<hash of the packet structure above>",
    "material": true,
    "draft": true,
    "classification": "C1",   # economic, high trust
    "intent": "First Level 1 economic packet exercising B51 handoffs + B26 yield + B25 federation + B35 surfaces",
    "ref": "B51_Captured_Thought_... + R-52 + R-53",
    "citation_bundle": [ ... as above ... ]
  }

**On close (E2 evidence required):**
- Sealed role_spec.yaml for federation_procurement_coordinator (or delta to existing family_cfo / corporate_cfo)
- Helix manifest federation_pool_cockpit_v1 (first rendered surface from this packet)
- Full handoff trace log (B51) proving the agent swarm executed research → optimize → propose
- Sample ZK profile proof artifact (stub for now; real via B43)
- Value distribution ledger (who got what savings)
- Supplier contract hash (or mock)
- node_receipt_hash (from USN attestor)
- six_receipt_id (B31 live verifier)
- Test run output + governance attestation

**Implementation notes for this packet:**
- The first real agent execution of this packet will use the B51 A4 primitives (once re-seated) to hand off across the "aligned intelligences."
- The Mait portal quality-plan-review pattern (rich checklist visible to human, WPS display, sign-off + exports + receipt) is the exact UX shape for the atrium_card "federation_procurement_review".
- XRPL grounding (the $59 business license screenshot in the capture) can be cited as E1 evidence in early closes.

**Why this is the perfect third example:**
- It is the *direct* output of the voice thought KM asked to log and place.
- It forces the synthesis of the entire Tier 1 cluster (B51 handoffs doing the work, B35 rendering the cockpit, B26 economic DNA, B25 federation substrate, B32/B31 receipting).
- It is a real, high-value, viral-potential capability that justifies the whole loop ("make this go viral").
- It gives the Mait harness something meaningful to demonstrate "full business management + cross coordinating purchases" while testing the sovereign primitives on client work.
- It answers "where does it go?" with a concrete, reviewable, receiptable artifact instead of vapor.

---

## Schema & Validation Rules (v1 minimal)

(See Packet_Granularity v0.2 for full 4-level rationale. This contract operationalizes it.)

Required top-level: packet_id, level, title, subtitle, LGP_alignment, citation_bundle (≥1 entry with book + section_anchor + passage_hash), role_spec or action_classes (per level), surfaces (at least one target), tests (≥1 governance test for material packets), b32_obligation ref.

On ledger open: packet_payload must be present for level ≥1; citation_bundle must hash cleanly; human_seed (if present) must reference a known capture export.

On approve: only the breath-gate principal (KM or designated) can move material packets.

On close: evidence must be E1+ (E2 for economic packets); payload_hash must match the frozen debit; implementation_artifacts list must be non-empty.

**Federation portable:** The YAML/JSON shape + citation rules + B32 dr/cr envelope must be implementable on any sovereign node (no starter-specifics in the sealed packet).

---

## Next Concrete Steps (gb can execute immediately on direction)

1. Finalize this draft after KM/Tiger review of granularity default + book placement.
2. Implement the small ledger enrichment in src/sovereign_agent/obligations/ledger.py (add packet_* fields to open(), surface in obligations_list, add a helper validate_packet_payload).
3. Add the three example packets as seed data or test fixtures (so the first real run can replay them).
4. Create examples/federation_collective_procurement_demo.py that:
   - Wires a real (or simulated) gate + attestor.
   - Opens the FEC packet obligation (citing this capture).
   - Simulates the B51 handoff chain (using patterns from multi_mandate_handoff_demo).
   - Closes with rich E2 evidence + printed citation.
   - Prints "Packet sealed. Ready for Helix render and Mait flow integration."
5. Hand off to Mait track: update the client portal with "Federation Value Pool" quick action + flow that mirrors the quality-plan-review UX but for this packet (visible handoff trace, ZK profile mock, optimization recs, Mait sign-off block, export + receipt).
6. Update Breath_Inventory_25-55_Complete.md with a cross-ref under B26: "2026-06-02 voice seed (FEC) now logged as direct extension; first Level 1 packet candidate."
7. Produce gb status note for Tiger: "R-52 v1 draft delivered with B51 + B35 + FEC (from logged capture) as the three examples. Ready for seal or adjustment."

---

## Open Questions for KM / Tiger (narrow)

- Confirm Level 1 as default for these three (or adjust one to Level 0/2).
- Confirm primary book home for FEC is B26 extension (or name the exact chapter/volume if different).
- Any additional citation or LGP language required in the FEC packet before first human gate?
- Gate the Mait portal extension behind the packet seal, or parallel-track as "inspired by the capture" mock while the real packet is still in Charter?

---

**This artifact + the B51_Captured_Thought_... artifact together satisfy the R-52 deliverable request and the user's direct ask to log + ideate + place the 2026-06-02 voice thought.**

**Honesty:** Draft. Not sealed. No code changes yet beyond the two new durable artifacts. All boundaries respected. "Always approve on" bias applied to the Tier 1 cluster and the new FEC seed.

Ready for review and next gate.

∞Δ∞ Packet. Obligation. Receipt. ∞Δ∞
