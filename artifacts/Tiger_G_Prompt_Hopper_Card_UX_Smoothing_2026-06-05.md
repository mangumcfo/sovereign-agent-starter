# Tiger → G (grok) — Design the smoother hopper / intake-card experience

*Paste-ready for G on grok.com. KM relays. Goal: G designs a concrete, buildable UX so KM can interact with
hopper/intake cards richly — understand where each idea routes, ask an agent about it, see where it lands and
its status — and so the cockpit guides even the steps that happen outside Atrium.*

---

**G — KM is using the Atrium cockpit live and the hopper (intake) cards are too thin to act on. We need your design.**

## Context (the system you're designing for)
- **The Atrium** is KM's primacy cockpit. The **Hopper** is the intake lane: captured ideas (B51 voice
  transcripts, text, screenshots) surface as **cards**. Each card today shows: a lane chip (tooling /
  coordination / private-learning / book), priority, an LGP hint, a one-line intent, and two buttons —
  **Send to Packet** and **Dismiss**. Clicking opens a popup with the full text + the same two buttons.
- **Send to Packet** opens a **B32 obligation** (a DRAFT debit) on the node; the **governed loop**
  (review → accept → apply → seal) takes it from there. Accepted book-edits render as rich **FEC cards**
  (story + 3 tiles + diff + one Accept gate). The **Series Pipeline** shows the book lifecycle; the
  **Coherence lens** shows book↔code fidelity.
- **3-lane fence:** KM ratifies · Tiger (executor) builds · GB (meta) proposes/curates. **K1:** one human
  gate (Accept). **LGP** is the judgment rule (families-first, minimal burden, generational).

## The problems (KM's words, paraphrased — design against ALL of these)
1. **Cards are too thin to act on.** KM sees one statement + Send/Dismiss. He can't tell **what the recommended
   activity is, where the concept falls (a book? a series? a book-update? a tooling task for Tiger? a process
   change?), or where the impact lands in the flow.**
2. **No way to ask.** KM wants to **ask an agent questions about a card** ("what is this, where does this go,
   should I send it, is it redundant?") right there — a conversational affordance, not just two buttons.
3. **No landing/status visibility.** When he hits Send to Packet, the card gives **no indication of where it
   lands or that anything changed** — and no status as it moves through the loop.
4. **He doesn't know which FEC card type(s)** a packet will become once it moves along.
5. **Out-of-Atrium manual handoffs.** Some flows require leaving Atrium — e.g. **KDP's rigid web interface**
   for publishing. KM wants the cockpit/renderer to **guide him through the whole flow including the manual,
   human-must-do-it-outside-Atrium steps** (a guided checklist with "do this in KDP now → mark done → resume"),
   for any capability not yet automatable in Atrium.
6. **Redundancy + stale cards.** The feed has **duplicates and already-done items** (e.g. "make hopper cards
   rich" — already built; the same Mait-call idea seeded 5×). KM wants intake to **check for redundancy/stale
   before adding**, and cards to show if they're already done/in-progress.
7. **Full-span breakdown.** KM's standing steer: **any voice recording/transcript should get a complete
   breakdown + inference across ALL spans**, so we pick up **every** related impact to **every** workstream /
   open project / activity — then route each impact to where it belongs. (This is the upstream of the cards.)

## Design questions for you (G) — give concrete, buildable answers
1. **Card anatomy.** What should a hopper/intake card show so KM can act in one glance? Propose the fields and
   layout: lane · a **routing classification** (see Q2) · **recommended next action** · **where it lands** ·
   **status** · the one-line intent · provenance (B51 cyl + span) · LGP. Keep it lightweight (thin intent, not
   a full FEC body) but **decision-complete**.
2. **Routing taxonomy.** Define the small, fixed set of **destinations** an intake idea can route to, so each
   card says where it goes: e.g. `book-edit` (which book/chapter) · `new-series/title` · `tooling→Tiger build`
   · `process/governance change` · `coordination/decision (KM)` · `meta (GB)` · `research/G` · `not-actionable/
   park`. What's the right taxonomy + how is it shown?
3. **Agent Q&A in-card.** Design the conversational affordance: KM asks a question about the card; an agent
   answers (grounded in the card + repo state) and can **recommend** route/action — without auto-acting (K1).
   What does the interaction look like (inline chat? a "?" that expands?)? What can the agent answer vs not?
4. **Landing + status.** After Send to Packet, what should the card show — the obligation id, the lane it
   landed in, the next step, and a live status as it moves (drafted → processing → diffs-ready → sealed)?
5. **FEC card-type preview.** Before sending, how should a card indicate **which FEC card type(s)** it will
   become (book-diff card · tooling card · coordination note · info/no-change), so KM knows what he's creating?
6. **Out-of-Atrium guided handoffs.** Design the pattern for guiding a human through steps Atrium can't do
   itself (KDP upload, a web form, a physical action): a **guided checklist** with per-step "do this outside →
   mark done → resume in Atrium," evidence capture, and honest "not-yet-automatable" labeling.
7. **Redundancy/stale + full-span breakdown.** How should the **intake** (upstream of the cards) (a) do the
   full-span breakdown of a transcript so no impact is lost, (b) **dedupe** against existing cards/obligations,
   and (c) **mark done/stale** so KM never sees a card for work already shipped?

## Constraints (hold these)
Lightweight + honest (label forward/partial/done loudly) · thin-waist (no new layers) · K1 one human gate
(agents recommend, never auto-act) · 3-lane fence (GB curates the feed, Tiger builds the surface, KM ratifies)
· LGP as the judgment rule · reuse the existing FEC/kanban/coherence chrome where possible.

**Deliver:** a concrete design — card anatomy + routing taxonomy + the Q&A interaction + landing/status model +
the out-of-Atrium guided-handoff pattern + the dedup/full-span-breakdown discipline — that Tiger can build
incrementally and KM can ratify. Note what's a thin Tiger build vs a deeper substrate change.

Thank you, G. ∞Δ∞
