# RCCM — "After Accept, card stays in Diffs Ready (status not moving)"

**Date:** 2026-06-04 · **Owner:** Tiger · **Severity:** High (core review flow) · **Source:** KM voice tests (Hopper feed #23, #32)

## 1. Problem statement (containment)
After the operator clicks **Accept** on a diff card, the card sometimes **stays in "Diffs Ready"** — it doesn't move to Sealed, shows no error, and the button can sit on "applying…". The operator can't tell whether it's working, stuck, or failed.

## 2. Root cause analysis (verified in code, `scripts/atrium_apply.py`)
The apply agent runs **detached** (`Popen → stdout/stderr = DEVNULL`) and can abort in two places **without surfacing anything to the UI**:

- **RC1 — Silent failure (primary).** On a before-text mismatch, `_apply_group` returns not-ok → revert → `return 2`, **and** the proposal is left in the store untouched. The UI keeps polling, finds the proposal still present, and renders the card in "Diffs Ready" indefinitely — indistinguishable from "still applying." No reason is ever shown.
- **RC2 — `pytest` exit-5 false-red.** For code/starter changes the agent re-runs `pytest` and treated `returncode != 0` as red. **Exit code 5 = "no tests collected"** is non-zero, so a valid apply touching a path with no collectible tests aborted (`return 3`) → same silent stuck card.
- **RC3 — No apply status channel.** Unlike the producer (which writes a run-status the UI reads), the apply had **no failure feedback path**, so the frontend could never distinguish stuck-vs-working-vs-failed.

*(Success path was fine — close obligation + clear proposal → card moves to Sealed. The defect was entirely in the failure/abort paths being invisible.)*

## 3. Corrective measures (shipped)
- **CM1 (RC1/RC3):** new `_mark_error(pid, reason)` — on **any** abort the agent now writes `status="apply_failed"` + `apply_error=<reason>` onto the proposal. The card is no longer silent.
- **CM2 (RC2):** the pytest gate now treats **exit 5 as PASS** (`returncode not in (0, 5)`), so "no tests collected" no longer aborts a valid apply.
- **CM3 (UI):** the rich card renders a red **"✗ Apply failed — <reason>"** banner; the kanban Diffs-Ready card shows "✗ apply failed — click to see why"; the popup signature includes the error so an open card refreshes to show it. The operator sees *why* and can Refine or Dismiss.

## 4. Verification
`atrium_apply.py` + `index.html` parse clean; standalone rebuilt. A failed apply now resolves to a visible, explained card instead of a silent stuck one; a valid no-tests apply commits + seals + moves to Sealed.

## 5. Systemic / preventive
- Failure feedback is now a first-class part of the apply loop (parity with the producer's transparency).
- The exit-5 class of false-negative is closed at the gate.
- *Watch-item:* before-text mismatches (RC1's trigger) come from stale proposals; the `apply_error` message tells the operator to Refine/re-process — and the producer dedupe (ATR-15) reduces stale duplicates upstream.

∞Δ∞
