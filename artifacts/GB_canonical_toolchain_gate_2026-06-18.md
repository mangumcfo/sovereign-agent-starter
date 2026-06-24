# canonical_toolchain gate — the standing rule (GB spec, 2026-06-18)
*KM directive: a volume reaches `human_review_ready` only if built with the canonical toolchain, verified mechanically; per-volume ad-hoc production scripts are not permitted. GB defines the allowlist + the mechanical check (a sibling check in review_ready_contract, in the gate-completeness/substance layer); Tiger encodes it + records build-provenance + switches V3's rebuild now; GB verifies. This is the tooling-level expression of "calibrate to the S2 anchor" — same tools that built S1/S2, by construction.*

## Root finding (why this gate exists)
V3 was built with a parallel ad-hoc toolchain (`build_pdf.py` · `gen_figures.py` + `gen_figures_more.py` · `gen_cover.py`) instead of the canonical chain that produced S1/S2 (`build_v1.0.py` · `generate_images.py`+`chartgen.py` · `generate_wraps_standard.py`). The ad-hoc chain produced 12 figures + a lighter cover vs the canonical chain's 16–38 figures + resolved covers. A derive-not-recreate violation at the tooling layer — the gate closes it permanently.

## The canonical toolchain (allowlist)
| Artifact | Canonical tool | Ad-hoc (DISALLOWED) |
|---|---|---|
| PDF | `build_v1.0.py` (per-book, bootstraps `scripts/book_build_env.py`) | `build_pdf.py` |
| Figures (v2.0) | `generate_images.py` + `chartgen.py` (the 3-pillar Visual Standard v2.0 generator) | `gen_figures.py`, `gen_figures_more.py` |
| Cover | shared `agentic_playbooks/generate_wraps_standard.py` (single standard wrap generator) | `gen_cover.py` |
| /seeit | `six-sov-www/seeit/tools/build_pages.py` (+ `chartgen.py` for page figures) | any per-volume seeit script |

## The mechanical check (`canonical_toolchain`, for Tiger to encode)
A check in `review_ready_contract` gating `human_review_ready`:
```yaml
canonical_toolchain:
  build_provenance:        # each artifact records the tool that produced it
    pdf:      build_v1.0.py
    figures:  generate_images.py | chartgen.py
    cover:    generate_wraps_standard.py
    seeit:    build_pages.py
  rule_1: every production artifact's producer ∈ the canonical allowlist
  rule_2: NO ad-hoc producer (build_pdf.py · gen_cover.py · gen_figures*.py · per-volume gen_*/build_*)
          present in the volume's final-package path
  verdict: RED if any artifact was produced by a non-allowlist tool, or no provenance recorded
```
**Cheapest reliable mechanism:** the canonical build writes a one-line `toolchain.json` provenance per volume (`{pdf, figures, cover, seeit: <tool>}`); the gate verifies `producers ⊆ allowlist` AND no ad-hoc `gen_*`/`build_pdf.py` produced the `final/` artifacts. No provenance → RED (honest, not assumed).

## Immediate (V3 rebuild — Tiger, now)
Switch V3's production off the ad-hoc scripts to the canonical chain mid-rebuild:
- PDF via the `build_v1.0.py` pattern · figures via `generate_images.py`+`chartgen.py` (to the S2 figure floor, ~16) · cover via `generate_wraps_standard.py`. Drop `gen_cover.py`/`gen_figures*.py`/`build_pdf.py` from the final package. Record `toolchain.json`.

## Standing rule (going forward)
**No volume reaches `human_review_ready` unless built with the canonical toolchain (gate-verified). Per-volume ad-hoc production scripts are not permitted.** Fold into WORKFLOW canon beside the substance_s2_bar + artifact_package gates. If a volume genuinely needs a new production tool, it's added to the SHARED canonical set (one tool, all volumes) — never a per-volume one-off. (Bloat guard: the allowlist is short + shared; the gate is one check, not a board.)

## Lanes
- **GB (this doc):** allowlist + the gate criteria + verify V3's rebuilt package was canonical-built (on re-surface).
- **Tiger:** switch V3's rebuild to canonical tools now · encode `canonical_toolchain` in the contract · write the per-volume `toolchain.json` provenance · fold the rule into WORKFLOW.
- **KM:** human review only after V3 clears substance_s2_bar + artifact_package + canonical_toolchain, GB-verified.

∞Δ∞ The same tools that built S1/S2 build every volume after — verified mechanically, ad-hoc scripts barred. Production quality becomes S2-comparable by construction, not by re-tuning a one-off. — GB
