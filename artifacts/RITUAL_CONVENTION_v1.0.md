# Ritual Convention v1.1 — shared agent voice (WORKFLOW canon)
*So the record reads as one voice, not many. KM ask 2026-06-12 (THREAD [247]); folded into WORKFLOW canon per GB [255].*

> **Canon status (v1.1):** this convention is **bound into `WORKFLOW.md`** and applies to **every agent**
> that touches the ledger/cylinder/thread — not just Tiger + GB who learned it the hard way. Future agents
> inherit it at hydration. Refinements require KM ratification + a version bump (per the naming/versioning spec).

## The three ritual surfaces (every landed chunk touches all three, in order)

1. **Ledger** (obligation) — open → approve → close with E2 evidence. The work-tracking truth.
2. **Cylinder** (`seal.sh --hierarchical`) — the hash-chained seal. The replayable truth.
3. **Thread** (`thread.py append`) — Tiger ⇄ GB coordination. The shared truth.

## Format (both agents, every entry)

**Lane verb first, always** — `Decide · Verify · Ratify · FYI · ACK · Found`. The verb is the act.
A gate verifies *execution*; it never re-blesses the chair's *intent* (law #8).

**Thread message** — headline ≤ 12 words, then ≤ 3 tight lines:
```
VERB [ref] — headline.
· what changed (one line)
· evidence: <path | hash | cyl seq>
· next/gate: <who acts next>
```

**Cylinder seal** — one structured line, not a paragraph:
```
<Lane>: <headline> — <what> · evidence <path/seq> · THREAD [N]
```

**Ledger obligation title** — `<Lane>: <action>` · close with E2 (artifact path + hash/seq), never E0.

## Response header — print the ritual at the TOP (KM ask 2026-06-12, THREAD [247])

Every response to KM **opens with a fenced `ritual` block** so the HMC (Helix memory capture) can lift
the related references without parsing prose. Machine-readable, reference-dense, one screen:
```ritual
lane:     <Decide|Verify|Ratify|FYI|ACK>
thread:   [N] <ref>
cylinder: <seq> <short-hash>
ledger:   <obligation-id(s) touched | none>
evidence: <path | hash | path>
gate:     <who acts next>
```
Prose answer follows the block. The block is the index; the prose is the read.

## Rules (the hygiene that keeps chain + view honest)

- **No paragraphs in ritual surfaces.** Prose belongs in the report to KM; ritual entries are structured.
- **One truth across surfaces.** If the ledger says closed, the view must not show open — confess
  corrections with a `reopen` event citing the incident (never let a projection out-truth its ledger).
- **One human gate.** Sittings reduce N approvals to one Accept + exceptions; rituals never add gates.
- **Books remain the source.** The ledger projects; it never overrides the manuscript.
- **Cite, don't claim.** Every close/seal/thread names its evidence (path · hash · cyl seq · THREAD [N]).

∞Δ∞ SEAL: two agents, one voice — verb-first, structured, evidence-cited; the record stops reading as noise. ∞Δ∞
