# Series-Level Flow Model — fewer human touchpoints, quality held-or-tighter
*GB-proposed 2026-06-18, surfaced at the V3-Helix review_ready gate per KM directive. Goal: move from per-volume qualification (≈N cards/volume) to a **two-gate-per-series** model, while keeping the FULL Review-Ready Rail and the human gate, and STRENGTHENING the quality bar through standardization + the Living Claim Rail. Incorporates KM's four requirements + Lumen's claim-registry refinement.*

> **RATIFIED WITH AMENDMENTS — KM-1176, 2026-06-19 (voice notes, cyl entries 303–304): "Approved with these changes."**
> Three changes folded below: **(1)** Gate B is per-volume **separate sign-off** at full (V3-level) depth — not one bundled batch approve; **(2)** a new **Forward Feedback Loop** — KM review feedback enters the deterministic rail (as a standard/gate update) and applies across all series going forward, quality same-or-tighter; **(3)** **bloat guards** kept and extended to the feedback loop. Confirmed unchanged: Gate A (catalog-lock = proof of concept), static rail, claim registry seeded, deterministic rail with no intermediate human cards, editorial rounds recorded as full obligation artifacts (findings + closure), UX + Tech/Arch boards ("agreed and critical"), Education board ("agreed and critical"), distribution as its own deterministic rail with a similar handoff.*

## The shift in one line
**Today:** the human sees many intermediate cards per volume (kickoff, bar-ratify, board findings, contract result…).
**Proposed:** the human sees **two clean gates per series** — *Series Lock* (front) and *Batch Review* (end) — and nothing in between, because the *deterministic rail + the claim rail* enforce the bar that intermediate cards used to.

## The two human gates (the only two KM cards per series)

### Gate A — SERIES LOCK (one ratification, front)
KM approves, in one card: (1) the series' **locked outlines** (the `outline_lock_lint` proves all volumes complete — the catalog-lock pass is the proof-of-concept), (2) that the series runs the **standard rail unchanged**, (3) the **claim registry seeded** for the series (claims extracted from the Gate-6 capability-promises). **Precondition (your freeze):** no volume drafts until Gate A is ratified.

### …then volumes FLOW the deterministic rail — no human cards
Each volume runs the *same* rail it runs today — 3 editorial rounds + UX board + Tech/Arch board (6 gates incl. Gate 6) + `seeit` Education Board + `review_ready_contract` — but **autonomously, surfacing zero intermediate cards to KM.** The rail *is* the bar. The exemplar-first cadence (Ch1 ratified → roll the rest) proven on V3 becomes the per-volume default. GB witnesses fidelity; Tiger drives; the contract gates.

### Gate B — BATCH REVIEW (one card per series, end) — **per-volume separate sign-off (KM amendment 2026-06-19)**
When the series' volumes reach `review_ready`, **one batch card** is the entry point and carries: the per-volume Review Briefs (3–7 judgment calls each), **and the substantive-quality signal** (below). It replaces N separate *cards* — but **NOT** N separate sign-offs. **KM amendment:** the review must include a **separate sign-off of EACH volume**, at the **full depth we went on V3 last night** (the completeness/length of the V3 6-judgment-call pass is the depth floor — a batch must not dilute per-volume rigor). So: one card to open the batch; inside it, KM signs off volume-by-volume, each at V3 depth. A volume KM doesn't sign stays in iteration; the others can seal. The batch reduces *card count*, never *per-volume scrutiny*.

## The control that makes "fewer touchpoints" safe — substantive-quality-at-scale (#4)
Reduced human touch is only safe if the thing the human used to catch is caught structurally. **The batch card surfaces the Cold-Reader / adversarial-board verdict as a structural metric per claim-family** — not just "structurally complete (0 thin)" but "rated good/clear/true by the adversarial pass." Completeness lints say *the parts are present*; this says *it's actually good*. **This is the enforcement of your "quality must not drop" line** — without it, the flow-model is where quality silently erodes. Quality bar = **same-or-tighter**: every board + Gate 6 + the contract still run per volume; only the *human card count* drops.

