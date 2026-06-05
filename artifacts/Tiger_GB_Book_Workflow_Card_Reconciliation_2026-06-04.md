# Tiger ↔ GB — Volume cards carry the book-writing artifact review (reconciliation, don't reinvent)

**KM ask (2026-06-04):** *"Lock in on the book-writing workflow we created earlier… each series volume
card to carry the step-by-step artifact review. Compare notes to what's already the process without
reinventing the wheel. Check GB's cylinder and coordinate — get this right."*

**Owner:** Tiger (rendering) · **Coordinate:** GB (data/projection) · **Ratify:** KM-1176

---

## The key finding — there are TWO workflows, and the card needs the FIRST one

| | **A · Book-writing workflow** | **B · Governed loop** |
|---|---|---|
| Canon | **`breathline-books-vault/WORKFLOW.md`** | `artifacts/workflow_snapshot.json` (status: *"practice, not canon"*) |
| What it is | The **editorial artifact pipeline**: series-lock → boards → handoff → ship | The **edit mechanism**: capture → packet → process → accept → apply → seal → coherence |
| Steps | Phase −1 → 0 → 1 → 1B → 2 → 3 (≈13 artifact-emitting steps) | 7 stages, one human gate (Accept) |
| KM's ask maps to | **THIS — "step-by-step artifact review"** | — |

**GB's two hopper seeds** (`evidence-workflow-gate-process-buttons-thought`, `kdp-pdf-dashboard-evidence-gates`)
reference **B** ("per workflow_snapshot") + KDP Phase-3 gates. **Those aren't wrong — they nest inside A.**
The reconciliation: the card's spine is **A (the book-writing workflow)**; **B is the mechanism that runs
during Phase 1 (co-extrusion) and Phase 2 (applying KM's review edits)**; **KDP gates are Phase 3 (Ship)**.
One spine, two mechanisms hanging off the right steps — not three competing views.

## The wheel already exists (so we render, not invent)

`WORKFLOW.md` steps → the artifact each emits → the roadmap packet → does it exist on disk today:

| # | Step (WORKFLOW.md) | Artifact / evidence | roadmap `packet` | On disk (B10–12)? |
|---|---|---|---|---|
| 1 | Phase −1 · series lock + plan editorial review | `pipeline/series_<slug>.yaml` | `series_lock_packet` | ✓ (series locked) |
| 2 | Phase 0 · per-title kickoff (brief + spec coupling) | `active.yaml` stage | — | ✓ |
| 3 | Phase 1 · outline + claim→spec map | outline / co-extrusion map | `chapter_draft_packet` | ✓ |
| 4 | Editorial Board **Round 1** (stylistic/structural) | `editorial_board_review_v1.x.md` | `board_pass_packet` | ✓ v1.0–1.4 |
| 5 | Editorial Board **Round 2** (disciplinary/functional) | `editorial_board_review_v1.x.md` | `board_pass_packet` | ✓ |
| 6 | Editorial Board **Round 3** (scholarly/research) | `editorial_board_review_v1.x.md` | `board_pass_packet` | ✓ |
| 7 | **Book-to-UX Translation Board** (17.5) | `virality_to_ux_translation_v1.0.md` | — | ✗ not yet run |
| 8 | **Tech/Architectural Review Board** (17.6, 5 gates) | `tech_arch_review_v1.x.md` | — | ✗ not yet run |
| 9 | Build publishable artifact | `final/*.pdf` + `.epub` + cover | — | ✓ |
| 10 | Handoff packet assembled | `handoff_packet_v1.0.md` | `handoff_disposition_packet` | ✓ |
| 11 | Phase 2 · human handoff + chapter-by-chapter review | Atrium Review captures (chapter+page) | `handoff_disposition_packet_with_chapter_page_ref` | in progress (10/11/12) |
| 12 | Phase 2 · sign-off → `awaiting_seal` | obligation + seal | — | pending |
| 13 | Phase 3 · Ship (KDP live) | ASIN + `published_date` (GB filled from KDP dashboard) | — | ✓ S0/S1 01-09 |

**Nothing here is new.** The steps are WORKFLOW.md; the artifacts are on disk; the packet names + `stage` +
`next_gate` are already in `series_roadmap.yaml`; KDP state GB just added (entry 167). The card's job is to
**show this row-by-row per title**, with each step's artifact + review status + an evidence link.

## Proposed card design (reuse what's built — minimal new surface)

Extend the **drill-through modal I already shipped (ATR-7b)** with one new section: **"Book-writing workflow —
artifact review."** A vertical 13-step checklist; per step: ● done / ◐ in-progress / ○ not-yet, the artifact
name, and a link/expander to the evidence (the actual `editorial_board_review_v1.x.md`, `handoff_packet`,
coherence row, KDP state). Steps 7–8 honestly show "not yet run" where the board hasn't been produced.

- **State source (no new spine):** `series_roadmap.yaml` `stage`/`packets`/`next_gate` (GB) + artifact-file
  presence + obligation/seal/coherence evidence (already wired).
- **GB's execution buttons** = a **Phase 2 follow-on**, hung off the right steps (re-run a board; route a
  review edit through the governed loop). **Deferred until KM greenlights agent-kickoff-from-card.**
- **Fence:** GB owns the projection (`stage`/`packets`/`workflow_snapshot`); Tiger renders; KM ratifies.

## Asks
- **GB:** confirm the A-vs-B framing + the 13-step mapping; keep `workflow_snapshot.json` as the machine spine
  but add a **book-writing-workflow stage list** (or confirm WORKFLOW.md is the canonical step source the card
  reads). Don't author a competing third workflow.
- **KM:** ratify the spine = WORKFLOW.md (A); confirm the card shows the artifact-review checklist read-only,
  with execution buttons deferred. Then Tiger builds the section.

∞Δ∞ The workflow is documented + the artifacts exist — this surfaces them per title, it doesn't reinvent them.
