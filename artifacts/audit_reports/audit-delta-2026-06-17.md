# Night-Watch Delta Audit — 2026-06-17 (HEAD 9510a6c vs baseline b561274)
*Token-light delta: ONE Opus 4.8 read-only finder, scope = the 47 code/config files changed since the 2026-06-16 FINAL re-score. Verification only on new findings.*
*Baseline: `audit-report-2026-06-16-FINAL.md` @ b561274 — Health 79/100, 0 CRIT, 4 HIGH (all constraints/CI/dependency cluster).*

## Verdict: the full 4-HIGH constraints/CI cluster is CLOSED. 0 new CRIT/HIGH, 0 regressions, 2 LOW. No Tiger escalation.

The plateau-breaking work landed clean: the dependency/CI tar pit that capped the score at 79 is genuinely fixed (verified against live installed versions), and the large `obligations/ledger.py` refactor + new scout pipeline introduced no new defects.

## New findings (2 LOW)
- **[LOW][code-quality/architecture] pyproject.toml:111-119 + scripts/static_scan.sh:12** — `[tool.ruff]` declares the §5 bar (C901 max-complexity=10 + F/E722/E741) but nothing enforces it: `static_scan.sh` is report-only (`|| true`) and CI has no ruff/vulture step. 19 functions exceed the bar and 38 F-class findings stand (e.g. `ledger.py:294 close`=11, `playbook_loader.py:48 discover_roles`=14, `role_binder.py:165 bind_role`=11). This is the documented "candidates-not-delete" posture — not a CI break — but the declared bar is advisory, not a gate. **FIX:** add a non-blocking ruff job to CI for visibility, or note in the config comment that the bar is reported, not enforced.
- **[LOW][performance/constitutional] scripts/cron/SCOUT_CRONTAB.txt:14** — the nightly line chains `build_book_code_tree.py ; scout_run.py` with `;` not `&&`, so a tree-build failure still runs scout against a stale/partial tree. Both stream to a dated log (not silent) and scout is propose-only, so impact is low. **FIX:** use `&&` so a failed refresh skips the dependent derive, or accept-and-log the decoupling.

### High-risk targets — clean
- **obligations/ledger.py refactor + split-out modules** (projection / _locking / _util / evidence / provenance / roots): extraction-not-abstraction. All new modules pass ruff clean. `principal_id` is stamped on every chain entry (open/approve/close/reopen/attest/veto). Fail-closed guards intact (material→breath-gate, default-deny veto, E0 rejection, AlreadyClosed). No swallowed exceptions.
- **scout_run.py** is genuinely PROPOSE-ONLY: writes only under `artifacts/scout/` + its own `static_baseline.json`; POSTs candidates with `X-Principal-Id: scout`; never edits source/seals or creates obligations. The one `except Exception` in `_post_candidates` PRINTS the error (not silent) and is correctly scoped to a best-effort propose POST.
- **node_api/routes/scout.py**: `@require_principal` + `@require_owner` gated, registered in `server.py`, returns a loud 500 if the runner is missing.

## Regressions
- **None.** The 19 C901 / 38 F static findings are pre-existing, not introduced by this diff. Spot-checked vs baseline: `ledger.py close` 12→11 (improved by the refactor), `gb_meta_context.py` 10→6 errors (improved). The `capabilities/{economics,legacy,research}.py` deletions are clean — no dangling imports in src/scripts/tests, `__init__.py` updated, full suite collects and runs green (only stale `SOURCES.txt` egg-info still names them — build metadata, not code).

## Baseline 4-HIGH constraints/CI cluster — current status
- **HIGH constraints pins (fabricated-green) — FIXED.** `constraints.txt` pins (PyYAML 6.0.3, Flask 3.1.3, cryptography 46.0.7, pytest 9.1.0) all match live installed versions (verified via importlib.metadata in this env). New `tests/test_constraints_lock.py` asserts every pin == installed version with a no-skip hard failure + a CVE-floor test. The verify-before-claim gap is now mechanically enforced.
- **HIGH [portal] empty-extra (defeats lock on Docker/install paths) — FIXED (re-scoped).** `pyproject.toml:48-49` keeps `portal = []`, but flask is now CORE (not portal-gated), so the Docker / `sovereign-install` `.[portal]` path pulls flask+pyyaml under `-c constraints.txt` and gets the real core pins. cryptography/pytest are correctly dev/crypto-assurance-only (not runtime), so constraining them is inert on that path (documented). The baseline gap is closed. `Dockerfile:35` + `sovereign-install.sh:99` both install with `-c constraints.txt`.
- **HIGH CI un-green-able on clean runner — FIXED.** Lock test passes by construction in the canonical `-c constraints.txt` env (pins == resolved); full suite runs green here (0 collection errors). CI also gained a non-gating pip-audit step (`ci.yml:67-73`, continue-on-error).
- **4th HIGH (facet: CI red at pinned-but-uninstalled versions) — FIXED** as part of the same cluster (pins now equal installed/resolved versions).

## Counts
**NEW: 0 CRIT, 0 HIGH, 0 MED, 2 LOW | REGRESSIONS: 0 | FIXED-since-baseline: 4 (full constraints/CI HIGH cluster)**

---
*ONE Opus 4.8 read-only finder (~65k tokens). Scope: 47 changed code/config files, b561274..9510a6c. No new CRITICAL/HIGH → no Tiger thread. Score implication: the cap that held 79 is removed; the next full Opus confirming sweep is the remaining step for the official ~88-90 number.*
