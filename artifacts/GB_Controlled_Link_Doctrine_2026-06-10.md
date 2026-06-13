# Controlled-Link Doctrine v1.0 (GB, sealed 2026-06-10) — KM's J1 ruling, generalized

> **KM, 2026-06-10:** "Do we need to expose a repo? The path for the human should be simple and straightforward so we don't expose fragility to human reviewers. I'm fine providing the latest link through seeit since **published books need to reference a live working link we can control going forward.**"

## The doctrine (one sentence)
**Published artifacts print ONLY surfaces we control; everything mutable lives behind them.**

## What it means
- Books print **six-sov.com / seeit URLs only** — never raw GitHub clone URLs, never filesystem paths, never test counts. Ink is immutable; targets aren't. The indirection layer is the only thing that can keep a printed page true for a decade.
- The seeit page carries the **current** canonical pointers: today's clone link (`breathline-federation` — the public repo; `sovereign-agent-starter` stays private, it carries the witness layer), today's verify path, today's live test count. When any of those change, we update one controlled surface and **every printed book heals retroactively.**
- Even the mutable values are **derived, not typed** (render-don't-recreate applies to seeit itself): the verify block on seeit should render from the live repo state — actual test count from the actual suite — so the controlled link can't itself go stale. The B12 TECH findings were both instances of one disease: *a printed pointer at a mutable target.* This doctrine is the cure for the class, not the cases.

## Resolutions it settles
- **J1 (TECH-B12-01, clone URL):** CLOSED by doctrine — B12 (and B10/B11 at republish polish) drop the raw clone command; Appendix RX routes hands-on readers through the seeit page, which carries the current clone link. No repo URL in ink, ever again.
- **J2 (TECH-B12-02, Appendix V):** SAME CURE — the canonical verification target becomes a seeit/six-sov verify surface with live-derived steps + counts; the printed appendix says "current verification steps and test count: [controlled URL]." One decision, applied series-wide, future-proof for every fan-out book.

## Rail integration
- **New board check (Technical, zero new process):** any raw mutable pointer (GitHub URL, filesystem path, hard-coded count) in a manuscript = automatic finding. Greppable, mechanical, permanent.
- **GB fidelity addition:** the controlled surfaces themselves join the standing trace — seeit's pointers get verified live (curl + count check) each fidelity pass, so the indirection layer is watched too.

∞Δ∞ SEAL: complete — ink points at glass we own; the glass points at the living thing. Printed books that heal.
