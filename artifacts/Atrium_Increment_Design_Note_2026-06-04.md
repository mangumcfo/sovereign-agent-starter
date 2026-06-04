# Atrium Increment — Design Note (for KM's quick OK before I build)

**Date:** 2026-06-04 · **From:** Tiger · **Discipline:** design-then-build (ratified) — state-model-first → KM OK → build once + reviewer pass + batch. Lightweight, mock-first, `api.js` seam, honest labels.

KM directed: **ATR-5b (PDF in-app depth) + read-only Series Pipeline lens + minimal Hopper lane.** Here's the lightweight plan + state model for each, and the order. **Nothing built until you OK this.**

## Build order (lightest → heaviest — rebuilds momentum, lowest interaction-state risk first)
1. **Series Pipeline lens** (read-only) — *first*
2. **Minimal Hopper lane** (B51 delta cards)
3. **ATR-5b depth** (selectable PDF text)

---

## 1. Series Pipeline lens — read-only
- **Surface:** the existing "Series Pipeline" sub-tab — read-only, witness the whole hopper.
- **Data (existing seams):** `series_roadmap.yaml` (the projection) + the obligation ledger (per-title status). New `GET /series` (reads roadmap) + the live `/obligations/log`; through `api.js`.
- **Shows:** each series → titles → status + visibility (public/private) + LGP through-line; per-title drill-down; the Review surface is the "Human Handoff" sub-view.
- **State model:** read-only, polled with the **change-signature guard** (re-render only on change — no buttons to clobber). **Zero write → zero interaction-state risk.**
- **Real vs forward:** real = roadmap + ledger data, honestly labeled; forward = in-surface editing (read-only now).

## 2. Minimal Hopper lane — B51 delta cards
- **Surface:** a lightweight "Hopper" column/lane (a thin renderer, no logic in the lens).
- **Data:** recent unsealed B51 voice-delta entries. **Mock-first** (a few seed cards), then wire to GB's delta (GB provides the delta in handoffs, per the fence).
- **Cards:** ts · short preview · source (cyl id + entry hash) · actions: **Send to Packet** / **Dismiss**. Honest "live delta — mock for now" label.
- **State model:** each card → one action → creates a B32 packet (reuses the existing proposals/obligation seam). **Human breathe/Accept only.** Same sig-guard poll.
- **Real vs forward:** real = the lane + Send-to-Packet (reuses the loop); forward = the live HMC delta feed (mock first).

## 3. ATR-5b depth — selectable PDF text
- **What:** add the pdf.js **text layer** over the canvas (same pattern as the clickable-link layer) → you can **select + copy text** from the in-app PDF (your copy-paste request).
- **State model:** additive to the renderer; no interaction-state risk.
- **Real vs forward:** real = selectable text. *Note:* the deterministic `fix_prompt_wraps` pass handles the "many breaks," so pointing-by-copy is now a convenience, not the bottleneck.

## State-model discipline applied (the lessons we just learned)
- Every poll uses the **change-signature guard** — re-render only when the data set changes; never wipe a button state mid-action.
- **Reload rarely** — live data flows via the 4s poll; reloads only for a new build (batched).
- **One human gate**, honest labels, **reviewer pass before push**.

## Ship as practice (not canon)
All three behind honest *forward* labels where not yet live. Prove one real cycle each before anything is canonized.

---
**KM:** OK to build in this order (Series Pipeline → Hopper → ATR-5b depth)? Or reprioritize? Once you OK, I build #1 once, reviewer-pass it, surface status + cylinder for your Atrium review.
