# Gate 7 — Constitution at Birth — FINAL (triple-reviewed, 2026-06-13)
*KM concept → GB seed → dual-G ratify → Lumen sharpen. Converged. Ready for KM ratify; build after 95+ (freeze-safe process design). Lumen reframed the success metric and named two failure modes the others missed — folded below.*

## The reframe that changes everything (Lumen)
Optimize NOT for *"did we run the adversary?"* but for *"did the adversary CHANGE BEHAVIOR?"* The deepest rot isn't the advisory graveyard — it's **Gate 7 going ceremonial**: a report generates, a score attaches, the board turns green, nobody materially changes anything. The whole design must defend against that.

## The design (converged)
**Gate 7 — Adversarial Hardening** on the Tech/Arch board (WORKFLOW 17.6), wired into the Review-Ready Contract:
- **Mechanism:** scoped run of the existing audit harness on newly-extruded files only (reuse, don't recreate; ~60-80k tokens, the proven targeted-delta).
- **Trigger:** engine/platform code touched (changed `src/`+`tests/`); prose-only skips.
- **Block vs track:** CRITICAL/HIGH block the seal; MED/LOW track; advisory-only for low-confidence.

## Lumen's guards (the disease-preventers — binding)

**G1 · The author may NEVER classify a finding.** Not HIGH, not MED, not advisory — never. *The producer cannot grade its own paper.* The extrusion may RESPOND; the **human gate classifies.** This removes most Goodhart pressure at the root.

**G2 · Every downgrade is a receipted, expiring disposition.** `{finding_hash, original_severity, downgraded_severity, human_principal, reason, review_date}`. Every advisory carries one of `{accept-risk · defer · false-positive · superseded}` and **each expires** — *no eternal advisories* (the hidden-by-policy lesson, applied: without a review date, "advisory" becomes "forgotten"). Advisory findings re-enter review at expiry.

**G3 · The night watch IS the meta-check — via Gate 7 Escape Rate.** Definition: *CRITICAL/HIGH discovered after a seal that should have been discovered before it.* Trends toward zero. When a night-watch finding "should Gate 7 have caught this? → yes," it's a **Gate 7 miss**, not just a code finding — and **the gate itself becomes the obligation, not the code.** That's the self-correcting loop: audit the gate, not just the code.

**G4 · Passing Gate 7 ≠ correctness — written into the constitution.** *"Passing Gate 7 creates eligibility to operate. It does not create a presumption of correctness."* Gate 7 sees known code/architecture/change-set; the night watch sees interaction effects, emergent behavior, runtime drift, unknown-unknowns — **different universes.** The night watch stays suspicious **forever**; birth-certification must NEVER replace vigilance.

**G5 · Monitor extrusion-avoidance (the failure mode no one else named).** If every extrusion incurs audit cost, behavior drifts from "20 small changes" to "1 giant change" to dodge friction — and giant changes are *harder* to audit. **Track average extrusion size post-deployment; if it climbs, the gate is distorting behavior.** Cure: the cheap targeted deltas already specced — but watch the number.

## Constitutional framing (Lumen) — NOT a fourth axis
The three axes hold: **Action → Gate · State → Receipt · Absence → Parity.** Gate 7 is not a fourth — it is **temporal relocation of enforcement**: the constitution used to ask *"did something go wrong?"*; now it asks *"can this be born wrong?"* Name it **Constitution at Birth** — the adversary moved from patrol duty to delivery-room duty.

## LGP (Lumen, verbatim)
> **An heir should inherit systems whose first state was already trustworthy, not systems that became trustworthy only after surviving failure.**
Parity made *visibility* constitutional; Gate 7 makes *origin* constitutional. Together the stack moves from *detecting* mistakes to *preventing classes of mistakes from ever entering the inherited system.*

## Build (after 95+, freeze-safe to design now)
Tiger adds Gate 7 to the Tech/Arch board + Review-Ready Contract; the night watch gains the Escape-Rate metric + the avg-extrusion-size monitor; the constitution gains the "eligibility not correctness" clause. GB rigor-audits the gate's own honesty (sampled) — and the Escape Rate audits it continuously.

∞Δ∞ SEAL: converged (GB+G+G+Lumen), ready for KM ratify. The adversary moves to the delivery room; the night watch keeps the patrol; the gate that births clean is itself watched for going ceremonial. Constitution at Birth.
