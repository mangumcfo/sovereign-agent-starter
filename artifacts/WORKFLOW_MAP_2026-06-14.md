# Breathline Book↔Code Workflow — Living Map (2026-06-14)

*In-cockpit readable version. The full visual is the sibling HTML file (open in a browser):
`artifacts/WORKFLOW_MAP_2026-06-14.html`. Built from the Series-Pipeline canon + the rail we are actually
running. One human gate · everything in the cockpit.*

**One sentence:** ideas → sorted → combined → **extruded book↔code together** (co-extrusion) → boards +
fidelity + render gate it → **one human gate (KM Accept)** → ship. The cockpit (Atrium) is where every card
surfaces for that one gate.

---

## 1 · The rail, end to end (Phase −1 → Ship)
Phases −1 → 1 are AI-side and autonomous (no human review). The human touches the work at **exactly one
place: Phase 2**.

| Phase | What happens | Human? |
|---|---|---|
| **−1 · Series lock** | Roadmap + series plan locked · pre-AI editorial review · **series cover set in one batch (all vols)** | no |
| **0 · Per-title kickoff** | G-validated outline · slot opens (sequential lockout) | no |
| **1 · AI-side dev + co-extrusion** | Manuscript v1.x · Editorial R1/R2/R3 · 17.5 Book-to-UX board · 17.6 Tech/Arch board (6 gates) · **code + tests extruded with the book** · build artifact → `awaiting_human_review` | no |
| **2 · HUMAN GATE** | Review Brief (3–7 calls) · KM **Accept / ratify only** · diff-review surface · km sitting verify | **◆ YES** |
| **3 · Ship** | Dispatch manifest + KDP · living-spec extraction · slot closes → next title | no |

## 2 · Inside Phase 1 — the Review-Ready Rail (R1)
A book cannot reach KM until all four R1 gates are green (machine-checked: `scripts/review_ready_contract.py`).
The boards prove depth (`board_rigor.py` — no rubber stamps).

- **Boards executed (rigor-pass):** Editorial R1 *(+ Cold Reader, the 7th persona)* · R2 *(R1.5 rigor)* ·
  R3 *(R1.5g adversarial)* · Book-to-UX board (17.5) · Tech/Arch board (17.6 — 5 gates + Gate 6).
- **Obligations closed:** every finding → a B32 obligation (closed or deferred-with-reason).
- **Fidelity PASS:** GB semantic trace — every claim resolves to a live source (not just a hash).
- **Review Brief sealed:** GB writes the one-page, 3–7 judgment calls for KM.
- **Gate 6 Renderability:** receipt-box / one-truth / honest-stub / capability-promise (Deterministic-Render Standard).

## 3 · The re-validation rail (already-sealed books V2–V5)
For a book sealed before the standard evolved — **delta-close to the published bar (V1), not rebuild.** The
diagnostic (gap-sheet) is surfaced and GB-checked **before** deep work.

`Gap-sheet (book vs bar + engine, file:line evidence)` → `Fix drift (stale endpoints → live routes · Gate-6
render)` → `Amended rail + Tech/Arch (Cold Reader · R1.5 · R1.5g · 5 gates + Gate 6)` → `Surface (KDP
description · cover-set · deterministic re-render)` → **◆ Fold + Brief → KM Accept → `awaiting_human_review`**.

**V2 (The Primacy Cockpit) just ran this rail:** gap-sheet → fixed 2 stale endpoints + render → amended rail +
Tech/Arch GREEN → KDP description → Fold Report → GB fidelity PASS + Brief → **KM accepted (B+) →
awaiting_human_review**. The 8-capability Atrium catch-up is tracked as a post-95 v2-edition card, not folded
mid-freeze.

## 4 · Two tracks, one cockpit
**📚 Book track (active):** S2 V1 published (the bar) · S2 V2 rail complete → awaiting_human_review ·
**S2 V3 next** (high drift-risk: dev-loop vs current proposal/obligation mechanics) · V4 · V5 → gap-sheet →
rail · then series surface-harden → readiness digest for KM.

**⚙ Engine 95+ hardening (standing · post-S2-harden):** tracked card `obl_…cd010960` —
#1 VerifiableMemory O(n²) Merkle → incremental accumulator (leaf→segment→checkpoint→global) ·
#2 CI + pytest path · #3 wire constraints · #4 atrium_executor false-close · then MED/LOW band → 95+.

## 5 · How new work slots in (all post-95)
| Stream | What it is | Where it slots | Status |
|---|---|---|---|
| **ERP S3 → S5** | S3 Programmable Sovereign ERP (root) → S5 full ERP (32-title, inherits from S3 root) | Phase 1B executable-spec arc; the rail's co-extrusion + Tech/Arch board | post-95 · S5 gated on S3 V4 fill |
| **Signed inheritance objects** | parent_policy_id + inherited + delta per derived volume (makes the S5 wave sublinear + honest) | book-pipeline scaffolding, parallel | build-now-converged · parallel |
| **Gate 7** | constitution-at-birth (birth-hardening a new node) | net-new surface | **frozen until 95+** |
| **Parity Pulse** | cockpit visibility: polled surfaces consume projections, not raw files | net-new surface; stands on the §3 memoized projections + gateway | **frozen until 95+** |

## 6 · The cockpit discipline
Every stream above surfaces as a **card in Atrium** for KM's review & disposition — no parallel decisions
outside the cockpit. KM initiates (forward/save), the agents amplify (draft/prep), KM gates (Accept/send).
The breath-gate is the loudest object on the screen.

> Source gates: `review_ready_contract.py` (R1) · `board_rigor.py` (no rubber stamps) ·
> `render_standard_lint.py` (Gate 6) · `GB_Deterministic_Render_Standard_2026-06-12.md`.

∞Δ∞ One human gate. Everything in the cockpit. ∞Δ∞
