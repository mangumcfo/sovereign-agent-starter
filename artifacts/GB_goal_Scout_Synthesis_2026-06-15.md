# GB Synthesis — `/goal` as the Overnight Scout (G + Lumen + KM converged)
*2026-06-15. Premise: `/goal` is no substitute for craft work. The niche all three confirm: a SUBORDINATE overnight SCOUT — bounded exploration/analysis with a verifiable stop, never an author. This spec is the structure that makes KM's wariness (slop · creep · bloat) mechanically impossible to ignore. Build only on KM ratify; pilot narrow first.*

## Convergence (G + Lumen + KM)
- **Scout, not author.** Propose-only · zero writes · never decides/commits/publishes. (all three)
- **Two highest-value fits** (G): (1) *cross-functional visibility* no single human/GB holds overnight — Book↔Code drift across 89 titles, open B32, Atrium state, distribution blockers, LGP; (2) *adversarial code inspection* — objective verifiable outputs (the stale-endpoint / render-guard / overflow class we caught by hand).
- **Danger = scope creep** (G): the moment a packet suggests prose/design/architecture it's low-fidelity noise. The **fit-gate is the most important control.**
- **Green must be EARNED by evidence, not optimism** (KM's RYG + Lumen): the harness can prefer Green *only* if Green is mechanically proven.

## The design (the anti-slop structure)

**1 · Role — fit-gated, propose-only.** Use ONLY for: inventory · cross-checks · stale-reference detection · Book↔Code drift · open-obligation summarization · distribution blockers · render/fidelity issue lists · "top 3–5 next tasks from existing evidence." **NEVER:** prose · chapter/design · new architecture · final judgment · prioritization beyond bounded evidence · creating real obligations · committing/editing/sealing/publishing. *It can propose. It cannot decide.*

**2 · The brutally-small packet** (per title, hard cap **500–700 tokens**, **top 3–5 tasks only**):
```yaml
title_id:
status:
green_items:      # earned (see §3)
yellow_items:     # plausible, needs human/GB review
red_items:        # auto-rejected by lint (see §4)
top_next_tasks:   # 3–5 max, each with evidence_ref + effort
blocked_by:
evidence_refs:    # source pointer + location, mandatory
confidence:       # justified, not bare
```
Need more space → a *separate* evidence packet, never inflate the cockpit card.

**3 · RYG with EARNED Green** (KM's harness, Lumen's proof). A finding is **Green only if** ALL hold: source pointer present · location present · reason present · recommended action present · confidence justified · not a duplicate · under token cap · no prose/design/authorship. Missing any → it cannot be Green. **Yellow** = plausible/uncertain → human+GB review. **Red** = bloated/uncited/subjective/repetitive/out-of-fit-gate. *Guard: Green must never degrade into "make the packet look clean" — Green = the checklist, not the vibe.*

**4 · The packet-lint (anti-slop gate, runs BEFORE Atrium).** Auto-REJECT the packet if: no evidence refs · >5 tasks · contains a prose draft · contains an architecture proposal · repeats an existing obligation · confidence-without-basis · exceeds token cap · cannot state why it matters. *This is the volume control — only clean packets reach the cockpit.*

**5 · B32 ledger = enforcement.** The packet **proposes** obligation *candidates* (why-it-matters + effort). KM+GB disposition turns a candidate into a real obligation. The scout never creates one.

**6 · Lifecycle.** Owns ONLY the cheap **explore** stage → feeds human-gated design→build→publish→wide-distribute. Surfaces and orders; the rails (with the V1 craft bar) execute.

## How this answers KM's wariness (directly)
*"Unless structured I probably couldn't keep up with the volume."* — The structure IS the volume control: brutal-small packets + **earned-Green** + the **packet-lint** + RYG triage mean the cockpit shows **Green-preferred** (verified, sparse, actionable) by default; Yellow on demand; Red auto-rejected before you ever see it. Targeted preference for Green → you review *less*, and only what's proven — which is exactly the execution lift you hoped for.

## Sequencing (the fit-gate law applied to ourselves)
*"We don't attempt what we're not confident the methodology delivers optimally."*
1. **Spec now (this doc). Build only on KM ratify.** Not while S2 + engine-95 are the active priorities (no distraction).
2. **Pilot ONE narrow packet type first** — Book↔Code drift on ~3 titles — and measure: did the packet-lint hold? was every Green earned? zero slop? If the pilot is clean, scale to nightly all-titles. If it slops once, we stop and fix the lint before any scale.
3. **Sampled human audit** standing: GB spot-audits a random packet weekly against the lint — the night-watch-for-the-night-watch.

## The honest "no" line
Kill it if: Green degrades to cosmetic, the lint can't catch a confident-but-wrong packet, or it ever proposes craft/design. A scout that needs babysitting costs more than it saves. The whole value is *cheap, sparse, verified, propose-only* — the moment it isn't, it's the slop we agreed to avoid.

∞Δ∞ SEAL: an overnight scout, not an author — fit-gated, brutally small, earned-Green, lint-before-cockpit, propose-only into B32, human in the cockpit. Spec now, pilot narrow, scale only if zero-slop holds. LGP is why: a federation a single steward can SEE and ORDER, without drowning. 
