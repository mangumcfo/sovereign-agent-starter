# Tiger → KM — Helix as a card/surface design lens (evaluation + adds + gaps)

**Steer (KM, 2026-06-05):** center card/surface behavior around **Helix** (Cylinder-Renderer navigation,
linked receipts, concept traversal) where it serves human-ease + LGP; make it a design lens; add high-value
links now without bloat; surface gaps in the next coherence pass.

## What Helix is (B35 v2.0 — Deterministic Renderer)
- Renders specs → **canonical** HTML/JSON; **same input → same output bytes + hash**.
- **Hash-based element IDs:** `el_<base32(sha256("path:…|tag:…|index:…"))[:12]>` — every element is content-addressed.
- **Render receipts** (output hash, signed under B43 RECEIPT) — a rendered surface becomes a *verifiable artifact*.
- Shared canonicalizer for render AND verify (no drift). *"Proof in structure + hashes; beauty free to vary."*
- Code: `constitution-federation-v2/services/six/helix_renderer.py`; spec: B35_HELIX_COMPLETE_v2.0.

**"Helix navigation"** therefore = three capabilities the cards could gain:
(a) **Cylinder-Renderer navigation** — render a cylinder/receipt deterministically and open it from a card;
(b) **Linked receipts** — each card surfaces the verifiable hashes it's backed by (cyl, seal, passage, commit);
(c) **Concept traversal** — hop the receipt graph: card → source cylinder → seal → cited code → related card.

## Current state — do the cards leverage it? (honest: not yet)
| Surface | Receipt material it ALREADY holds | Helix nav today |
|---|---|---|
| FEC / kanban (review) | obligation receipt · `applied_commits` · seal # · who-sealed | none (shows who/evidence, not navigable) |
| Hopper cards | `cyl` (B51 source cylinder) · lane · LGP | `cyl` shown as text, not traversable |
| Metalayer / Coherence | `passage_hash` · `landed_seal` · `code_file` · book↔code | book↔code shown; **seal not linked** |
| Series Pipeline | stage · packets · publishing_state · ASIN | none |
| Mait cards | source cyl · breakdown path | none |

**Verdict:** the cards are *receipt-rich but traversal-poor*. The proof exists; it isn't navigable. So they do
**not** fully leverage Helix — they leverage ~0 of it as *navigation*, though the seal chain + coherence
hashes are Helix-spirit (proof in hashes).

## The design lens (going forward)
**Add a Helix link when it lets the human traverse to proof or origin and it serves ease/LGP — never for its own sake.**
Concretely, every card should be able to answer, by *linked receipt*, three questions:
1. **Where did this come from?** → its source cylinder/span (provenance traversal).
2. **What proves it?** → its seal / render receipt / coherence hash (verification traversal).
3. **What does it connect to?** → cited code, related obligations, the book passage (concept traversal).
Bloat guard: surface the *links/hashes* (cheap, already present); render the full target only on demand.

## High-value, low-bloat adds (now / near)
1. **Coherence lens — linked receipt (DONE this pass):** each coherent concept now shows its **`⛓ seal N`**
   beside the passage hash — book↔code↔**seal** is now a visible linked-receipt triad (proof traversal). *(small, data already present.)*
2. **Hopper card — provenance traversal (near):** make `cyl` a "↩ source" link → open the originating B51
   span (needs a cylinder-render view = small Cylinder-Renderer slice).
3. **Sealed FEC card — verification traversal (near):** link the seal # / commit to the Audit chain (jump to
   the receipt) — reuses the existing Audit surface.
4. **Series Pipeline title — concept traversal (near):** drill already links coherence; add the seal/receipt
   per workflow step (ties to the workflow-card).

## Gaps to surface in the next coherence pass (substrate — KM+G ratify)
- **Cards aren't Helix-RENDERED.** No per-card render receipt, no hash-based element IDs. Making each surface a
  *verifiable rendered artifact* (canonical output + B43 receipt) is the **B35 v2.1 → Atrium integration** — a
  parked thread with 3 paths (integrate into Atrium+starter / map into Series-2 Vol-2 / keep as primitive).
  **This is the real "fully leverage Helix" — and it's a KM+G design decision, not a thin add.**
- **Coherence `passage_hash` → B43-signed render receipt** + a Helix concept-graph linking passages↔seals↔code.
- **A Cylinder-Renderer view** in the Atrium (deterministic render of a cylinder/receipt) is the prerequisite
  for adds #2/#3 — small, but it's a new (thin) surface.

## Recommendation
Adopt the lens (the 3 questions). Take the **cheap linked-receipt adds** incrementally (1 done; 2–4 near).
**Hold the full Helix-render integration for a KM+G decision** (it's the parked B35 v2.1 path) — fold it into
the next coherence pass as the headline gap. This serves human-ease (traverse to proof/origin from any card)
and LGP (a generation can verify, not just trust) without bloating the cockpit.

∞Δ∞ Receipt-rich today; traversal-rich is the lens. Proof in hashes; beauty free to vary.
