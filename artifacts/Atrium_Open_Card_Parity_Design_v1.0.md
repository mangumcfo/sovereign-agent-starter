# Atrium Visibility Parity — Design Overview
### Ensuring nothing is ever silently hidden or lost
**Version 1.1 · For circulation · 2026-06-13**

*Goal: a cockpit whose visibility the operator can trust at a glance — no manual reconciliation, no downloads, no wondering whether something was missed.*

> **Scope, stated up front (so nothing is overclaimed):** this is **Visibility Parity** — it proves the cockpit *faithfully shows* the engine's open-card truth set. **A green Pulse means no recognized open card is hiding; it does not mean every card is correct.** Gates, receipts, and the night watch govern *correctness*. Parity governs *visibility*. The two are deliberately separate jobs.

---

## The problem
Even with a strong, tamper-evident ledger underneath, the **surfaces** an operator looks at can drift out of sync with reality. Cards appear, disappear, or go stale; a queue can show empty while work genuinely waits. The operator is left asking *"Is everything visible? Did something slip?"* — and falls back to manual downloads, cross-checks, and reconciliation. That is the opposite of a single trustworthy surface.

The root cause is conceptual: a transaction system (the ledger) is being operated as a flow system (the human's day), and the cards in between are **separately created objects** that can lag, duplicate, or vanish.

## The invariant
**For every open item in the system, one of two things must be true:**
1. it **appears** on the correct surface, **or**
2. it has a **declared, receipted reason** for not appearing (archived · superseded · private/system lane · pending a higher gate · not yet qualified to view).

*No silent hiding. No phantom cards. No lost work.* And — critically — **every hidden item carries an expiry or review condition.** A reason without a review date eventually becomes a place where things are quietly forgotten; so "hidden" is itself a governed, time-bounded state, not a graveyard.

> *Concrete example.* A card may be hidden with the reason *"superseded by the v1.4 revision — review on next volume seal (2026-07-01)."* It does not clutter the operator's queue, but it is not gone: it carries who hid it, why, and the date it must re-justify its absence. On that date it returns to review automatically.

## How it works
- **The queue is a query.** Cards are not minted and maintained as separate objects — they **render automatically** whenever a ledger condition is true (e.g. *"open obligation, no human disposition, viewer is authorized"*). A view over truth cannot forget to exist, so the entire class of stale/missing/duplicate cards disappears at the root.
- **The Parity Pulse.** The **first thing the operator sees on every sit-down** — one indicator at the very top of the queue, before any individual card. It never reduces to a bare "PASS"; it always shows what it actually checked:
  > **Visibility Parity: PASS** · epoch 2026-06-13T14:22Z · predicate `open_cards_v1.0` · surfaces 6/6 reporting · hidden-by-policy 3 · divergence 0
  Green is visibility-trust at a glance. Any divergence becomes the **top item**, with full evidence.
- **Four honest states, because silence is not success.** The Pulse reports **PASS · DEGRADED · FAIL · UNKNOWN.** If any surface fails to report, the Pulse is **DEGRADED, never PASS** — a mature system says when it cannot see, rather than rendering a confident green over a blind spot. **UNKNOWN** is a first-class state: the cockpit admits when it doesn't know.
- **Continuous, three-way check.** The system continuously reconciles *engine state ↔ each surface ↔ every other surface.* Divergence is graded — from "the engine holds an open item no surface shows and no policy explains" (most serious) down to a cosmetic render mismatch — and the serious classes raise loudly rather than degrade quietly.
- **Act-type lanes.** Instead of one undifferentiated pile, the work is sorted by the *kind* of human act it needs: **Decide** (rich card, accept/refine/defer) · **Verify** (aggregated to a human sitting — one card per reading, many resolutions inside, one accept) · **Ratify** (an artifact + one accept) · **FYI** (a digest line that never becomes a gate).
- **The download is the receipt, not the product.** An operator *can* export the open set as a verifiable bundle for an audit or an accountability partner — but in steady state they should never *need* to. Needing the download means the surface hasn't earned trust yet; the Pulse saying PASS is the trust.

## The hardest failure mode: predicate monoculture (and its guard)
The subtle danger isn't a surface drifting — it's the engine, the surfaces, and the parity checker all sharing the *same wrong definition of "open."* If the canonical predicate accidentally excludes a real open state (say, `pending_review`), then engine=47, visible=47, **Pulse PASS — while a whole class of cards was never counted.** That is faithful, confident, *wrongness.*

The guard: every Pulse is tied to a **named, versioned predicate** (`open_cards_v1.0`) with its own tests, and **the night watch independently reconstructs the open set from the raw ledger** and asks: *did the predicate include every state that should count as open? did every surface report? did any hidden item silently outlive its expiry?* This keeps the parity system from becoming **self-certifying** — the checker is itself checked, from outside, against raw truth.

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

## Pulse states (what a reader/operator should expect)
| State | Meaning |
|---|---|
| **PASS** | Every engine-recognized open card is visible or receipted-hidden; all surfaces reporting; predicate current. *(Visibility only — not a correctness claim.)* |
| **DEGRADED** | A surface didn't report, or the snapshot epoch is stale. Visibility is not currently provable — treat as "cannot confirm," not "fine." |
| **FAIL** | A real divergence: an open card hiding with no receipted reason, or a surface showing what the engine says is closed. Becomes the top card with evidence. |
| **UNKNOWN** | The checker itself can't run or the predicate version is unverified. The system admits it doesn't know. |

---

### The line for a skeptic (CTO, security reviewer, or an heir's advisor)
> **A green Pulse means no recognized open card is hiding; it does not mean every card is correct. Gates, receipts, and the night watch govern correctness. Parity governs visibility.**

*Constitutional invariants preserved throughout: one human gate · hash-chained receipts on every state change · truth is derived, never hand-kept · loud failures, never silent · the checker is checked from outside.*
