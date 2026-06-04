# RCCM — "No change" cards losing context + principles dying + tags not sticking

**Date:** 2026-06-04 · **Owner:** Tiger · **Source:** KM (Test 2 hangs; "no-change cards get lost in communication, agents lose context access"; "tags should stick with the card when complete")

## 1. Problem
A cluster of cards return **"Processed — no change"** when they shouldn't, **Test 2 (embodied principle) never surfaces a ◈ badge**, and the **reflection-mode tag doesn't persist** on the completed/sealed card.

## 2. Per-card analysis (the 5 live "no change" cards)
| Card | What KM said | Why it died | Root cause |
|---|---|---|---|
| 521882 (p29) | "should be 'must' … not a bold" | refers to a **prior obligation's** diff the producer never received | **RC2 context-loss** |
| 466778 (p29) | **"This is a K invariant.** not a bolding request" | a **principle/K-invariant** → producer has no home for it → "not a book edit" | **RC1 principle-dies** (+ RC2: refers to prior oblig) |
| 422486 (p29) | "It **must hold the same focus**" (on a selected line) | a **principle** anchored to a passage → classified as a mere "observation" | **RC1 principle-dies** |
| 065956 (p13) | "hand this over to **Tiger**, don't lose these ideas" | a **tooling/handoff** ask → died as "no change" instead of routing to Tiger | **RC3 tooling-dead-ends** |
| 019402 (p13) | "Any way to create **kdp click-through links**?" | a **feasibility/tooling** question → "not a manuscript edit" | **RC3 tooling-dead-ends** |

## 3. Root causes
- **RC1 — Embodied principles / K-invariants have no home.** The producer attaches `reflection_mode` only to a *diff group*; a principle usually has **no literal diff** → it returns empty groups → bare "no change." The classification + the principle are lost, and ◈ principle (Test 2) can never appear.
- **RC2 — In-card notes lose the passage/prior-diff context.** A note like "this should be 'must'" or "this is a K invariant" references a **prior obligation's** content, but the new packet carries only the note + page — not the prior obligation's intent/diff. The producer can't ground "this." (KM's hypothesis — confirmed.)
- **RC3 — Tooling/feasibility asks dead-end as "no change"** instead of routing to Tiger's tooling lane — even when KM literally says "hand this to Tiger, don't lose these ideas."
- **RC4 — The reflection-mode tag doesn't persist.** The badge lives on the proposal's diff group; the sealed card re-renders the diff without it, so the tag is lost on completion. (KM: "tags should stick with the card.")

## 4. Corrective measures
- **CM1 (RC1):** Producer treats an **embodied principle / K-invariant as a valid classified outcome** — returns `info:true` **+ `reflection_mode:"embodied_principle"` + `principle`** (routed to GB fidelity + drift watch), never a bare "no change." Surfaces as **◈ Principle captured**.
- **CM2 (RC2):** **In-card notes carry the originating card's context** — `_atrCardSend` pulls the source obligation's intent **and its prior diff (before/after)** into the new packet so "this/that" is grounded.
- **CM3 (RC3):** Producer classifies non-edit asks with a **`route`** ("tooling" | "principle" | "observation"); tooling ones surface a **"Send to Tiger"** action (open a tooling obligation) instead of a dead "no change."
- **CM4 (RC4):** The **reflection-mode badge persists on the sealed card's diff** (and applied cards keep their `reflection_mode`).

## 5. Verification
After: Test 2 ("this is a K invariant") → a **◈ Principle captured** card (not "no change"); an in-card "make this 'must'" grounds against the prior diff; a "hand to Tiger" note offers Send-to-Tiger; a sealed card shows its ⚙/◈ tag.

∞Δ∞
