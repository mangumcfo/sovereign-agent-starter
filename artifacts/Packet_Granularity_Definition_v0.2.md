# Packet Granularity Definition — v0.2
**For:** R-50 Continuous Governed Book-to-Code Loop  
**Date:** 2026-06-01  
**Status:** Draft for Review (Addresses blocker identified in R-23 / R-50 planning)

---

## Context & Why This Matters Now

Tiger (in R-23 / R-51 update, seal 405) explicitly called out **packet granularity** as gb's stated blocker for advancing R-50.

This document extracts and advances the earlier strawman (from plan.md) into a durable, reviewable artifact. It is intended to unblock concrete packet definition work against the Tier 1 breaths identified in the Breath Inventory.

**Core Requirement (from KM vision):**
When a book/chapter/section reaches the fine-tune stage, it must produce a **hashed set of approved packets**. These packets must:
- Be reviewable and approvable in natural language via Atrium.
- Contain everything needed for deterministic implementation (roles, actions, surfaces, tests, citations).
- Carry full B32 receipting + exact book provenance + human approval.
- Be small enough to be governed, yet large enough to be meaningful.

---

## Guiding Principles

1. **Human Primacy** — All material packets require human disposition (Y/N/M + phrased feedback). Agents propose; humans dispose.
2. **Receipted Everything** — Every packet must be wrapped in B32-style obligations from Ideation onward.
3. **Book as Source of Truth** — Every packet must carry an immutable citation back to the exact book passage(s) that authorized it.
4. **Scalable Rigor** — Granularity must support Major / Mid / Minor changes without forcing everything through the same process.
5. **Agent-Friendly** — Packets must be generatable and verifiable by the governed agent loop (scanners → proposers → implementers).
6. **Federation Portable** — The packet format itself must work across sovereign nodes.

---

## Proposed Packet Levels (v0.2)

### Level 0: Primitive / Action-Class Packet
**Scope:** One discrete, low-risk primitive (single action class, small utility function, narrow governance rule, or tiny Atrium surface element).

**Typical Contents:**
- Single action class definition + handler spec
- Minimal governance / compliance rules
- Tiny Atrium surface fragment (if any)
- Test expectations (unit level)
- LGP alignment note
- Exact book citation (paragraph or sentence level)
- Lightweight B32 obligation proposal

**Examples:**
- A new `validate_cross_sell_rate()` action class.
- A small utility for obligation rollup formatting.
- A single new validation rule in an existing guardian.

**Governance Weight:** Lightest. Suitable for fast iteration on GREEN items or well-scoped MINOR changes.

**When to Use:** Small, well-understood increments where the book text is already very precise.

**Risk:** Fragmentation if over-used. Requires strong conventions to avoid "death by a thousand tiny cards."

---

### Level 1: Role / Capability Packet (Recommended Default for v1)

**Scope:** One coherent role or major capability (the natural unit most book sections describe).

**Typical Contents:**
- Full role_spec (or major update to an existing role)
- All associated action classes
- Relevant Atrium surfaces / card definitions
- Test suite (unit + integration expectations)
- Helix render requirements (if the capability produces rendered output)
- LGP alignment + Series alignment notes
- Strong book citations (section or multi-paragraph level)
- Full B32 obligation proposal (Charter stage onward)

**Examples:**
- The complete "Synergy_Validation_Guardian" role with its 5–7 action classes.
- The "Revenue_Lane_Organism" capability (drawing from B26).
- A new "SIX_Attestation_Verifier" surface + supporting roles.

**Governance Weight:** Balanced. This is the sweet spot for most book-driven development.

**When to Use:** The majority of normal development. Maps cleanly to book chapters/sections and produces deployable, reviewable units.

**Recommendation:** Make this the **default packet level** for the v1 loop.

---

### Level 2: Chapter / Functional Area Packet

**Scope:** A coordinated set of roles, surfaces, and capabilities that together implement a book chapter or major functional area.

**Typical Contents:**
- Multiple related role_specs + action classes
- Full set of Atrium surfaces for the area
- Data models / state schemas (if new)
- Comprehensive test strategy
- Helix manifest updates
- Cross-role impact analysis
- Strong narrative book citation (whole chapter or major section)
- Higher-rigor B32 proposal (may trigger additional guardians)

