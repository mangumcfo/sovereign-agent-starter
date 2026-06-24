# Delta Audit — 2026-06-24 (GB night watch)

**Baseline:** audit-delta-2026-06-23.md (which builds on audit-report-2026-06-19.md + audit-delta-2026-06-19.md)
**Scope:** code files changed since the 2026-06-23 baseline (commits bab31b4..545a342, 24 commits). Audited code only — JSON/NDJSON/MD artifacts excluded.
**Method:** one read-only Opus finder agent; every finding cross-verified against live code before surfacing; reported only NEW / REGRESSION / FIXED-SINCE-BASELINE vs. baseline. NEW HIGH independently re-verified by the night watch against live `atrium_executor.py` + `scheduler.py`.

## Changed code files audited
- scripts/atrium_executor.py
- scripts/board_findings_archive.py
- scripts/dist_generators/gen_x_thread.py
- scripts/dist_scheduler/scheduler.py
- scripts/outline_from_pipeline.py
- scripts/review_ready_contract.py
- scripts/thread.py
- src/sovereign_agent/node_api/routes/feedback.py
- tests/test_dist_launch_gate.py

---

## NEW FINDINGS

### [HIGH] Launch-bell handler always raises AttributeError → approved live posts fire but obligation never closes (false failure)
- **File:** scripts/atrium_executor.py:134 (`_exec_distribution_launch`)
- **Dimension:** Code quality (correctness) / Constitutional conformance (no silent/false-failure receipts)
- **Status:** NEW
- **Evidence:** Line 134 does `chans = ",".join(sorted((res.get("results") or {}).keys())) or "none"`, but `scheduler.dispatch` returns `results` as a **list** of per-channel dicts (scheduler.py:121, success path :160, and refusal path :127-129) — never a mapping. `.keys()` on a list raises `AttributeError`, swallowed by the broad `except Exception` at atrium_executor.py:129 → records an `apply_close_failed` handshake and `return 1`. Fires on **every** launch:
  - Approved launch: `dispatch` runs its loop and *actually posts live* (scheduler.py:148), then line 134 throws → the obligation is **never closed** and a misleading `apply_close_failed` ("launch dispatch error") handshake is recorded — a real action with a false-failure receipt (inverse of the no-silent-failure discipline the file documents).
  - Refused launch: same throw before the intended `mode != "live"` guard (:136), so that guard and the `except PermissionError` branch (:125) are **unreachable**. (`dispatch` signals refusal by *returning* `{"refused": True}`, never by raising `PermissionError` — so :125 is dead code regardless.) Still fails closed (returns 1), but for the wrong reason.
- **Fix:** Read the channel list from the actual shape: `chans = ",".join(sorted(r.get("channel","?") for r in (res.get("results") or []))) or "none"`. Detect refusal explicitly via `if res.get("refused"):` → `blocked_unapproved` handshake (not via `mode` / `PermissionError`); remove the dead `except PermissionError`. Add a test driving `_exec_distribution_launch` against a stubbed `dispatch` returning the real list-shaped dict for both approved and refused cases (currently untested — tests/test_dist_launch_gate.py exercises `dispatch` only, never the bell handler that consumes it).

