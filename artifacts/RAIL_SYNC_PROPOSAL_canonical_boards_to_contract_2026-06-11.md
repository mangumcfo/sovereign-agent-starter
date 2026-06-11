# Rail-Sync Proposal — Canonical WORKFLOW Boards → review_ready_contract Machine Gate
## For GB ratification (rail owner) · drafted by Tiger 2026-06-11 · KM-directed, fence-clean

> **Why:** Tiger drifted — ran ad-hoc `findings.json` boards (editorial/ux/technical/cold_reader) that do not
> match the canonical Series-Pipeline boards in `WORKFLOW.md`. KM caught it. The wrong artifacts are removed and
> the unilateral `REQUIRED_BOARDS` change is reverted. This proposal reconciles the machine gate to the canonical
> boards **for GB to ratify** — Tiger does not change the rail spec again unilaterally.

## The canonical boards (WORKFLOW.md, what KM's Series-Pipeline card shows)

| Step | Board | Artifact (per book) | Rounds / gates |
|---|---|---|---|
| P−1.5 | Series-plan editorial review (scores the *plan*, pre-manuscript) | `EDITORIAL_BOARD_REVIEW_v1.0.md` (series-level) | one pass, 6 personas → KM lock (step 6) |
| P1.12–13 | Editorial **R1** — stylistic / structural | `editorial_board_review_v1.x_round1.md` | 6 lenses |
| P1.14–15 | Editorial **R2** — disciplinary / functional | `…_round2.md` | escalated lenses + `BOOK_UX_SYNC_CHECKLIST` |
| P1.16 | Editorial **R3** — scholarly / research | `…_round3.md` | highest-capability lenses |
| P1.17.5 | Book-to-UX Translation | `virality_to_ux_translation_v1.0.md` | 12 reviewers, book→UX (prescriptive, not prose-critique) |
| P1.17.6 | Tech / Architectural Review | `tech_arch_review_v1.x.md` | **5 gates**: arch fit · test coverage · integration green · thin-waist/K1 · LGP (reviews co-extruded code↔book) |

## Current machine gate (what `review_ready_contract.py` checks today)

- `REQUIRED_BOARDS = ("editorial", "ux", "technical")` — globs `*<board>*findings.json` and runs `board_rigor.rigor_check` on each.
- Mismatch: (a) editorial is **three rounds**, not one; (b) "ux" = Book-to-UX, "technical" = Tech/Arch (5 gates), but the names + artifact format (`findings.json` vs canonical `.md`) differ; (c) no series-plan (P−1.5) gate; (d) the Cold Reader amendment has no home.

## Proposed reconciliation (GB rules; Tiger implements on ratification)

1. **Canonical artifact = the `.md` board.** The human-readable board document is the source of truth (named personas, scoring, attributed S/W/R). The machine gate verifies the `.md` exists **and** that it carries R1.5 rigor — rather than requiring a separate `findings.json`.
2. **Map `REQUIRED_BOARDS` to the canonical set:**
   - `editorial` → **all three rounds present**: `editorial_board_review_v1.x_round{1,2,3}.md`.
   - `ux` → `virality_to_ux_translation_v1.0.md` (already produced for Vol 1).
   - `technical` → `tech_arch_review_v1.x.md` (5 gates).
3. **R1.5 rigor on the `.md`.** Two options for GB to pick:
   - **(A) Embedded machine block** — each board `.md` ends with a fenced `rigor` JSON block (findings[] + section_coverage[]) that `board_rigor.rigor_check` parses. One artifact, both human + machine.
   - **(B) Sidecar** — keep a small `<board>.rigor.json` beside the `.md`, regenerated from it. Two artifacts, looser coupling.
   - *Tiger's lean: (A)* — single source, no drift between prose and machine layer.
4. **Material findings → obligations** stays binding (R1.5). Each `.md` board's material weaknesses open `editorial_rN:<book>` obligations; the contract's `obligations_closed` gate already enforces close-or-defer.
5. **Cold Reader (B12 pilot amendment) — GB rules where it seats.** Tiger's recommendation: a **7th lens inside the Editorial rounds** ("Cold Reader" — the line-level reader who catches what KM was catching), not a separate board — so it rides the existing R1/R2/R3 rigor + sampled audit rather than adding a board to every title. GB decides.
6. **Series-plan gate (P−1.5)** — add an optional `series_plan_reviewed` check that confirms `EDITORIAL_BOARD_REVIEW_v*.md` exists at the series root before any volume mints review-ready. (S2 already satisfies it.)

## What Tiger will do on GB's word

- Implement the ratified `REQUIRED_BOARDS` mapping + the chosen rigor-on-`.md` mechanism in `review_ready_contract.py` + `board_rigor.py`.
- Re-point the S2 Vol 1 rail at the canonical boards (R1 already produced in canonical `.md`).
- Nothing changes in the rail until GB ratifies.

∞Δ∞ The board proves its depth; the gate reflects the board; the fence stays clean — GB holds the pen on the rail.
