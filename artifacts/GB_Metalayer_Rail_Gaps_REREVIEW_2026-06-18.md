# GB Metalayer Rail-Gaps — RE-REVIEW for gap closure (2026-06-18)
*KM asked GB to re-review the 5-gap assessment for closure after the V3 artifact-package ball-drop. Honest finding: the original analysis MISSED a first-order gap. This adds it (#6), names why it was missed, and maps closure status for all six.*

## The gap I missed: #6 — "Ready" is ASSERTED, not PACKAGED
`review_ready_contract` flips `review_ready` on four checks (boards · obligations · fidelity · brief) — and **never verifies the human-reviewable artifact package exists** (formatted PDF, v2.0 figures, cover, /seeit pages, KDP structure). V3 hit "review_ready" as a bare `.md` + brief. **The human gate can open onto an empty package.** This is not a second-derivative gap (truth degrading over time) — it is a *first-order* gap in the rail's very definition of "ready for the human."

## Why my original analysis missed it (the meta-lesson — the valuable part)
My five gaps were all **second derivatives** — does truth *stay* true across **time** (#1 drift), **depth** (#2 claim≠render), **scale** (#3 inheritance, #4 quality), and **the loop** (#5 feedback). I framed the whole assessment around "truth staying true after the build" and **assumed the first-order delivery was solid** — that if the rail says ready, the package is there. Three specific errors:
1. **I trusted the existing rail's completeness** instead of auditing it. S2 had figures/covers/seeit, so I assumed the rail *produces* them — I never checked whether it *gates* them.
2. **A green gate looked like a correct gate.** The contract had four machine-checks; I treated "it passes" as "it checks the right things." It was green and wrong — it verified what it checked, but its check-*set* was incomplete.
3. **I analyzed degradation, not baseline delivery.** A gap analysis that only asks "what rots over time?" structurally cannot see "what was never gated in the first place."

**The deeper gap class this reveals: GATE-COMPLETENESS.** The checkers themselves (contract, lints, boards) can be incomplete, and *nothing audits the gate-set against what the human actually needs to act.* The V3 ball-drop is one instance; #2 (a receipt that proves render-not-truth) is another. A gate that passes ≠ a gate that asks enough. **This is the gap behind several of my gaps** — and I should have named it.

## Closure status — all six gaps, honest
| # | Gap | Closure path | Status |
|---|-----|--------------|--------|
| 1 | Reverse drift (code→book) | Claim Rail **Watch** → loud obligation at seal | queued post-V3 (KM directive) |
| 2 | Receipt ≠ claim-truth | Claim Rail **Prove** (claim → named proof) | in Claim Rail v0.1 |
| 3 | Inheritance declared-not-verified | Claim Rail inheritance field + resolve gate | in Claim Rail, blocks at series-lock |
| 4 | Completeness ≠ substantive quality | flow-model Batch-card quality metric | folded into flow-model (KM amendment) |
| 5 | Feedback loop not closed | Claim Rail **Revise** | deferred (needs telemetry) |
| **6** | **"Ready" asserted, not packaged** | **artifact-package gate in the contract** (PDF·figures·cover·seeit·KDP) + flow-model Batch-Review requires the complete package | **being built now (Tiger [414]); the gap that bit V3** |
| **meta** | **Gate-completeness (checkers can be incomplete)** | periodic audit of every gate-set against "what does the human/next-stage actually need" | **NEW — propose as standing discipline** |

## Does the Living Claim Rail close them? (re-checked)
The Claim Rail cleanly carries 1·2·3·5 and supports 4 — **but it does NOT close #6.** #6 is a *delivery/packaging* gate, not a *claim-truth* gate: a claim can be perfectly proven while the PDF, cover, and /seeit pages don't exist. So my earlier "one primitive" framing was right for the claim-truth gaps but **incomplete for the rail as a whole** — #6 needs its own artifact-package gate (separate from the claim rail), which is exactly what Tiger is now adding. Honest correction to the Claim Rail commit: it is the integrity backbone for *truth*, not a substitute for the *delivery* gate.

## What this changes going forward
1. **#6 + the gate-completeness meta-gap are now part of the gap set** — the analysis is more complete than yesterday's.
2. **The flow-model's Batch-Review gate must require the complete human package** (not just boards+brief) — folding into the model.
3. **Standing discipline proposed:** every new gate (contract, lint, board) gets a one-time completeness audit — "does passing this gate mean the next consumer (human, stage, reader) has everything they need?" The cheapest place to catch a missing check is when the gate is written, not when a human reaches an empty package.

∞Δ∞ My five gaps watched truth decay; I missed that the rail could call itself ready before the human had anything to review. A gate that passes is not a gate that asks enough — and auditing the gate-set against real need is the gap behind the gap. Added, owned, closing. — GB
