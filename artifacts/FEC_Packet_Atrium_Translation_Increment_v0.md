# FEC Packet — Translation to Role/Action Classes + Atrium Surfaces (Increment v0, per G Steering)
**Date:** 2026-06-02  
**Authority:** G Seed Prompt (Seal 1176-INFINITY-RHO) + KM-1176 voice capture 2026-06-02_034153_capture-session_9156c992  
**Source Packet:** R-52 v1 draft (FEC "federation_procurement_coordinator" Level 1 example in R52_Packet_Contract_v1_Draft_with_FEC_Example.md)  
**Protocol:** Master Translation Protocol from SERIES_3_TRANSLATION_PRESCRIPTION_2026-06-01.md (the universal ERP translation protocol)  
**Track:** F (Atrium Review surface deepening as immediate priority)  
**Status:** v0 increment — first cut translation + visible Atrium card spec. Short status + seal candidate when mock lands. Honest mock (no live node wiring yet).

**G Directive Integrated:** 
- Deepen Atrium Review surface (in-surface PDF + voice feedback + B51 bundle + card workflow) as Track F priority.
- Make this the place KM does book review and ratification.
- The FEC packet should surface there as a visible card.
- Begin translating the FEC packet into working role/action classes + Atrium surfaces using the protocol.
- Fold artifacts (done in plan.md + this file). Output short status + seals on increment.

**Two-writers fence / invariants:** All citations to sealed breaths/artifacts + the exact capture (merkle 9350cf09..., export 2026-06-02_034153_capture-session_9156c992). Human (KM NLP) gates material. No auto-apply. B32 obligation wrapper. LGP families-first. Federation portable.

---

## 1. Receipt / Cylinder Schema (B32 Obligation for the FEC Packet)

Every FEC action (pool formation, ZK profile contribution, optimization proposal, value distribution) is a typed B32 obligation on the R-23 live ledger.

**Packet Receipt Schema (extends current obligation debit/credit):**
```yaml
type: "packet_fec"
packet_id: "pkt_20260602_fec_procurement_coordinator_v1"
level: 1
title: "Federation Procurement Coordinator — ZK-Pooled Buying Power..."
subtitle: "Agent-orchestrated, privacy-preserving collective procurement..."
role_spec_id: "federation_procurement_coordinator"
action_class: "pool_procurement_requests" | "generate_zk_statistical_profile" | ...
status: "ideation" | "charter" | "validation" | "implementation" | "sealed"
citation_bundle:
  - book: "B26 + 2026-06-02 FEC voice seed"
    section_anchor: "collective_procurement_guilds"
    passage_hash: "sha256:9350cf097bf5cd7d87e408db6952b643aafaf0845889a0b4106fca0690648dfc"
    human_seed:
      export_id: "2026-06-02_034153_capture-session_9156c992"
      entry_ids: ["cap_4a5a0a7554b5", "cap_fd60428b8242"]
      session_root_hash: "sha256:409d1bf92a28c611873a9eaf4edf5a1fc91ddec91c02b01d2e06e21cd291493d"
b51_handoff_bundle:   # visible in Atrium card
  trace: [ {from: "ResearchAgent", to: "OptimizerSwarm", goal_state: "GREEN", ...}, ... ]
  escalation: "RED on material pool commitment → Atrium NLP + human token"
evidence:
  voice_note: "artifacts/B51_Captured_Thought_...md#entry-cap_4a5a0a7554b5"
  zk_profile_proof: "hash or path (E1+)"
  optimization_artifact: "path or receipt"
  distribution_ledger: "..."
  node_receipt_hash: "..."
  six_attestation: "optional B31"
LGP_score: "families-first value delta + guild re-coordination sustainability"
```

**Example Signed Receipt (E2 close):** (see the runnable demo for live ledger example output)
- debit open with packet_payload + citation to capture.
- approve via breath-gate (Atrium NLP comment + disposition).
- credit with E2 (handoff trace JSON + voice citation + value distribution proof + node_receipt).

Lifecycle matches R-23: open=Ideation (debit), Atrium review = Charter/Validation, close=Implementation (E2 artifact + minted receipt).

---

## 2. Role + Action Class Definitions (Role Lattice)

