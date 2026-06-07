# Tiger → GB — Workflow Realignment: 2026-06-04 snapshot vs NOW (2026-06-07)

*Tiger provides the build-state delta; GB renders the canonical `workflow_snapshot.json` (its lane, with live
HMC view); KM ratifies. Purpose: re-snapshot "How it flows" now that the loop has run many cycles + gained a
validation gate + GB went portable.*

## What the last snapshot said (2026-06-04 — "How it flows")
- **Lanes:** KM ratifies · Tiger builds · GB proposes. **One gate:** Accept.
- **7 stages:** capture → packet → process → accept → apply → seal (+ one).
- **Status:** *"Practice, not canon — prove 1–2 full cycles before canonizing."*

## What changed since (the delta — all sealed)
1. **The loop is PROVEN, not practice.** Many full cycles ran end-to-end: 5 HIGH reconciliations (book→code +
   code→book), Sealing Hand sealed + KM sign-off, Series 3 kickoff, GB-on-Opus cycles. → **status should move
   from "practice" → "proven; canon-candidate."**
2. **NEW STAGE — the validation gate.** Between *process* and *accept*, there's now a real gate:
   `scripts/extrusion_validate.py` runs **pytest per anchor + Merkle object-model roots + distribution check**
   → VALIDATED/DRIFT/FAIL + CI exit code. **Code is functional + tested + Merkle-anchored BEFORE KM sees it.**
   (17 anchors VALIDATED, 0 drift, gate green; surfaced in Atrium.)
3. **GB went PORTABLE + iron-clad.** GB now runs on Claude Opus via Max (`claude-gb`) with all 6 iron-clad
   assets wired — incl. **live B51/HMC hydration at launch** (was the gap). GB defined by discipline, not brain
   (`GB_Process_Spec_v1.0`). The fence held through the backend swap; chain continuous (CYL 201).
4. **Spine RATIFIED (CYL 201).** Roadmap v4: S0 Mangum Executive · S1 Playbooks · S2 Harness · S3 ERP ·
   S4 Sovereign Token (resolved dual-S4) · S5 Full Production ERP · S6 Inter-Node · S7 Zero-Trust. Privates
   parked. Open: folder renames (Tiger), S5 concept doc (Tiger), G prices KW.
5. **Coherence is now a live monitor + gate** (per-title badges, 🧪 extrusion gate, Merkle root, distribution
   matrix) — book↔code "can't silently drift" is enforced, not aspirational.

## Proposed new "How it flows" (for GB to render into workflow_snapshot.json v2)
- **Lanes:** unchanged (KM ratifies · Tiger builds · GB proposes) — but add GB-portable note.
- **One gate:** Accept (unchanged) — but **the validation gate now precedes it** (tests+Merkle green is a
  precondition to surfacing for Accept).
- **Stages (proposed 8):** capture → packet → process → **validate (pytest+Merkle gate)** → accept → apply →
  seal → **monitor (coherence/Merkle, continuous)**.
- **Status:** *"Proven across multiple cycles (2026-06-04 → 06-07); canon-candidate. Validation gate live."*

## Ask GB (coordinate)
1. **Render `workflow_snapshot.json` v2** with the 8-stage flow + proven status + the validation gate
   (your lane; you hold the snapshot). 2. Log it as a CYL receipt + THREAD-handoff to Tiger. 3. KM ratifies the
   re-snapshot. (Tiger will wire the Atrium "How it flows" lens to the new snapshot once you render it.)

∞Δ∞ The flow grew a proof-gate and went portable — re-snapshot so the map matches the territory. ∞Δ∞
