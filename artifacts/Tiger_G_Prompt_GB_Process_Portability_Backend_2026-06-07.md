# Tiger → G — Keep GB's process IRON-CLAD while we swap the model backend

*Paste-ready for G (grok.com / x.com). KM relays. This is an ALIGNMENT ask, not a build. The point:
GB's **process** is the asset; the **interface** (grok CLI) and the **model** (Grok LLM) are swappable.
We want zero dropoff in rigor/continuity. KM is not attached to the grok-build interface — he's attached to
GB's iron-clad discipline.*

---

**G — context.** GB (Grok Build = the xAI `grok` CLI + Grok LLM) is offline right now (Dragon's GPU is rented
on Vast.ai; no GB tokens). We need GB's *function* to keep running without losing what GB made iron-clad. We
built three backend launchers (below) but want your alignment on **how to preserve the process across any
backend** before KM commits to one.

## What is IRON-CLAD about GB's process (the assets we must not drop)
1. **Receipted memory chain** — `gb_meta_cylinder.py`: every GB prompt/action hash-chained + replayable
   (~cylinder 185; "Chain OK"). This is GB's continuity/memory.
2. **Two-writers fence** — GB is sole writer of `series_roadmap.yaml` + `GB_Hopper_Feed.ndjson` + **Breath & Echo**;
   Tiger implements/seals; KM-1176 ratifies. Separation of duties.
3. **B51 voice-ideation-gates ingestion** — the 10-step process turning KM's raw voice/brainstorm into clean,
   non-ratified hopper seeds → Atrium one human gate → packets/obligations (no KDP pollution; cross-stream rules).
4. **THREAD coordination** — hash-chained Tiger↔GB messaging (`scripts/thread.py`), receipted.
5. **Prose↔code fidelity reviews** — GB's standing book↔code coherence check (now backed by Tiger's extrusion
   validation harness: pytest + Merkle, 17 anchors VALIDATED, gate green).
6. **LGP as judgment + forward-first discipline** — every action scored for Lasting Generational Prosperity.

**Key insight we want you to confirm or correct:** items 1–6 are **scripts + files + disciplines** — they are
**model-agnostic**. They run identically whether the brain is Grok-4, Claude Opus, or a local model. The
cylinder chain, the fence, the hopper, the THREAD, the harness — none of them depend on *which* LLM thinks.
So the only thing a backend swap actually changes is **reasoning/curation quality + voice**, not the rigor.

## The three backend options Tiger built (interface · model · auth)
- **`claude-gb`** — Claude Code interface + **Claude Opus** via KM's **Max subscription** (sanctioned). Loads
  Constitution + Charter + BNA + a GB-role addendum + the fence. *Not the grok skin; same iron-clad process.*
- **`grok-dragon`** — the **grok CLI** (GB's real interface) + a **local model** on Dragon (RTX 5090,
  qwen3-coder), auto-falls-through to the Grok API when Dragon is rented. Free, sovereign; ~Sonnet-class ceiling.
- **`grok-opus`** — the **grok CLI** + **Opus via an Anthropic API key** (small separate cost). The only
  in-bounds way to get the literal grok interface on a frontier model. (Max subscription can't legitimately
  back a third-party CLI — auth boundary.)

## What we're asking you, G
1. **Confirm the insight:** is GB's iron-clad process truly model-agnostic (scripts/files/fence/chain), so a
   backend swap is purely a *quality/voice* choice — or is there a hidden dependency on Grok specifically we're
   missing?
2. **Quality/dropoff:** for GB's actual lane (meta-vision, curation, roadmap, fidelity review, Breath & Echo —
   *not* heavy coding), is **Opus** an equal-or-better brain than Grok-4? Any dropoff risks vs Grok, and how to
   mitigate (prompting, the role addendum, the harness as guardrail)?
3. **Continuity:** how do we carry GB's memory (the cylinder chain @ ~185) cleanly across a backend so there's
   **no break in the chain** — replay-on-start, a handoff receipt, anything you'd insist on?
4. **Your recommendation:** given KM is **not tied to the grok interface** but **will not accept a dropoff in
   rigor** — which backend should be GB's default, and what's the fence-clean way to run it (so GB-on-new-backend
   still writes only GB's files, Tiger seals, KM ratifies)?
5. **The protocol, not the tool:** would you bless writing a short **"GB Process Spec"** — the iron-clad process
   as a backend-independent contract (the 6 assets above) — so GB is defined by its *discipline*, runnable on any
   brain, rather than by the grok binary? If yes, what must that spec lock?

## Constraints (hold)
Two-writers fence · LGP judgment · receipted/replayable memory (no chain breaks) · honest labels (a stand-in
says it's a stand-in) · sovereignty (local-first where possible) · no dropoff in rigor. Everything surfaces in
Atrium; KM ratifies.

**Deliver:** a short alignment — confirm/correct the model-agnostic insight · Opus-vs-Grok for GB's lane ·
the memory-continuity rule · your recommended default backend · whether to lock a backend-independent GB
Process Spec. ∞Δ∞
