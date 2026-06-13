# Design Note — Interactive Chapter-Outline Cards in the Series Pipeline
*Source: G (grok.com) 2026-06-07, in response to GB's architecture prompt. Captured by GB-on-Opus as a stable build spec. Route: GB seeds (hopper) → Tiger builds → KM ratifies. G's verdict: "Tiger can build the first slice now."*

## 1. Data model (in series_roadmap.yaml — GB's sole-writer lane)
Add `chapters:` under each title. Lightweight, content-agnostic, human-editable:
```yaml
chapters:
  - n: 1
    title: <chapter title>
    promise: <one sentence>
    beats: [<3-5 short>]
    keywords: [<3-5>]
    stage: outline_locked   # outline_locked / draft / board_review / validated / drift
    coherence_pin: null     # populated after the book chapter exists
```
**Already live:** GB folded **S4 Vol 1** (8 chapters) in this exact shape (CYL 207) — Tiger has real data to render against immediately.

## 2. Card surface (Atrium)
- **Hierarchy:** Series → Volume/Title card (existing) → expandable / drill-down **Chapter cards**.
- **Each chapter card:** number + title (bold) · one-line promise (the hook) · status chip · beats (3-5, collapsible) · coherence badge (✅/⚠/◌ → drill to validation) · ⛓ render-receipt (Helix popup).
- Calm, high-signal, minimal whitespace; reuse existing card chrome + Helix popup.

## 3. Interaction loop (B32 + one gate — preserves read-only-first)
KM edits a chapter field → **capture → B32 packet (diff preview)** → Tiger process → **VALIDATE (coherence + Merkle on the roadmap change)** → KM **Accept / Refine / Dismiss** (one gate) → on Accept, **GB applies** back to `series_roadmap.yaml`. AI "better outline" suggestions appear as **advisory proposals in the same flow — never auto-apply.**

## 4. Coherence tie-in
Once an outline drives a real manuscript chapter, the card shows a coherence badge linked to that chapter; the validation harness treats the outline as the **seed** (book passage must trace back to the outline's promise/beats); **drift surfaces** if book and approved outline diverge.

## 5. Phasing (thin first slice — build now)
**First slice:** read-only chapter cards rendered from the yaml (expandable under titles) + status + coherence badge + **one editable field (`promise`) behind the B32 gate** to test the loop.
**Defer:** full in-place rich editing · AI auto-suggest generation (advisory only) · heavy version history (the cylinder already holds it).

## Build note for Tiger
The extension point is `node_api/routes/series.py` — `_TITLE_FIELDS` has no `chapters` yet; add `chapters` to the title card so `/series` surfaces them. Keep the renderer content-agnostic. The edit path is a B32 packet (never a direct yaml write from the UI) — on Accept, the write lands in GB's lane (series_roadmap.yaml).

∞Δ∞ The outline is the seed of the book; the card is where the human keeps it aligned. Thin waist, one gate, no drift. ∞Δ∞
