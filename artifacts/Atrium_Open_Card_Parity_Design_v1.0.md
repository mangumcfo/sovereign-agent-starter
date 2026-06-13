# Atrium Open Card Parity — Design Overview
### Ensuring nothing is ever silently hidden or lost
**Version 1.0 · For circulation · 2026-06-13**

*Goal: a cockpit the operator can trust at a glance — no manual reconciliation, no downloads, no wondering whether something was missed.*

---

## The problem
Even with a strong, tamper-evident ledger underneath, the **surfaces** an operator looks at can drift out of sync with reality. Cards appear, disappear, or go stale; a queue can show empty while work genuinely waits. The operator is left asking *"Is everything visible? Did something slip?"* — and falls back to manual downloads, cross-checks, and reconciliation. That is the opposite of a single trustworthy surface.

The root cause is conceptual: a transaction system (the ledger) is being operated as a flow system (the human's day), and the cards in between are **separately created objects** that can lag, duplicate, or vanish.

## The invariant
**For every open item in the system, one of two things must be true:**
1. it **appears** on the correct surface, **or**
2. it has a **declared, receipted reason** for not appearing (archived · superseded · private/system lane · pending a higher gate · not yet qualified to view).

*No silent hiding. No phantom cards. No lost work.* And — critically — **every hidden item carries an expiry or review condition.** A reason without a review date eventually becomes a place where things are quietly forgotten; so "hidden" is itself a governed, time-bounded state, not a graveyard.

## How it works
- **The queue is a query.** Cards are not minted and maintained as separate objects — they **render automatically** whenever a ledger condition is true (e.g. *"open obligation, no human disposition, viewer is authorized"*). A view over truth cannot forget to exist, so the entire class of stale/missing/duplicate cards disappears at the root.
- **The Parity Pulse.** One indicator at the top of the operator's queue, seen before anything else:
  > **Parity: PASS** · engine 47 · visible 47 · hidden-by-policy 0 · divergence 0 · checked 14s ago
  Green is trust at a glance. Any divergence becomes the **top item**, with full evidence — it is impossible to miss and cannot silently persist.
- **Continuous, three-way check.** The system continuously reconciles *engine state ↔ each surface ↔ every other surface.* Divergence is graded — from "the engine holds an open item no surface shows and no policy explains" (most serious) down to a cosmetic render mismatch — and the serious classes raise loudly rather than degrade quietly.
- **Act-type lanes.** Instead of one undifferentiated pile, the work is sorted by the *kind* of human act it needs: **Decide** (rich card, accept/refine/defer) · **Verify** (aggregated to a human sitting — one card per reading, many resolutions inside, one accept) · **Ratify** (an artifact + one accept) · **FYI** (a digest line that never becomes a gate).
- **The download is the receipt, not the product.** An operator *can* export the open set as a verifiable bundle for an audit or an accountability partner — but in steady state they should never *need* to. Needing the download means the surface hasn't earned trust yet; the Pulse saying PASS is the trust.

## Where it sits in the larger discipline
The system already governs two axes of truth: **actions** (nothing executes without a gate) and **state** (nothing changes without a receipt). Open Card Parity adds the third: **visibility** (nothing hides without a declared, time-bounded reason).

> **Action → Gate · State → Receipt · Absence → Parity.**

With all three, the operator can no longer be surprised by an action, a state, *or an absence.*

## Why it matters
An heir — or any future operator — should open the cockpit and have **certainty by construction**, not a system that requires forensics to trust. The current operator had to learn, the hard way, to distrust surfaces that drift. The next one never should: they open Atrium, the Pulse reads PASS, and that is enough. **Certainty is the inheritance.**

## How we'll know it works
- The operator completes a full work session entirely inside the cockpit, with zero need to leave the surface to verify what's there.
- "Hidden-by-policy" never grows unbounded — every entry has a review date and re-enters review on expiry.
- The reconciliation runs continuously, not on demand, so parity is *proven* rather than spot-checked.

## Build approach
Reuse existing patterns — the same projection technique already used for the publishing and coherence views, and the existing verifiable-export engine — so this is **wiring and discipline, not new machinery.** Surface a working prototype for review before committing to the final operator-facing surface.

---
*Constitutional invariants preserved throughout: one human gate · hash-chained receipts on every state change · truth is derived, never hand-kept · loud failures, never silent.*
