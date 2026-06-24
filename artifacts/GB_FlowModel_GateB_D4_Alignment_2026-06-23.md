# Flow-Model Gate B + D4 — Design Alignment for Tiger's P2 Wiring (GB, 2026-06-23)
*The paused P2 pieces (Gate B per-volume sign-off + D4 route-up/Stillpoint-Synod) need GB design alignment before Tiger wires them. This doc resolves the open design questions with KM's decisions baked in, so Tiger can build without guessing. Companion to [[GB_Series_Flow_Model_2026-06-18]] + [[GB_Forward_Feedback_Loop_Spec_2026-06-19]]. GB sole-write (design lane); Tiger implements.*

## What's already built (P2 core, Tiger) — context
- **FFL Capture** (tag-as-standard → GB obligation) — live + tested.
- **Phase-0 re-seed** (`seed_volume.py`, inherit-by-construction) — live; new volumes inherit all gates incl `cover_standard` + the new `board_execution` standard.
- **Reject-with-note capture** (Item 1) — landed: a disposition note mints a follow-on obligation to the owning agent, not buried in close-event evidence.
Remaining to wire: **(A) Gate B per-volume sign-off** and **(B) D4 route-up / contest escalation**.

---

## A. Gate B — per-volume sign-off (KM decided: **N cards grouped by series**)
**The decision:** when a series' volumes reach `review_ready`, surface **one card per volume**, **visually grouped under the series** in the cockpit — NOT one expandable batch card. Each volume is an independent, separately-dispositioned item (closer to today's cockpit; KM's explicit choice).

**Wiring (extends existing breath-gate, no new gate):**
1. **Grouping key, not a new obligation type.** Each volume's `review_ready:<book_id>` obligation already mints to `awaiting_km` (`src/sovereign_agent/node_api/routes/feedback.py` `_awaiting`). Add a **`series_ref` field** to the obligation (or derive it from the book_id → series map in `series_roadmap.yaml`) and have `awaiting_km` (and the Atrium projection) **group the cards by `series_ref`** under a series header. Pure presentation grouping over the existing per-obligation cards.
2. **Per-volume sign-off at V3 depth.** Each card carries that volume's Review Brief (the 3–7 judgment calls) + the substantive-quality signal (the adversarial-board verdict summary). KM dispositions each volume independently via the existing `POST /feedback/<id>/disposition` (accept→approve, reject→close-with-note). **Depth floor = the existing 3–7-call brief + the board verdict** — no new minimum needed; the brief gate already enforces it.
3. **Independent fates.** A volume KM doesn't sign stays `material=True / next_gate=HUMAN_GATE` (remains in `awaiting_km`); signed volumes leave the view (approved=True → owning agent's execution queue). **No approve-all** — that's the whole point of "separate sign-off."
4. **Reject-with-note routing (per the FFL spec, already landed):** a reject note → follow-on obligation owned by the card's **owner-agent** (`ref=feedback:<closed_id>`); a note KM **tags as a standard** → routes to **GB** (encode into the yaml); a plain local fix → the **owning agent** (usually Tiger, to iterate the volume). The closed-card ↔ feedback-obligation ↔ fix-commit link is preserved.

**Bloat guard:** Gate-B feedback that names a quality requirement accumulates into `human_review_ready` (tighten an existing gate); mint a NEW gate only when nothing existing can carry it (a KM-visible decision). No new card types, no third human gate.

---

## B. D4 — contested → route UP, never silently pick a winner
**The principle (V3 Ch4 Stillpoint Synod, the canonical model):** *"It never silently picks a winner. On a genuine contest it escalates — routing the dispute up… decided on the record, sealed like any other receipt. An uncontested render proceeds without ceremony."* D4 gates this into the rail: **green + uncontested = silent (zero intermediate cards); contested/RED = an escalation card to KM.** This is what keeps "no intermediate cards" honest — silence is earned only when nothing is in dispute.

**Contest detection (the wiring — concrete triggers):** a volume is **CONTESTED** (→ escalate to KM as a card) when ANY of:
1. **Inter-board disagreement** — two boards reach opposing readiness verdicts on the same volume (e.g., editorial says ready, tech_arch says incomplete). Detect by comparing the boards' rigor-block verdicts/severities for the volume.
2. **Unresolved RED gate** — any `review_ready_contract` gate is RED after the owning agent's iteration budget (i.e., it didn't self-resolve) → escalate rather than loop silently.
3. **Material finding without agreed disposition** — a board surfaces a material finding that the boards themselves split on how to resolve.
Anything NOT matching → **uncontested**, stays silent (the agents resolve it in-lane; the rail only surfaces the final gate-green volume).

**Escalation card shape:** a single "⚖️ Contested — `<volume>`" obligation to `awaiting_km`, material, carrying: the competing positions in plain terms (board A says X, board B says Y), the artifact refs, and KM's options. KM's disposition IS the Synod ruling — recorded on the obligation, sealed like a receipt (the decision + reasons persist for a later reader). **The rail never auto-resolves a contest.**

**Relationship to Gate B:** Gate B is the *normal* end-of-series human gate (per-volume sign-off). D4 escalation is the *exception* path that can fire mid-flow when the rail itself can't reach consensus — it does NOT wait for Gate B. Both feed `awaiting_km`; D4 cards are tagged `contested` so they're visually distinct from the routine review cards.

---

## Lanes
- **GB (this doc):** the design decisions above; the contest-detection criteria; verifies Tiger's wiring matches.
- **Tiger (wire P2):** (A) series-grouping key on review_ready obligations + the cockpit grouping; (B) contest-detection (the 3 triggers) + the escalation-card mint + the `contested` tag. Reuse the existing `awaiting_km` + disposition breath-gate; no new gate/packet type.
- **KM:** per-volume sign-off (Gate B) + Synod rulings on any contested card.

∞Δ∞ Two human gates plus an honest exception path: routine review per-volume (Gate B), contest escalated visibly (D4/Synod). The rail stays silent only when nothing is in dispute. — GB
