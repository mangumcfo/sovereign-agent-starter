# S2 /seeit Full Build-Out — pre-review spec (GB-drafted, Atrium-card-ready) — 2026-06-16
*KM directive (Option A): fully build out the S2 /seeit walkthrough pages to v2.0 standard as PRE-REVIEW work, then conduct the formal S2 final review. Coordination routes through Atrium; GB specs + verifies, Tiger executes, KM disposes via cockpit cards. Scout stays the standing overnight track.*

## Why (the gap, measured + CORRECTED 2026-06-16)
The Option-1 publish gate (in-book links → live /seeit BASE) is met. KM elects the HIGHER bar: every walkthrough page at v2.0 standard before review.
**GB correction:** my earlier "V3 laggard / s2v3-ch1 404" was a PROBE-NAMING ERROR — V3 uses section anchors (s1/s2a/s2b/s3/s4), not ch1. Full sweep: **all 43 in-book-referenced /seeit URLs resolve 200** (V2 13/13 · V3 6/6 · V4 13/13 · V5 11/11). So **COMPLETENESS is DONE** — every page the books link to is live.
**The real gap is CONTENT QUALITY, not completeness.** Spot-check of the live pages: they carry the walkthrough *narrative* ("Run it yourself", "The command", "the receipt") BUT are NOT at full v2.0 standard — **0 inlined SVG detailed charts** and **0 `<pre>`/`<code>` runnable-command blocks** (the command is in prose, not copy-pasteable).

## Scope — UPLIFT the 43 live pages to full v2.0 standard (not build-missing)
Per page, bring narrative-walkthrough → full v2.0:
1. **Inline the v2.0 detailed SVG chart** (the 3-pillar `figure_X_Y.svg`) relevant to that chapter/section — the page should *show* the detail, not just describe it.
2. **Proper runnable command block** — the "run it yourself" command in a real `<pre>/<code>` block (copy-pasteable), not prose.
3. **Deterministic receipt/result shown** — what the reader sees when they run it (the actual receipt/output), matching V1's seeit quality.
4. **Fidelity** (V1 seeit_review discipline): every command points at a real path; keep all 43 URLs 200 (already met).
*Completeness is done; this is a quality pass over the 43 existing pages.*

## Sequencing
1. Tiger: per-volume completeness audit (V3 first) → build missing/stub pages to v2.0 standard → deploy.
2. **GB verify (the gate to review):** every `s2v{2..5}-ch{m}` URL → 200 (full sweep, not spot); a content spot-check that pages are real walkthroughs at v2.0 bar (not stubs); commands resolve.
3. **Then** the formal S2 final review pass (the 4 GB-sealed Review Briefs V2/V3/V4/V5, already done) → KM accept per volume → dispatch (deterministic re-render v1.4 → KDP).

## Verify-bar (GB, reproducible)
- A URL sweep over every S2 deep page returns all 200 (no 404s); GB re-runs it.
- Sampled page content is a v2.0-standard walkthrough (command + receipt + detailed chart), not a stub.
- Suite stays 279 green; the books' in-book /seeit links still resolve.

## Notes
- The 4 Review Briefs (V2/V3/V4/V5) are already GB-sealed; the final review is gated only on this build-out completing + GB URL/quality verification.
- Scout, engine, and the Claim Packet are unaffected (separate, closed tracks).
- One human gate; everything in the cockpit; GB verifies before "ready."

∞Δ∞ SEAL: complete the /seeit walkthrough surface to V1/v2.0 quality across all S2 volumes (V3 first, consistent deploy, every URL 200, real walkthroughs not stubs), GB-verify it, then the formal S2 final review → KDP. Pre-review build-out: make the reader's "see it work" promise fully live before the book reaches a reader.
