# GB Prompt — Prepare message to G (grok.com) on Series Pipeline in the Atrium

**From:** Tiger (via KM) · **For:** GB (planning lane) · **Relay:** KM to G on grok.com · **Date:** 2026-06-02

**Goal:** GB drafts (or refreshes) a concise, paste-ready message to **G on grok.com** to align on how to introduce and manage the full book series pipeline (WORKFLOW.md) inside the Atrium — toward the 100%-in-Atrium north star — and how it relates to the packet/obligation model. This is not just review/tweaks (current Atrium strength); it's the whole lifecycle: Phase −1 series-lock → drafting → editorial boards → human handoff (current Review) → living specs.

**Trigger for this cycle (Tiger seq 446 + KM):** ATR-5 done and sealed (feedback packets now carry "ref: review:<chapter> · p<page>" context so the agent knows what you're looking at during review). Firefox voice honesty fixed (Web Speech API unsupported in FF → detects and degrades to clear "use B51" affordance; B51 cylinder remains the real voice path). Series-pipeline question explicitly teed: "your series-pipeline question is framed for G/GB." Tiger wrote the GB+G handoff (Series_Pipeline_in_Atrium_GB_G_Alignment_2026-06-02.md) with implementer's read: cleanest first increment = read-only Series Pipeline lens (visibility of roadmap + each title's stage + packets), then gates, then authoring. State: coordination ledger 18 closed / 9 open, chain valid. Atrium Review surface now: read → speak/type (with context) → portable packet → implement, all in-surface. Open queue includes ATR-5b (pdf.js), ATR-6 (portability), FEC-T1/T2/T3 (role into real code), BG-1/2, Mait splits, GB's Mait assessment + this series item. Tiger's pick: FEC-T1 next or ATR-5b. Recap from Tiger: "We're building the Atrium into the place you run book-review and obligations end-to-end; just finished ATR-5 ... and teed up the series-pipeline question for G/GB. ... Prepare the prompt for G on grok.com"

**KM explicit deep-dive ask to weave in:** "Thx No1 GB. can you deep dive this with me? What is the optimal approach for LGP? Whats the correct operating systems for Atrium...what is sovereign and what is going to be the most viral for the federation?" The message must surface thoughtful, grounded answers (families-first + long-horizon + human-out + ZK opt-in + Bitcoin/heritage for LGP; Atrium as the sovereign decision surface / lens for 100% UX with honest limits; sovereign = human primacy + constitutional invariants + receipted B32 + book source of truth + resonance federation; viral = LGP-to-families + visible Atrium trust + ship-blank adaptability + extreme-yields-earth + Jakob-style heritage permanence + Mait-style real productivity) as context for why the series pipeline visibility matters.

## Why now (KM's question in the Atrium)
KM, reviewing in the Atrium: *"What if I want to create a NEW book series? This already has a written book… we have the full book WORKFLOW.md we run in Claude Code primarily. Is the intent only to tweak existing materials, or how do we introduce and manage the series pipeline?"*

The Atrium Review surface (ATR-1…6) is excellent at **reviewing/tweaking an existing manuscript** — read in-surface → speak/type feedback (now with chapter+page context from ATR-5) → feedback becomes a portable packet → implement. **But that is only ONE stage** of the book lifecycle.

The full canonical pipeline already exists and is disciplined:
- **WORKFLOW.md** (breathline-books-vault): Phase −1 (multi-series roadmap → **series lock**: all titles defined upfront → keyword/thirst research) → Phase 0 kickoff → Phase 1 AI development (outlines, drafts, escalating editorial boards: stylistic/structural, disciplinary/functional, scholarly/research, plus Book-to-UX Translation Board) → **human handoff** (the first time KM sees it — *this is what the Atrium Review surface covers today*) → published → **books are living specs** (map to breathline-federation/specs/<series>/).

Today: authoring + series management lives in Claude Code (WORKFLOW.md); only the handoff-review stage lives in the Atrium. For the 100%-in-Atrium north star, the *whole* pipeline needs to be visible and driveable there — not just review.

## What the G message should cover (GB to draft, concise, factual)
1. **Where the Atrium / pipeline stands now (factual, current):**
   - Atrium Review surface is the "human handoff" stage: read (in-surface PDF/voice from ATR-5b pending), speak/type feedback with precise context (chapter + page ref from ATR-5), feedback → portable packet (with citations, LGP), implement.
   - The full pipeline (WORKFLOW.md) is already running in Claude Code: series-level locking (not title-level), Phase −1 series activation (all titles defined upfront), multiple escalating editorial boards, human handoff, books → living specs.
   - Current Atrium strength: review/tweaks on existing (e.g., FEC packet as visible card with voice seed, B51 trace, LGP). G's steer (Seal 1176-INFINITY-RHO): deepen Atrium Review surface (in-surface PDF + voice feedback + B51 bundle + card workflow) as Track F priority — make this the place KM does book review and ratification.
   - Obligations/packets: review feedback is already packetized (ATR-1…5); the loop is governed (B32 obligations, granularity L1 default, human gates on material).

2. **The series pipeline question (the ask for G):**
   - How do we introduce and manage the **full series pipeline inside the Atrium** (toward 100% UX), and how does it relate to the packet/obligation model?
   - Specifically align on:
     - **Surface shape**: a new **"Series / Authoring" lens** (or expansion of Review) that shows: the multi-series roadmap, series-lock state, each title's **pipeline stage** (Phase −1 → drafting → board pass N → handoff → published), and the **packets** each stage/fine-tune produces. Review becomes one *stage view* within this.
     - **Authoring vs review scope**: (a) tweak-existing only (simpler, real today), (b) full new-series authoring orchestrated from the Atrium, or (c) phased: review now + surface pipeline state (read-only) next, then drive stages from the cockpit later? KM leans toward full pipeline over time.
     - **Packets across the whole lifecycle**: not just review-feedback packets. Each chapter fine-tune → hashed packet set → obligations → code/specs (the R-50 loop). A *new series* generates packets from drafting + board passes too. Confirm packet granularity (L1 default) maps cleanly onto pipeline stages.
     - **Where the pipeline state lives**: the obligation ledger already models the work; a series/title/stage model could ride on it (each title = tracked obligation set; each stage transition = gated event). Or a dedicated `series_roadmap.yaml` that the lens reads. G/GB to decide source of truth.
     - **WORKFLOW.md ↔ Atrium**: does WORKFLOW.md stay the canonical pipeline (Atrium = its cockpit/lens), or does the pipeline definition migrate into a spec the Atrium drives?
   - Explicitly tie to the deeper KM deep-dive questions (verbatim): optimal approach for LGP, correct operating systems for Atrium, what is sovereign, and what is going to be the most viral for the federation. Use the framing in the draft message (families-first viral LGP with Bitcoin/heritage/Quad parallels; Atrium as the sovereign decision surface / lens for end-to-end review+obligations with ATR-5 context + honest limits; sovereign = human primacy + constitutional + B32 receipted + book source + resonance federation; viral = LGP-to-families + visible Atrium trust + ship-blank + extreme-yields-earth + real productivity like Mait). This keeps the series ask grounded in north-star and 100% UX.

3. **Request:** G's review + any corrections to the architecture. G's read on scope/phasing (review-first vs. full pipeline visibility in Atrium), packet mapping across lifecycle, source of truth (ledger vs. dedicated roadmap), and sequencing vs. current granular queue (ATR-5b pdf.js auto-page, ATR-6 packet portability, FEC-T1/2/3 role translation, BG-1/2 real breath-gate, Mait splits, GB's Mait assessment + series pipeline itself).

## Deliverable
- `artifacts/Message_to_G_Series_Pipeline_2026-06-02.md` — paste-ready (KM relays to grok.com-G), with short attachments list (this prompt, the Series_Pipeline handoff, WORKFLOW.md, Packet_Granularity v0.2, OBLIGATIONS_MASTER_INDEX, Atrium FEC mock, plan.md fold-ins, prior ARC message, Mait handoff + workflow, Unveil analysis + Jakob/backer HTMLs).
- Keep it tight + factual; honest labeling (today: review in Atrium, authoring in Claude/WORKFLOW; proposed: whole pipeline visible/driveable in Atrium as lens over sovereign substrate). No over-claim. Include latest Tiger 446 state (ATR-5 sealed with chapter+page, FF honest "use B51", 18/9 ledger, open queue incl. FEC-T1 + this series, Tiger's pick note).
- Tie the series question to the deeper KM questions on LGP/Atrium OS/sovereign/viral federation (as context for why this matters for 100% UX and LGP). The deep-dive answers are framed in the message body itself.

## Constraints
- G defines the model/principles (GB surfaces the question + Tiger's implementer read; G/GB decide; Tiger builds the surface).
- Two-writers fence; KM ratifies; honors existing WORKFLOW.md (extend/surface it, don't fork).
- Read-only framing for now; no mutations.

## Tiger's implementer read (for grounding in the message)
- Cleanest first increment (if approved): a **read-only "Series Pipeline" lens** that renders the roadmap + each title's current stage from a `series_roadmap.yaml` (sourced from WORKFLOW.md) — makes the pipeline *visible* in the Atrium without yet driving it. Then add stage-transition gates, then authoring orchestration.
- The Review surface (ATR-1…6, now with ATR-5 chapter+page context + honest FF "use B51" degrade) slots in as the "human handoff" stage of this larger pipeline — no rework, just framing.
- Reuse api.js seam + obligation ledger for state; honest labels for stages not yet automated.
- North-star tie: full pipeline visibility in Atrium supports LGP (multi-gen sovereignty via visible authoring/series management under human root + agent extension with provable gates); Atrium as the correct OS/lens (content-agnostic over sovereign node, driven by starter primitives + the deep-dive framing from KM's ask); sovereign (node/contract sovereign, Atrium thin lens, federation resonance medium); viral for federation (resonance via ship-blank + content-agnostic adaptation + resonant patterns + provable human-primacy + LGP + real productivity testbeds like Mait + heritage permanence ties).
- The prepared message should also note Tiger's current pick (FEC-T1 to turn the FEC packet into real working role_spec.yaml via universal ERP translation protocol + Atrium surfaces, or ATR-5b to perfect the review surface first) and the open GB obligation status (Mait assessment + series pipeline).

∞Δ∞ Review is one stage; the goal is the whole pipeline in the cockpit. Frame for G + GB to define the model. Over to GB.

**Attachments for the G message (list in the paste-ready version):**
- artifacts/Series_Pipeline_in_Atrium_GB_G_Alignment_2026-06-02.md (Tiger's handoff framing the question + implementer read: cleanest first = read-only "Series Pipeline" lens...)
- breathline-books-vault/WORKFLOW.md (canonical full pipeline: Phase −1 series lock etc. through living specs).
- artifacts/Packet_Granularity_Definition_v0.2.md (L1 default; maps to pipeline stages).
- artifacts/OBLIGATIONS_MASTER_INDEX_2026-06-02.md (current obligations clarity across ledgers; 18/9 in tiger_coordination post-ATR-5, chain valid).
- examples/atrium_fec_review_card_mock.html (FEC as concrete example of visible pipeline stage card in Review; story from voice, B51 trace, LGP, citations, disposition; ATR-FEC-001).
- plan.md (with G steering folds including Track F Atrium priority, external signals like Unveil alignment, and this series question + deep dive).
- (For current Atrium state) breathline-ui/atrium/ files (WHAT_ATRIUM_IS_FOR.md, UX_DEVELOPMENT_STATUS.md — lens over sovereign node, content-agnostic, resonance not control, ship-blank, LGP north-star).
- (Optional) GB's other recent: the ARC alignment message (for autonomic context + hard gates), Mait handoff + updated quality-plan-review-workflow.html (live testbed with MAIT-12 AI Plan Generator + Live-Edit/Change Tracker deltas exactly as voice "play around... this one got done"), Unveil analysis + Jakob_Unveil_Sovereign_Integration.html + Backer_Agentic_AI_Package_Financial_Case.html (external decision layer parallel + financial ops funding case without giving away the farm).
- The GB prompt for this (artifacts/GB_Prompt_Series_Pipeline_for_G_2026-06-02.md).