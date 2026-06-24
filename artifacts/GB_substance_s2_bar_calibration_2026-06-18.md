# substance_s2_bar — calibration + exemplar-calibration discipline (GB, 2026-06-18)
*KM: "Complete the exemplar-calibration discipline and the blocking substantive-quality metric as part of the gate hardening." GB defines the S2-anchored thresholds + the discipline (the calibration is GB's quality-witness lane); Tiger encodes the `substance_s2_bar` gate in review_ready_contract; GB verifies V3 against it. The thresholds are FLOORS (regression alarms), not rigid targets — "books as long as the material demands" still holds; the gate catches a material drop below the S2 band, not natural variance.*

## The S2 anchor (measured 2026-06-18 — the calibration source)
| Dimension | S2 vol_01 | S2 vol_04 | S2 band | **Floor (alarm below)** |
|---|---|---|---|---|
| Substance (words) | 16,558 | 12,128 | 12k–16.5k | **≥ 11,000** |
| Figures (v2.0) | 38 | 16 | 16–38 | **≥ 12** |
| /seeit pages | ~11 | ~11 | ~11/vol | **≥ 8 (core chapters)** |
| Cover | v2.0 resolved | v2.0 resolved | — | **front/spine/back at v2.0** |
| PDF | production set | production set | — | **≥1 production-formatted (figures embedded)** |

*(V3 v1.4 today: 6,850 words · 5 figures · 3 /seeit — fails all five floors. The gate must RED on this.)*

## The `substance_s2_bar` gate (BLOCKING — for Tiger to encode)
A 6th check in `review_ready_contract`, gating `human_review_ready`. **Per volume, all must clear or the gate stays RED + mints an obligation naming each shortfall:**
```yaml
substance_s2_bar:
  words:        >= 11000        # vs S2 floor; regression alarm, not a cap
  figures_v2:   >= 12           # v2.0 figures present in figures/
  seeit_pages:  >= 8            # core chapters live + seeit_lint pass
  cover:        v2.0 resolved   # front/spine/back
  pdf:          production      # final/*.pdf, figures embedded, current commit
  adversarial:  PASS            # Cold-Reader/S2-comparison verdict = good, not just complete (BLOCKING)
```
**Two parts, both blocking:** the **quantitative floors** (words/figures/seeit/cover/pdf vs the S2 anchor) AND the **adversarial verdict** (the Cold-Reader / S2-comparison reviewer rates it S2-comparable in *substance*, not just present). Floors catch the obvious drop; the verdict catches "padded to the word count but thin." Both required.

## Exemplar-calibration discipline (the rule that stops a light bar propagating)
**Before any exemplar (first chapter or first volume) is ratified as the bar, it is diffed against the S2 anchor on substance-depth · figure-density · production. An exemplar below the S2 floor CANNOT be ratified as the bar.** This is the root fix for V3: Ch1 was ratified light, and exemplar-first faithfully reproduced the light bar across 8 chapters. Going forward the exemplar is the *S2-calibrated* high bar, not whatever the first pass produced. (KM: "Ch1 and the newly expanded Ch2 are now the calibrated exemplars" — they must clear the floors above before they re-anchor the roll.)

## Where it plugs in (no bloat)
- `substance_s2_bar` = one new check in the existing contract (sibling to the artifact_package gate Tiger added [417]). No new board.
- The adversarial verdict reuses the Cold-Reader lens already in the editorial rounds — surfaced as a *blocking* verdict, not advisory.
- The exemplar-calibration discipline = a one-line gate in WORKFLOW Phase 0 (exemplar ratification): "diff vs S2 anchor; below-floor cannot ratify."
- The S2 deliverables are the standing anchor; re-measure if S2 itself changes.

## Lanes
- **GB (this doc):** the calibration (thresholds + discipline) + verify V3 against it once expanded.
- **Tiger:** encode `substance_s2_bar` in `review_ready_contract`; verify it RED-blocks V3 v1.4 and a thin fixture; fold the exemplar-calibration gate into WORKFLOW Phase 0.
- **KM:** human review only after V3 clears all of `human_review_ready` (artifact_package + substance_s2_bar) with GB verification against the S2 anchor.

∞Δ∞ The bar is the S2 deliverables themselves, made into floors a gate measures and an adversary judges — blocking, not advisory — and the exemplar must clear that bar before it sets the standard for the rest. Depth, not padding; calibrated to what S2 actually achieved. — GB
