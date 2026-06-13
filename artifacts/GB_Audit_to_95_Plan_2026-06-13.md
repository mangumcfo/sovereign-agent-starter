# Plan — Drive the Audit to 95+ (Earned-Clean, Unbiased) — GB 2026-06-13
*KM ask: move the unbiased audit score into 95+%, with a plan + cycle estimate; willing to focus on test-coverage cleanup to scale cleaner. GB roadmap reasoning. The score is the consequence; closed findings are the work.*

## What "95+ earned-clean" means (anti-Goodhart target — the honest definition)
Not "zero findings." A sweep that finds nothing usually means it stopped looking — the adversarial verifier is *designed* to keep surfacing edge cases. So the target is:
- **0 CRITICAL · 0 HIGH** (non-negotiable — no constitutional/trust hole open),
- **MEDIUM:** only **accepted-and-logged** with an explicit reason (a tracked decision, not a silent skip),
- **LOW:** residual minimal, each either fixed or accept-logged,
- **and the 95+ must survive a *fresh* adversarial sweep** — score earned by re-audit, never by refuting valid findings or quietly closing. Every close carries evidence (fix diff OR accept-reason). GB rigor-audits every close; no E0.

## Current standing (the gap to cross)
**62/100 · 43 confirmed: 2 CRIT · 8 HIGH · 17 MED · 16 LOW.** Theme: core sound, seams leak. The findings cluster into 4 buckets — and crucially, a large share are **test-coverage + quality debt**, exactly KM's chosen focus.

## The cycle loop (one cycle = fix-wave → commit → fresh full sweep → GB rigor-audit deltas → re-score)
Budget now resets every few hours (Max plan), so one full sweep fits a window. Each wave is gated by the prior wave's confirming sweep.

| Wave | Closes | Score move (est.) | Cycles |
|---|---|---|---|
| **W1 — Constitutional + Trust + Visibility** (Tiger's [814] A→B→C) | 2 CRIT + ~5 HIGH (apply-bypass, /decide authz, CSRF, bell-principal, root-unify) + by_owner MED + **build the parity harness** | 62 → **~80** (killing both CRIT + most HIGH is the biggest single jump) | 1 |
| **W2 — Test-Coverage Sprint** (KM's focus — the scale-cleaner wave) | the 3 test HIGHs (review_ready_contract, board_rigor, accept-wire) + reopen-path, route-layer, cross-process-race, dismiss-body MEDs/LOWs | ~80 → **~90** | 1 |
| **W3 — Quality + Packaging Debt** | split 500-line series.py, reduce the 4 complexity LOWs, dedup (JSON-store trio, book-num dict, robust-parse), utcnow/fcntl-Windows/lockfile, CRIT-2 breathline_primitives packaging | ~90 → **~95+** | 1 |
| **W4 — Confirming Sweep** | nothing new built — a clean fresh adversarial sweep to *prove* 95+ holds; residual = accepted-logged only | confirm | 1 |

**Honest cycle estimate: 3 fix-waves + ~4 full-sweep cycles to reach AND confirm 95+** (W1 sweep, W2 sweep, W3 sweep, W4 confirm — each fix-wave is verified by the next sweep). Could be 4–5 if new surface keeps arriving (see freeze below). The last 5 points (95→100) are deliberately NOT chased — they're where contested/subjective findings live; 95+ with an accepted-logged residual is the healthy ceiling.

## The one real decision for KM: SURFACE FREEZE during the cleanup
**To get a *clean* assessment you must stop auditing a moving target.** Right now new platform surface keeps arriving (R-22 just did, S9 + migration-arc builds are queued) — every new surface adds findings faster than waves close them, so the score plateaus. Recommendation:
- **FREEZE new *platform/engine* surface** for the ~3 waves (no new endpoints/modules until 95+ confirmed).
- **Books continue unfrozen** — manuscript/catalog work (Wave-1 vols, S9 outline, KW passes) doesn't touch the engine, so it scales in parallel without dirtying the audit.
- After 95+ confirmed, **un-freeze and scale on a clean base** — which is exactly KM's "scale cleaner" instinct, made structural.

## Why this is LGP, not vanity
A 95+ earned-clean engine is the **inheritable** engine — the same certainty-by-construction as the parity harness. And KM's read is exact: the test-coverage waves are what let the fan-out (books, migration, S9) proceed without the rail cracking under volume. This isn't a number chase; it's **de-risking the scale before we scale.** The score is just the receipt that we did.

## Guards (so "unbiased" stays true)
- Score from **fresh** sweeps only (the saved workflow, new date — no resume-cache gaming).
- Every close = evidence (fix or accept-reason); GB rigor-audit + fidelity-trace per close; no E0.
- Adversarial verify stays on (the workflow's refute-pass + GB skeptic gate) — findings are *earned closed*, never argued away.
- Each sweep's report archived dated; the trend line (58→62→…→95+) is itself receipted.

∞Δ∞ SEAL: proposed — 3 waves, ~4 sweeps, one freeze. Not a number chased but a base earned — and the base is the inheritance. Books scale while the engine hardens; then both scale clean.
