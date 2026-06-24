# GB Metalayer Assessment — what the book↔code rail is missing (2026-06-18)
*KM asked: from the metalayer, what are we missing in the workflow / book↔code rail. Grounded in WORKFLOW.md (the rail is mature on book→code AUTHORING) + this session's lived signals. Five gaps, prioritized, each with the gate that would close it. Not a critique of the rail — the edges it doesn't yet cover.*

## What the rail already covers well (so the gaps are real, not noise)
Co-extrusion (book + code + tests at authoring) · 3 editorial rounds + UX board + Tech/Arch board (6 gates) · **Gate 6 Renderability machine-checked** (`review_ready_contract.py`) · ritual/one-truth discipline · `outline_lock_lint` + `roadmap_sealed_guard` (structural, re-runnable). The rail is strong at **authoring-time, book→code, one volume.**

## The five gaps (where the rail thins)

### 1. Living-spec REVERSE drift — code→book — has no BLOCKING gate *(highest leverage)*
The whole thesis is "books are living specs." The rail enforces book→code at authoring. But after a book seals, **the code keeps moving** (platform releases, engine changes) — and nothing *hard-stops* a code change that invalidates a sealed book's claim. The Scout finds Book↔Code drift, but **propose-only, overnight** — a watch, not a gate. **The spec rots silently exactly where the books promise it can't.** Ch1's own thesis ("a copy drifts in silence; a single source drifts out loud") indicts this gap. **Close it:** a reverse-coherence gate — a code change touching a published book's claim opens a *material* obligation (or fails CI) until the book's coherence_pin is re-verified or a next-edition note is filed. Make drift loud at commit, not at the next Scout run.

### 2. The receipt proves a render HAPPENED, not that the CLAIM is TRUE
Gate 6 requires every capability-promise has a render target + a Receipt box. That proves a deterministic render exists — **not that the rendered code does what the prose claims.** "The breath-gate stops unapproved execution" can pass Gate 6 with a receipt and pass "test coverage" with comprehensive tests — without a test that proves *that specific claim*. **Close it:** claim→test traceability — each capability-promise binds to a *named passing test that proves THAT claim* (the /seeit "command + receipt" pattern, generalized to every manuscript claim). Render-honesty → claim-honesty.

### 3. Inheritance is DECLARED but not VERIFIED *(becomes load-bearing now)*
S5's 32 titles inherit from S3 via `signed_inheritance_objects` + the `no_invisible_inheritance` guard — declared in the roadmap, but **I see no rail gate that verifies it.** With the catalog now 93 outlines locked and the series-flow-model about to let volumes flow with fewer human touches, **unverified inheritance is how S3 root-errors propagate silently into 32 children.** **Close it:** an inheritance-verification gate — an S5 volume can't draft until a valid signed inheritance object resolves (parent_policy_id exists, inherited pattern present, delta declared). The `outline_lock_lint` is the template; this is its inheritance sibling.

### 4. Structural completeness ≠ substantive quality — and the flow-model widens this *(the timely one)*
This session proved structural lints (`0 thin`, 93 locked). But "complete" (has promise/beats/keywords) is not "good." The 3 editorial rounds catch substance *during drafting* — but the **series-flow-model you're designing reduces human touchpoints**, and the lints don't measure quality, only completeness. **The risk is precise: automation passes technically-compliant-but-mediocre work, and you — seeing fewer cards — lose the catch.** That is exactly the "quality must not drop" line. **Close it:** a substantive-quality signal that *scales* — surface the Cold Reader / adversarial-board verdict as a structural metric on the batch card, so your reduced touchpoints still carry "is this actually good," not just "is this complete." **This must be built INTO the flow-model, or the flow-model is where quality quietly erodes.**

### 5. The figure-8 isn't closed — no published→rail feedback loop
Book → code → platform → reader. But **reader/market/platform signal doesn't route back** as rail input. `ALIGNMENT_AND_NEXT_EDITION_NOTES` exists as a passive doc, not a trigger. We can't yet learn from what shipped — which /seeit pages engaged, which claims confused readers, what the platform telemetry showed — to sharpen the next volume. **Close it:** post-publish signal (reader/platform/`/seeit` engagement) routes back as next-edition obligations on a cadence. Close the loop the federation thesis implies.

## The metalayer synthesis
The rail is excellent at **make-it-once, correctly, under human witness.** Its blind spots are the **second derivatives**: keeping it true *over time* (1, reverse drift), true *in depth* (2, claim≠render), true *at scale* (3 inheritance, 4 substantive-quality), and true *in a loop* (5 feedback). **#1 and #4 are the urgent pair right now** — #4 because the series-flow-model you're about to design is precisely where reduced human touch meets completeness-not-quality lints; #1 because 93 locked outlines are about to become living specs that the code will start to outrun.

**Recommendation:** fold **#4 (substantive-quality-at-scale) directly into the series-flow-model proposal** (it's the mechanism that protects your "quality must not drop" constraint), and queue **#1 (reverse-coherence gate)** as the next rail-hardening after V3. The other three are real but can follow.

∞Δ∞ The rail builds truth well. What it doesn't yet guarantee is that truth stays true after the build — across time, depth, scale, and the loop back. Those are the missing gates.
