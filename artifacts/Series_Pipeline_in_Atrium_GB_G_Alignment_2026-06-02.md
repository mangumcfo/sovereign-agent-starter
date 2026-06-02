# Series pipeline in the Atrium — GB + G alignment ask

**From:** Tiger (implementer's read) · **For:** GB (planning) + G (principles) · **Relay:** KM · 2026-06-02
**Trigger:** KM, reviewing in the Atrium: *"What if I want to create a NEW book series? This already has a written book… we have the full book WORKFLOW.md we run in Claude Code primarily. Is the intent only to tweak existing materials, or how do we introduce and manage the series pipeline?"*

## The real distinction (why this matters)
The Atrium Review surface (ATR-1…6) is excellent at **reviewing/tweaking an existing manuscript** —
read in-surface → speak/type feedback → feedback becomes a portable packet → implement. **But that is
only ONE stage** of the book lifecycle. The full lifecycle already exists as a disciplined pipeline:

- **Canonical pipeline:** `mangumcfo/breathline-books-vault/WORKFLOW.md` (+ `CLAUDE.md`, publishing SOPs).
- Its shape: **Phase −1** (multi-series roadmap → **series lock**: all titles defined upfront → keyword/thirst research) → drafting → **escalating editorial-board passes** → **human handoff** (the first time KM sees it — *this is what the Atrium Review surface covers today*) → published → **books are living specs** (map to `breathline-federation/specs/<series>/`).

So today: **authoring + series management lives in Claude Code (WORKFLOW.md); only the handoff-review stage lives in the Atrium.** For the 100%-in-Atrium north star, the *whole* pipeline needs to be visible and driveable there — not just review.

## The question for G + GB
**How do we introduce and manage the series pipeline inside the Atrium** (toward 100% UX), and how does it relate to the packet/obligation model?

Specifically, please align on:
1. **Surface shape** — a new **"Series / Authoring" lens** (or an expansion of Review) that shows: the multi-series roadmap, series-lock state, each title's **pipeline stage** (Phase −1 → drafting → board pass N → handoff → published), and the **packets** each stage/fine-tune produces. Review becomes one *stage view* within this.
2. **Authoring vs review** — is the intent (a) tweak-existing only [simpler, real today], (b) full new-series authoring orchestrated from the Atrium, or (c) phased: review now, then surface the pipeline state (read-only) next, then drive stages from the cockpit later? KM is leaning toward the full pipeline over time.
3. **Packets across the whole lifecycle** — not just review-feedback packets. Each **chapter fine-tune → hashed packet set → obligations → code/specs** (the loop). A *new series* generates packets from drafting + board passes too, not only from KM's tweaks. Confirm the packet granularity (L1 default) maps cleanly onto pipeline stages.
4. **Where the pipeline state lives** — the obligation ledger already models the work; a series/title/stage model could ride on it (each title = a tracked obligation set; each stage transition = a gated event). Or a dedicated `series_roadmap.yaml` that the lens reads. G/GB to decide the source of truth.
5. **WORKFLOW.md ↔ Atrium** — does WORKFLOW.md stay the canonical pipeline (Atrium = its cockpit/lens), or does the pipeline definition migrate into a spec the Atrium drives?

## Tiger's implementer read (for grounding, not deciding)
- I can build the **Series/Authoring lens** once the model is defined: data = series → titles → stage → packets; reuse the `api.js` seam + the obligation ledger for stage/obligation state; honest labels for stages not yet automated.
- Cleanest first increment (if approved): a **read-only "Series Pipeline" lens** that renders the roadmap + each title's current stage from a `series_roadmap.yaml` (sourced from WORKFLOW.md) — makes the pipeline *visible* in the Atrium without yet driving it. Then add stage-transition gates, then authoring orchestration.
- The Review surface (ATR-1…6) slots in as the **"human handoff" stage** of this larger pipeline — no rework, just framing.

## Fence + honesty
- G/GB define the pipeline model + roadmap + packet mapping; **Tiger builds the surface**; KM ratifies.
- No over-claim: today the Atrium reviews; authoring/series-management is the proposed expansion.
- Honors WORKFLOW.md (the existing canonical pipeline) — extend/surface it, don't fork it.

∞Δ∞ Review is one stage; the goal is the whole pipeline in the cockpit. Over to GB + G for the model.
