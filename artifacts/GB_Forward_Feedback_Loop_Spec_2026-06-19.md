# Forward Feedback Loop — mechanism spec (GB, 2026-06-19)
*KM ratified (flow-model voice notes, cyl 304): "once I do a review and provide feedback, there must be a feedback loop that applies my feedback across all series going forward, and that feedback enters the deterministic rail — because quality must not drop; it becomes same or tighter." This spec is the buildable mechanism. GB owns the standards-encoding step; Tiger wires the capture + obligation plumbing. Bounded by the bloat guard.*

## The principle
KM's review feedback is **never a one-off manuscript edit**. A feedback comment that names a *quality requirement* (not a typo/local fix) becomes a **rail update** that every subsequent volume and series inherits by construction. This is the discipline the V3 arc proved ad-hoc (render_fidelity, production_standards, no_orphan_markup, and now forward_reference + keyword_discipline were each born from a KM catch) — now formalized so it happens every time, mechanically.

## The four steps
1. **CAPTURE (Tiger plumbing).** At Gate B per-volume sign-off, a comment KM tags as a standard (vs a local edit) mints a `feedback_standard:<id>` obligation in B32 — owner GB, carrying the verbatim feedback + the volume it came from.
2. **CLASSIFY (GB).** GB decides: does an existing gate/standard carry this (tighten it), or is a new criterion genuinely needed (bloat-guard decision, KM-visible)? Default = tighten existing.
3. **ENCODE (GB, sole-write).** GB writes the requirement into the machine source of truth — `book_standard.yaml` / `distribution_standard.yaml` (a new field, a tightened floor, or a new gate in `human_review_ready`). Documentation-only is insufficient: it MUST land in the YAML the gates LOAD from. Version-bump + KM-ratified note. Close the `feedback_standard` obligation with the commit ref as the receipt.
4. **INHERIT (by construction).** Every volume after re-evaluates against the tightened standard at Phase-0 init (new volumes seed FROM `book_standards/`). No memory, no manual reapplication. Quality is **same-or-tighter, never looser**.

## Guarantees
- **Monotonic quality:** a standard can be tightened or added by feedback; it is never loosened by it. A loosening is a separate, explicit KM decision, not a feedback side-effect.
- **Traceable:** every standard rule can name the volume/feedback that birthed it (the `feedback_standard` obligation is its provenance) — the audit trail of why the bar is where it is.
- **Bounded (bloat guard):** feedback tightens existing gates by default; a new gate/board is minted only when nothing existing can carry the requirement, and that minting is a KM-visible decision. Duplicate/overlapping feedback-rules get consolidated, not accumulated.

## Lanes
- **GB:** classify + encode into the YAML (steps 2–3); own the provenance trail; run the bloat-guard consolidation.
- **Tiger:** the capture plumbing (step 1: the Gate-B "tag as standard" affordance + the `feedback_standard` obligation); the Phase-0 re-seed that makes step 4 automatic; gate code that loads the new criteria.
- **KM:** at Gate B, tag a comment as a standard (vs a local edit) — one extra signal, no extra card.

## Capture reliability — the reject-with-note gap (KM 2026-06-19, MUST FIX)
KM's recurring pain — *"my 'respond to feedback' sends a packet somewhere and GB/Tiger don't see it; it gets lost."* Root cause, confirmed in the ledger: when KM **rejects** a card with a note, the note is written into the close-event's `evidence` string and the obligation closes — it **never mints a follow-on actionable obligation routed to the owning agent.** The 2026-06-13 fix covered feedback *typed into* an open card (POST /feedback); the **reject-disposition path** (POST /feedback/<id>/disposition, action=reject) has the same disease and was missed. Result: feedback is only recoverable by manually grepping the ledger — the opposite of "accounted in standard process."
**The fix (binding):** any disposition that carries a NOTE (reject OR accept-with-comment) must, in the same transaction:
1. **Mint a follow-on obligation** owned by the **closed card's owner-agent** (GB or Tiger), `ref=feedback:<closed_id>`, intent = the verbatim note, gated on that agent's action (not on KM again).
2. **Surface it** in that agent's work queue (the thread handoff + the agent's open-obligations view) — never only in a close-event evidence string.
3. **Preserve the link** closed-card ↔ feedback-obligation ↔ the eventual fix commit (the provenance chain).
So: KM rejects with a note → the agent is *told* "here's what to fix," tracked to closure. No grep, no loss. This makes Capture step 1 reliable for BOTH paths (tag-as-standard AND reject-with-note).

## v1 proving slice
First exercised by the V3 6-call calibrations themselves: D2 (forward_reference) + D5 (keyword_discipline) + D1 (receipt-as-requirement) were just encoded into `book_standard.yaml` v1.3 — the loop's first real pass, done by hand; this spec makes it repeatable.

∞Δ∞ The human's judgment, given once, propagates forward mechanically. Quality tighter through standardization, not looser through automation. — GB
