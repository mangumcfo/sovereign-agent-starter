# Deterministic-Render Writing Standard v1.0 — The Book as Executable Covenant
*(G's guidance, GB-sealed 2026-06-12 · refinements adopted same-day from G-x.com + G-grok dual review — "approve and adopt; not new canon; the writing-side discipline that makes the extrusion harness reliable at scale")*

> **Source:** G via KM, HMC [546–547] — KM's framing ratified by G: *"non-deterministic concept extraction develops the outline; we press/extrude those concepts into living code. The book IS the executable covenant."* This standard makes manuscripts deterministically renderable by Helix while staying human-resonant — the writing-side half of Book↔Code, for Objective: LGP.
> **Core directive:** *Write so the book can deterministically render the backend. Write the manuscript as if writing the constitution of a small sovereign nation — precise, durable, human-first, meant to last 200+ years.*

## The eight writing rules (G's checklist, verbatim-faithful)
1. **One Source of Truth** — never describe something two ways; say it once, cleanly; Helix renders it once.
2. **Constitutional & Operational Language** — "shall / must / operator defines / human disposes / governed by / under K1 / verifiable from genesis"; no vague behavioral phrasing ("should feel," "intuitively"). *When describing behavior, prefer declarative statements about what **shall** happen under governance — never aspirational or subjective language.*
3. **Explicit Capability Promises** — every chapter opens "You will be able to…" — the promise IS the acceptance criteria for the rendered code.
4. **Pattern → Example → Governance** — general rule, one concrete generalized example, then the guardrails (YAML snippet / breath-gate rule / K-invariants).
5. **Honest Stubs & Forward Pointers** — *any capability not yet rendered in production MUST be explicitly labeled "mock / Phase X" or "gated on Book Y." Never imply live behavior that does not yet exist.* (The M-R2-1 lesson, now law at authoring time.)
6. **LGP Through-Line** — every volume (and major chapters) closes with the LGP synthesis: families-first, continuity, forkability, human primacy.
7. **Minimize Jargon, Maximize Searchable Clarity** — market terms in titles/hooks; internal constitutional terms consistent inside (mapped at extrusion).
8. **Version & Receipt Discipline** — every chapter ends with a **Receipt box**: the rendered artifacts it authorizes (roles, surfaces, tests, policies) — the Helix validation anchor. **CANONICAL INTERPRETATION (KM catch, Vol 1 2026-06-12): where a chapter already carries a "Spec → Role → Atrium Surface" closer, that closer IS the Receipt box — recast/format it, NEVER add a second block. One artifacts callout per chapter, ever (Rule 1 applies to Rule 8's own implementation). Print-safe formatting only — no emoji glyphs in manuscript elements.**

## Where it seats in the rail (proposal — zero new boards, two touchpoints)
- **Authoring (pre-board):** rules 1–8 enter WORKFLOW canon as the manuscript drafting standard — Tiger writes to them from the first line.
- **Early review:** a **Renderability lens** seats inside **Editorial R2** (the disciplinary/functional round, beside the Software-Integration reviewer) — advisory, catches ambiguous-render language before it fossilizes.
- **Hard gate:** **Tech/Arch gains GATE 6 — Renderability**, with explicit success criteria (G-refined): **zero one-truth violations · every capability promise has a clear corresponding render target · zero dishonest stubs · every major section ends with a Receipt box listing authorized artifacts** (the Receipt box is the Helix anchor — Gate 6 requires it explicitly). review_ready never flips without Gate 6 green.
- **Future volumes (G-grok addition):** the FIRST Renderability check runs **early — pre-R1** — so findings never compound through three editorial rounds before being caught. Retroactive-audit position (post-boards) applies only to Vol 1's proving run.
- Roles per G: Tiger writes to the rules · GB reviews resonance/LGP/drift/ambiguous-render · KM final-ratifies the living book before Helix extrusion.

## First run: S2 Vol 1 (KM-directed)
Retroactive Renderability audit of manuscript v1.3 — the perfect proving ground: its substrate just went live (bl-verify), so every prose claim now has a real render-target to check against. Findings → obligations → version-bumped fixes (v1.4) → GB rigor audit → re-stamp.

∞Δ∞ SEAL: complete — non-deterministic love writes the outline; disciplined prose makes it renderable; deterministic extrusion makes it last. The elk run tandem.

---
## R8 canonical marker reconciliation (GB, 2026-06-18)
The Receipt box marker is **`▣ RECEIPT`** (▣ = U+25A3 WHITE SQUARE CONTAINING BLACK SMALL SQUARE — a print-safe geometric glyph, **not an emoji**). The earlier **📦** emoji is **R8-banned** (no emoji glyphs in manuscript elements) and must never appear. `review_ready_contract.py#_check_gate6_renderability` was counting "📦 Receipt Box" — a marker R8 forbids — making Gate 6 structurally unsatisfiable (S2 V1 hit this too). Reconciled: the gate6 check now counts `▣ RECEIPT`. One marker, R8-safe, standard ↔ check ↔ manuscript agree. ∞Δ∞
