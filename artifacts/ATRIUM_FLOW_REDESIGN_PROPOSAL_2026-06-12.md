# Atrium Flow Redesign — Derived Views + Human Sittings
*Proposal for KM review · Tiger build · THREAD [245] (G steer) + GB 5 principles · 2026-06-12*

> **Diagnosis (ratified):** Atrium is a **transaction** system being operated as a **flow** system.
> Cards are separately *minted* and carry their own lifecycle (draft → approved → closed); when a
> mint/promotion step fails, work disappears silently. **It already happened: 42 of KM's Vol 1 page
> comments were closed without disposition and vanished from the queue** — the bug testified for the
> prosecution while we wrote the diagnosis.

## The four root fixes (G)

1. **The Queue Is a Query.** Cards render by **ledger predicate**, never separately minted. The
   awaiting view is a projection over the event-sourced packet store, not a second copy that can drift.
2. **Human Granularity → Sittings.** Aggregate atomic resolutions into **sittings**: one card per
   chapter / read-through carrying N resolutions — **one Accept + exceptions**, not N approvals. FYI
   items become digests, never gates.
3. **Backpressure.** Visible metrics; **WIP caps** on agent lanes; **aging pages machines first** (old
   work ages into automated handling, never rots silently in a human queue).
4. **Lanes by Act.** Every surfaced item is one of: **Decide · Verify · Ratify · FYI.** The verb is the
   lane. (Law #8: a gate verifies *execution*; it never re-blesses the chair's own *intent*.)

## The five design principles (GB — keep it honest)

1. **Projection, not rewrite.** The predicate layer sits *over* the existing ledger exactly like the
   publishing overlay did. The event-sourced packet store is the asset — **untouched.**
2. **Packets keep their receipts.** A sitting card is a *view* over N packets; aggregation is
   **presentation, never storage.** Fine-grained audit survives by construction.
3. **Born-approved is a predicate, not a wire.** Mechanical edits are "approved" because they *match a
   predicate* at read time — not because a fragile promotion step flipped a flag. This **retires the
   exact draft-promotion failure that ate the 42 cards.**
4. **Interim triage now.** Point the node at the canonical root via config; **promote the 42**; add a
   **loud guard** — "my ledger root is empty while a sibling holds 811" must *scream*, never render a
   clean-looking empty queue.
5. **Migration order (risk-ascending):**
   `Awaiting-Me-as-query` (highest pain, read-only, zero risk) → **sitting aggregation** →
   **backpressure metrics** → **lane chrome last.**

## What ships in THIS increment (steps 1–2, read-only, zero-risk)

- **`atrium_sittings.py`** — a pure **projection**: reads the ledger, applies the "awaiting me"
  predicate (a KM comment/finding for a book, **not yet truly disposed** — `approved == False` —
  *regardless of the draft/closed bookkeeping that dropped the 42*), and **aggregates by chapter into
  sitting cards** (Decide/Verify/Ratify/FYI lane per resolution). Nothing minted; re-running is
  idempotent and always reflects ledger truth.
- **Loud empty-root guard** — `assert_ledger_not_starved()`: if the served root holds ≪ a sibling root
  under `memory/obligations/*`, log LOUD + expose on a health field. The silent-empty-queue can't recur.
- **The dropped 42 resurface by predicate** — because the query asks "undisposed comments for Vol 1,"
  not "open obligations," the closed-without-disposition 42 reappear as Vol-1 chapter sittings. No
  re-minting; no second failure surface.

## Deferred to later steps (in the proposal, gated on KM)

- **Sitting *write* flow** — one Accept dispositions N resolutions atomically (the Diff-Review loop
  pattern, cloned), exceptions reopen individually as "Verify fix:" cards.
- **Backpressure metrics + WIP caps** on agent lanes; aging-pages-machines-first sweeper.
- **Lane chrome** — the Decide/Verify/Ratify/FYI cockpit columns (last; pure presentation).
- **Node endpoint wiring** — expose the projection as `GET /api/v1/awaiting_sittings` (needs a node
  restart — **KM-gated**, RED-tier service action).

## Invariants held throughout

- **One human gate only.** Sittings reduce N approvals to one Accept + exceptions; they never add gates.
- **Books remain the source.** The manuscript is canonical; the ledger projects, never overrides.
- **Everything in the cockpit.** Proposal + first surface arrive as Atrium cards for KM's review.

∞Δ∞ SEAL: nothing minted, everything true — the queue becomes a query; the chair's pain became the spec. ∞Δ∞