### [LOW] Approving principal is hardcoded, not read from the ledger chain
- **File:** scripts/dist_scheduler/scheduler.py:93 (`launch_approval`)
- **Dimension:** Constitutional conformance (principal_id provenance)
- **Status:** NEW
- **Evidence:** `return True, (found.get("approved_by") or "KM-1176"), "approved"`. `found` comes from `lg.open_obligations()` → `projection.replay()`, which sets `approved=True` (projection.py:50) but does **not** populate `approved_by` (only `full_log()` does, projection.py:92). So `found.get("approved_by")` is always `None` and the stamped principal silently falls back to the constant `"KM-1176"` — dispatch provenance (`approved_by` on dispatch_log/channel_state) records a hardcoded principal, not the actual approver from the chain.
- **Fix:** Resolve the real approver via `lg.full_log()` (or the approval event's `approved_by`) for the matching obligation and stamp that. Drop the `or "KM-1176"` fallback; a missing approver on an approved obligation is itself a refusal condition.

---

## REGRESSIONS

None.

---

## FIXED SINCE BASELINE

### [HIGH→FIXED] scheduler.py `--live` now enforces Propose→Approve→Execute with principal stamping
- **File:** scripts/dist_scheduler/scheduler.py:67-93 (`launch_approval`), 122-137 (gate in `dispatch`), 170-175 (loud refusal in `main`); tests/test_dist_launch_gate.py
- **Evidence (live):** `launch_approval(book_id)` loads `ObligationLedger` via `get_ledger_root`, scans `open_obligations()` for `ref == distribution_launch:{book_id}`, refuses unless `approved` — failing **closed** if the ledger is unavailable. `dispatch` calls this before any post when `not dry_run`; on refusal writes `gated` channel_state, logs `live_refused`, returns `{"refused": True}` **without posting**. On approval stamps `approved_by=principal` on every result + channel_state/dispatch_log. `main` surfaces `⛔ LIVE POST REFUSED` / exit 2. Backed by meaningful tests (refused-when-unapproved, permitted+stamped, dry-run-never-posts, fail-closed-without-ledger). Closes baseline audit-delta-2026-06-23 HIGH.

### [HIGH→FIXED] thread.py fork-race (TOCTOU on the hash chain) now locked
- **File:** scripts/thread.py:58-80 (`append`)
- **Evidence (live):** the read-prev → compute-hash → append critical section now runs under an exclusive `fcntl.flock(lf, LOCK_EX)` on `NDJSON.with_name(NDJSON.name + ".lock")` (the same lock the node writer uses), released in `finally`. A CLI append racing a node `/relay` append can no longer both read the same `prev` and fork genesis. Closes baseline 2026-06-19 HIGH #1.

### [HIGH→FIXED] Pillow now a declared optional dependency
- **File:** pyproject.toml:64-71 (`tooling` extra: `Pillow>=10.0`)
- **Evidence (live):** the cover gate (review_ready_contract.py) + carousel generator imports are satisfied by `pip install .[tooling]`; the Pillow import is unwrapped so a missing dep crashes loudly (no false PASS). Closes baseline 2026-06-19 HIGH #3.

---

## CARRY (baseline finding still open — not re-counted)

- **[MEDIUM] `pytesseract` (+ `tesseract` binary) still undeclared.** review_ready_contract.py imports `pytesseract`; the `tooling` extra declares only Pillow. Bounded (import wrapped → fails gate RED, never a silent pass). Unchanged from baseline audit-delta-2026-06-23, so not re-counted. Fix: add `pytesseract>=0.3` to the `tooling` extra + `tesseract-ocr` to the Dockerfile apt line.

---

## SUMMARY

| Severity | NEW | REGRESSION | FIXED |
|----------|-----|-----------|-------|
| CRITICAL | 0 | 0 | 0 |
| HIGH | 1 | 0 | 3 |
| MEDIUM | 0 | 0 | 0 |
| LOW | 1 | 0 | 0 |
| **Total** | **2** | **0** | **3** |

**Verdict:** Baseline constitutional HIGH genuinely fixed — `scheduler.py --live` enforces an APPROVED `distribution_launch` obligation, fails closed without a ledger, stamps the approving principal, and is test-backed. thread.py fork-race and the Pillow extra also fixed. One NEW HIGH: the launch *bell* (`atrium_executor._exec_distribution_launch:134`) calls `.keys()` on the list-shaped `dispatch` result → throws on every launch; approved posts fire live but the obligation never closes and a false `apply_close_failed` handshake is recorded — threaded to Tiger. One NEW LOW: stamped approver hardcoded `"KM-1176"`. pytesseract remains undeclared (unchanged baseline MEDIUM).
