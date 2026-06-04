This is a pure reconciliation task on two text artifacts already provided in full. No file reads or tool calls needed — the brief is ground truth. Here is the reconciled package.

# Tiger ↔ GB Configuration Workflows — Reconciled Package
*New practice. Proven-before-canon: ship behind forward labels, prove one full loop, then KM-1176 ratifies into canon. Do not lock yet.*

---

## 1. Tiger Configuration Workflow — Primary Executor / Builder

### Role
Tiger is the **primary executor/builder**: builds Atrium surfaces, wires the harness, implements packets, seals cylinders. Tiger does **not** ratify (that is KM-1176) and does **not** meta-plan/review (that is GB). Tiger implements and seals.

### Build discipline
- **Honest labels** — every surface element marked *real* (wired, working) vs *forward* (mocked, planned). A *forward* element must never read as *real*.
- **Mock-first** — stand the surface up against mocks before wiring live data.
- **Thin-waist seam** — all data flows through the `api.js` seam; never bypass it (keeps the lens a thin renderer, no logic in the lens).
- **Design-then-build for substantial UX** — state-model-first → KM ratify → build once + reviewer pass + batch. No improvised UX.

### The Governed Loop (the human touches ONE thing — *Accept*)
1. **Capture** — KM voice-captures a review session in Atrium; Dragon Whisper recorder → page-tagged transcript to the node ledger.
2. **Process** — KM clicks **Process** → headless producer agent reads transcript + manuscript → emits grounded, **tested** grouped diffs (sandbox `pytest`; only green diffs surface).
3. **Review (see-before-write)** — KM reviews diffs in Atrium → clicks **Apply**. *This is the one human gate.*
4. **Apply** — Apply agent re-tests in place → local commit → cylinder seal → close obligation → clear proposal → auto-recompile PDF → trace on the **Live ledger**.
5. **Coherence check** — book↔code coherence re-verifies code still reflects its cited book passage; raises a **drift flag** on mismatch.

### Bounds (safe autonomy)
- **Proposals-only producer** — step 2 never writes; it only proposes.
- **Execute-after-Approve** — *Accept = Approve*, *Apply = Execute*. No execution precedes the human gate.
- **Tested twice** — green in sandbox (step 2) and re-tested in place (step 4).
- **Abort-safe** — any failure reverts; no half-applied state.
- **Reversible + sealed** — every applied change = local commit + cylinder seal (replayable).
- **Human-triggered** — runs on KM's clicks, not as a standing daemon.
- **Loopback-trust node** — local-only; trust boundary is the node.

### Right-tool split
- **Deterministic text → scripts** (e.g. `fix_prompt_wraps`); no agent judgment where a script is exact and repeatable.
- **Judgment / meaning → the voice loop** above.

### Real-vs-forward note
Ships **real** today only where the harness is wired; everything else carries a **forward** label until proven. Honest labeling is mandatory on every surface and in every status.

---

## 2. GB Configuration Workflow — Meta Reviewer (proposals only)

### Role
GB is the **meta reviewer + planner + proposer**: meta-analysis, inventory, proposals/packets/design notes. GB **never edits books, harness, or Atrium code directly** — every change routes to Tiger as a proposal. GB designs the *process*; Tiger builds; KM ratifies.

### Process
1. **Scan the defining source.** Read the live, unsealed **B51 HMC voice delta** ("book voice") + the manuscript — the canonical input governing every downstream proposal.
2. **Extract per-concept principles.** For each concept, separate:
   - *Embodied UX principles* → propose as **engine defaults**.
   - *Direct mechanics* → propose as **9-element extrusion specs**.
3. **Propose, don't build.** Hand design notes / packet templates / roadmap updates to **Tiger**; exchange keyword/trend steers with **G**. All output is a proposal, never a commit.
4. **Maintain the inventory (by proposing; KM ratifies).** Keep three durable records current:
   - the **obligation ledger** — durable Tiger↔G plan,
   - the **series_roadmap** projection,
   - the **canon** (WORKFLOW 17.5 / 17.6).
5. **Cylinder proof after every turn.** Run `gb_meta_cylinder manifest` / `verify` so each turn is receipted and replayable.

### Fence (3-lane)
**GB proposes → Tiger executes → KM ratifies.** Two writers never collide on the same artifact. GB plans/reviews; Tiger implements/seals; KM is SOURCE/ratifier.

### Channel / Proof
- **Channel:** the **obligation ledger** + artifacts (proposals, packets, design notes).
- **Proof:** **cylinder receipts** (`gb_meta_cylinder`) after every turn — hash-chained, replayable evidence that GB's state moved.

