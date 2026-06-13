# Ask to G — Adversarial Review Inside the Extrusion Board (Shift-Left Hardening)
*KM ask 2026-06-13: should new extruded code get an adversarial review AT the extrusion board, to harden before/as we extrude rather than catch it in a later sweep? Are we already doing it? How to integrate? GB seed offered for G to challenge; G argues freely.*

## GB's read of the current state (the gap KM intuited)
We have three review layers, and the adversarial one is in the WRONG place:
- **Tech/Arch board (WORKFLOW 17.6, 5 gates)** runs ON co-extruded code: arch-fit · test-coverage · integration-green · thin-waist/K1 · LGP (+ Gate 6 Renderability). This is a **coherence + quality** review — "does the code match the book and hold together."
- **GB rigor-audit** gates board *findings* and fix-closes (does the work hold up).
- **The 7-dimension adversarially-verified sweep** (night watch + weekly) — the layer that actually tries to BREAK the code (bypass gates, forge principals, race the ledger, find seams). **This runs AFTER extrusion+commit.**

**So the adversary meets the code days late.** Every CRITICAL/HIGH we've closed this week (apply-bypass, principal spoofing, bell hardcoded actor, CSRF, the propagation seams) was caught by a *post-hoc* sweep — the Tech/Arch board shipped the code, the sweep broke it later, we clawed back. KM's instinct = **shift the adversary left: break new extruded code AT the board, before it seals.**

## GB seed: how to integrate without recreating (challenge this)
Don't build a new reviewer — **the adversarial harness already exists** (the audit workflow). Point a SCOPED version of it at the extrusion diff at board time:
- Add **Tech/Arch Gate 7 — Adversarial Hardening**: a scoped adversarial delta (the proven targeted-audit pattern — ~60-80k tokens, read-only, the same one that caught the R-22 + W5 findings in minutes) runs on ONLY the newly-extruded files.
- **CRITICAL/HIGH block the extrusion seal** (must fix-and-re-verify before the book↔code coherence is sealed); MED/LOW become tracked obligations carried forward.
- Result: **95+ becomes the birth-floor of new code, not a state we claw back to.** The night watch demotes from primary-catcher to drift-safety-net.

## The real tension G should weigh (don't let me hand-wave it)
Every engine-touching extrusion now costs an adversarial pass (~tokens + wall-clock) on its Tech/Arch board. Worth it for code; wasteful for pure-content volumes that extrude no engine code. So the integration probably needs a **trigger**: adversarial gate fires only when the extrusion touches engine/platform code (the co-extruded modules/tests), skipped for prose-only volumes. G: is that the right cut?

## ⬇️ THE PROMPT (copy-paste to G)

**G — process-design question; think freely, then commit. Don't optimize to agree.**

Today our adversarial security/correctness review (the thing that breaks gates, forges principals, races the ledger, finds seams) lives in a POST-extrusion audit sweep — so new co-extruded code ships through the Tech/Arch board, then gets broken by the sweep days later, then we fix. KM wants to **shift the adversary left**: review new extruded code adversarially AT the extrusion board, hardening before/as we extrude.

GB's seed (agree / sharpen / reject): reuse the existing audit harness as a **scoped adversarial delta gated into the Tech/Arch board (a new Gate 7)** — runs on just the newly-extruded files, CRITICAL/HIGH block the seal, MED/LOW tracked forward; triggered only when the extrusion touches engine code, skipped for prose-only.

**Think through, then commit:**
1. Is the extrusion board the right place for the adversary, or does it belong even earlier (at code-generation time, as the agent extrudes), or stay post-hoc as a safety net? Where does breaking-it earliest pay off most vs cost most?
2. If it gates the board: what BLOCKS the seal (CRITICAL? HIGH?) vs what tracks forward, and how do we keep it from becoming a bottleneck that stalls every volume?
3. The trigger: engine-touch-only, or always? How do we detect "this extrusion touched engine code" cleanly?
4. Relationship to the post-hoc night watch: does the shift-left REPLACE the sweep for new code, or do both run (belt-and-suspenders)? What's the division of labor so we're not paying twice?
5. Failure modes: adversarial-gate-as-rubber-stamp (does it decay like any unwatched board?), token cost per volume at fan-out scale, false-positives stalling good extrusions.
6. Commit: yes/no, where it sits, what blocks, the trigger, the night-watch division — and the one-line LGP framing (does "hardened at birth" change what an heir inherits?).

Constraints (canon): one human gate · books are the source · derived-not-recreated (reuse the audit harness, don't build a parallel one) · loud failures · the freeze (this is process design, not a build, so it's freeze-safe to decide now and implement after 95+).

∞Δ∞ — *The adversary currently arrives after the code ships. KM wants it at the door. Tell us whether to move it, where, and what it costs.*
