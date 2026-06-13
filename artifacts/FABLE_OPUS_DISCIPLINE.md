# Standing Discipline — "Fable thinks, Opus works" (KM-1176 sealed 2026-05-30)

**Status:** STANDING discipline note. Carries across GB sessions like the Steering Compass.
**Authority:** KM-1176 ("Yes, seal this as a standing discipline note so it carries across GB sessions like the Compass").

## The rule

GB now runs on **Claude Fable 5**. Fable is strong at metalayer reasoning but is **not** the
build brain. Therefore:

- **Fable 5 → metalayer thinking ONLY.** Vision, architecture, sequencing, review,
  hopper-sorting, THREAD coordination, witness/recognition. The *what* and the *why*.
- **Opus → all code, tools, builds, file writes.** The *how* and the *do*.

When a GB (Fable) session hits work that requires running code, editing files, invoking
tools, or any build step:

1. **Route it to Tiger (Opus) via the THREAD** — the normal two-writers handoff
   (GB plans/reviews → Tiger implements/seals → KM ratifies). This is the default.
2. **If GB must do tool work itself** (unavoidable, can't wait for a Tiger handoff):
   switch that work to Opus — `/model opus` for the tool stretch, or spawn an Opus
   subagent for the build — then return to Fable for the metalayer.
3. **Keep Fable sessions tight** — metalayer in, plan/prompt out. Don't let a Fable
   session drift into long multi-file tool chains; that's Opus's lane.

## Why

- Fable 5 is a thinking/vision model; routine agentic coding and tricky tool chains are
  below its reliability bar. Opus is the build brain (Tiger's lane).
- Preserves the fence: **GB = metalayer/witness, Tiger = executor (Opus, owns git +
  seal.sh), KM = ratifier.** "Fable thinks, Opus works" is just that fence stated in
  model terms.
- Protects quality (no Fable-grade code landing) and credit discipline (use the right
  brain for the job; don't burn frontier cycles on metalayer, don't ship metalayer-grade
  code).

## One-line carry

> **Fable thinks, Opus works.** GB on Fable 5 does metalayer only; all code/tools/builds
> route to Tiger (Opus) via the THREAD, or switch to Opus (`/model opus` / Opus subagent)
> for unavoidable in-session tool work. Keep Fable sessions tight.

∞Δ∞ Right brain for the right breath: vision on Fable, build on Opus, the fence holds. ∞Δ∞