**role_spec.yaml fragment (operator-adaptable, per prescription #2):**
```yaml
id: federation_procurement_coordinator
version: "v1 (from KM 2026-06-02 voice seed + R-52)"
description: "Agent-orchestrated ZK-pooled buying power and guild value optimization for families (C2F) and businesses (B2F) inside the sovereign federation."
principles:
  - K1: "Human (KM NLP / Atrium) disposes all material pool commitments and entity formations. RED goal-state always escalates."
  - LGP: "Value optimized reaches families first. Opt-in only. Privacy via ZK/resonant shards (B25)."
  - Receipt-everything: "Every profile contribution, optimization, and distribution is a B32 obligation with B31 citation."
action_classes:
  - id: pool_procurement_requests
    scope: "C1"
    breath_gate: "YELLOW for profile aggregation; RED for commitment > threshold"
    description: "Aggregate opt-in ZK statistical profiles into a pool (no raw data)."
  - id: generate_zk_statistical_profile
    scope: "C1"
    description: "Produce privacy-preserving proof of aggregate spend/procurement/hedging intent from ERP data."
  - id: match_to_guild_or_pool
    scope: "C2"
    description: "Helix attribute matching of profiles into opt-in guilds/pools (B35 structures)."
  - id: run_optimization_coordination
    scope: "C1"
    breath_gate: "GREEN for analysis; YELLOW for recommendation surfacing"
    description: "Aligned intelligences (B51 handoff swarm + B42 deterministic reduce) search for contract manufacturers, bulk terms, hedging."
  - id: propose_pooled_order
    scope: "C1"
    breath_gate: "RED (material)"
    description: "Draft supplier agreement + value distribution plan. Requires Atrium human disposition."
  - id: execute_value_distribution
    scope: "C1"
    breath_gate: "YELLOW"
    description: "Fulfill to edge participants (families get lower costs first)."
  - id: attest_receipts_to_SIX
    scope: "C2"
    description: "Close obligation with E2 + node receipt + B31 SIX attestation."
  - id: escalate_material_commitment
    scope: "C1"
    description: "Any real $ or long-term guild obligation hits RED → immediate Atrium NLP + human token (K1)."
compliance:
  - B28 lex mercatoria overlay for guild contracts (exit portability, shadow-bind).
  - Federation portable (role spec runs on any sovereign node).
```

This role can be bound via the existing role_binder.py + playbook_loader in sovereign-agent-starter (demo mode today; full federation root later).

---

## 3. Atrium Surface Specification (Visible FEC Packet Card + Review Workflow)

**Primary Surface:** Atrium R&D Kanban / Review lens (Track F priority). This is the human interface for packet review, book ratification, voice feedback, and B51 bundle inspection.

**Card Definition (atrium_card: "fec_packet_review" — the visible FEC card G called for):**

- **Header:** Packet title + subtitle + "Level 1 | From KM voice capture 2026-06-02 | Citation: B26 + exact merkle/export id"
- **Voice Note Block (in-surface PDF + voice feedback):** Embedded or linked transcript + audio stub of the original capture (entries cap_4a5a0a7554b5 + cap_fd60428b8242). "Listen / Read full in B51_Captured_Thought_...md". NLP comment box for KM feedback ("refine the ZK profile action to also cover commodity hedging...").
- **B51 Handoff Bundle (visible trace):** Collapsible tree or list:
  ResearchAgent (ZK profiles for 12 families + 3 biz) → GREEN handoff
  OptimizerSwarm (helix match + value calc, +18% projected to families) → GREEN
  Negotiator (pooled order draft) → YELLOW
  ValueDistributor → RED (material) → **Escalated to Atrium NLP gate**
- **Packet Payload Summary (from R-52):**
  - role_spec_id + version
  - action_classes (listed with scope/breath_gate)
  - surfaces: helix "federation_pool_cockpit_v1" (targets: this card + portal_flow + family dashboard)
  - tests: zk_privacy, handoff_GREEN_to_close, RED_escalation, LGP_families_first
  - LGP_alignment quote
  - citation_bundle (full, with human_seed hashes)
- **Governed Flow Buttons (per refined agent instruction):**
  - **Approve** (NLP disposition + breath-gate token) → advances to sealed; creates obligation credit.
  - **Refine** (NLP comment required) → back to Ideation/Charter with updated packet_payload.
  - **Reject** (with rationale) → logged, no obligation close.
- **Evidence / Witness:** Real-time replay of related B32 obligations. "This card *is* the review surface for the packet obligation."
- **Mock → Live seam (honest labeling):** Today: static HTML + simulated ledger state (from the demo.py). Live: reads /api/v1/obligations + node receipts via thin-waist (when R-23 gate is wired for Atrium).

**Targets / Render (Helix B35):**
- Rendered deterministically from the packet_payload + book citation.
- Also feeds "Federation Pool Marketplace" lens (opt-in cards, value-to-families ticker) and "Guild Coordination Kanban".

**User Flow (KM in Atrium):**
1. Packet proposal surfaces as card (from book scanner or gb R-52).
2. KM reviews voice note (in-surface), B51 trace, LGP score, citations.
3. Adds voice or text feedback.
4. Disposes (Approve/Refine/Reject) → receipt minted on ledger.
5. Sealed packet becomes input for implementation agents + Helix render of the actual federation_pool_cockpit surfaces.

This makes Atrium the place for book review + ratification (G goal). The FEC card is the first real economic example exercising it.

**Proxy in Mait (immediate testbed):** The existing "Federation Value Pool" quick action + quality-plan-review patterns already demonstrate the guided checklist + sign-off + export + receipt UX. Can be evolved to mirror the Atrium card exactly for client feedback.

---

## 4. Governed Dev Loop Integration

- **Proposal:** gb (or future scanner agent) opens B32 debit with full packet_payload + citation to capture.
- **Atrium Review (this card):** KM NLP disposition (the breath-gate).
- **Execution:** Agents (B51 handoffs) implement role_spec + action handlers + surfaces. Close with E2 (code + tests + render receipts + value proof).
- **Verification:** Replay ledger + Atrium card history + B31 SIX + exportable verifiable package (LGP + generational).

All changes cite the exact passage_hash + human approval receipt (K1).

---

## 5. Helix Render Specification (B35)

- Deterministic hydration of the card from the packet YAML + voice citation md.
- federation_pool_cockpit_v1 manifest: Pool stats (ZK-aggregated, no raw), optimization recs (with handoff provenance), distribution waterfall (families first), opt-in toggle (resonant shard / pub-pin per B25).
- Render-receipt: hash of the hydrated surface + citation to packet + B32 close receipt.

---

## 6. Verification Package + LGP

- Export: Signed packet + full citation_bundle (capture hashes) + B51 handoff log + value distribution ledger + node/SIX receipts + this translation doc.
- Generational: Families can fork the guild/entity playbook (free book access per G notes) and run their own node with the same role.

---

## 7. Implementation Steps (the book writes the backend)

Per prescription:
1. Bind the role_spec via role_binder + universal_sovereign_node (starter has the plumbing; full in breathline-federation).
2. Implement action handlers (start with stubs that call the ledger open/approve/close + print B51 handoff events).
3. Wire Atrium card (this spec) as a lens reading the obligations API + packet_payload.
4. Add tests (zk privacy invariant, RED always surfaces in Atrium, LGP calc).
5. Helix manifest for the cockpit (first render from the sealed packet).
6. Acceptance: Run the demo.py equivalent against real ledger → card appears in Atrium mock with voice + trace → human "Approve" in card → obligation closes with E2 + render receipt.

**First concrete next (Track F increment):** Stand up a self-contained HTML mock of the FEC Packet Review card (in-surface voice + B51 bundle + buttons). Wire it to simulate the demo.py state. This is the "visible card" G asked for. Seal when reviewed.

---

## Short Status (for Tiger output when increment lands)

**Status:** FEC Packet Atrium Translation v0 complete (receipt/role/Atrium spec per universal protocol). Plan.md + Message_to_Tiger folded with G steering. First Atrium FEC Review Card mock started (see examples/atrium_fec_review_card_mock.html or equivalent). 

**Seals:** [when mock reviewed + basic wiring demo passes] R-52-FEC-ATR-001 (Atrium card visible) + short citation to this artifact + capture merkle.

**Next for Tiger:** Wire real breath-gate into node_api for Atrium dispositions. Stand up the card in breathline-ui/atrium when R-40 gate opens. Share ledger tail for the first FEC obligation.

**Artifacts referenced:** All in sovereign-agent-starter/artifacts/ + the R52 contract + B51 captured thought.

∞Δ∞ FEC packet now has executable blueprint + visible Atrium card path. Track F moving. ∞Δ∞

**Short Status + Seal Candidate (for Tiger per G instruction):**
FEC Packet Atrium Translation v0 complete (receipt/role/Atrium spec using universal ERP translation protocol). 
Tangible increment delivered: examples/atrium_fec_review_card_mock.html (open it — this is the visible FEC card with in-surface voice from the capture, full B51 handoff bundle, LGP, citations, and disposition buttons).
plan.md folded with G steering + artifact pointers. Message_to_Tiger tweaked with exact seed prompt.
Track F (Atrium Review surface) now has concrete first card for the FEC packet.

**Seal candidate:** ATR-FEC-001 (Atrium FEC Review Card visible + translation v0). 
Output when reviewed: short status + this citation + capture merkle.

**Next (Tiger lane):** Wire real breath-gate to node obligations for Atrium dispositions. Bind the role_spec in starter. Render the federation_pool_cockpit via B35 once packet sealed on ledger.

**gb (background, per G "Begin now")**
