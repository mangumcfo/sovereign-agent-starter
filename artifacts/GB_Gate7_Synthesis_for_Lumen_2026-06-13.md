# Tech/Arch Gate 7 — Adversarial Hardening: Synthesis + Lumen Pressure-Test
*KM concept → GB seed → G-x.com + G-grok both RATIFIED. Now to Lumen for the disease-prevention pass (Lumen's edge: the failure mode hiding inside the fix — cf. the parity "hidden-by-policy graveyard" catch). GB synthesizes; Lumen sharpens; then KM ratifies + Tiger builds (after 95+, freeze-safe to design now).*

## The near-final design (G-ratified, converged)
**Gate 7 — Adversarial Hardening**, added to the Tech/Arch board (WORKFLOW 17.6), wired into the Review-Ready Contract so it runs before a book reaches KM:
- **Mechanism:** a SCOPED run of the existing audit harness (reuse, don't recreate) on ONLY the newly-extruded files. The proven targeted-delta pattern (~60-80k tokens, minutes).
- **Trigger:** fires only when the extrusion touches engine/platform code (changed files in `src/` + `tests/`); prose-only volumes skip it.
- **Block vs track:** CRITICAL/HIGH **block the seal** (fix + re-verify before book↔code coherence seals); MED/LOW **track forward** as obligations; **advisory-only** category for low-confidence findings that don't block.
- **Honesty:** R1.5 rigor (sampled audit, LGP alignment, human-sense) applies to this gate too.
- **Division of labor:** does NOT replace the night watch — the board becomes the **birth gate**, the sweep becomes **drift-safety-net + regression guard.**
- **LGP:** an heir inherits code **hardened at birth**, not clawed back later. 95+ becomes the floor new code is born at.

## The three questions for Lumen (where the design is still soft)
GB flags these as the spots most likely to rot — Lumen, rule on them:

**Q1 — The advisory-downgrade pressure (the Goodhart of THIS gate).** G added an "advisory-only" category for low-confidence findings. But the seal-pressure (every extrusion *wants* to pass) will push real CRITICAL/HIGH findings DOWN into "advisory" to avoid blocking — the same way "hidden-by-policy" threatened to become a graveyard on the parity work. **What stops advisory from becoming the dumping ground where blocking findings go to be ignored?** (Candidate, for Lumen to confirm/replace: every advisory-downgrade is itself a receipted decision with an author + reason; a finding can only be downgraded by the human gate, never by the agent that wants its code to ship; downgrades are sampled-audited.)

**Q2 — Who watches the adversarial gate? (watcher-watched, one level deeper).** An adversarial gate that runs on every extrusion is itself a board that can decay into rubber-stamp — and it's the *last* gate before code is trusted, so its decay is the most dangerous. R1.5 sampled-audit helps, but: **does Gate 7 need its own meta-adversarial check — a periodic "did the birth-gate actually try to break this, or wave it through?" — and who runs it?** (The night watch re-finding something Gate 7 should have caught = a Gate-7-failure signal, not just a code finding. Is that the feedback loop?)

**Q3 — The constitutional framing.** The parity synthesis named three axes: action→gate, state→receipt, absence→parity. Gate 7 isn't a new axis — it's a *relocation in time* (the adversary moves from patrol to birth). **Is "hardened at birth" a fourth thing, or is it the maturation of the existing three — the moment the engine starts being born constitutional instead of made constitutional?** Lumen's framing tends to be the one that sticks.

## ⬇️ THE PROMPT (copy-paste to Lumen)

**Lumen — Gate 7 (Adversarial Hardening) is GB-synthesized and dual-G-ratified; I want your disease-prevention pass before we build. You caught the "hidden-by-policy graveyard" on the parity work — find the equivalent here.**

The design (near-final): add an adversarial review to the extrusion board (Tech/Arch Gate 7) — a scoped run of the existing audit harness on newly-extruded engine files, at board time, before the book↔code seal. CRITICAL/HIGH block the seal; MED/LOW track; advisory-only for low-confidence; triggered on engine-touch; complements (doesn't replace) the night watch; an heir inherits code hardened at birth.

**Rule on the three soft spots, then commit:**
1. **Advisory-downgrade pressure:** what stops "advisory-only" from becoming the graveyard where blocking findings get quietly downgraded to ship the code? (Who may downgrade, with what receipt, audited how?)
2. **Watcher-watched:** an adversarial gate is itself a board that can decay into rubber-stamp — and it's the last gate before trust. Does it need its own meta-check? Is "the night watch re-finds what Gate 7 missed" the honest feedback loop, or is that too late?
3. **Constitutional framing:** is "hardened at birth" a 4th axis beside action→gate / state→receipt / absence→parity, or the maturation of the three? Name it the way it should be named.
4. **Adversarial on the whole idea:** what does shifting-left BREAK that the post-hoc model did right? (e.g., does birth-gating create false confidence that suppresses the night watch's vigilance? does per-extrusion adversarial cost change behavior at fan-out scale — do we extrude less, or worse, to avoid the gate?)
5. **Commit:** build it / don't / build-it-differently, the downgrade guard, the meta-check, the framing, the one-line LGP.

Constraints (canon): one human gate · books are the source · derive-not-recreate (reuse the audit harness) · loud failures · freeze-safe (process design now, implement after 95+).

∞Δ∞ — *The adversary moves to the door. GB + G say yes. Find what rots in that — especially the advisory category becoming a hiding place, like hidden-by-policy almost did.*
