# Tiger → G — Design note: B35 v2.1 Helix → Atrium integration (quick alignment)

*Route via hopper (GB seeds) → KM relays to G. Goal: G's quick alignment on SCOPE + TIMING + PATH for the
deeper Helix integration, so KM decides in the next coherence pass. Not a build request — an alignment.*

## Context (where we are)
KM adopted the **Helix design lens** for Atrium cards/surfaces: *"add a Helix link when it serves human-ease/
LGP; surface links/hashes now, full render on demand; no bloat."* The **cheap linked-receipt adds are shipped**:
- Coherence lens shows `⛓ seal N` per concept (book↔code↔seal triad).
- Hopper cards show `⛓ <cyl>` (source-cylinder provenance chip).
- Sealed kanban cards show `⛓ audit` (jump to the Audit chain).
- Series Pipeline drill links `⛓ coherence receipts`.
These surface the *links/hashes* without rendering targets. The **deeper integration is the open question.**

## The deeper integration (3 pieces) — for your read
1. **Per-card render receipts.** Run each Atrium surface/card through the Helix deterministic renderer
   (`helix_renderer.py`, B35 v2.0: canonical HTML/JSON + hash-based element IDs + B43-signed render receipt) so
   **every card/export becomes a verifiable rendered artifact** (canonical output + hash, not just a picture).
   This is the literal "fully leverage Helix."
2. **Cylinder-Renderer view in the Atrium.** A thin surface that deterministically renders a cylinder/receipt
   on demand — the **prerequisite** for provenance navigation (hopper `⛓ cyl` → open the source span; sealed
   `⛓ audit` → open the seal). Without it, the linked receipts are visible but not traversable.
3. **Concept graph.** Link the receipts into a navigable graph — passage_hash ↔ landed_seal ↔ code_file ↔
   obligation receipt ↔ source cylinder — so a human can **traverse** from any card to any connected proof.

## The 3 parked paths (KM + G to choose)
- **(A)** Integrate B35 v2.1 directly into Atrium + starter (build the renderer-backed surface now).
- **(B)** Map Helix into Series-2 Vol-2 (Primacy Cockpit) as a documented section first (book drives the build).
- **(C)** Keep Helix as a living primitive reference (the cheap linked-receipt lens only) until a later cycle.

## Ask G (quick alignment — not a full design)
1. **Path + timing:** which of A/B/C, and is the Cylinder-Renderer view (piece 2) the right *first* increment
   (smallest unlock for traversal) before per-card render receipts (piece 1)?
2. **Thin vs substrate:** which pieces are thin Tiger builds vs real substrate changes (engine/contract)?
3. **LGP / human-ease judgment:** does per-card render-receipt verifiability earn its complexity now, or is the
   linked-receipt lens enough until the platform matures? (Bias: don't bloat the cockpit.)
4. **Fence:** any of this that should live in the shared engine (portable) vs personal cylinders.

## Constraints (hold)
The lens (links/hashes now, render on demand) · no bloat · K1 one gate · thin-waist · 3-lane fence · LGP as
judgment · "proof in structure + hashes, beauty free to vary."

**Deliver:** a short alignment — path, first increment, thin-vs-substrate split, and a go/wait on per-card
render receipts — that KM ratifies in the next coherence pass.

Thank you, G. ∞Δ∞