## The integrity backbone — Living Claim Rail v0.1 (Lumen's primitive, KM-accepted)
What makes claim-truth survive fewer human touches: every capability-promise becomes a tracked **claim** (`claim_id · proof_refs · code_refs · inheritance · status`). The rail's four movements map onto the flow:
- **Declare** at Series Lock (claims extracted from outlines/manuscripts).
- **Prove** during volume flow (test/command/receipt/seeit — blocks at review_ready without ≥1 proof).
- **Watch** post-publish (code→claim reverse-drift mints a loud obligation — gap #1, queued post-V3).
- **Revise** via next-edition obligations (reader/platform feedback — gap #5).
**v0.1 builds first on V3** (its /seeit pages already carry command+receipt = proof) — the proving slice, per your directive.

## The Forward Feedback Loop (KM amendment 2026-06-19 — the load-bearing addition)
*"Once I do a review and provide feedback, there must be a feedback loop that applies my feedback across all series going forward, and that feedback enters the deterministic rail — because quality must not drop; it becomes same or tighter."* — KM, cyl 304.
This formalizes, as a standing flow-model movement, the exact discipline the V3 arc proved: **KM review feedback is never a one-off manuscript edit — it is captured as a RAIL UPDATE that all subsequent volumes/series inherit by construction.** The mechanism (reusing what's already built):
1. **Capture** — a Gate-B sign-off comment that names a quality requirement (not a typo) is logged as a feedback obligation.
2. **Encode** — GB translates it into the machine source of truth: a `book_standard.yaml` / `distribution_standard.yaml` rule or a new/tightened gate criterion (the way render_fidelity, production_standards, no_orphan_markup were each born from a KM catch). Documentation alone is insufficient — it must land in the YAML the gates LOAD from.
3. **Inherit** — every volume after re-evaluates against the tightened standard at Phase-0 init (by construction, not memory). Quality is **same-or-tighter, never looser**.
4. **Bound** — the bloat guard (below) applies: feedback tightens *existing* gates by default; it earns a *new* gate/board only when no existing one can carry it.
This is the loop that makes "fewer human touchpoints" safe over time: the human's judgment, given once, propagates forward mechanically.

## Contested → route UP, never silently pick a winner (KM D4, 2026-06-19)
A governance primitive confirmed in the V3 calls and binding on the whole rail: **anything that would normally gate as RED, or is genuinely contested between agents/boards, routes UPWARD to the human — the rail must NOT silently pick a winner.** This is what keeps "no intermediate cards" honest: zero cards in the *normal* flow, but a *contested/red* condition is exactly the signal that earns a card. The Stillpoint Synod (the Ch4 render-dispute model) must therefore **escalate on contest**, not auto-resolve. Silence is only permitted when the rail is green and uncontested.

## KM reviews only COMPLETE volumes (KM D6, 2026-06-19)
The human gate fires **only when a volume is complete** — KM does not check in on production mid-flight. AI-internal rail reviews (GB fidelity, the boards, the contract) run continuously and are the agents' call; they do **not** surface to KM until the volume is whole and review-ready. This is the workflow expression of the build-ahead model: production runs ahead autonomously, KM engages at Gate B on finished volumes (per-volume sign-off, full depth), never on partial work.

## Quality stays same-or-tighter (the proof it doesn't drop)
| Dimension | Today | Under the model |
|---|---|---|
| Boards (3 editorial + UX + Tech/Arch 6-gate) | per volume | **per volume (unchanged)** |
| Gate 6 + review_ready_contract | per volume | **per volume (unchanged)** |
| Claim-truth | implicit | **explicit (claim rail, blocks without proof) — tighter** |
| Substantive quality | human judgment per card | **adversarial verdict as a structural metric — tighter, scalable** |
| KM human cards | many per volume | **two per series** |

## Distribution lane (held visible, your directive)
The distribution / broader-human-domain outreach thread runs as a **parallel lane** with its own gate — surfaced alongside Series Lock so it scales *with* the catalog instead of staying invisible. Not folded into the rail (different concern); held in view, not dropped.

## Non-goals / bloat guard (KM: "agreed, include bloat guards")
No new boards. No new packet types. Two human gates, not more. The model REUSES the existing rail + lints + contract + B32; it only changes *card cadence* (per-volume-per-step → per-series-two-gate) and adds the claim rail + the quality metric + the forward feedback loop. **Bloat guard extended to the feedback loop:** feedback tightens *existing* gates/standards by default; it may mint a new gate or board ONLY when no existing one can carry the requirement, and that minting is itself a KM-visible decision. If the model grows a third human gate, a new board, or accumulates feedback-rules that duplicate each other, it has bloated — stop and consolidate.

## Rollout (after KM approves the model)
1. Claim Rail v0.1 live on V3 (proving slice).
2. First series to run the two-gate model: **S3** (V3 is its exemplar; V1/V2/V4 flow under one Series-Lock + one Batch-Review). The freeze lifts only at S3 Series Lock.
3. Then the S5–S9 batch (the 64 locked outlines) under the same model.

∞Δ∞ Two gates, not many cards. The rail and the claim hold the bar; the human keeps the judgment at lock and at batch-review. Quality tighter through standardization, not looser through automation. — GB
