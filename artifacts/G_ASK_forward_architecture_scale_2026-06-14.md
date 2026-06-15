# Ask to G — Forward Architecture: can this scale to 1M books? (post-universalize)
*KM ask 2026-06-14: take the universalize-wave learnings, look forward at the 89-title catalog + design, project what surfaces at integration with current primitives, and decide what to put in place NOW to be robust + token-efficient at the 1M-book load. GB seed offered for G to challenge (architecture/scaling lens). Deliberately open.*

## GB's seed (challenge it)
**The universalize wave's real gift is scaling-shaped:** it collapsed every duplicated pattern into ONE primitive with ONE home — the ndjson gateway, the single root-resolver, the memoized-projection layer, the append-only store. That didn't just clean propagation debt — it created **chokepoints**: the exact seams where a scale-change can be made ONCE and every caller inherits it. *That is the precondition for scaling — you can't shard a substrate that 14 modules read directly; you can shard one behind a gateway.* So the question isn't "is the code clean" (it is) — it's "are the chokepoints in the right places for the 89→1M trajectory."

## Where current primitives likely break at 1M (GB's projection — sharpen/refute)
1. **The single ever-growing ndjson ledger.** Tail-parse + memoize bought headroom, but ONE append-only file per root, replayed from genesis, does not survive 1M-books-worth of obligations. Needs segment rotation + a compacted current-state snapshot (replay from snapshot, not genesis). *The gateway now makes this swappable without touching callers — design it now.*
2. **Single-node / process singleton.** The node is one process today; 1M books is inherently multi-node. **Federation (S6) stops being a future book and becomes the load-bearing architecture** — the real horizontal-scale axis.
3. **The catalog as one monolithic YAML.** `series_roadmap.yaml` is ~112KB now; it cannot be one file at catalog scale. The "queue is a query" lesson applies to the CATALOG: roadmap → a queryable/partitioned store, not a monolith.
4. **Token economics of the publishing pipeline.** Per-book boards + co-extrusion + full audit sweeps are token-expensive (we hit spend walls repeatedly at *single*-book cadence). 1M books at S1/S2 per-book cost is impossible. Scaling demands **sublinear per-book cost**: series-inherited boards/specs (a volume derives from the series, doesn't re-run it), **delta-audit as default** (the gateway enables clean change-only audit vs full sweeps), template/pattern reuse — the universalize principle applied to the PIPELINE, not just the code.
5. **Parity/visibility at scale.** The cockpit must remain a query over a partitioned store, never a scan, as cards reach millions.

## What to put in place NOW (cheap, pre-load — GB's candidates)
- **Design the ledger segment-rotation + snapshot behind the existing gateway** (the seam is already there; spec it before the load, build at need).
- **Treat S6 federation as the scaling spine**, not a content series — what's the minimum federation primitive that makes N-node real.
- **Catalog-as-query** design (roadmap → partitioned/queryable).
- **A per-book token-economics model**: derive-don't-recreate at the pipeline layer + delta-audit default + the Gate-7 birth-gate keeping new code clean so audits stay cheap.

## ⬇️ THE PROMPT (copy-paste to G — architecture/scaling lens)

**G — forward architecture review; think freely, then commit. The question is whether what we've built scales to the load an entity would put through it (target: ~1M books), not whether it's clean today (it is — 0 CRITICAL, disciplines now universal).**

Context: we just ran a "universalize wave" that collapsed every duplicated pattern into one primitive with one home (one ndjson gateway, one root resolver, one memoized-projection layer, one append-only store). The catalog is 89 titles across 12 series, fully enriched; the substrate is a single append-only ndjson obligation ledger + a Merkle attestation memory + a node_api lens layer + a YAML roadmap projection, single-node today, federation (S6) specced as future books.

GB's thesis to react to: the universalize wave's gift is that it created **chokepoints** — the seams where a scale-change is made once and all callers inherit it — which is the precondition for sharding/rotation/federation. The work now is to put the right scale-affordances at those chokepoints before the load arrives.

**Think through, then commit:**
1. **At 1M books, what breaks first?** Rank the failure modes (ledger-growth, single-node, monolithic catalog, token-cost-per-book, parity-at-scale, Merkle-memory, the lens layer). Where's the real wall, and at what scale does each hit?
2. **Token economics is the quiet killer:** per-book boards + co-extrusion + full audit sweeps are linear-or-worse per book and we hit spend walls at single-book cadence. What makes per-book cost SUBLINEAR at scale — series-inheritance, delta-audit-default, template reuse, caching? Design the cost model.
3. **Federation as the scaling spine:** is S6 the right horizontal axis, and what's the minimum federation primitive to make N-node real without forking the constitution?
4. **What to build NOW vs. defer:** given the chokepoints exist, what cheap scale-affordance do we install pre-load (ledger segment+snapshot spec, catalog-as-query, partition keys) vs. what do we correctly defer until the load is real (YAGNI guard — don't build 1M-scale machinery for 89 books)?
5. **Is this a long-term architecture an heir/entity can operate at load, or will it need a rewrite?** Name the parts that are genuinely durable vs. the parts that are 89-book scaffolding wearing a 1M-book costume.
6. **Adversarial:** what does designing-for-1M-now BREAK for the 89-book reality (premature abstraction, over-engineering, token waste building unused scale)? Where's the honest line?

Constraints (canon): one human gate · derive-not-recreate · sovereign/forkable (an entity must be able to run AND inherit it) · loud failures · token-sustainable (the architecture must be affordable to operate at load, not just correct).

∞Δ∞ — *We universalized the patterns; that built the chokepoints. Now tell us if the chokepoints are placed for 1M — and what cheap thing to put at each one before the load, without over-building for 89.*