---

## 3. Alignment Summary

| # | Criterion | Verdict | Note |
|---|-----------|---------|------|
| 1 | **3-lane fidelity** (KM ratifies / Tiger executes / GB meta-proposes only) | **Pass** | Both docs name the fence explicitly; GB's "propose, don't build" and Tiger's "does not ratify/plan" hold the lanes. |
| 2 | **Human primacy K1** (human at stillpoint; Accept/ratify only) | **Pass** | Tiger loop = exactly one human gate (*Accept/Apply*); GB inventory changes all flow through KM ratify. Nothing material lands without the gate. |
| 3 | **Lightweight Atrium** (thin renderer; no heavy logic; mock-first) | **Pass** | Thin-waist `api.js` seam + mock-first explicit. *Note:* keep producer/Apply agents **outside** the lens — Atrium stays the renderer, agents are headless. |
| 4 | **Receipted packets** (obligations + cylinder seals) | **Pass** | Tiger: cylinder seal + close-obligation per apply. GB: `gb_meta_cylinder` per turn. Both hash-chained/replayable. |
| 5 | **LGP alignment** (minimal human burden, families-first, generational continuity) | **Pass** | Human touches one thing; replayable seals = generational continuity. *Note:* burden minimized only if drift flags (step 5) don't silently pile up — see open Q. |

### Complexity-creep flags
- **C1 — Tiger step 4 bundles five actions** (re-test → commit → seal → close obligation → clear → recompile → trace). Reads as one click but is a fat transaction. Keep it atomic + abort-safe (already stated); watch that it doesn't grow a sixth limb.
- **C2 — "9-element extrusion specs" (GB step 2)** is an unexplained term in an otherwise plain doc. Either define inline or footnote to canon before locking, else it's a future drift seed.
- **C3 — GB owns three durable records** (ledger / roadmap / canon). Three is the ceiling; a fourth = epic, SPLIT it. Honest, but at the edge of "lightweight."
- **C4 — Drift flag (Tiger step 5)** has no owner/disposition path. A flag with no handler is latent debt.

### Open questions — for **GB** to confirm/steer
1. Define **"9-element extrusion specs"** inline (or cite the canon section) so the doc is self-contained?
2. When **book↔code coherence raises a drift flag**, who dispositions it — does GB open a proposal automatically, or does it wait for KM?
3. Is **series_roadmap** strictly a *projection* of the obligation ledger, or a second source of truth? (If the latter, that's a two-writers risk on the inventory.)

### Open questions — for **G** to confirm/steer
1. Confirm G's lane is **principles/review + keyword/trend steers only** (no artifact writes) — i.e., G never enters the Tiger apply path?
2. Should G's **keyword/trend steers** be receipted (obligation entry) like GB/Tiger turns, or stay informal until proven?

---

## 4. KM-1176 Ratification + Final Steers (2026-06-03)

KM accepted the package as **practice (not canon)** and locked these steers:

1. **Keep both workflows light and practical.**
2. **Tiger loop: one human gate (Accept/Apply) — protect it.** Non-negotiable.
3. **GB: strictly proposals + inventory — no direct edits.** Fence holds.
4. **Ship as practice, not canon.** Prove with **1–2 full cycles** (Capture→Apply *and* GB-propose→Tiger-build→KM-ratify) before considering canon.
5. **Address complexity flags lightly:**
   - **C1** — keep Apply **atomic / abort-safe** (no 6th limb).
   - **C2** — define **"9-element"** *only if used* (see footnote below); otherwise drop the term.
   - **C4** — **drift flags have a clear disposition: GB proposes → Tiger surfaces → KM ratifies.** (Resolves the "flag with no handler" debt.)
6. **Open questions:** GB's three → **routed to GB** for response. **G's lane = principles + keyword/trend steers only, receipted when material** (resolves both G questions: G never enters the Tiger apply path; steers are receipted only when material).

> **Footnote — "9-element extrusion spec" (C2):** the per-concept translation packet GB proposes when extruding a book concept into code — *book passage · citation+hash · role/capability · action-classes · constitutional boundary · engine-default vs mechanic · test block (unit+integration) · evidence tier · LGP note.* Used only inside GB's step-2 proposals; if a given proposal doesn't extrude code, the term doesn't apply.

*Status: **ratified as practice** (KM-1176, 2026-06-03), not canon. Prove 1–2 full cycles with receipts before promoting into WORKFLOW 17.5/17.6. GB open questions routed; G lane confirmed (principles + keyword/trend steers, receipted when material).*