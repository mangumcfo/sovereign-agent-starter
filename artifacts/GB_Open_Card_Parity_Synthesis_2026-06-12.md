# Open Card Parity — GB Synthesis v1.0 (toward Objective: LGP, 2026-06-12)
*Sources: KM "download + reconcile" instinct · GB conformance-harness framing · G-grok "Cockpit Parity Pulse" · Lumen "Open Card Parity Harness." Both independent designs converged. GB synthesizes + rules + enhances toward LGP. Status: PROPOSED — KM ratify → Tiger builds as the next increment of the flow redesign already in flight.*

## The convergence (all four voices agree — adopt whole)
**Not a better download. A cockpit that cannot lose a card.** The download is the *receipt*; the invariant is the *query*; the human experience is *certainty*. In steady state KM should NEVER need to download — needing to means the surfaces aren't trusted yet. The button's end-state is rare "trust audit," not daily navigation.

## The invariant (Lumen's phrasing, kept verbatim — it is the heart)
> **For every open card: either a valid surface appearance, OR a valid *declared* reason for non-appearance. Hidden states need receipts too. No silent hiding.**

This is the breath-gate principle applied to **visibility** — see §LGP.

## GB rulings on the splits
1. **Name — two layers, both names kept:** the mechanism = **Open Card Parity Harness** (Lumen); the thing KM SEES = the **Parity Pulse** (grok) — a live indicator atop the queue (`Parity: PASS · engine 47 · visible 47 · hidden-by-policy 0 · divergence 0 · checked 14s ago`). Harness proves; Pulse shows.
2. **Card identity — adopt Lumen's canonical uid** (`source_namespace + source_id + obligation/proposal_id + predicate_version`), never title/text. Mutable cards compare `{card_uid, state, revision_hash, surface_render_hash}`.
3. **Severity ladder — adopt Lumen's 4-tier:** CRITICAL (engine-open, no surface, no valid hidden policy) · HIGH (surface shows what engine says closed) · MEDIUM (on one surface not another where predicate says it should) · LOW (render-metadata only). Divergence becomes the **top card**; truth never silently auto-heals (only the view cache may).
4. **Hidden-with-receipt — adopt:** sealed/archived · blocked-pending-evidence · private GB/Tiger/system lane · tiered-gate items KM isn't qualified for (R22-5 `visible_to`) · superseded · child-of-parent-bundle. Each non-appearance cites its policy in the evidence packet.
   - **HARD GUARD (Lumen 2026-06-12, the disease-preventer): hidden-by-policy must never become a new hiding place.** Every hidden record carries `{card_uid, policy_id, authorized_by, timestamp, expiry_or_review_condition, surfaces_excluded_from, evidence_hash}`. **`expiry_or_review_condition` is MANDATORY** — a hidden card with no review trigger is itself a CRITICAL parity finding (the harness audits its own exclusions). Without this, "hidden-by-policy" silently becomes a graveyard — the exact phantom-card disease, relocated. The hiding is gated too.
5. **Derive, don't recreate:** the export IS **R22-1 evidence-packet pointed at `predicate=open-cards`** (Merkle-verifiable bundle, not CSV); the open-set query rides **R22-2**'s projection; the visibility policy rides **R22-5**'s qualification tiers. **Three of tonight's five R-22 builds compose into this — almost no new machinery.**

## Build order (RATIFIED — Lumen's sequence, hidden-receipts BEFORE the checker)
1. **Canonical open-card query service** — ONE engine function returns the open set; no surface computes "open" independently. (The single source — everything else is a lens.)
2. **Surface manifests** — every surface declares `{surface_id, predicate, filter_reason, rendered_card_ids, render_hashes, snapshot_epoch}`.
3. **Hidden-by-policy receipts** *(Lumen-ordered 3rd, before the checker — so the checker has a complete truth to check against; a checker without hidden-receipts would false-CRITICAL every legitimately-hidden card)* — the full `{card_uid…expiry_or_review_condition…}` record per non-appearance.
4. **Continuous parity checker** — engine ↔ surfaces ↔ cross-surface ↔ hidden-receipts; divergence mints a CRITICAL card; a hidden card lacking an expiry/review condition is itself CRITICAL; runs background-sampled + nightly (joins the night watch).
5. **Parity Pulse indicator** — KM sees parity health BEFORE he sees the queue (top of Awaiting-Me).
6. **R22-1 export = the receipt** — Merkle packet for the current parity epoch, snapshot-epoch + engine_query_hash inside (kills snapshot-skew false drift).

## G-grok refinements (adopted 2026-06-12, dual-G ratify)
- **Parity Pulse = the TOP element of Awaiting-Me** — first thing seen on every sit-down, before the queue itself.
- **One-click "Show All Hidden-by-Policy" expander** — every non-appearance with its declared reason, on demand (transparency = the receipts made browsable).
- **Tie into the existing coherence monitor** — card↔ledger divergence joins book↔code drift; both auto-surface as CRITICAL cards through the one channel (no second drift system).

## Explicitly NOT build (both designs agree)
CSV-as-truth · manual reconcile queue · per-surface "open" logic · silent auto-close / silent hide · another dashboard that becomes its own queue.

## Objective: LGP — the synthesis enhancement
**This completes the constitution's third axis of truth.** The harness already governs two: **actions** (nothing executes without a gate — the governed loop) and **state** (nothing changes without a receipt — the ledger). This adds the third: **visibility** — *nothing hides without a declared reason.* Gate → Receipt → **Parity.** With all three, the cockpit is fully constitutional: an operator can no longer be surprised by an action, a state, OR an absence.

And the generational point — why this is LGP, not just UX: **certainty-by-construction is inheritable.** An heir inherits not only the systems but a cockpit they can *trust without forensics* — they open it and the Pulse says PASS, and that is enough. KM's original instinct ("let me download and check") is the *manual* version of what the heir gets *for free*: KM had to learn to distrust his surfaces the hard way; the heir never will. **The day KM never wants to press the download button is the day the feature succeeded** — and that day is the inheritance.

Mirror to S9 Sovereign Self: the Parity Pulse (external certainty the cockpit can't lose a card) is the outward twin of the operator's own inward clarity (the Sovereign Self can't lose a promise). Same discipline, both faces.

∞Δ∞ SEAL: proposed — gate, receipt, parity: the three axes complete. Not a better download — a cockpit that cannot lose a card, and an heir who never has to wonder.