**Examples:**
- Full implementation of the "Cross-Functional Due Diligence" chapter from the MA book.
- The complete "Sovereign Inference Exchange" surface set (tying B31 + B51 + B32).
- A major new ERP spine module.

**Governance Weight:** Heavier. Requires more cross-functional review.

**When to Use:** Major new capabilities or when the book itself treats the material as a single coherent deliverable.

---

### Level 3: Vertical / Major Module Packet (Rare in v1)

**Scope:** An entire vertical or large cross-cutting module (multiple chapters, new major product area).

**Typical Contents:** Everything in Level 2, plus:
- Full architecture and integration specs
- Federation portability notes
- Long-term maintenance / evolution plan
- Significant constitutional impact assessment

**Governance Weight:** Heaviest. Likely requires KM + cross-role + possibly external review.

**When to Use:** Only for explicitly scoped "major vertical" work (e.g., launching an entirely new Series 3 ERP pillar).

---

## Recommended Operating Model for v1 of the Loop

- **Default:** Level 1 (Role / Capability Packets)
- **Light path:** Level 0 allowed for small, low-risk, GREEN changes (lighter gates, faster cycle)
- **Heavy path:** Level 2 (and rarely Level 3) for major work — with explicit scoping in the Charter stage and higher review rigor
- **Card Metadata:** Every Atrium Kanban card must clearly declare its packet level + size classification (Major/Mid/Minor) from the Charter stage onward.
- **Evolution:** The system must support "packet splitting" and "packet merging" over time as understanding deepens during book writing.

---

## Open Design Questions (Current Blockers)

1. **Exact Packet Schema** — What is the minimal mandatory structure of a packet file/object? (YAML? Structured data + receipts? Merkle root + citation bundle?)
2. **Book Citation Format** — How do we make citations machine-verifiable while remaining human-readable? (Section anchors? Paragraph hashes? Direct quotes + stable IDs?)
3. **Private vs Published** — How do mandate scoping (private development vs published books) affect packet visibility and governance weight?
4. **Immutability Trigger** — At what exact moment does a packet (or set of packets) become immutably tied to the book? (End of fine-tune pass? Human "seal chapter" signal? First successful implementation?)
5. **Agent Generation Rules** — What are the constitutional bounds on what agents are allowed to propose autonomously vs what must always carry a human "intent seed"?

---

## Connection to Tier 1 Breaths (from Breath Inventory)

This granularity model is designed to be immediately testable against the highest-value existing work:

- **B32 + B51 + B42 + B30 cluster** → Naturally produce Level 1 and Level 2 packets (roles, handoff protocols, obligation primitives, agent behaviors).
- **B35 (Helix)** → Strong candidate for Level 2 packets around rendering capabilities and manifest-driven surfaces.
- **B43 + B39** → Level 0/1 packets for crypto primitives and wiring rules.
- **B31 (SIX)** → Excellent source of Level 1 packets for verification surfaces, schemas, and attestation roles.
- **B26 (Yield Organisms)** → Level 1–2 packets for revenue lane organisms and XRPL integration patterns.
- **B28 (Legal Hardening)** → Governance and compliance rules that should appear inside many packets (especially Level 1+).

---

## Next Steps

1. KM / Tiger / G direction on the recommended default (Level 1) and the operating model above.
2. Once direction is given, gb can produce the first concrete packet schema (YAML + receipt bundle) and example packets drawn from 2–3 Tier 1 breaths (e.g., B32 handoff primitive + B35 Helix surface + B51 agent handoff role).
3. This directly unblocks detailed R-50 packet work and gives Tiger a clear target for R-51 live handoff confirmation.

---

**Status:** This v0.2 is ready for feedback. It replaces the earlier in-progress strawman in plan.md.

**Durable location:** This file (extracted for the same durability reasons as the Breath Inventory).

*Extracted 2026-06-01 in response to Tiger's R-23/R-51 update identifying packet granularity as the current R-50 blocker.*