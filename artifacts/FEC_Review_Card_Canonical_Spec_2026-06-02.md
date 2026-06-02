# FEC / Packet Review Card — Canonical Human-Informed Spec

**Status:** ratified-in-intent by KM 2026-06-02 ("keep the human-informed pieces as the design and intent").
**Reference implementation (richest):** `examples/atrium_fec_review_card_mock.html` (the approved mock).
**Live lens:** `breathline-ui/atrium` → Review → **FEC Packet** (`fecView`).

## Why this exists
KM reviewed the first live Atrium port and flagged it was ~80% of the approved card — the *structure*
survived but the **human-informed richness** had thinned. Those pieces are not decoration; they are the
**design intent**: keep the human genuinely in the loop so that decisions — and, in time, **book-publishing
and other workflows — automate *around* the human, never without them.** This spec pins them so no future
iteration silently regresses below the bar.

## Required elements (every packet review card MUST carry these)

| # | Element | Why (human-informed intent) | Live-lens status (ATR-1) | Full/live via |
|---|---|---|---|---|
| 1 | **In-depth story** + verbatim voice excerpt | the exec understands the decision as a narrative, not a data dump | ✅ restored (narrative + ZK voice excerpt) | — |
| 2 | **Voice replay** | hear the original human seed in the operator's own words | ▶ button (labeled; transcript today) | **ATR-4** (stream cylinder audio + B32 receipt) |
| 3 | **Clickable source files + attached docs** | one click to the evidence behind any claim | ✅ GitHub links (R-52, translation v0, captured-thought, gb note, demo, ledger) | **ATR-2** (in-cockpit inline view + live ledger read) |
| 4 | **Refine → verbal/typed feedback (NLP)** | the human shapes the proposal in their own words | ✅ `Refine (speak / type)` prompt captures + echoes | **BG** (re-opens packet as a new debit carrying the comment) |
| 5 | **Key messages** (what it is / what agents did / what you're deciding) | 10-second executive orientation | ✅ | — |
| 6 | **B51 handoff trace** (GREEN→YELLOW→RED) | see exactly where agents stopped + escalated | ✅ | ATR-2 (live trace) |
| 7 | **LGP + citation bundle + human-seed** | grounded, not hallucinated; families-first | ✅ | — |
| 8 | **Disposition** (Approve / Refine / Reject) | the human is the ratifier — nothing proceeds without the gate | ✅ (static) | **BG-2** (real breath-gate + node receipt) |

## The principle (do not regress)
- **Agents propose; the human disposes.** The card's job is to make the human's "should this proceed?"
  decision *fast and well-informed* — story + evidence + the agents' visible reasoning + a one-gesture gate.
- As surfaces get used live they will evolve — but **elements 1–8 are the floor**, not the ceiling.
- This is the template for **all** packet review cards (FEC today; book-publishing packets, Mait quality-plan
  reviews, etc. tomorrow) — the same human-informed review loop, reused.

## Mapping to granular obligations
- **ATR-2** — live `/api/v1/obligations` read → makes #3/#6 live, source links resolve in-cockpit.
- **ATR-3** — in-surface PDF render (the manuscript-review variant of this card).
- **ATR-4** — in-surface voice (B51) capture + replay → makes #2/#4 fully live.
- **BG-1 / BG-2** — real breath-gate → makes #8 authoritative, #4 re-opens a real debit.

∞Δ∞ The human stays at the stillpoint; the surface does the work and hands up the gold nugget. ∞Δ∞
