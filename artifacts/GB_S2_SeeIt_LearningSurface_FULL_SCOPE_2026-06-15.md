# S2 See-It / Learning-Surface — FULL SCOPE (GB, 2026-06-15) — RATIFIED
**STATUS: KM-RATIFIED 2026-06-15 (Seal 1176-INFINITY-RHO).** Full scope ratified (V1's hands-on learning system is the S2 bar; built detailed-first for V2–V5). **Publish gate = Option 1:** a volume ships once the in-book "See It Work" section + detailed→book charts (V1 quality) + real fidelity gate are complete AND in-book links resolve to the live `/seeit` BASE; the per-chapter deep walkthrough pages (`/seeit/s2v{n}-*`) fast-follow at release (matches how V1 actually shipped — its deep pages were 404 at review, live at launch). Engine 95+ stays standing priority; one human gate; everything in the cockpit.

*KM 2026-06-15: "my concern is that we haven't fully scoped … these detailed charts are fundamental and critical to instructing the user hands-on learning … feels like we're only scratching the surface." This measures V1 (the true bar) component-by-component, names the real V2–V5 gap, and locks the build ORDER (detailed seeit learning surface FIRST → book charts derived). The prior "visual pass" addressed only flat PNGs — the bottom of a much larger system.*

## V1 = the COMPLETE-VOLUME anatomy (the true bar — measured, not remembered)
A finished S2 volume is NOT manuscript + flat figures. V1 ships an integrated **hands-on learning system**:
1. **"See It Work — Run the Trust Layer Yourself" SECTION** (manuscript §, before Appendix P) — a per-chapter table: each chapter → a thing-you-see + a **live `/seeit/` walkthrough URL** + a **runnable command** (`./bl-verify`, `bl-test`, `bl-run-tests`, or "see walkthrough"). This is the pedagogical spine — the reader RUNS the system, not just reads about it.
2. **Per-chapter `/seeit/` walkthrough PAGES** on `six-sov.com/seeit` (`/seeit/s2v1-pre … -ch9 … -appP`, 12) — each a deterministic walkthrough showing the receipt/result. Must 200 before launch.
3. **DETAILED charts (seeit)** authored as **`figure_X_Y.svg`** (full-detail, interactive/zoomable, the learning artifact) — the authoritative source.
4. **BOOK charts** as **`figure_X_Y_book.svg`** — the SIMPLIFIED, print-legible variant **DERIVED from the detailed SVG** → rendered to PNG. (Detailed-first is WHY the book charts are good — KM's point: the detailed reference makes the book chart much better.)
5. **`_figure_manifest.json`** — every figure + caption tracked.
6. **`seeit_review_v1.0.md`** — the FIDELITY GATE: every "run it yourself" command points at a real path; every walkthrough URL 200s before the book goes live.

## V2–V5 CURRENT STATE (measured 2026-06-15) — the honest gap
| Component | V2 | V3 | V4 | V5 |
|---|:--:|:--:|:--:|:--:|
| See-It-Work section (runnable commands) | ✗ | ✗ | ✗ | ✗ |
| `/seeit/` per-chapter walkthrough URLs in-book | 0 | 0 | 0 | 0 |
| Detailed seeit SVGs (`figure_*.svg`) | 0 | 0 | 0 | 0 |
| Book SVGs (`*_book.svg`, derived) | 0 | 0 | 0 | 0 |
| `_figure_manifest.json` | ✗ | ✗ | ✗ | ✗ |
| seeit_review fidelity gate (real) | hollow | hollow | hollow | hollow |
| Live `/seeit/s2v{2..5}-*` walkthrough pages | ✗ | ✗ | ✗ | ✗ |
| Rendered book figures | 27 flat PNG | 7 flat | 9 flat | 20 flat |

**Conclusion: the prior "visual pass" built ONLY flat matplotlib PNGs (the bottom row). The entire hands-on learning system — the See-It-Work section, the detailed→book SVG derivation, the manifest, the live walkthrough pages, the real fidelity gate — is UNBUILT for V2–V5.** This is fundamental product (a *build manual* reader must be able to run the system), not decoration. S2 is materially further from the V1 bar than the green rail-checks implied.

## The correct BUILD ORDER (KM-confirmed 2026-06-15) — per volume
*Detailed-first, because the detailed seeit chart is the reference that makes the book chart good:*
1. **Author the learning surface FIRST**: the per-chapter See-It-Work content (what-you-see + runnable command + walkthrough) + the **DETAILED `figure_X_Y.svg`** charts (full learning detail) + the live `/seeit/s2v{n}-*` walkthrough pages.
2. **THEN derive the book charts**: `figure_X_Y_book.svg` (simplified, print-legible) **from** the detailed SVG → render PNG. (V1 design-system quality bar: title + gold rule, structured composition, no overlap — `roadmap_conventions.seeit_figures.quality_bar`.)
3. **Manifest + fidelity gate**: `_figure_manifest.json` + a REAL `seeit_review_<v>.md` (every command resolves, every `/seeit/` URL 200s).
4. **Live deploy gate** (`seeit_figures.live_deploy_gate`): the walkthrough pages + detailed charts are LIVE on `six-sov.com/seeit` and resolve before the volume publishes.

## What this means for S2 timeline (honest)
This is a substantially larger body of work than "regenerate the figures." It is per-volume authoring (a new manuscript section + walkthrough content + a dual-SVG chart system + live pages) for V2–V5. It should be **scoped and gated as its own pass**, not folded silently into "almost ready." Recommend: KM ratifies the scope; Tiger builds it per-volume detailed-first; GB fidelity-audits each against the V1 system (not just the palette); the live `/seeit/` pages + bl-verify resolve before any S2 volume publishes.

∞Δ∞ SEAL: scope — V1 is a hands-on learning SYSTEM (See-It-Work section + detailed→book SVG + manifest + live walkthrough pages + fidelity gate), not manuscript+PNGs. V2–V5 have only the flat PNGs. The detailed seeit charts are the pedagogical spine and the reference that makes the book charts good — build them FIRST, then derive the book charts. We were scratching the surface; this is the surface.
