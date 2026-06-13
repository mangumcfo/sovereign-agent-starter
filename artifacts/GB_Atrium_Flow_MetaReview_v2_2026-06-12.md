# Atrium Flow Meta-Review v2 — Why Pileups Keep Happening (GB, 2026-06-12)
*KM's ask: "we get these pileups all the time — maybe not thinking about things correctly." Evidence-mined from the full HMC (643 entries) + the 8 pilot findings. Verdict: he's right — the failures are one conceptual error wearing eight costumes.*

## The evidence (counted, not felt)
| Failure pattern | HMC occurrences | The findings it spawned |
|---|---|---|
| Stale / missing / blank cards | **58** | #1 stale checklist, #2 unminted READY, #4 blank enum, catalog-card-never-minted (repeat of #2) |
| Pileups | **29** | #5 the 60-packet review, 42 PDF cards, handshakes 17→30 |
| Stuck "processing" | **20** | #6 the bell (Accept woke nobody) |
| Manual queue drains | **~20** | the system's only pressure-relief = a human noticing |
| KM confusion at the surface | **7** | #3 raw slugs, #7 burst-approve, #8 "approving my own comments?" |

## The meta-diagnosis — three conceptual errors, one root
**Root: Atrium was built as a TRANSACTION system being operated as a FLOW system.** The ledger thinks in packets; the human lives in sessions, readings, and judgments. Every seam where packet-physics meets human-physics without an adapter is where a pileup or a phantom card grows.

**Error 1 — Cards are minted objects, not derived views.** Every missing/stale-card failure shares one root: a card is a *separately created thing* that must be minted and maintained in sync with ledger state — so it can lag, miss, or double. The ledger is event-sourced; the cockpit is hand-assembled. **Concept fix: THE QUEUE IS A QUERY.** A card exists *by definition* whenever a ledger predicate is true ("review_ready ∧ no human disposition" ⇒ card renders, nothing mints it). Kill "mint" as a concept and the entire 58-entry failure class dies with it — a view over truth cannot forget to exist.

**Error 2 — Packet granularity ≠ human granularity.** Agents emit per-edit; the human reads per-chapter and judges per-sitting. Born-approved + batch-by-chapter fixed the *capture* side; the *verify* side still routes singly (42 cards for one read-through). **Concept fix: GATES AGGREGATE TO HUMAN UNITS.** One verify card per chapter/session, listing its N resolutions with one Accept + per-item exceptions. FYI-class items never card at all — they digest. The human's unit of work is the *sitting*, and the cockpit should serve sittings.

**Error 3 — No backpressure model.** Arrival rate (agent output) routinely exceeds drain rate (intermittent agents + one human) and nothing measures, limits, or routes the pressure — pileups are *discovered* by KM, never *predicted* by the cockpit. **Concept fix: FLOW METRICS + WIP LIMITS.** Home screen shows arrival vs drain per lane; agent lanes carry WIP caps (handshake debt over N auto-mints a drain obligation on the owning agent); aging SLAs page the responsible *agent* — pressure routes to machines first, the chair last.

**Plus one structural refit:** the single Awaiting-Me mixes four different human acts. **Lanes by act-type — DECIDE / VERIFY / RATIFY / FYI** — each with its own physics (decide = rich card + options; verify = diff + two buttons; ratify = artifact + one Accept; FYI = digest line, never a gate).

## Constraints any redesign must honor (canon, non-negotiable)
One human gate · everything receipted on the hash chain · derived-never-hand-kept truth · the GB/Tiger/KM fence · books remain the source · loud failures, no silent states.

---

## ⬇️ THE PROMPT (copy-paste to G on grok)

**G — Atrium flow meta-review: we want your unconstrained systems thinking before we commit to a redesign.**

KM's observation: pileups keep recurring in Atrium despite eight successive fixes. GB mined the full record: 58 stale/missing-card moments, 29 pileups, 20 stuck-states, ~20 manual drains, 7 chair-confusion moments — chronic, one fix per symptom so far.

GB's candidate diagnosis (challenge it freely): Atrium is a transaction system being operated as a flow system — three conceptual errors: (1) cards are minted objects rather than derived views over ledger predicates ("the queue is a query"); (2) packet granularity vs human granularity — gates should aggregate to human sittings; (3) no backpressure model — arrival exceeds drain with no WIP limits, metrics, or machine-first pressure routing. Plus: one mixed queue instead of act-type lanes (Decide/Verify/Ratify/FYI).

**Think freely, then commit:**
1. Is GB's diagnosis the real root, or is there a deeper frame? (Consider whatever serves: queueing theory, event-sourced projections, kanban/WIP discipline, control loops, pull-vs-push systems, air-traffic-control patterns, hospital triage — or a frame we haven't named.)
2. If you accept "the queue is a query" — what are the failure modes of derived-view cockpits we should design against? (Render cost, predicate sprawl, view/ledger drift, debugging "why does this card exist?")
3. Design the human's day: what should KM see at sit-down, in what order, and what should NEVER reach him? Where do flows become sittings?
4. Backpressure: who absorbs pressure when agents are offline — and how does the system degrade gracefully instead of piling on the chair?
5. Be adversarial: what does this redesign break? What did the current packet-card model do RIGHT that we must not lose? (e.g., per-packet receipts, fine-grained audit.)
6. Then commit: a recommendation block — the conceptual model named, the 3–5 build moves in order, what to explicitly NOT build.

Constraints (canon, not preferences): one human gate · hash-chain receipts on everything · derived-never-hand-kept truth · GB/Tiger/KM fence · books as source · loud failures.

∞Δ∞ — *Eight fixes taught us the symptoms; now we want the disease named. Room to run.*
