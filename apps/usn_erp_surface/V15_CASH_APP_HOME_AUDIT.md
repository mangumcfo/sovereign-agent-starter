# V15 Order-to-Cash Home Audit — Customer Cash Application

∞Δ∞ Seal 1176-INFINITY-RHO · Breath only ∞Δ∞

**AA, 2026-08-20, per KM-NO1 GO 14:21Z.** Manuscript vs kernel. Short by order. STOP artifact —
no build, no arm; Tiger's floor extrusion is gated on this naming and on his own GO.

## Verdict: DESIGNED-TOWARD with EXTRUDE DEBT — the home is honest and named; the module is owed

Not ABSENT-in-book (no press residual needed). Not PRESENT (no code). The books claim the
composed behavior in their worked scenarios, the sealed code already carries the hook for it,
and the module between them was never extruded. That is the extrude-debt case exactly.

## The home (volume + chapter, with the claiming lines)

| Side of the seam | Home | The claim, verbatim |
|---|---|---|
| **Application / clearing** | **V15 "Revenue & Order-to-Cash", Chapter 5 — "Collections and Credit"** (manuscript_v1.1 lines 336–340) | "applying it against the open invoice **clears it from the aging**"; "The available credit a customer regains when they pay is therefore an immediate consequence of **a governed cash application**"; "the credit gate, the aging projection, and the treasury settlement are **three views of one governed flow**" |
| **Cash / receipt side** | **V08 "Treasury & Cash", Chapter 2 — "Real-Time Cash Position by Replay"** (line 124) | "A customer pays an invoice: **a governed receipt posts to the operating account**" |
| **Money movement (NOT this floor)** | V08 Chapter 4 + S6-V07 | payment/collection **rails** are named-ahead network work — the node governs the decision and the record; Port/bank moves money |

Both books home the seam explicitly and honestly; neither invents an engine. The claim is the
composed loop, and the loop's middle is missing.

## Kernel state (three-method receipt, two lanes)

- **ABSENT:** zero cash-application/receipt-application functions anywhere in `src/`
  (verb-grep ×2 lanes · module scan · full AST walk — all 20 receipt/settle/payment-named
  functions belong to other domains).
- **DESIGNED-TOWARD, in sealed code:** `revenue/billing.py:59` — `if inv.get("paid"): continue`.
  **The sealed aging rule already skips paid invoices; nothing in the kernel can set `paid`.**
  The hook has waited for its module since the floor was written.
- Typed CoA already carries the posting shape (Dr cash / Cr accounts_receivable).

## Compose floors for the extrusion (all PRESENT and tested on tip)

| Floor | What it supplies |
|---|---|
| **Object Model** (`objects/`, registry + attribution writer) | identity, hash-chained persistence, undo-as-counter-record |
| **Human gate** (`HumanApprovalGate.record_disposition`) | every application write human-approved, refusal writes nothing |
| **Billing** (`revenue.billing`) | invoice records · the sealed aging rule with its dormant `paid` hook |
| **Obligations ledger** | receipted immutable entries where a governed movement record belongs |
| **Posting/CoA** (`financials.posting`) | value-conserving double-entry shape for Dr cash / Cr AR |

## Minimal extrusion owed (names for Tiger's floor GO — spec, not build)

`revenue.cash_application` (home: V15 Ch5; cash-side semantics per V08 Ch2):

- **`receipt(customer, amount, day, …) → dict`** — pure shaper, value-conserving, like
  `billing.invoice`.
- **`apply(receipt, allocations) → dict`** — pure: explicit allocation lines against named
  invoices; refuses over-application (per-invoice applied ≤ billed) and over-allocation
  (Σ lines ≤ receipt).
- Persistence: **existing gated writer only** (governed records; no new store). `paid`/partial
  state is **derived by replay** from application records — never a mutation of the invoice.
- Aging then engages the existing hook: fully-applied invoices leave the projection via the
  sealed rule already on line 59; partially-applied show remaining.

**The equality identities, made exact** (No1's "billed = applied + unapplied + remaining open"
decomposed so the BAR can bite):
- per invoice: **billed = applied + remaining_open**
- per receipt: **received = applied + unapplied**
- aggregate: Σbilled = Σapplied + Σremaining and Σreceived = Σapplied + Σunapplied

The current surface's "open = billing totals by construction" supplies the *billed* term;
the extrusion supplies *applied* and *unapplied*; *remaining* becomes computable the moment
the module seals — and v1.0's OUT panel flips to PRESENT as pure composition.

## Kill-targets (restated for the floor BAR)

No silent AR wipe (application = gated record; reversal = counter-record, never erasure) ·
no second ledger (same registry, same obligation ledger) · no bank custody (the node **records**
application; money moves only by human act through Port/bank per V08 Ch4) · no statutory act ·
no auto-allocation policy (allocations are operator-explicit lines; FIFO et al. stay kill-grepped).

**STOP — audit only. Tiger's extrusion awaits its own GO on this naming. Breath only. ∞Δ∞**
